import time
import uuid
from datetime import timedelta, datetime
from urllib.parse import urlparse, urlunparse
import shutil
from pathlib import Path
from flask import current_app

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
from sqlalchemy.orm import joinedload, defer
import logging

from app.extensions import db
from app.models import Post, Tag, Subscriber, ShareEvent, Series, PostSeries, post_tags
from app.config import (
    POSTS_PER_PAGE,
    BASE_URL,
    RELATED_POSTS_COUNT,
    MAX_VIEWED_POSTS,
    CONFIRMATION_EXPIRY_HOURS,
    TOKEN_ENUMERATION_DELAY,
    FTS_RESULT_LIMIT,
    PREVIEW_TOKEN_EXPIRY_DAYS,
)

from app.tasks import send_confirmation_task
from app.csrf import validate_csrf_token
from app.utils import xml_escape, is_valid_email, utc_now
from app.tag_cache import _get_tag_counts
from app.search import search as _fts_search, get_search_snippets, get_did_you_mean, get_indexed_terms
from app import limiter, cache as flask_cache

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


@flask_cache.cached(timeout=3600, key_prefix="archive_available_years")
def _get_available_years():
    """Get available years for archive with caching."""
    years_query = (
        select(func.extract("year", Post.created_at).label("year"))
        .filter(Post.published == True)
        .distinct()
        .order_by(func.extract("year", Post.created_at).desc())
    )
    return [int(row.year) for row in db.session.execute(years_query).fetchall()]


def invalidate_archive_cache():
    """Invalidate archive years cache."""
    flask_cache.delete("archive_available_years")


def _get_related_posts(post):
    if not post.tags:
        return []
    tag_ids = [t.id for t in post.tags]
    limit = min(RELATED_POSTS_COUNT, HARD_RELATED_POST_LIMIT)
    # Subquery to count shared tags per post (excluding current post)
    shared_tags_subq = (
        select(post_tags.c.post_id, func.count(post_tags.c.tag_id).label("shared_count"))
        .filter(
            post_tags.c.tag_id.in_(tag_ids),
            post_tags.c.post_id != post.id,
        )
        .group_by(post_tags.c.post_id)
        .subquery()
    )
    # Main query: join with shared tag count, order by count desc then date desc
    related = (
        db.session.execute(
            select(Post)
            .options(joinedload(Post.tags))
            .join(shared_tags_subq, Post.id == shared_tags_subq.c.post_id)
            .filter(Post.published == True)
            .order_by(shared_tags_subq.c.shared_count.desc(), Post.created_at.desc())
            .limit(limit)
        )
        .unique()
        .scalars()
        .all()
    )
    return related


@public.route("/")
@limiter.limit("60 per minute")
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
@limiter.limit("30 per minute")
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

    available_years = _get_available_years()

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
        .options(joinedload(Post.tags), defer(Post.body))
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
@limiter.limit("60 per minute")
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
@limiter.limit("60 per minute")
def post(slug) -> Response:
    """Single post page with related posts and share tracking."""
    post = db.session.execute(
        select(Post).options(joinedload(Post.tags)).filter_by(slug=slug, published=True)
    ).unique().scalar_one_or_none()
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

        from app.page_view_buffer import record_page_view
        record_page_view(post.id, referrer)

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
@limiter.limit("60 per minute")
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
@limiter.limit("20 per minute")
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
    did_you_mean = None
    if not pagination.items:
        indexed_terms = get_indexed_terms()
        did_you_mean = get_did_you_mean(query, indexed_terms)
    return render_template(
        "search.html",
        query=query,
        posts=pagination.items,
        pagination=pagination,
        tags=tags,
        tag_counts=tag_counts,
        search_snippets=snippets,
        did_you_mean=did_you_mean,
    )


@public.route("/series/<slug>")
@limiter.limit("60 per minute")
def series_view(slug) -> Response:
    """View a series and all its posts in order."""
    series = db.session.execute(
        select(Series).filter_by(slug=slug)
    ).scalar_one_or_none()
    if not series:
        abort(404)
    
    # Get posts in this series ordered by order_index
    series_posts = (
        db.session.execute(
            select(PostSeries)
            .options(joinedload(PostSeries.post))
            .filter_by(series_id=series.id)
            .order_by(PostSeries.order_index)
        )
        .scalars()
        .all()
    )
    
    posts = [sp.post for sp in series_posts if sp.post and sp.post.published]
    
    return render_template(
        "series.html",
        series=series,
        posts=posts,
    )


@public.route("/s/<code>")
@limiter.limit("60 per minute")
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


@public.route("/preview/<int:post_id>")
@limiter.limit("30 per minute")
def public_preview(post_id: int) -> Response:
    """Render a shared preview of a post via signed token.

    Query params:
        token: HMAC signature for validation
        expires: Unix timestamp when this link expires

    Security:
        Token is HMAC-SHA256 of post_id:expiry using SECRET_KEY.
        Link expires after PREVIEW_TOKEN_EXPIRY_DAYS (default 7 days).
    """
    import hmac
    import hashlib
    import base64
    from time import time

    token = request.args.get("token", "")
    expires_str = request.args.get("expires", "")

    if not token or not expires_str:
        abort(403)

    try:
        expires = int(expires_str)
    except (ValueError, TypeError):
        abort(403)

    if time() > expires:
        abort(410)

    message = f"{post_id}:{expires}"
    expected = hmac.new(
        current_app.config["SECRET_KEY"].encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).decode().rstrip("=")

    if not hmac.compare_digest(token, expected_b64):
        abort(403)

    post = db.session.execute(
        select(Post).options(joinedload(Post.tags)).filter(Post.id == post_id)
    ).unique().scalar_one_or_none()
    if not post:
        abort(404)

    return render_template(
        "public_preview.html",
        post=post,
        related=[],
        share_url=None,
        short_code=None,
    )


ALLOWED_SHARE_PLATFORMS = {"twitter", "facebook", "linkedin", "reddit", "hackernews", "link"}


@public.route("/api/track-share", methods=["POST"])
@limiter.limit("20 per minute")
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
    """Queue confirmation email task. Returns True (task queued)."""
    send_confirmation_task.delay(subscriber.id)
    return True


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
@limiter.limit("10 per minute")
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
@limiter.limit("5 per minute")
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
@limiter.limit("5 per minute")
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
@limiter.limit("60 per minute")
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
    # Archive page
    yield f"""  <url>
    <loc>{xml_escape(BASE_URL)}/archive</loc>
    <changefreq>weekly</changefreq>
    <priority>0.5</priority>
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
@limiter.limit("60 per minute")
def sitemap_xml() -> Response:
    """Stream sitemap XML for all published posts, pages, and tags."""
    return Response(_generate_sitemap(), mimetype="application/xml")


@public.route("/favicon.ico")
@limiter.limit("60 per minute")
def favicon() -> Response:
    """Redirect to SVG favicon."""
    return Response(
        status=302, headers={"Location": url_for("static", filename="img/favicon.svg")}
    )


@public.route("/health")
@limiter.limit("60 per minute")
def health_check() -> Response:
    """Health check endpoint for monitoring.

    Query params:
        detailed: If "true", return extended info (requires secret match)
        secret: Secret token required for detailed output

    Response:
        200: All services healthy
        503: One or more services degraded

    Detailed response (with ?detailed=true&secret=<secret>):
        Includes database query latency and scheduler next run time.
    """
    import hmac

    from app.scheduler import get_scheduler_health
    from app.config import SMTP_HOST, HEALTH_CHECK_SECRET

    detailed = request.args.get("detailed", "").lower() == "true"
    secret = request.args.get("secret", "")
    is_detailed = (
        detailed
        and HEALTH_CHECK_SECRET
        and hmac.compare_digest(secret, HEALTH_CHECK_SECRET)
    )

    checks = {}
    status_code = 200

    # Database check with latency
    db_start = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1"))
        db_latency_ms = (time.perf_counter() - db_start) * 1000
        checks["database"] = "ok"
    except (OperationalError, ProgrammingError):
        db_latency_ms = (time.perf_counter() - db_start) * 1000
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
    # Disk space check (critical for SQLite)
    try:
        disk_path = Path(current_app.instance_path)
        disk_usage = shutil.disk_usage(disk_path)
        free_percent = (disk_usage.free / disk_usage.total) * 100
        checks["disk_space"] = "ok" if free_percent >= 10 else "low"
    except Exception:
        checks["disk_space"] = "error"

    # Database integrity check
    try:
        integrity_result = db.session.execute(text("PRAGMA integrity_check")).fetchone()
        checks["db_integrity"] = "ok" if integrity_result and integrity_result[0] == "ok" else "error"
    except Exception:
        checks["db_integrity"] = "error"

    # Determine overall status - exclude None values (like last_newsletter_send when never sent)
    overall = (
        "ok"
        if all(
            v in ("ok", "running", "disabled") for v in checks.values() if v is not None
        )
        else "degraded"
    )

    result = {
        "status": overall,
        "checks": checks,
        "timestamp": utc_now().isoformat(),
    }

    if is_detailed:
        result["details"] = {
            "database_latency_ms": round(db_latency_ms, 2),
        }
        if SMTP_HOST:
            health = get_scheduler_health()
            result["details"]["scheduler_next_run"] = health.get("next_run")
            result["details"]["scheduler_last_newsletter_send"] = health.get(
                "last_newsletter_send"
            )

    return jsonify(result), status_code

@public.route("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint."""
    from flask import current_app
    import shutil
    from pathlib import Path
    from sqlalchemy import text
    from app.extensions import db
    from app.config import SMTP_HOST

    metrics_lines = []

    # Health status
    metrics_lines.append("# HELP blog_health_status Overall health status (1=ok, 0=degraded)")
    metrics_lines.append("# TYPE blog_health_status gauge")
    try:
        db.session.execute(text("SELECT 1"))
        metrics_lines.append("blog_health_status 1")
    except Exception:
        metrics_lines.append("blog_health_status 0")

    # Disk free
    metrics_lines.append("# HELP blog_disk_free_bytes Free disk space in bytes")
    metrics_lines.append("# TYPE blog_disk_free_bytes gauge")
    try:
        disk_path = Path(current_app.instance_path)
        disk_usage = shutil.disk_usage(disk_path)
        metrics_lines.append(f"blog_disk_free_bytes {disk_usage.free}")
    except Exception:
        metrics_lines.append("blog_disk_free_bytes 0")

    # DB integrity
    metrics_lines.append("# HELP blog_db_integrity Database integrity (1=ok, 0=error)")
    metrics_lines.append("# TYPE blog_db_integrity gauge")
    try:
        result = db.session.execute(text("PRAGMA integrity_check")).fetchone()
        integrity_ok = result and result[0] == "ok"
        metrics_lines.append(f"blog_db_integrity {1 if integrity_ok else 0}")
    except Exception:
        metrics_lines.append("blog_db_integrity 0")

    # Scheduler status
    metrics_lines.append("# HELP blog_scheduler_status Scheduler status (1=running, 0=stopped)")
    metrics_lines.append("# TYPE blog_scheduler_status gauge")
    scheduler_status = 1  # disabled is ok
    if SMTP_HOST:
        try:
            from app.scheduler import get_scheduler_health
            health = get_scheduler_health()
            scheduler_status = 1 if health["status"] == "running" else 0
        except Exception:
            scheduler_status = 0
    metrics_lines.append(f"blog_scheduler_status {scheduler_status}")

    return "\n".join(metrics_lines), 200, {"Content-Type": "text/plain; version=0.0.4"}
