"""Import/export service functions for site data transfer."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime


from sqlalchemy import select

from app.extensions import db
from app.models import Post, Subscriber, Tag, Page
from app.search import sync_fts
from app.services.operations.results import ExportResult, ImportResult
from app.services.serialization import export_data_to_dict
from app.transaction import commit_with_rollback

SUPPORTED_EXPORT_VERSIONS: set[int] = {1}


def export_site_data(destination: str, *, force: bool = False) -> ExportResult:
    """Export all site data to a JSON file.

    Uses atomic write (write to temp file, then rename). Raises
    ``FileExistsError`` if *destination* already exists and *force* is False.
    Requires application context.
    """
    if os.path.exists(destination) and not force:
        raise FileExistsError(
            f"Destination file already exists: {destination}. Use force=True to overwrite."
        )

    posts = db.session.execute(select(Post).order_by(Post.created_at)).scalars().all()
    subscribers = (
        db.session.execute(select(Subscriber).order_by(Subscriber.created_at)).scalars().all()
    )
    tags = db.session.execute(select(Tag).order_by(Tag.name)).scalars().all()
    pages = db.session.execute(select(Page).order_by(Page.created_at)).scalars().all()

    data = export_data_to_dict(posts, subscribers, tags, pages)

    dest_dir = os.path.dirname(destination) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dest_dir, suffix=".tmp", prefix=".export-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, destination)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return ExportResult(
        ok=True,
        code="export.success",
        summary=(
            f"Exported {len(posts)} posts, {len(subscribers)} subscribers, "
            f"{len(tags)} tags, and {len(pages)} pages to '{destination}'."
        ),
        posts=len(posts),
        subscribers=len(subscribers),
        tags=len(tags),
        pages=len(pages),
        path=destination,
    )


def validate_import(source: str) -> ImportResult:
    """Validate an import file without making changes.

    Returns structure and counts. Subscriber emails are redacted from
    the summary. Requires application context.
    """
    with open(source, encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", 1)

    if version not in SUPPORTED_EXPORT_VERSIONS:
        return ImportResult(
            ok=False,
            code="import.unsupported_version",
            summary=f"Unsupported export version: {version}",
            remediation=[f"Supported versions: {sorted(SUPPORTED_EXPORT_VERSIONS)}"],
        )

    post_count = len(data.get("posts", []))
    tag_count = len(data.get("tags", []))
    subscriber_count = len(data.get("subscribers", []))
    page_count = len(data.get("pages", []))

    return ImportResult(
        ok=True,
        code="import.valid",
        summary=(
            f"Valid import file with {post_count} posts, {subscriber_count} subscribers, "
            f"{tag_count} tags, and {page_count} pages."
        ),
        posts=post_count,
        subscribers=subscriber_count,
        tags=tag_count,
        pages=page_count,
        details={
            "version": version,
            "exported_at": data.get("exported_at"),
        },
    )


def import_site_data(
    source: str,
    *,
    skip_confirmed: bool = True,
    dry_run: bool = False,
) -> ImportResult:
    """Import site data from a JSON file.

    Validates before mutation. Supports dry run. Preserves transaction
    boundaries (each entity type committed separately). FTS synchronisation
    is performed through ``app.search.sync_fts``. Duplicate policy: skip
    existing records by slug/email. Requires application context.
    """
    with open(source, encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", 1)
    if version not in SUPPORTED_EXPORT_VERSIONS:
        return ImportResult(
            ok=False,
            code="import.unsupported_version",
            summary=f"Unsupported export version: {version}",
            remediation=[f"Supported versions: {sorted(SUPPORTED_EXPORT_VERSIONS)}"],
        )

    if dry_run:
        post_count = len(data.get("posts", []))
        tag_count = len(data.get("tags", []))
        subscriber_count = len(data.get("subscribers", []))
        page_count = len(data.get("pages", []))
        return ImportResult(
            ok=True,
            code="import.dry_run",
            summary=(
                f"Dry run: would import {post_count} posts, {subscriber_count} subscribers, "
                f"{tag_count} tags, and {page_count} pages."
            ),
            posts=post_count,
            subscribers=subscriber_count,
            tags=tag_count,
            pages=page_count,
        )

    imported_posts = 0
    imported_tags = 0
    imported_subscribers = 0
    imported_pages = 0

    for tag_data in data.get("tags", []):
        existing = db.session.execute(
            select(Tag).filter_by(slug=tag_data["slug"])
        ).scalar_one_or_none()
        if not existing:
            tag = Tag(name=tag_data["name"], slug=tag_data["slug"])
            db.session.add(tag)
            imported_tags += 1
    if imported_tags > 0:
        commit_with_rollback()

    tag_cache = {t.slug: t for t in db.session.execute(select(Tag)).scalars().all()}

    for post_data in data.get("posts", []):
        existing = db.session.execute(
            select(Post).filter_by(slug=post_data["slug"])
        ).scalar_one_or_none()
        if existing:
            continue

        post = Post(
            title=post_data["title"],
            slug=post_data["slug"],
            body=post_data["body"],
            summary=post_data.get("summary", ""),
            image=post_data.get("image"),
            published=post_data.get("published", False),
        )
        if post_data.get("published_at"):
            post.published_at = datetime.fromisoformat(post_data["published_at"])
        if post_data.get("scheduled_publish_at"):
            post.scheduled_publish_at = datetime.fromisoformat(post_data["scheduled_publish_at"])

        for tag_name in post_data.get("tags", []):
            existing_tag: Tag | None = tag_cache.get(Tag.generate_slug(tag_name))
            if existing_tag:
                post.tags.append(existing_tag)

        db.session.add(post)
        imported_posts += 1
    if imported_posts > 0:
        commit_with_rollback()

        for post_data in data.get("posts", []):
            existing = db.session.execute(
                select(Post).filter_by(slug=post_data["slug"])
            ).scalar_one_or_none()
            if existing and post_data.get("tags"):
                sync_fts(
                    existing.id,
                    existing.title,
                    existing.body,
                    existing.summary,
                    existing.published,
                )

    for subscriber_data in data.get("subscribers", []):
        if skip_confirmed and subscriber_data.get("confirmed"):
            continue

        existing = db.session.execute(
            select(Subscriber).filter_by(email=subscriber_data["email"])
        ).scalar_one_or_none()
        if existing:
            continue

        subscriber = Subscriber(
            email=subscriber_data["email"],
            token=uuid.uuid4().hex,
            confirmed=subscriber_data.get("confirmed", False),
        )
        if subscriber_data.get("created_at"):
            subscriber.created_at = datetime.fromisoformat(subscriber_data["created_at"])
        if subscriber_data.get("expires_at"):
            subscriber.expires_at = datetime.fromisoformat(subscriber_data["expires_at"])
        if subscriber_data.get("unsubscribed_at"):
            subscriber.unsubscribed_at = datetime.fromisoformat(subscriber_data["unsubscribed_at"])

        db.session.add(subscriber)
        imported_subscribers += 1
    if imported_subscribers > 0:
        commit_with_rollback()

    for page_data in data.get("pages", []):
        existing = db.session.execute(
            select(Page).filter_by(slug=page_data["slug"])
        ).scalar_one_or_none()
        if existing:
            continue

        page = Page(
            title=page_data["title"],
            slug=page_data["slug"],
            body=page_data["body"],
            published=page_data.get("published", False),
        )
        if page_data.get("created_at"):
            page.created_at = datetime.fromisoformat(page_data["created_at"])
        if page_data.get("updated_at"):
            page.updated_at = datetime.fromisoformat(page_data["updated_at"])

        db.session.add(page)
        imported_pages += 1
    if imported_pages > 0:
        commit_with_rollback()

    return ImportResult(
        ok=True,
        code="import.success",
        summary=(
            f"Imported {imported_posts} posts, {imported_subscribers} subscribers, "
            f"{imported_tags} tags, and {imported_pages} pages."
        ),
        posts=imported_posts,
        subscribers=imported_subscribers,
        tags=imported_tags,
        pages=imported_pages,
    )
