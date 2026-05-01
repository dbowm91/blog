from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, abort, Response
from sqlalchemy import select

from app.extensions import db
from app.models import Post, Comment
from app.routes.public import public


@public.route("/post/<slug>/comment", methods=["POST"])
def add_comment(slug: str) -> Response:
    """
    Submit a comment on a post.

    Methods: POST
    POST: Validates and saves comment (requires approval).
    """
    post = db.session.execute(
        select(Post).filter(Post.slug == slug, Post.published == True)
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

    comment = Comment(
        post_id=post.id,
        parent_id=parent_id if parent_id else None,
        author_name=author_name,
        author_email=author_email,
        content=content,
        approved=False,
    )
    db.session.add(comment)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for("public.post", slug=slug))

    flash("Comment submitted and awaiting approval.", "success")
    return redirect(url_for("public.post", slug=slug))
