import logging

from flask import Blueprint

from app import limiter

logger = logging.getLogger(__name__)

public = Blueprint("public", __name__)

# Import registration functions from sub-modules
from app.routes.public.browse import register_browse_routes
from app.routes.public.posts import register_post_routes
from app.routes.public.subscribe import register_subscribe_routes
from app.routes.public.meta import register_meta_routes

# Register all routes
register_browse_routes(public)
register_post_routes(public)
register_subscribe_routes(public)
register_meta_routes(public)

# For backwards compatibility - export helper functions used by other modules
from app.routes.public.browse import _get_related_posts, invalidate_archive_cache
from app.routes.public.posts import _safe_redirect_url
