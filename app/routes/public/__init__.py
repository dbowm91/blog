import logging

from flask import Blueprint

from app import limiter  # noqa: F401

logger = logging.getLogger(__name__)

public = Blueprint("public", __name__)

# Import registration functions from sub-modules
from app.routes.public.browse import register_browse_routes  # noqa: E402, F401
from app.routes.public.posts import register_post_routes  # noqa: E402, F401
from app.routes.public.subscribe import register_subscribe_routes  # noqa: E402, F401
from app.routes.public.meta import register_meta_routes  # noqa: E402, F401
from app.routes.public.authors import register_author_routes  # noqa: E402, F401
from app.routes.public.pages import register_page_routes  # noqa: E402, F401
from app.routes.public.auth import register_auth_routes  # noqa: E402, F401
from app.routes.public import comments  # noqa: E401, E402, F401

# Register all routes
register_browse_routes(public)
register_post_routes(public)
register_subscribe_routes(public)
register_meta_routes(public)
register_author_routes(public)
register_page_routes(public)
register_auth_routes(public)

# For backwards compatibility - export helper functions used by other modules
from app.routes.public.browse import _get_related_posts, invalidate_archive_cache  # noqa: E402, F401
from app.routes.public.posts import _safe_redirect_url  # noqa: E402, F401
