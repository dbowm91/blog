"""Admin blueprint package.

Registers the admin blueprint and imports route handlers from submodules.
All shared helpers live in `helpers.py` — import from there, not via star imports.
"""

from flask import Blueprint, abort
from functools import wraps
from flask_login import login_required, current_user

admin = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


from app.routes.admin.helpers import (
    ALLOWED_EXTENSIONS,
    TAG_NAME_REGEX,
    BACKUP_FILENAME_RE,
    logger,
    _categorize_referrer,
    _check_password_complexity,
    _get_posts_query,
    _get_analytics_data,
    validate_tag_name,
    _detect_image_type,
    _allowed_file,
    _generate_unique_slug,
    _save_image,
    _cleanup_orphan_tags,
    _get_or_create_tags,
    _apply_post_updates,
    invalidate_analytics_cache,
    _get_backup_dir,
    invalidate_tag_cache,
    safe_delete_file,
    utc_now,
    sync_fts,
    remove_fts,
    DASHBOARD_PER_PAGE,
    _analytics_cache,
    _analytics_cache_lock,
)
from app.routes.admin.auth import login, logout, newsletter_reset
from app.routes.admin.posts import (
    dashboard,
    new_post,
    edit_post,
    delete_post,
    preview_post,
    bulk_operations,
    preview_markdown,
)
from app.routes.admin.subscribers import (
    subscribers,
    delete_subscriber,
    export_subscribers,
    subscribers_bulk,
)
from app.routes.admin.tags import tags_list, rename_tag, delete_tag, create_tag
from app.routes.admin.users import users_list, create_user, delete_user, change_password
from app.routes.admin.sessions import sessions_list, revoke_session
from app.routes.admin.media import media, upload_media, delete_media
from app.routes.admin.backup import (
    backup,
    create_backup,
    download_backup,
    restore_backup,
    delete_backup,
)
from app.routes.admin.analytics import analytics
from app.routes.admin.newsletter import newsletter_test
from app.routes.admin.settings import settings, settings_theme
