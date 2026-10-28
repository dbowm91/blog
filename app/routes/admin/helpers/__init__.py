"""Package exports for admin helpers.

Re-exports all public functions from submodules for backward compatibility.
"""

from app.routes.admin.helpers.analytics import (
    invalidate_analytics_cache,
)
from app.routes.admin.helpers.dashboard import (
    invalidate_dashboard_cache,
)
from app.routes.admin.helpers.posts import (
    _get_posts_query,
    _apply_post_updates,
)
from app.routes.admin.helpers.slug import (
    _generate_unique_slug,
)
from app.routes.admin.helpers.tags import (
    validate_tag_name,
    _cleanup_orphan_tags,
    _get_or_create_tags,
)
from app.routes.admin.helpers.images import (
    _detect_image_type,
    _allowed_file,
    _save_image,
)
from app.routes.admin.helpers.shared import (
    ALLOWED_EXTENSIONS,
    TAG_NAME_REGEX,
    BACKUP_FILENAME_RE,
    logger,
    _categorize_referrer,
    _check_password_complexity,
    _get_backup_dir,
    _resolve_database_path,
)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "TAG_NAME_REGEX",
    "BACKUP_FILENAME_RE",
    "logger",
    "_categorize_referrer",
    "_check_password_complexity",
    "_get_backup_dir",
    "_resolve_database_path",
    "invalidate_analytics_cache",
    "invalidate_dashboard_cache",
    "_get_posts_query",
    "_generate_unique_slug",
    "_apply_post_updates",
    "validate_tag_name",
    "_cleanup_orphan_tags",
    "_get_or_create_tags",
    "_detect_image_type",
    "_allowed_file",
    "_save_image",
]
