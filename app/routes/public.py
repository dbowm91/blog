import smtplib
import time
import uuid
from datetime import timedelta
from urllib.parse import urlparse, urlunparse

from flask import Blueprint, render_template, request, redirect, jsonify, flash, session, Response, url_for
from sqlalchemy import func, or_, text
from sqlalchemy.orm import joinedload
import logging

from app.extensions import db
from app.models import Post, Tag, Subscriber, PageView, ShareEvent
from app.config import POSTS_PER_PAGE, BASE_URL, RELATED_POSTS_COUNT, MAX_VIEWED_POSTS, CONFIRMATION_EXPIRY_HOURS

from app.email import send_confirmation
from app.utils import xml_escape, is_valid_email, utc_now
from app.cache import invalidate_tag_cache, _get_tag_counts

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
        Post.query.options(joinedload(Post.tags))
        .filter(
            Post.published == True,
            Post.id != post.id,
            Post.tags.any(Tag.id.in_(tag_ids)),
        )
        .order_by(Post.created_at.desc())
        .limit(RELATED_POSTS_COUNT)
        .all()
    )
    return related


@public.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Post.query.options(joinedload(Post.tags))
        .filter_by(published=True)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    )
    tags = Tag.query.order_by(Tag.name).all()
    tag_counts = _get_tag_counts()
    return render_template(
        "index.html",
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
    )


@public.route("/post/<slug>")
def post(slug):
    post = Post.query.filter_by(slug=slug, published=True).first_or_404()

    viewed = session.get("viewed_posts", [])
    if post.id not in viewed:
        referrer = None
        if request.referrer:
            parsed = urlparse(request.referrer)
            sanitized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
            referrer = sanitized[:512] if sanitized else None
        pv = PageView(
            post_id=post.id,
            referrer=referrer,
        )
        db.session.add(pv)
        db.session.commit()
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
    )


@public.route("/tag/<slug>")
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    pagination = (
        Post.query.options(joinedload(Post.tags))
        .filter(Post.published == True, Post.tags.any(Tag.id == tag.id))
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    )
    total_posts = pagination.total
    tags = Tag.query.order_by(Tag.name).all()
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
def search():
    query = request.args.get("q", "", type=str)[:200].strip()
    page = request.args.get("page", 1, type=int)

    if not query:
        return redirect("/")

    tags = Tag.query.order_by(Tag.name).all()
    tag_counts = _get_tag_counts()

    post_ids = _fts_search(query)
    if post_ids:
        id_list = ",".join(str(i) for i in post_ids)
        pagination = (
            Post.query.options(joinedload(Post.tags))
            .filter(Post.published == True, Post.id.in_(post_ids))
            .order_by(db.text(f"CASE posts.id { ' '.join(f'WHEN {i} THEN {n}' for n, i in enumerate(post_ids)) } END"))
            .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
        )
    else:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_term = f"%{escaped}%"
        pagination = (
            Post.query.options(joinedload(Post.tags))
            .filter(
                Post.published == True,
                or_(
                    Post.title.ilike(search_term, escape="\\"),
                    Post.body.ilike(search_term, escape="\\"),
                    Post.summary.ilike(search_term, escape="\\"),
                )
            )
            .order_by(Post.created_at.desc())
            .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
        )

    return render_template(
        "search.html",
        query=query,
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
    )


def _fts_search(query: str):
    """Search using FTS5. Returns list of post IDs or empty list if unavailable."""
    try:
        check = db.session.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
        )).fetchone()
        if not check:
            return []

        fts_query = " OR ".join(f'"{w}"' for w in query.split() if w)
        if not fts_query:
            return []
        result = db.session.execute(text(
            "SELECT rowid FROM posts_fts WHERE posts_fts MATCH :q ORDER BY rank LIMIT 100"
        ), {"q": fts_query}).fetchall()
        return [row[0] for row in result]
    except Exception:
        return []


@public.route("/s/<code>")
def short_url_redirect(code):
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
    db.session.commit()

    return redirect(f"/post/{post.slug}")


@public.route("/api/track-share", methods=["POST"])
def track_share():
    data = request.get_json(silent=True)
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
    db.session.commit()
    return jsonify({"ok": True})


def _try_send_confirmation(subscriber):
    """Send confirmation email. Returns True on success, False on SMTP failure."""
    try:
        send_confirmation(subscriber)
        return True
    except (smtplib.SMTPException, ConnectionError, OSError):
        logger.exception("Failed to send confirmation email to %s", subscriber.email)
        return False


@public.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()[:256]
    if not is_valid_email(email):
        flash("Please enter a valid email address.", "error")
        return redirect(_safe_redirect_url())

    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if existing.unsubscribed_at:
            existing.unsubscribed_at = None
            existing.confirmed = False
            existing.token = uuid.uuid4().hex
            existing.expires_at = utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)
            db.session.commit()
            if _try_send_confirmation(existing):
                flash("Check your inbox to confirm your subscription.", "success")
            else:
                flash("Subscribed, but confirmation email could not be sent.", "error")
        elif existing.confirmed:
            logger.info("Already-subscribed user %s attempted to resubscribe", email)
            flash("Check your inbox to confirm your subscription.", "success")
        else:
            existing.token = uuid.uuid4().hex
            existing.expires_at = utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)
            db.session.commit()
            if _try_send_confirmation(existing):
                flash("Check your inbox to confirm your subscription.", "success")
            else:
                flash("Subscribed, but confirmation email could not be sent.", "error")
        return redirect(_safe_redirect_url())

    sub = Subscriber(email=email, expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS))
    db.session.add(sub)
    db.session.commit()

    if _try_send_confirmation(sub):
        flash("Check your inbox to confirm your subscription.", "success")
    else:
        flash("Subscribed, but confirmation email could not be sent.", "error")

    return redirect(_safe_redirect_url())


@public.route("/confirm/<token>")
def confirm(token):
    sub = Subscriber.query.filter_by(token=token).first()
    time.sleep(0.1)  # Always sleep for constant time to prevent timing attack
    if not sub:
        logger.warning("Confirm enumeration attempt with invalid token from %s", request.remote_addr)
        flash("Subscription confirmed! You'll receive our newsletter.", "success")
        return redirect("/")
    if sub.expires_at and sub.expires_at < utc_now():
        # Confirmation window expired — remove the subscriber
        db.session.delete(sub)
        db.session.commit()
        logger.info("Removed expired unconfirmed subscriber: %s", sub.email)
        flash("This confirmation link has expired. Please subscribe again.", "warning")
        return redirect("/")
    sub.confirmed = True
    db.session.commit()
    flash("Subscription confirmed! You'll receive our newsletter.", "success")
    return redirect("/")


@public.route("/unsubscribe/<token>")
def unsubscribe(token):
    sub = Subscriber.query.filter_by(token=token).first()
    time.sleep(0.1)  # Always sleep for constant time to prevent timing attack
    if not sub:
        logger.warning("Unsubscribe enumeration attempt with invalid token from %s", request.remote_addr)
        flash("You have been unsubscribed.", "success")
        return redirect("/")
    # Soft delete: set unsubscribed_at and mark unconfirmed
    sub.unsubscribed_at = utc_now()
    sub.confirmed = False
    db.session.commit()
    flash("You have been unsubscribed.", "success")
    return redirect("/")


@public.route("/robots.txt")
def robots_txt():
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
    for post in Post.query.filter_by(published=True).order_by(Post.updated_at.desc()).yield_per(100):
        lastmod = post.updated_at.strftime("%Y-%m-%d") if post.updated_at else ""
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/post/{xml_escape(post.slug)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n"""
    # Tags
    for tag in Tag.query.yield_per(100):
        yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/tag/{xml_escape(tag.slug)}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>\n"""
    yield '</urlset>\n'


@public.route("/sitemap.xml")
def sitemap_xml():
    return Response(_generate_sitemap(), mimetype="application/xml")


@public.route("/favicon.ico")
def favicon():
    return Response(status=302, headers={"Location": url_for("static", filename="img/favicon.svg")})


@public.route("/health")
def health_check():
    """Health check endpoint for monitoring."""
    from app.scheduler import get_scheduler_status
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return jsonify({
        "status": "ok" if db_status == "connected" else "error",
        "database": db_status,
        "scheduler": "running" if get_scheduler_status() else "stopped",
        "timestamp": utc_now().isoformat(),
    })
