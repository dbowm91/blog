"""Author resolution for posts, listings and author pages.

This module is the single producer of author data. The post page, the post
listing and the author page all render the same resolved author, so they can
never disagree about who wrote a post.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, cast

from flask import url_for
from werkzeug.routing import BuildError
from sqlalchemy import func, select

from app.config import APP_TITLE, AUTHOR_AVATAR, AUTHOR_NAME, AUTHOR_ROLE
from app.extensions import db
from app.models import Post, User


@dataclass(frozen=True)
class AuthorView:
    """The resolved author of a post.

    ``username`` is ``None`` for the config-level fallback author: that
    author has no profile page, so the name must not be linked.
    """

    name: str
    role: str
    avatar_url: str | None
    bio_short: str
    bio_full: str
    username: str | None


def author_view_for_user(user: User) -> AuthorView:
    """Build the author view of a user."""
    return AuthorView(
        name=user.profile_name,
        role="",
        avatar_url=user.avatar_url,
        bio_short=user.bio_short or "",
        bio_full=user.bio_full or "",
        username=user.username,
    )


def resolve_author(post: Post) -> AuthorView:
    """Resolve the author of a post.

    The assigned user wins. A post without an author falls back to the
    config-level author, and the site title is the last resort so that no
    post ever renders a blank author name.
    """
    user = cast(Optional[User], post.author)
    if user is not None:
        return author_view_for_user(user)

    config_name = (AUTHOR_NAME or "").strip()
    return AuthorView(
        name=config_name or APP_TITLE,
        role=AUTHOR_ROLE or "",
        avatar_url=AUTHOR_AVATAR or None,
        bio_short="",
        bio_full="",
        username=None,
    )


def author_url(username: str) -> str:
    """Return the public path of an author's page.

    The registered endpoint is used when it is available so the URL always
    follows the route, with the canonical path as the fallback.
    """
    try:
        return url_for("public.author", username=username)
    except BuildError:
        return f"/author/{username}"


def list_authors() -> list[User]:
    """Return the users that can author posts, ordered by display name."""
    display_name = func.coalesce(func.nullif(User.display_name, ""), User.username)
    return list(
        db.session.execute(select(User).order_by(display_name, User.username)).scalars().all()
    )


def default_author_id() -> int | None:
    """Return the id of the oldest admin, the fallback author of a post."""
    return db.session.execute(
        select(User.id).filter(User.is_admin.is_(True)).order_by(User.id).limit(1)
    ).scalar_one_or_none()


def resolve_author_id(raw: str | None, actor: Any = None) -> int | None:
    """Resolve the author id to assign to a post.

    An admin may assign any author, any other signed-in user may only assign
    themselves. An empty request falls back to the signed-in user, or to the
    oldest admin when nobody is signed in.

    Raises:
        ValueError: when the requested author does not exist or may not be
            assigned by the actor.
    """
    requested: int | None = None
    if raw:
        try:
            requested = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid author.") from exc

    signed_in = actor is not None and bool(getattr(actor, "is_authenticated", False))

    if requested is None:
        if signed_in:
            return actor.id
        return default_author_id()

    if db.session.get(User, requested) is None:
        raise ValueError("Unknown author.")

    if signed_in and not actor.is_admin and requested != actor.id:
        raise ValueError("You may only assign posts to yourself.")

    return requested
