"""Author pages - the public profile of a post author."""

from __future__ import annotations

import weakref
from typing import Any

from flask import abort, render_template
from flask.typing import ResponseReturnValue
from sqlalchemy import select

from app import limiter
from app.extensions import db
from app.models import Post, User
from app.services.authors import author_view_for_user, resolve_author

_REGISTERED_BLUEPRINTS: "weakref.WeakSet[Any]" = weakref.WeakSet()


def _install_resolve_author(state: Any) -> None:
    """Expose ``resolve_author`` to the templates of the application."""
    state.app.jinja_env.globals["resolve_author"] = resolve_author


def register_author_routes(public: Any) -> None:
    """Register author routes on the Blueprint."""
    if public in _REGISTERED_BLUEPRINTS:
        return
    _REGISTERED_BLUEPRINTS.add(public)

    public.record(_install_resolve_author)

    @public.route("/author/<username>")
    @limiter.limit("60 per minute")
    def author(username: str) -> ResponseReturnValue:
        """Public profile page of an author."""
        user = db.session.execute(
            select(User).filter(User.username == username)
        ).scalar_one_or_none()
        if user is None:
            abort(404)

        posts = (
            db.session.execute(
                select(Post)
                .filter(Post.author_id == user.id, Post.published.is_(True))
                .order_by(Post.created_at.desc())
            )
            .scalars()
            .all()
        )

        return render_template(
            "author.html",
            author=author_view_for_user(user),
            posts=posts,
        )
