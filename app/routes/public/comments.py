from __future__ import annotations

import re
from flask import request, redirect, url_for, flash, abort, has_request_context
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Post, Comment
from app.routes.public import public
from app import limiter
from app.config import (
    COMMENT_MIN_LENGTH,
    COMMENT_MAX_LENGTH,
    COMMENT_RATE_LIMIT_PER_IP,
    COMMENT_RATE_LIMIT_PER_POST,
    COMMENT_NOTIFY_PENDING,
    COMMENT_SPAM_WORDS,
)
from flask.typing import ResponseReturnValue


def get_client_ip() -> str:
    """Get client IP for rate limiting."""
    if has_request_context():
        return request.remote_addr or "unknown"
    return "unknown"


def get_per_post_comment_key() -> str:
    """Get rate limit key that includes post slug and IP for per-post limiting."""
    slug = "unknown"
    if has_request_context() and request.view_args:
        slug = request.view_args.get("slug", "unknown")
    return f"comment:{slug}:{get_client_ip()}"


def compute_spam_score(content: str, author_name: str, author_email: str) -> float:
    """Compute a simple spam heuristic score (0.0 to 1.0)."""
    score = 0.0

    # Excessive links (more than 3 URLs)
    url_count = len(re.findall(r"https?://|www\.", content, re.IGNORECASE))
    if url_count > 5:
        score += 0.3
    elif url_count > 3:
        score += 0.15

    # Repeated content (same character repeated more than 5 times)
    if re.search(r"(.)\1{5,}", content):
        score += 0.2

    # Configured spam words
    spam_words = COMMENT_SPAM_WORDS.split(",") if COMMENT_SPAM_WORDS else []
    for word in spam_words:
        word = word.strip().lower()
        if word and word in content.lower():
            score += 0.25
            break

    # Author name looks like an email
    if "@" in author_name and "." in author_name:
        score += 0.15

    # Content is mostly uppercase
    upper_count = sum(1 for c in content if c.isupper())
    alpha_count = sum(1 for c in content if c.isalpha())
    if alpha_count > 10 and upper_count / alpha_count > 0.7:
        score += 0.2

    return min(score, 1.0)


@public.route("/post/<slug>/comment", methods=["POST"])
@limiter.limit(COMMENT_RATE_LIMIT_PER_IP, key_func=get_client_ip)
@limiter.limit(COMMENT_RATE_LIMIT_PER_POST, key_func=get_per_post_comment_key)
def add_comment(slug: str) -> ResponseReturnValue:
    """
    Submit a comment on a post.

    Methods: POST
    POST: Validates and saves comment (requires approval).
    """
    from app.context_processors import get_site_settings

    if not get_site_settings()["comments_enabled"]:
        flash("Comments are closed.", "error")
        return redirect(url_for("public.post", slug=slug))

    # Honeypot check - if filled, silently reject
    honeypot = request.form.get("website_url", "").strip()
    if honeypot:
        flash("Comment submitted and awaiting approval.", "success")
        return redirect(url_for("public.post", slug=slug))

    post = db.session.execute(
        select(Post).filter(Post.slug == slug, Post.published)
    ).scalar_one_or_none()
    if not post:
        abort(404)

    author_name = request.form.get("author_name", "").strip()
    author_email = request.form.get("author_email", "").strip()
    content = request.form.get("content", "").strip()
    parent_id = request.form.get("parent_id", type=int)

    if not author_name or not author_email or not content:
        flash("All fields are required.", "error")
        return redirect(url_for("public.post", slug=slug))

    if "@" not in author_email or "." not in author_email.split("@")[-1] or len(author_email) > 254:
        flash("Please provide a valid email address.", "error")
        return redirect(url_for("public.post", slug=slug))

    if parent_id is not None:
        parent = db.session.execute(
            select(Comment).filter(Comment.id == parent_id)
        ).scalar_one_or_none()
        if not parent or parent.post_id != post.id:
            parent_id = None

    # Content length validation
    if len(content) < COMMENT_MIN_LENGTH:
        flash(f"Comment must be at least {COMMENT_MIN_LENGTH} characters.", "error")
        return redirect(url_for("public.post", slug=slug))
    if len(content) > COMMENT_MAX_LENGTH:
        flash(f"Comment must be no more than {COMMENT_MAX_LENGTH} characters.", "error")
        return redirect(url_for("public.post", slug=slug))

    # Compute spam score
    spam_score = compute_spam_score(content, author_name, author_email)

    # Auto-quarantine if spam score is high
    is_spam = spam_score >= 0.7

    comment = Comment(
        post_id=post.id,
        parent_id=parent_id if parent_id else None,
        author_name=author_name,
        author_email=author_email,
        content=content,
        approved=False,
        is_spam=is_spam,
        spam_score=spam_score,
    )
    db.session.add(comment)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for("public.post", slug=slug))

    # Dispatch email notification for pending comments (non-spam)
    if COMMENT_NOTIFY_PENDING and not is_spam:
        from app.tasks import notify_pending_comment_task

        try:
            notify_pending_comment_task.delay(comment.id)
        except Exception:
            pass

    flash("Comment submitted and awaiting approval.", "success")
    return redirect(url_for("public.post", slug=slug))
