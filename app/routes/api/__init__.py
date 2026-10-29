"""REST API routes package."""

from flask import Blueprint

api = Blueprint("api", __name__, url_prefix="/api")

from app.routes.api import (  # noqa: E402, F401
    auth,
    posts,
    subscribers,
    stats,
    tags,
    pages,
    projects,
    series,
)
