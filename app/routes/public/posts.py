"""Post-related routes - view, preview, share tracking."""

import logging
from dataclasses import dataclass
from typing import Any, cast

from flask import current_app

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    jsonify,
    abort,
    session,
)
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import Post, ShareEvent, PostSeries, Comment
from app.config import MAX_VIEWED_POSTS, BASE_URL
from app import limiter

logger = logging.getLogger(__name__)

ALLOWED_SHARE_PLATFORMS = {"twitter", "facebook", "linkedin", "reddit", "hackernews", "link"}

CLOCK_SKEW_TOLERANCE = 30


@dataclass(frozen=True)
class SeriesNavLink:
    """A neighbouring post within the same series."""

    slug: str
    title: str


@dataclass(frozen=True)
class SeriesNav:
    """Context object describing the series a post belongs to."""

    series_title: str
    series_slug: str
    prev: SeriesNavLink | None
    next: SeriesNavLink | None


def _build_series_nav(post_obj: Post) -> SeriesNav | None:
    """Build the series navigation for a post that belongs to a series.

    The neighbours are the published posts that sit either side of the post
    within its own series, ordered by ``PostSeries.order_index``.
    """
    entries = sorted(post_obj.series_entries or [], key=lambda entry: entry.order_index)
    if not entries:
        return None

    series = entries[0].series
    if series is None:
        return None

    siblings = (
        db.session.execute(
            select(PostSeries)
            .options(joinedload(PostSeries.post))  # type: ignore[arg-type]
            .filter(PostSeries.series_id == series.id)
            .order_by(PostSeries.order_index)
        )
        .scalars()
        .unique()
        .all()
    )

    published = [entry for entry in siblings if entry.post is not None and entry.post.published]
    position = next(
        (index for index, entry in enumerate(published) if entry.post_id == post_obj.id),
        None,
    )
    if position is None:
        return None

    def _link(entry: PostSeries | None) -> SeriesNavLink | None:
        if entry is None or entry.post is None:
            return None
        return SeriesNavLink(slug=entry.post.slug, title=entry.post.title)

    return SeriesNav(
        series_title=series.name,
        series_slug=series.slug,
        prev=_link(published[position - 1] if position > 0 else None),
        next=_link(published[position + 1] if position + 1 < len(published) else None),
    )


def _safe_redirect_url() -> str:
    """Return a safe redirect URL, preventing open redirects via spoofed Referer header."""
    referrer = request.referrer
    if referrer:
        from urllib.parse import urlparse

        parsed = urlparse(referrer)
        if parsed.netloc == "" or parsed.netloc == request.host:
            return referrer
    return url_for("public.index")


def register_post_routes(public: Any) -> None:
    """Register post-related routes on the Blueprint."""

    @public.route("/post/<slug>")
    @limiter.limit("60 per minute")
    def post(slug: str) -> ResponseReturnValue:
        """Single post page with related posts and share tracking."""
        post_obj = (
            db.session.execute(
                select(Post)
                .options(
                    joinedload(cast("QueryableAttribute[Any]", Post.tags)),
                    joinedload(Post.series_entries).joinedload(PostSeries.series),  # type: ignore[arg-type]
                )
                .filter_by(slug=slug, published=True)
            )
            .unique()
            .scalar_one_or_none()
        )
        if not post_obj:
            abort(404)

        viewed = session.get("viewed_posts", [])
        if post_obj.id not in viewed:
            referrer = None
            if request.referrer:
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(request.referrer)
                sanitized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
                referrer = sanitized[:512] if sanitized else None

            from app.page_view_buffer import record_page_view

            record_page_view(post_obj.id, referrer)

            if post_obj.id in viewed:
                viewed.remove(post_obj.id)
            viewed.insert(0, post_obj.id)
            if len(viewed) > MAX_VIEWED_POSTS:
                viewed = viewed[:MAX_VIEWED_POSTS]
            session["viewed_posts"] = viewed

        from app.routes.public import _get_related_posts

        related = _get_related_posts(post_obj)
        short_code = post_obj.short_code()
        share_url = f"{BASE_URL}/s/{short_code}"

        comments = (
            db.session.execute(
                select(Comment)
                .where(
                    Comment.post_id == post_obj.id,
                    Comment.approved.is_(True),
                    Comment.parent_id.is_(None),
                )
                .order_by(Comment.created_at.asc())
            )
            .scalars()
            .all()
        )

        return render_template(
            "post.html",
            post=post_obj,
            related=related,
            comments=list(comments),
            series_nav=_build_series_nav(post_obj),
            share_url=share_url,
            short_code=short_code,
            show_full_share=True,
        )

    @public.route("/preview/<int:post_id>")
    @limiter.limit("30 per minute")
    def public_preview(post_id: int) -> ResponseReturnValue:
        """Render a shared preview of a post via signed token."""
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

        if time() > expires + CLOCK_SKEW_TOLERANCE:
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

        post_obj = (
            db.session.execute(
                select(Post)
                .options(joinedload(cast("QueryableAttribute[Any]", Post.tags)))
                .filter(Post.id == post_id)
            )
            .unique()
            .scalar_one_or_none()
        )
        if not post_obj:
            abort(404)

        return render_template(
            "public_preview.html",
            post=post_obj,
            related=[],
            share_url=None,
            short_code=None,
        )

    @public.route("/s/<code>")
    @limiter.limit("60 per minute")
    def short_url_redirect(code: str) -> ResponseReturnValue:
        """Redirect short URL (base62-encoded post ID) to canonical post URL."""
        from app.base62 import decode

        try:
            post_id = decode(code)
        except (ValueError, KeyError):
            return redirect("/")
        post_obj = db.session.get(Post, post_id)
        if not post_obj or not post_obj.published:
            return redirect("/")

        event = ShareEvent(post_id=post_obj.id, platform="link")
        db.session.add(event)
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()

        return redirect(f"/post/{post_obj.slug}")

    @public.route("/api/track-share", methods=["POST"])
    @limiter.limit("20 per minute")
    def track_share() -> ResponseReturnValue:
        """Track social share events."""
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

        post_obj = db.session.get(Post, post_id)
        if not post_obj or not post_obj.published:
            return jsonify({"error": "not found"}), 404

        event = ShareEvent(post_id=post_obj.id, platform=platform)
        db.session.add(event)
        try:
            db.session.commit()
        except (IntegrityError, OperationalError):
            db.session.rollback()
            return jsonify({"error": "database error"}), 500
        return jsonify({"ok": True})
