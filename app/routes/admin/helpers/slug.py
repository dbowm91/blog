"""Slug generation helpers for admin routes."""

from app.services.slug import generate_unique_slug


def _generate_unique_slug(
    model, title, exclude_id=None
):
    """Generate a unique slug (delegates to service layer)."""
    return generate_unique_slug(model, title, exclude_id)
