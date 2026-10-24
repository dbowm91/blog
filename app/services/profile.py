"""Profile validation and persistence for user accounts.

The admin profile editor owns every rule about the profile fields, so the
routes never parse raw form values and never build a storage path themselves.
The stored avatar value is always the filename returned by the shared image
helper, never anything supplied by the client.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import User

logger = logging.getLogger(__name__)

MAX_DISPLAY_NAME_LENGTH = 120
MAX_BIO_SHORT_LENGTH = 300
ALLOWED_AVATAR_TYPES = "png, jpg, jpeg, gif, webp"


@dataclass(frozen=True)
class ProfilePayload:
    """Validated profile field values."""

    display_name: str
    bio_short: str
    bio_full: str


def validate_profile_payload(form: Mapping[str, str]) -> ProfilePayload:
    """Read and normalise the profile fields of a submitted form.

    Unknown keys are ignored. The display name and the short bio are trimmed
    and truncated to their column limits; the full bio is kept as typed.
    """
    display_name = str(form.get("display_name") or "").strip()[:MAX_DISPLAY_NAME_LENGTH]
    bio_short = str(form.get("bio_short") or "").strip()[:MAX_BIO_SHORT_LENGTH]
    bio_full = str(form.get("bio_full") or "")
    return ProfilePayload(
        display_name=display_name,
        bio_short=bio_short,
        bio_full=bio_full,
    )


def save_profile(
    user: User,
    payload: ProfilePayload,
    avatar: FileStorage | None,
    remove_avatar: bool,
) -> tuple[bool, str]:
    """Persist a validated profile and apply the avatar change.

    An empty file input leaves the stored avatar untouched. A rejected image
    aborts the whole save, so the text fields are never written when the
    avatar is invalid. The replaced file is deleted from storage only after
    the database change is committed. The user is read back from the session
    after the upload, because storing the avatar can run image processing
    that resets the database session.
    """
    new_filename, error = _store_avatar(avatar)
    if error:
        return False, error

    target = db.session.get(User, user.id)
    if target is None:
        return False, "User not found."

    previous_path = target.avatar_path
    target.display_name = payload.display_name
    target.bio_short = payload.bio_short
    target.bio_full = payload.bio_full
    if new_filename:
        target.avatar_path = new_filename
    elif remove_avatar:
        target.avatar_path = None

    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        if new_filename:
            _delete_stored_file(new_filename)
        return False, "Database error occurred. Please try again."

    if previous_path and previous_path != target.avatar_path:
        _delete_stored_file(previous_path)

    return True, ""


def _store_avatar(avatar: FileStorage | None) -> tuple[str | None, str]:
    """Save an uploaded avatar and return its storage filename."""
    from app.routes.admin.helpers.images import _save_image

    if avatar is None or not avatar.filename:
        return None, ""

    filename, error = _save_image(avatar)
    if error:
        return None, error
    if not filename:
        return None, f"Unsupported file type. Allowed types: {ALLOWED_AVATAR_TYPES}."
    return filename, ""


def _delete_stored_file(path: str) -> None:
    """Delete a stored file, tolerating a file that is already gone."""
    from app.storage import get_storage

    try:
        get_storage().delete(path)
    except Exception:
        logger.warning("Failed to delete stored file: path=%s", path)
