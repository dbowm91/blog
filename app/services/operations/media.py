"""Media cleanup service — orphaned image detection and removal.

Provides scan (dry-run) and apply (mutating) operations for cleaning up
verified image files that are no longer referenced by post/page Markdown or
Post.image, and clearing stale image references from the database. Videos and
attachments are left in storage because the database has no authoritative references for them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.extensions import db
from app.models import Page, Post
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


def _is_image_media(storage: StorageBackend, name: str) -> bool:
    """Limit legacy orphan cleanup to files verified as supported images."""
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    signatures = {
        "png": (b"\x89PNG\r\n\x1a\n",),
        "jpg": (bytes((255, 216, 255)),),
        "jpeg": (bytes((255, 216, 255)),),
        "gif": (b"GIF87a", b"GIF89a"),
        "webp": (b"RIFF",),
    }
    expected = signatures.get(suffix)
    if expected is None:
        return False
    read_header = getattr(storage, "read_header", None)
    if not callable(read_header):
        return False
    try:
        header = read_header(name)
    except (OSError, AttributeError):
        return False
    if not isinstance(header, bytes) or not any(header.startswith(sig) for sig in expected):
        return False
    return suffix != "webp" or (len(header) >= 12 and header[8:12] == b"WEBP")


def _post_image_references_and_content() -> tuple[set[str], list[str]]:
    """Collect featured-image keys and bodies that may reference uploaded media."""
    referenced: set[str] = set()
    bodies: list[str] = []
    rows = db.session.execute(select(Post.image, Post.body)).all()
    for image, body in rows:
        if image:
            referenced.add(image)
        if body:
            bodies.append(body)
    page_bodies = db.session.execute(select(Page.body)).scalars().all()
    bodies.extend(body for body in page_bodies if body)
    return referenced, bodies


def _is_referenced_in_content(name: str, bodies: list[str]) -> bool:
    """Conservatively preserve a media key mentioned anywhere in authored content."""
    return any(name in body for body in bodies)


def scan_orphaned_media() -> MediaCleanupResult:
    """Scan for unreferenced verified images and missing DB references. Dry run — no deletion.

    Requires application context for database access and storage resolution.

    Returns:
        MediaCleanupResult with counts and lists of orphaned/missing items.
    """
    from app.storage import get_storage

    storage: StorageBackend = get_storage()

    referenced, content_bodies = _post_image_references_and_content()

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
            if (
                name not in referenced
                and not _is_referenced_in_content(name, content_bodies)
                and _is_image_media(storage, name)
            ):
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

    referenced, content_bodies = _post_image_references_and_content()

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
            if (
                name not in referenced
                and not _is_referenced_in_content(name, content_bodies)
                and _is_image_media(storage, name)
            ):
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
