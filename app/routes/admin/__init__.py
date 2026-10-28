"""Admin blueprint package.

Registers the admin blueprint and imports route handlers from submodules.
All shared helpers live in `helpers.py` — import from there, not via star imports.
"""

from flask import Blueprint, abort, request, session, redirect, url_for, flash
from functools import wraps
from flask_login import login_required, current_user, logout_user
from sqlalchemy import select
from typing import Callable, Any

admin: Blueprint = Blueprint("admin", __name__, url_prefix="/admin")


def _enforce_admin_session() -> Any | None:
    """Validate the admin session row and the IP binding.

    Returns a response to send instead of calling the view, or None when the
    admin session is in order. A session without an ``admin_session_id`` is
    not an admin session and is left alone.
    """
    from app.extensions import db
    from app.models import AdminSession
    from app.config import SESSION_IP_BINDING
    from sqlalchemy.exc import IntegrityError, OperationalError

    sid = session.get("admin_session_id")
    if not sid:
        return None

    admin_session = db.session.execute(
        select(AdminSession).filter_by(session_id=sid)
    ).scalar_one_or_none()
    if not admin_session:
        logout_user()
        session.clear()
        flash("Session has been revoked. Please log in again.", "error")
        return redirect(url_for("admin.login"))

    stored_ip = session.get("admin_session_ip")
    current_ip = request.remote_addr
    if stored_ip and current_ip and stored_ip != current_ip:
        if SESSION_IP_BINDING == "off":
            pass
        elif SESSION_IP_BINDING == "enforce":
            try:
                db.session.delete(admin_session)
                db.session.commit()
            except (IntegrityError, OperationalError):
                db.session.rollback()
            logout_user()
            session.clear()
            flash("Session invalidated due to IP address change.", "error")
            return redirect(url_for("admin.login"))
        else:
            logger.warning(
                "IP address changed for admin session %s: expected %s, got %s",
                sid,
                stored_ip,
                current_ip,
            )

    return None


def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)

        response = _enforce_admin_session()
        if response is not None:
            return response

        return f(*args, **kwargs)

    return decorated


def author_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Allow an administrator or a signed-in author to reach the view.

    Authors reach the post editor and nothing else. Their own posts are the
    only ones they may open, which the editor enforces separately. Every
    other admin route stays behind ``admin_required``.
    """

    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.is_admin:
            response = _enforce_admin_session()
            if response is not None:
                return response

        return f(*args, **kwargs)

    return decorated


from app.routes.admin.helpers import (  # noqa: E402, F401
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
)  # noqa: E402, F401
from app.routes.admin.helpers.analytics import (  # noqa: E402, F401
    _get_analytics_data,
    invalidate_analytics_cache as invalidate_analytics_cache_analytics,
)  # noqa: E402
from app.tag_cache import invalidate_tag_cache  # noqa: E402, F401
from app.utils import safe_delete_file  # noqa: E402, F401
from app.utils import utc_now  # noqa: E402, F401
from app.search import sync_fts  # noqa: E402, F401
from app.search import remove_fts  # noqa: E402, F401
from app.config import DASHBOARD_PER_PAGE  # noqa: E402, F401
from app.routes.admin.auth import login, logout, newsletter_reset  # noqa: E402, F401
from app.routes.admin.subscribers import (  # noqa: E402, F401
    subscribers,
    delete_subscriber,
    export_subscribers,
    subscribers_bulk,
)
from app.routes.admin.tags import tags_list, rename_tag, delete_tag, create_tag  # noqa: E402, F401
from app.routes.admin.users import (  # noqa: E402
    users_list,  # noqa: F401
    create_user,  # noqa: F401
    delete_user,  # noqa: F401
    change_password,  # noqa: F401
    promote_user,  # noqa: F401
    demote_user,  # noqa: F401
    make_owner,  # noqa: F401
)
from app.routes.admin.sessions import sessions_list, revoke_session  # noqa: E402, F401
from app.routes.admin.media import media, upload_media, delete_media  # noqa: E402, F401
from app.routes.admin.backup import (  # noqa: E402, F401
    backup,
    create_backup,
    download_backup,
    restore_backup,
    delete_backup,
)
from app.routes.admin.analytics import analytics  # noqa: E402, F401
from app.routes.admin.newsletter import newsletter_test, newsletter_preview  # noqa: E402, F401
from app.routes.admin.settings import settings, settings_theme, settings_appearance  # noqa: E402, F401
from app.routes.admin.pages import pages_list, new_page, edit_page, delete_page  # noqa: E402, F401
from app.routes.admin import project_docs  # noqa: E402, F401
from app.routes.admin.projects import (  # noqa: E402, F401
    projects_list,
    new_project,
    edit_project,
    delete_project,
    preview_project,
    set_project_published,
)
from app.routes.admin.series import (  # noqa: E402, F401
    series_list,
    series_new,
    series_edit,
    series_delete,
    series_posts,
    series_reorder,
)
from app.routes.admin.audit import audit_log  # noqa: E402, F401
from app.routes.admin.comments import comments_list, approve_comment, delete_comment  # noqa: E402, F401
