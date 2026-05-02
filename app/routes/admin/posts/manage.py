"""Manage routes - delete post, preview post."""

import os

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    abort,
    current_app,
    Response,
)

from app.extensions import db
from app.models import Post, PostRevision
from app.routes.admin import admin_required
from app.routes.admin.helpers import (
    _cleanup_orphan_tags,
    invalidate_analytics_cache,
    logger,
)
from app.context_processors import invalidate_footer_cache
from app.utils import safe_delete_file
from app.tag_cache import invalidate_tag_cache
from app.search import remove_fts
from app.routes.rss import invalidate_rss_cache
from app.routes.public import invalidate_archive_cache
from app.config import BASE_URL, PREVIEW_TOKEN_EXPIRY_DAYS


def _save_revision(post: Post, author_id: int | None) -> None:
    """Save a revision snapshot of the post."""
    revision = PostRevision(
        post_id=post.id,
        title=post.title,
        slug=post.slug,
        body=post.body,
        summary=post.summary,
        author_id=author_id,
    )
    db.session.add(revision)


def _generate_preview_token(post_id: int, expiry_timestamp: int) -> str:
    """Generate HMAC signature for preview URL."""
    import hmac
    import hashlib
    import base64

    message = f"{post_id}:{expiry_timestamp}"
    signature = hmac.new(
        current_app.config["SECRET_KEY"].encode(),
        message.encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _build_preview_url(post_id: int, expiry_timestamp: int) -> str:
    """Build full public preview URL with token."""
    token = _generate_preview_token(post_id, expiry_timestamp)
    return f"{BASE_URL}/preview/{post_id}?token={token}&expires={expiry_timestamp}"


def register_manage_routes(admin):
    """Register manage routes on the admin Blueprint."""

    @admin.route("/delete/<int:post_id>", methods=["POST"])
    @admin_required
    def delete_post(post_id: int) -> Response:
        """Delete a blog post."""
        post = db.session.get(Post, post_id)
        if not post:
            abort(404)
        old_image = post.image
        post_id_for_fts = post.id
        post_title = post.title
        db.session.delete(post)
        invalidate_tag_cache()
        invalidate_analytics_cache()
        invalidate_footer_cache()
        invalidate_rss_cache()
        invalidate_archive_cache()
        _cleanup_orphan_tags()
        db.session.commit()
        remove_fts(post_id_for_fts)
        if old_image:
            safe_delete_file(os.path.join(current_app.config["UPLOAD_FOLDER"], old_image))
        logger.info("Post deleted: id=%d title=%s", post_id, post_title)
        flash("Post deleted.", "success")
        return redirect(url_for("admin.dashboard"))

    @admin.route("/preview/<int:post_id>")
    @admin_required
    def preview_post(post_id: int) -> Response:
        """Preview a post before publishing."""
        post = db.session.get(Post, post_id)
        if not post:
            abort(404)

        if request.args.get("share") == "1":
            from time import time
            expiry_timestamp = int(time()) + (PREVIEW_TOKEN_EXPIRY_DAYS * 86400)
            preview_url = _build_preview_url(post_id, expiry_timestamp)
            return jsonify({
                "preview_url": preview_url,
                "expires_at": expiry_timestamp,
            })

        short_code = post.short_code()
        share_url = f"{BASE_URL}/s/{short_code}"
        return render_template(
            "admin/preview.html",
            post=post,
            related=[],
            share_url=share_url,
            short_code=short_code,
            preview_mode=True,
        )
