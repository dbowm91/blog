import smtplib
import time
import uuid
from datetime import timedelta, datetime
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
    g,
)
from sqlalchemy import func, or_, select, text, case
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
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
    FTS_RESULT_LIMIT,
)

from app.email import send_confirmation
from app.csrf import validate_csrf_token
from app.utils import xml_escape, is_valid_email, utc_now
from app.cache import _get_tag_counts
from app.search import search as _fts_search, get_search_snippets

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


HARD_RELATED_POST_LIMIT = 20


def _get_cached_tags_and_counts():
    """Get tags and tag counts with request-level caching via Flask g."""
    if not hasattr(g, "_cached_tags"):
        g._cached_tags = (
            db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
        )
    if not hasattr(g, "_cached_tag_counts"):
        g._cached_tag_counts = _get_tag_counts()
    return g._cached_tags, g._cached_tag_counts


def _get_related_posts(post):
    if not post.tags:
        return []
    tag_ids = [t.id for t in post.tags]
    limit = min(RELATED_POSTS_COUNT, HARD_RELATED_POST_LIMIT)
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
            .limit(limit)
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
    tags, tag_counts = _get_cached_tags_and_counts()
    return render_template(
        "index.html",
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
    )


ARCHIVE_PER_PAGE = 200


@public.route("/archive")
def archive() -> Response:
    """Chronological archive of all published posts grouped by year/month.

    Query params:
        year: Filter by specific year (optional)
        cursor: Cursor for pagination (created_at ISO string, optional)
        direction: 'next' or 'prev' for cursor direction (default 'next')
    """
    year_filter = request.args.get("year", type=int)
    cursor = request.args.get("cursor", type=str)
    direction = request.args.get("direction", "next", type=str)

    years_query = (
        select(func.extract("year", Post.created_at).label("year"))
        .filter(Post.published == True)
        .distinct()
        .order_by(func.extract("year", Post.created_at).desc())
    )
    available_years = [int(row.year) for row in db.session.execute(years_query).fetchall()]

    if year_filter and year_filter not in available_years:
        year_filter = None

    cursor_dt = None
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            cursor = None

    posts_query = (
        select(Post)
        .options(joinedload(Post.tags))
        .filter(Post.published == True)
    )

    if year_filter:
        year_start = datetime(year_filter, 1, 1)
        year_end = datetime(year_filter + 1, 1, 1)
        if direction == "prev" and cursor_dt:
            posts_query = posts_query.filter(Post.created_at > cursor_dt, Post.created_at < year_end)
        elif direction == "prev":
            posts_query = posts_query.filter(Post.created_at >= year_start, Post.created_at < year_end)
        elif cursor_dt:
            posts_query = posts_query.filter(Post.created_at < cursor_dt, Post.created_at >= year_start)
        else:
            posts_query = posts_query.filter(Post.created_at >= year_start, Post.created_at < year_end)
    elif cursor_dt:
        posts_query = posts_query.filter(
            Post.created_at < cursor_dt if direction == "next" else Post.created_at > cursor_dt
        )

    posts_query = posts_query.order_by(Post.created_at.desc())

    if direction == "next":
        posts_query = posts_query.limit(ARCHIVE_PER_PAGE)
    else:
        posts_query = posts_query.limit(ARCHIVE_PER_PAGE)

    posts = list(db.session.execute(posts_query).scalars().unique().all())

    archive_data: dict[int, dict[int, list[Post]]] = {}
    for p in posts:
        p_year = p.created_at.year
        p_month = p.created_at.month
        if year_filter and p_year != year_filter:
            continue
        if p_year not in archive_data:
            archive_data[p_year] = {}
        if p_month not in archive_data[p_year]:
            archive_data[p_year][p_month] = []
        archive_data[p_year][p_month].append(p)

    tags, tag_counts = _get_cached_tags_and_counts()

    has_next = len(posts) == ARCHIVE_PER_PAGE and (not year_filter or (year_filter and posts and posts[-1].created_at.year >= year_filter))
    has_prev = cursor is not None and direction == "next"
    next_cursor = posts[-1].created_at.isoformat() if posts and has_next else None
    prev_cursor = posts[0].created_at.isoformat() if posts and has_prev else None

    pagination_info = {
        "has_next": has_next,
        "has_prev": has_prev,
        "next_cursor": next_cursor,
        "prev_cursor": prev_cursor,
        "current_year": year_filter,
        "available_years": available_years,
    }

    return render_template(
        "archive.html",
        archive_data=archive_data,
        tags=tags,
        tag_counts=tag_counts,
        pagination=pagination_info,
    )


@public.route("/page/<slug>")
def page(slug) -> Response:
    """Static content page."""
    from app.models import Page

    page = db.session.execute(
        select(Page).filter_by(slug=slug, published=True)
    ).scalar_one_or_none()
    if not page:
        abort(404)
    return render_template(
        "page.html",
        page=page,
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
        if post.id in viewed:
            viewed.remove(post.id)
        viewed.insert(0, post.id)
        if len(viewed) > MAX_VIEWED_POSTS:
            viewed = viewed[:MAX_VIEWED_POSTS]
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
    tags, tag_counts = _get_cached_tags_and_counts()
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

    tags, tag_counts = _get_cached_tags_and_counts()

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
            .order_by(Post.created_at.desc())
            .limit(FTS_RESULT_LIMIT),
            page=page,
            per_page=POSTS_PER_PAGE,
            error_out=False,
        )

    snippets = get_search_snippets(list(pagination.items), query)
    return render_template(
        "search.html",
        query=query,
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
        search_snippets=snippets,
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


ALLOWED_SHARE_PLATFORMS = {"twitter", "facebook", "linkedin", "reddit", "hackernews", "link"}


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
    if platform not in ALLOWED_SHARE_PLATFORMS:
        return jsonify({"error": "invalid platform"}), 400

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
        csrf_token: CSRF token

    Response:
        Redirects with flash message. Sends confirmation email.
        Re-subscribes previously unsubscribed users.
    """
    validate_csrf_token()

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
            flash("You're already subscribed!", "info")
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
    """Serve robots.txt with sitemap URL and AI crawler blocking."""
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /static/uploads/

User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: DuckDuckBot
Disallow: /

User-agent: ia_aggregator
Disallow: /

User-agent: ImagesiftBot
Disallow: /

User-agent: img2dataset
Disallow: /

User-agent: Kraken
Disallow: /

User-agent: Orbisk
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Pileager
Disallow: /

User-agent: Seek
Disallow: /

User-agent: Sitebot
Disallow: /

User-agent: TikTokBot
Disallow: /

User-agent: Turpom
Disallow: /

User-agent: Vercel/Analytics
Disallow: /

User-agent: YouBot
Disallow: /

Sitemap: {BASE_URL}/sitemap.xml
"""
    return Response(content, mimetype="text/plain")


def _generate_sitemap():
    from app.models import Page

    yield '<?xml version="1.0" encoding="UTF-8"?>\n'
    yield '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # Homepage
    yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""
    # Static pages
    for pg in (
        db.session.execute(
            select(Page).filter_by(published=True).order_by(Page.updated_at.desc())
        )
        .scalars()
        .yield_per(100)
    ):
        lastmod = pg.updated_at.strftime("%Y-%m-%d") if pg.updated_at else ""
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/page/{xml_escape(pg.slug)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
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
    """Stream sitemap XML for all published posts, pages, and tags."""
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
    from app.scheduler import get_scheduler_health
    from app.config import SMTP_HOST

    checks = {}
    status_code = 200

    # Database check
    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except (OperationalError, ProgrammingError):
        checks["database"] = "error"
        status_code = 503

    # Scheduler check (only relevant if SMTP configured)
    if SMTP_HOST:
        health = get_scheduler_health()
        checks["scheduler"] = health["status"]
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
    except (OperationalError, ProgrammingError):
        checks["search"] = "error"

    # Determine overall status - exclude None values (like last_newsletter_send when never sent)
    overall = (
        "ok"
        if all(
            v in ("ok", "running", "disabled") for v in checks.values() if v is not None
        )
        else "degraded"
    )

    return jsonify(
        {
            "status": overall,
            "checks": checks,
            "timestamp": utc_now().isoformat(),
        }
    ), status_code
