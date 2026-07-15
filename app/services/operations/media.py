"""Media cleanup service — orphaned file detection and removal.

Provides scan (dry-run) and apply (mutating) operations for cleaning up
media files that are no longer referenced by any Post, and clearing stale
image references from the database.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.extensions import db
from app.models import Post
from app.services.operations.results import MediaCleanupResult

if TYPE_CHECKING:
    from app.storage import StorageBackend

logger = logging.getLogger(__name__)

_SUSPICIOUS_NAME_CHARS = frozenset("/\\")


def _is_safe_filename(name: str) -> bool:
    """Reject path traversal and OS-specific separators."""
    if not name or name.startswith("."):
        return False
    if any(c in name for c in _SUSPICIOUS_NAME_CHARS):
        return False
    if ".." in name:
        return False
    return True


def scan_orphaned_media() -> MediaCleanupResult:
    """Scan for orphaned media files and missing DB references. Dry run — no deletion.

    Requires application context for database access and storage resolution.

    Returns:
        MediaCleanupResult with counts and lists of orphaned/missing items.
    """
    from app.storage import get_storage

    storage: StorageBackend = get_storage()

    referenced: set[str] = set()
    posts = db.session.execute(select(Post.image).where(Post.image.isnot(None))).scalars().all()
    for img in posts:
        if img:
            referenced.add(img)

    missing_refs: list[str] = []
    for img in referenced:
        if not storage.exists(img):
            missing_refs.append(img)

    orphaned: list[str] = []
    warnings: list[str] = []

    try:
        for name in storage.list_files():
            if not _is_safe_filename(name):
                warnings.append(f"Skipped suspicious filename: {name}")
                continue
            if name not in referenced:
                orphaned.append(name)
    except (OSError, AttributeError) as e:
        warnings.append(f"Error listing storage files: {e}")

    summary = f"Found {len(orphaned)} orphaned file(s), {len(missing_refs)} missing DB reference(s)"
    return MediaCleanupResult(
        ok=True,
        code="media.scan.complete",
        summary=summary,
        details={
            "orphaned_files": orphaned,
            "missing_refs": missing_refs,
            "referenced_count": len(referenced),
        },
        orphaned_deleted=0,
        missing_cleared=0,
        warnings=warnings,
    )


def apply_orphaned_media_cleanup() -> MediaCleanupResult:
    """Delete orphaned files and clear stale DB references.

    Requires application context for database access and storage resolution.
    Performs a dry-run scan first, then applies deletions and DB updates.

    Returns:
        MediaCleanupResult with actual deletion/clearing counts.
    """
    from app.storage import get_storage

    storage: StorageBackend = get_storage()

    referenced: set[str] = set()
    posts = db.session.execute(select(Post.image).where(Post.image.isnot(None))).scalars().all()
    for img in posts:
        if img:
            referenced.add(img)

    missing_refs: list[str] = []
    posts_to_clear: list[Post] = []
    for img in referenced:
        if not storage.exists(img):
            missing_refs.append(img)
            matching_posts = db.session.execute(select(Post).filter_by(image=img)).scalars().all()
            posts_to_clear.extend(matching_posts)

    orphaned_deleted = 0
    delete_failures: list[str] = []
    warnings: list[str] = []

    try:
        for name in storage.list_files():
            if not _is_safe_filename(name):
                warnings.append(f"Skipped suspicious filename: {name}")
                continue
            if name not in referenced:
                if storage.exists(name) and storage.delete(name):
                    orphaned_deleted += 1
                    logger.info("Deleted orphaned file: %s", name)
                else:
                    delete_failures.append(name)
                    logger.warning("Failed to delete orphaned file: %s", name)
    except (OSError, AttributeError) as e:
        warnings.append(f"Error listing storage files: {e}")
        logger.error("Error listing storage files: %s", e)

    missing_cleared = 0
    for post in posts_to_clear:
        post.image = None
        missing_cleared += 1
        logger.info("Cleared missing image reference from post id=%d", post.id)

    if missing_cleared > 0:
        db.session.commit()

    if delete_failures:
        warnings.append(
            f"Failed to delete {len(delete_failures)} file(s): {', '.join(delete_failures)}"
        )

    summary = f"Deleted {orphaned_deleted} orphaned file(s), cleared {missing_cleared} missing DB reference(s)"
    logger.info(
        "Media cleanup complete: %d orphaned files deleted, %d missing DB references cleared",
        orphaned_deleted,
        missing_cleared,
    )
    return MediaCleanupResult(
        ok=True,
        code="media.cleanup.complete",
        summary=summary,
        details={
            "orphaned_deleted": orphaned_deleted,
            "missing_cleared": missing_cleared,
            "delete_failures": delete_failures,
        },
        orphaned_deleted=orphaned_deleted,
        missing_cleared=missing_cleared,
        warnings=warnings,
    )
