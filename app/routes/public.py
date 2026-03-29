import smtplib
import uuid
from datetime import timedelta
import threading

from flask import Blueprint, render_template, request, redirect, jsonify, flash, session, Response, url_for
from sqlalchemy import func, or_, text
from sqlalchemy.orm import joinedload
import logging
import time as _time

from app.extensions import db
from app.models import Post, Tag, Subscriber, PageView, ShareEvent, post_tags
from app.config import POSTS_PER_PAGE, BASE_URL, RELATED_POSTS_COUNT, MAX_VIEWED_POSTS, CONFIRMATION_EXPIRY_HOURS
from app.rate_limit import api_rate_limit
from app.email import send_confirmation
from app.utils import xml_escape, is_valid_email, utc_now

logger = logging.getLogger(__name__)

public = Blueprint("public", __name__)

_TAG_COUNTS_CACHE = {"data": None, "timestamp": 0}
_TAG_COUNTS_TTL = 60
_TAG_CACHE_LOCK = threading.Lock()


def invalidate_tag_cache():
    """Invalidate the tag counts cache."""
    with _TAG_CACHE_LOCK:
        _TAG_COUNTS_CACHE["data"] = None
        _TAG_COUNTS_CACHE["timestamp"] = 0


def _get_tag_counts():
    with _TAG_CACHE_LOCK:
        now = _time.monotonic()
        if _TAG_COUNTS_CACHE["data"] is not None and (now - _TAG_COUNTS_CACHE["timestamp"]) < _TAG_COUNTS_TTL:
            return _TAG_COUNTS_CACHE["data"].copy()
        counts = (
            db.session.query(post_tags.c.tag_id, func.count(post_tags.c.post_id))
            .join(Post, Post.id == post_tags.c.post_id)
            .filter(Post.published == True)
            .group_by(post_tags.c.tag_id)
            .all()
        )
        result = {row[0]: row[1] for row in counts}
        _TAG_COUNTS_CACHE["data"] = result
        _TAG_COUNTS_CACHE["timestamp"] = now
        return result


def _get_related_posts(post):
    if not post.tags:
        return []
    tag_ids = [t.id for t in post.tags]
    related = (
        Post.query.filter(
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
        pv = PageView(
            post_id=post.id,
            referrer=request.referrer[:512] if request.referrer else None
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
    
    search_term = f"%{query}%"
    pagination = (
        Post.query.options(joinedload(Post.tags))
        .filter(
            Post.published == True,
            or_(
                Post.title.ilike(search_term),
                Post.body.ilike(search_term),
                Post.summary.ilike(search_term),
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
    )


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
    limited = api_rate_limit()
    if limited:
        return limited

    data = request.get_json(silent=True)
    if not data or "post_id" not in data or "platform" not in data:
        return jsonify({"error": "invalid"}), 400

    post = db.session.get(Post, data["post_id"])
    if not post or not post.published:
        return jsonify({"error": "not found"}), 404

    event = ShareEvent(post_id=post.id, platform=data["platform"])
    db.session.add(event)
    db.session.commit()
    return jsonify({"ok": True})


@public.route("/subscribe", methods=["POST"])
def subscribe():
    limited = api_rate_limit(max_requests=10, window=300)
    if limited:
        return limited

    email = request.form.get("email", "").strip().lower()
    if not is_valid_email(email):
        flash("Please enter a valid email address.", "error")
        return redirect(request.referrer or "/")

    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if existing.unsubscribed_at:
            # Re-activate previously unsubscribed user
            existing.unsubscribed_at = None
            existing.confirmed = False
            existing.token = uuid.uuid4().hex
            existing.expires_at = utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)
            db.session.commit()
            try:
                send_confirmation(existing)
                flash("Check your inbox to confirm your subscription.", "success")
            except (smtplib.SMTPException, ConnectionError, OSError):
                logger.exception("Failed to send confirmation email to %s", email)
                flash("Subscribed, but confirmation email could not be sent.", "error")
        elif existing.confirmed:
            flash("You're already subscribed.", "success")
        else:
            existing.token = uuid.uuid4().hex
            existing.expires_at = utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS)
            db.session.commit()
            try:
                send_confirmation(existing)
                flash("Check your inbox to confirm your subscription.", "success")
            except (smtplib.SMTPException, ConnectionError, OSError):
                logger.exception("Failed to send confirmation email to %s", email)
                flash("Subscribed, but confirmation email could not be sent.", "error")
        return redirect(request.referrer or "/")

    sub = Subscriber(email=email, expires_at=utc_now() + timedelta(hours=CONFIRMATION_EXPIRY_HOURS))
    db.session.add(sub)
    db.session.commit()

    try:
        send_confirmation(sub)
        flash("Check your inbox to confirm your subscription.", "success")
    except (smtplib.SMTPException, ConnectionError, OSError):
        logger.exception("Failed to send confirmation email to %s", email)
        flash("Subscribed, but confirmation email could not be sent.", "error")

    return redirect(request.referrer or "/")


@public.route("/confirm/<token>")
def confirm(token):
    sub = Subscriber.query.filter_by(token=token).first()
    _time.sleep(0.1)  # Always sleep for constant time to prevent timing attack
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
    _time.sleep(0.1)  # Always sleep for constant time to prevent timing attack
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


@public.route("/sitemap.xml")
def sitemap_xml():
    posts = Post.query.filter_by(published=True).order_by(Post.updated_at.desc()).all()
    tags = Tag.query.all()
    
    urls = []
    # Homepage
    urls.append(f"""  <url>
    <loc>{xml_escape(BASE_URL)}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")
    
    # Posts
    for post in posts:
        lastmod = post.updated_at.strftime("%Y-%m-%d") if post.updated_at else ""
        urls.append(f"""  <url>
    <loc>{xml_escape(BASE_URL)}/post/{xml_escape(post.slug)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")
    
    # Tags
    for tag in tags:
        urls.append(f"""  <url>
    <loc>{xml_escape(BASE_URL)}/tag/{xml_escape(tag.slug)}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>""")
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""
    
    return Response(xml, mimetype="application/xml")


@public.route("/favicon.ico")
def favicon():
    return Response(status=301, headers={"Location": url_for("static", filename="img/favicon.svg")})


@public.route("/health")
def health_check():
    """Health check endpoint for monitoring."""
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return jsonify({
        "status": "ok" if db_status == "connected" else "error",
        "database": db_status,
        "timestamp": utc_now().isoformat() + "Z",
    })
