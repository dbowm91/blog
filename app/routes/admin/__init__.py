"""Admin blueprint package.

Registers the admin blueprint and imports route handlers from submodules.
All shared helpers live in `helpers.py` — import from there, not via star imports.
"""

from flask import Blueprint, abort, request, session, redirect, url_for, flash
from functools import wraps
from flask_login import login_required, current_user, logout_user
from sqlalchemy import select

admin = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)

        from app.extensions import db
        from app.models import AdminSession
        from app.config import SESSION_IP_BINDING

        sid = session.get("admin_session_id")
        if sid:
            stored_ip = session.get("admin_session_ip")
            current_ip = request.remote_addr
            if stored_ip and current_ip and stored_ip != current_ip:
                if SESSION_IP_BINDING == "enforce":
                    from app.extensions import db
                    from app.models import AdminSession
                    from sqlalchemy.exc import IntegrityError, OperationalError
                    admin_session = db.session.execute(
                        select(AdminSession).filter_by(session_id=sid)
                    ).scalar_one_or_none()
                    if admin_session:
                        try:
                            db.session.delete(admin_session)
                            db.session.commit()
                        except (IntegrityError, OperationalError):
                            db.session.rollback()
                    logout_user()
                    session.clear()
                    flash("Session invalidated due to IP address change.", "error")
                    return redirect(url_for("admin.login"))
                logger.warning(
                    "IP address changed for admin session %s: expected %s, got %s",
                    sid,
                    stored_ip,
                    current_ip,
                )

        return f(*args, **kwargs)

    return decorated


def _invalidate_all_caches() -> None:
    """Invalidate all application caches.

    Handles tag cache, FTS cache availability flag, analytics cache,
    dashboard cache, and footer cache.
    """
    invalidate_tag_cache()
    from app.search import reset_fts_available
    reset_fts_available()
    invalidate_analytics_cache()
    invalidate_dashboard_cache()
    from app.context_processors import invalidate_footer_cache
    invalidate_footer_cache()


from app.routes.admin.helpers import (
    ALLOWED_EXTENSIONS,
    TAG_NAME_REGEX,
    BACKUP_FILENAME_RE,
    logger,
    _categorize_referrer,
    _check_password_complexity,
    _get_backup_dir,
    invalidate_analytics_cache,
    invalidate_dashboard_cache,
    _get_posts_query,
    _generate_unique_slug,
    _apply_post_updates,
    validate_tag_name,
    _cleanup_orphan_tags,
    _get_or_create_tags,
    _detect_image_type,
    _allowed_file,
    _save_image,
)
from app.routes.admin.helpers.analytics import (
    _get_analytics_data,
    invalidate_analytics_cache,
)
from app.tag_cache import invalidate_tag_cache
from app.utils import safe_delete_file
from app.utils import utc_now
from app.search import sync_fts
from app.search import remove_fts
from app.config import DASHBOARD_PER_PAGE
from app.routes.admin.auth import login, logout, newsletter_reset
from app.routes.admin.posts import (
    dashboard,
    new_post,
    edit_post,
    delete_post,
    preview_post,
    bulk_operations,
    preview_markdown,
    post_revisions,
    restore_revision,
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
from app.routes.admin.newsletter import newsletter_test, newsletter_preview
from app.routes.admin.settings import settings, settings_theme
from app.routes.admin.pages import pages_list, new_page, edit_page, delete_page
from app.routes.admin.series import (
    series_list,
    series_new,
    series_edit,
    series_delete,
    series_posts,
    series_reorder,
)
from app.routes.admin.audit import audit_log
