"""REST API routes package."""

from flask import Blueprint

api = Blueprint("api", __name__, url_prefix="/api")

from app.routes.api import auth, posts, subscribers, stats