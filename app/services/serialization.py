"""Serialization service for exporting data to JSON."""

from datetime import datetime, timezone
from typing import cast, Any, Sequence

from app.models import Post, Subscriber, Page, Tag


def serialize_post(post: Post) -> dict:
    """Serialize a Post instance to a dictionary."""
    return {
        "title": post.title,
        "slug": post.slug,
        "body": post.body,
        "summary": post.summary,
        "image": post.image,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "published": post.published,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "scheduled_publish_at": (
            post.scheduled_publish_at.isoformat() if post.scheduled_publish_at else None
        ),
        "tags": [tag.name for tag in cast(list[Tag], post.tags)],
    }


def serialize_subscriber(subscriber: Subscriber, include_email: bool = False) -> dict:
    """Serialize a Subscriber instance to a dictionary.

    Args:
        subscriber: The Subscriber model instance
        include_email: If True, include email in output (default False for privacy)
    """
    result: dict[str, Any] = {
        "id": subscriber.id,
        "confirmed": subscriber.confirmed,
        "created_at": (subscriber.created_at.isoformat() if subscriber.created_at else None),
        "expires_at": (subscriber.expires_at.isoformat() if subscriber.expires_at else None),
        "unsubscribed_at": (
            subscriber.unsubscribed_at.isoformat() if subscriber.unsubscribed_at else None
        ),
    }
    if include_email:
        result["email"] = subscriber.email
    return result


def serialize_page(page: Page) -> dict:
    """Serialize a Page instance to a dictionary."""
    return {
        "title": page.title,
        "slug": page.slug,
        "body": page.body,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        "published": page.published,
    }


def serialize_tag(tag: Tag) -> dict:
    """Serialize a Tag instance to a dictionary."""
    return {
        "name": tag.name,
        "slug": tag.slug,
    }


def export_data_to_dict(
    posts: Sequence[Post],
    subscribers: Sequence[Subscriber],
    tags: Sequence[Tag],
    pages: Sequence[Page],
    version: int = 1,
) -> dict:
    """Export all data to a dictionary structure for JSON serialization."""
    return {
        "version": version,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "posts": [serialize_post(p) for p in posts],
        "subscribers": [serialize_subscriber(s) for s in subscribers],
        "tags": [serialize_tag(t) for t in tags],
        "pages": [serialize_page(p) for p in pages],
    }
