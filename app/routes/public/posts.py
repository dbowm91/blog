"""Post-related routes - view, preview, share tracking."""
 
import logging
from flask import current_app

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    jsonify,
    abort,
    session,
    Response,
)
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from sqlalchemy.orm import joinedload, QueryableAttribute
from typing import cast, Union, Any
from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db
from app.models import Post, ShareEvent
from app.config import MAX_VIEWED_POSTS, BASE_URL
from app import limiter

logger = logging.getLogger(__name__)

ALLOWED_SHARE_PLATFORMS = {"twitter", "facebook", "linkedin", "reddit", "hackernews", "link"}


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
        post_obj = db.session.execute(
            select(Post).options(joinedload(cast(QueryableAttribute, Post.tags))).filter_by(slug=slug, published=True)
        ).unique().scalar_one_or_none()
        if not post_obj:
            abort(404)

        viewed = session.get("viewed_posts", [])
        if post_obj.id not in viewed:
            referrer = None
            if request.referrer:
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(request.referrer)
                sanitized = urlunparse(
                    (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
                )
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

        return render_template(
            "post.html",
            post=post_obj,
            related=related,
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

        post_obj = db.session.execute(
            select(Post).options(joinedload(cast(QueryableAttribute, Post.tags))).filter(Post.id == post_id)
        ).unique().scalar_one_or_none()
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
