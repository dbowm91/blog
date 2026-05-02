"""Slug generation helpers for admin routes."""

from typing import Any

from app.services.slug import generate_unique_slug


def _generate_unique_slug(
    model: Any, title: str, exclude_id: int | None = None, slug: str | None = None
) -> str:
    """Generate a unique slug (delegates to service layer."""
    return generate_unique_slug(model, title, exclude_id, slug)
