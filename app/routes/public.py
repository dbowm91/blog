import smtplib
import time
import uuid
from datetime import timedelta
from urllib.parse import urlparse, urlunparse

from flask import (
    Blueprint,
    abort,
    render_template,
    request,
    redirect,
    jsonify,
    flash,
    session,
    Response,
    url_for,
)
from sqlalchemy import func, or_, select, text, case
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import joinedload
import logging

from app.extensions import db
from app.models import Post, Tag, Subscriber, PageView, ShareEvent
from app.config import (
    POSTS_PER_PAGE,
    BASE_URL,
    RELATED_POSTS_COUNT,
    MAX_VIEWED_POSTS,
    CONFIRMATION_EXPIRY_HOURS,
    TOKEN_ENUMERATION_DELAY,
)

from app.email import send_confirmation
from app.utils import xml_escape, is_valid_email, utc_now
from app.cache import _get_tag_counts
from app.search import search as _fts_search

logger = logging.getLogger(__name__)

public = Blueprint("public", __name__)


def _safe_redirect_url():
    """Return a safe redirect URL, preventing open redirects via spoofed Referer header."""
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        if parsed.netloc == "" or parsed.netloc == request.host:
            return referrer
    return url_for("public.index")


def _get_related_posts(post):
    if not post.tags:
        return []
    tag_ids = [t.id for t in post.tags]
    related = (
        db.session.execute(
            select(Post)
            .options(joinedload(Post.tags))
            .filter(
                Post.published == True,
                Post.id != post.id,
                Post.tags.any(Tag.id.in_(tag_ids)),
            )
            .order_by(Post.created_at.desc())
            .limit(RELATED_POSTS_COUNT)
        )
        .unique()
        .scalars()
        .all()
    )
    return related


@public.route("/")
def index() -> Response:
    """Paginated list of published posts with tag sidebar."""
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        select(Post)
        .options(joinedload(Post.tags))
        .filter_by(published=True)
        .order_by(Post.created_at.desc()),
        page=page,
        per_page=POSTS_PER_PAGE,
        error_out=False,
    )
    tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    tag_counts = _get_tag_counts()
    return render_template(
        "index.html",
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
    )


@public.route("/post/<slug>")
def post(slug) -> Response:
    """Single post page with related posts and share tracking."""
    post = db.session.execute(
        select(Post).filter_by(slug=slug, published=True)
    ).scalar_one_or_none()
    if not post:
        abort(404)

    viewed = session.get("viewed_posts", [])
    if post.id not in viewed:
        referrer = None
        if request.referrer:
            parsed = urlparse(request.referrer)
            sanitized = urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
            )
            referrer = sanitized[:512] if sanitized else None
        pv = PageView(
            post_id=post.id,
            referrer=referrer,
        )
        db.session.add(pv)
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
        viewed.append(post.id)
        if len(viewed) > MAX_VIEWED_POSTS:
            viewed = viewed[-MAX_VIEWED_POSTS:]
        session["viewed_posts"] = viewed

    related = _get_related_posts(post)
    short_code = post.short_code()
    share_url = f"{BASE_URL}/s/{short_code}"

    return render_template(
        "post.html",
        post=post,
        related=related,
        share_url=share_url,
        short_code=short_code,
        show_full_share=True,
    )


@public.route("/tag/<slug>")
def tag(slug) -> Response:
    """Posts filtered by tag with pagination."""
    tag = db.session.execute(select(Tag).filter_by(slug=slug)).scalar_one_or_none()
    if not tag:
        abort(404)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        select(Post)
        .options(joinedload(Post.tags))
        .filter(Post.published == True, Post.tags.any(Tag.id == tag.id))
        .order_by(Post.created_at.desc()),
        page=page,
        per_page=POSTS_PER_PAGE,
        error_out=False,
    )
    total_posts = pagination.total
    tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    tag_counts = _get_tag_counts()
    return render_template(
        "tag.html",
        tag=tag,
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
        total_posts=total_posts,
    )


@public.route("/search")
def search() -> Response:
    """Full-text search for published posts.

    Query params:
        q: Search query (max 200 chars, trimmed)
        page: Page number (default 1)

    Response:
        Renders search results template with pagination.
        Falls back to LIKE matching if FTS5 unavailable.
    """
    query = request.args.get("q", "", type=str)[:200].strip()
    page = request.args.get("page", 1, type=int)

    if not query:
        return redirect("/")

    tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    tag_counts = _get_tag_counts()

    post_results = _fts_search(query)
    if post_results:
        if not all(isinstance(r, tuple) and len(r) == 2 for r in post_results):
            logging.warning(f"FTS returned invalid results: {post_results}")
            post_results = []
        post_ids = [pid for pid, _ in post_results]
        pagination = db.paginate(
            select(Post)
            .options(joinedload(Post.tags))
            .filter(Post.published == True, Post.id.in_(post_ids))
            .order_by(case({pid: rank for pid, rank in post_results}, value=Post.id)),
            page=page,
            per_page=POSTS_PER_PAGE,
            error_out=False,
        )
    else:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        pagination = db.paginate(
            select(Post)
            .options(joinedload(Post.tags))
            .filter(
                Post.published == True,
                or_(
                    Post.title.ilike(search_term, escape="\\"),
                    Post.body.ilike(search_term, escape="\\"),
                    Post.summary.ilike(search_term, escape="\\"),
                ),
            )
            .order_by(Post.created_at.desc()),
            page=page,
            per_page=POSTS_PER_PAGE,
            error_out=False,
        )

    return render_template(
        "search.html",
        query=query,
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
    )


@public.route("/s/<code>")
def short_url_redirect(code) -> Response:
    """Redirect short URL (base62-encoded post ID) to canonical post URL."""
    from app.base62 import decode

    try:
        post_id = decode(code)
    except (ValueError, KeyError):
        return redirect("/")
    post = db.session.get(Post, post_id)
    if not post or not post.published:
        return redirect("/")

    event = ShareEvent(post_id=post.id, platform="link")
    db.session.add(event)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()

    return redirect(f"/post/{post.slug}")


@public.route("/api/track-share", methods=["POST"])
def track_share() -> Response:
    """Track social share events.

    Request body (JSON):
        {"post_id": int, "platform": str}

    Response:
        200: {"ok": True}
        400: {"error": "invalid"}
        404: {"error": "not found"}
    """
    data = request.get_json(silent=True)
    if not data:
        data = {
            "post_id": request.form.get("post_id"),
            "platform": request.form.get("platform"),
        }
    if not data or "post_id" not in data or "platform" not in data:
        return jsonify({"error": "invalid"}), 400

    try:
        post_id = int(data["post_id"])
    except (ValueError, TypeError):
        return jsonify({"error": "invalid"}), 400

    platform = str(data["platform"])[:32]

    post = db.session.get(Post, post_id)
    if not post or not post.published:
        return jsonify({"error": "not found"}), 404

    event = ShareEvent(post_id=post.id, platform=platform)
    db.session.add(event)
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        return jsonify({"error": "database error"}), 500
    return jsonify({"ok": True})


def _try_send_confirmation(subscriber):
    """Send confirmation email. Returns True on success, False on SMTP failure."""
    try:
        send_confirmation(subscriber)
        return True
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send confirmation email to %s", subscriber.email)
        return False


def _reset_subscriber_token(subscriber):
    """Reset subscriber token and expiry for new confirmation."""
    subscriber.token = uuid.uuid4().hex
    subscriber.expires_at = utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)


def _send_or_flash_confirmation(subscriber, skip_conflict=False):
    """Send confirmation and flash appropriate message. Returns redirect target."""
    if _try_send_confirmation(subscriber):
        flash("Check your inbox to confirm your subscription.", "success")
    else:
        flash("Subscribed, but confirmation email could not be sent.", "error")
    return redirect(_safe_redirect_url())


@public.route("/subscribe", methods=["POST"])
def subscribe() -> Response:
    """Subscribe to the newsletter.

    Form params:
        email: Subscriber email address

    Response:
        Redirects with flash message. Sends confirmation email.
        Re-subscribes previously unsubscribed users.
    """
    email = request.form.get("email", "").strip().lower()[:256]
    if not is_valid_email(email):
        flash("Please enter a valid email address.", "error")
        return redirect(_safe_redirect_url())

    existing = db.session.execute(
        select(Subscriber).filter_by(email=email)
    ).scalar_one_or_none()
    if existing:
        if existing.unsubscribed_at:
            existing.unsubscribed_at = None
            existing.confirmed = False
            _reset_subscriber_token(existing)
            db.session.commit()
            return _send_or_flash_confirmation(existing)
        elif existing.confirmed:
            logger.info("Already-subscribed user %s attempted to resubscribe", email)
            flash("Check your inbox to confirm your subscription.", "success")
            return redirect(_safe_redirect_url())
        else:
            _reset_subscriber_token(existing)
            db.session.commit()
            return _send_or_flash_confirmation(existing)

    sub = Subscriber(
        email=email, expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)
    )
    db.session.add(sub)
    try:
        db.session.commit()
        return _send_or_flash_confirmation(sub)
    except (IntegrityError, OperationalError):
        db.session.rollback()
        existing = db.session.execute(
            select(Subscriber).filter_by(email=email)
        ).scalar_one_or_none()
        if not existing:
            flash("Please enter a valid email address.", "error")
            return redirect(_safe_redirect_url())
        if existing.confirmed:
            flash("Check your inbox to confirm your subscription.", "success")
            return redirect(_safe_redirect_url())
        if existing.expires_at and existing.expires_at < utc_now():
            db.session.delete(existing)
            db.session.commit()
            sub = Subscriber(
                email=email,
                expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS),
            )
            db.session.add(sub)
            db.session.commit()
            return _send_or_flash_confirmation(sub)
        _reset_subscriber_token(existing)
        db.session.commit()
        return _send_or_flash_confirmation(existing)


@public.route("/confirm/<token>")
def confirm(token) -> Response:
    """Confirm newsletter subscription via token.

    Path params:
        token: UUID hex token from confirmation email

    Security:
        Uses constant-time delay to prevent token enumeration.
        Invalid tokens return success (not 404).
    """
    time.sleep(TOKEN_ENUMERATION_DELAY)
    sub = db.session.execute(
        select(Subscriber).filter_by(token=token)
    ).scalar_one_or_none()
    if not sub:
        logger.warning(
            "Confirm enumeration attempt with invalid token from %s",
            request.remote_addr,
        )
        flash("Subscription confirmed! You'll receive our newsletter.", "success")
        return redirect("/")
    if sub.expires_at and sub.expires_at < utc_now():
        try:
            db.session.delete(sub)
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
        logger.info("Removed expired unconfirmed subscriber: %s", sub.email)
        flash("This confirmation link has expired. Please subscribe again.", "warning")
        return redirect("/")
    if sub.confirmed:
        flash("Already confirmed.", "info")
        return redirect("/")
    sub.confirmed = True
    db.session.commit()
    flash("Subscription confirmed! You'll receive our newsletter.", "success")
    return redirect("/")


@public.route("/unsubscribe/<token>")
def unsubscribe(token) -> Response:
    """Unsubscribe from the newsletter via token.

    Path params:
        token: UUID hex token from email

    Security:
        Uses constant-time delay to prevent token enumeration.
        Invalid tokens return success (not 404).
    """
    time.sleep(TOKEN_ENUMERATION_DELAY)
    sub = db.session.execute(
        select(Subscriber).filter_by(token=token)
    ).scalar_one_or_none()
    if not sub:
        logger.warning(
            "Unsubscribe enumeration attempt with invalid token from %s",
            request.remote_addr,
        )
        flash("You have been unsubscribed.", "success")
        return redirect("/")
    # Soft delete: set unsubscribed_at and mark unconfirmed
    sub_email = sub.email
    sub.unsubscribed_at = utc_now()
    sub.confirmed = False
    db.session.commit()
    logger.info("Unsubscribed: email=%s", sub_email)
    flash("You have been unsubscribed.", "success")
    return redirect("/")


@public.route("/robots.txt")
def robots_txt() -> Response:
    """Serve robots.txt with sitemap URL."""
    content = f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n"
    return Response(content, mimetype="text/plain")


def _generate_sitemap():
    yield '<?xml version="1.0" encoding="UTF-8"?>\n'
    yield '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # Homepage
    yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""
    # Posts — yield one at a time to avoid loading all into memory
    for post in (
        db.session.execute(
            select(Post).filter_by(published=True).order_by(Post.updated_at.desc())
        )
        .scalars()
        .yield_per(100)
    ):
        lastmod = post.updated_at.strftime("%Y-%m-%d") if post.updated_at else ""
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/post/{xml_escape(post.slug)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n"""
    # Tags
    for tag in db.session.execute(select(Tag)).scalars().yield_per(100):
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/tag/{xml_escape(tag.slug)}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>\n"""
    yield "</urlset>\n"


@public.route("/sitemap.xml")
def sitemap_xml() -> Response:
    """Stream sitemap XML for all published posts and tags."""
    return Response(_generate_sitemap(), mimetype="application/xml")


@public.route("/favicon.ico")
def favicon() -> Response:
    """Redirect to SVG favicon."""
    return Response(
        status=302, headers={"Location": url_for("static", filename="img/favicon.svg")}
    )


@public.route("/health")
def health_check() -> Response:
    """Health check endpoint for monitoring.

    Response:
        200: All services healthy
        503: One or more services degraded
    """
    import sys
    from app.scheduler import get_scheduler_status
    from app.config import SMTP_HOST

    checks = {}
    status_code = 200

    # Database check
    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        status_code = 503

    # Scheduler check (only relevant if SMTP configured)
    if SMTP_HOST:
        checks["scheduler"] = "running" if get_scheduler_status() else "stopped"
    else:
        checks["scheduler"] = "disabled"

    # FTS check
    try:
        has_fts = db.session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
            )
        ).fetchone()
        checks["search"] = "ok" if has_fts else "unavailable"
    except Exception:
        checks["search"] = "error"

    overall = (
        "ok"
        if all(v in ("ok", "running", "disabled") for v in checks.values())
        else "degraded"
    )

    pool = db.engine.pool
    checks["pool"] = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }

    return jsonify(
        {
            "status": overall,
            "version": sys.version.split()[0],
            "checks": checks,
            "timestamp": utc_now().isoformat(),
        }
    ), status_code
