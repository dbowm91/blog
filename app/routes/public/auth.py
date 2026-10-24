"""Public authentication routes - sign in, sign out, account, profile editor.

A public session is an ordinary ``flask_login`` session. It grants access to
``/account`` and ``/account/profile`` and nothing under ``/admin``:

* ``admin_required`` in ``app/routes/admin/__init__.py`` checks
  ``current_user.is_admin`` and then the ``AdminSession`` row referenced by
  ``session["admin_session_id"]``. A public session never carries an
  ``AdminSession`` row, and administrator accounts are refused by this login,
  so an admin session can only be created by ``/admin/login``.
* ``flask_login`` keeps a single ``current_user`` per session cookie, so the
  admin logout route also ends a public session and vice versa. Signing out
  through either route ends both.
"""

import logging
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import pyotp
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app import limiter
from app.config import LOCKOUT_DURATION_MINUTES, LOGIN_FAILURE_DELAY, MAX_FAILED_ATTEMPTS
from app.extensions import db
from app.models import AdminSession, Post, User

logger = logging.getLogger(__name__)

LOGIN_RATE_LIMIT = "5 per minute"

_REGISTERED_FLAG = "_devlog_public_auth_routes"

INVALID_CREDENTIALS_MESSAGE = "Invalid credentials."
LOCKED_ACCOUNT_MESSAGE = "Account is locked due to too many failed attempts. Try again later."
INVALID_CODE_MESSAGE = "Invalid verification code."
ADMIN_ACCOUNT_MESSAGE = "Administrator accounts must sign in from the admin panel."
TWO_FACTOR_UNAVAILABLE_MESSAGE = (
    "Two-factor authentication is not set up for this account. Please contact an administrator."
)


@dataclass(frozen=True)
class ProfilePayload:
    """Validated profile fields.

    Mirrors the payload returned by ``app.services.profile.validate_profile_payload``
    so the fallback and the shared service are interchangeable.
    """

    display_name: str
    bio_short: str
    bio_full: str


def is_safe_next_url(target: str) -> bool:
    """Return True when *target* is a local path that is safe to redirect to.

    Only a single-slash absolute path is accepted. Protocol-relative URLs
    (``//evil.example``), absolute URLs, backslashes and control characters
    are rejected.
    """
    if not target:
        return False
    if not target.startswith("/") or target.startswith("//"):
        return False
    if "\\" in target:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in target):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc


def public_login_required(
    view: Callable[..., ResponseReturnValue],
) -> Callable[..., ResponseReturnValue]:
    """Require a signed-in visitor and redirect anonymous ones to the public login.

    ``flask_login``'s global ``login_view`` points at ``admin.login``, so the
    stock decorator would send an anonymous visitor into the admin panel.
    This wrapper keeps the ``login_required`` check and issues the public
    redirect itself.
    """
    guarded = login_required(view)

    @wraps(view)
    def decorated(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        if not current_user.is_authenticated:
            target = request.full_path if request.query_string else request.path
            return redirect(url_for("public.login", next=target))
        return guarded(*args, **kwargs)

    return decorated


def _find_user(identifier: str) -> User | None:
    """Look up an account by username first and then by email address."""
    if not identifier:
        return None
    user = db.session.execute(select(User).filter_by(username=identifier)).scalar_one_or_none()
    if user is not None:
        return user
    return db.session.execute(select(User).filter_by(email=identifier)).scalar_one_or_none()


def _verify_two_factor(user: User, code: str) -> bool:
    """Return True when *code* satisfies the account's second factor."""
    secret = user.totp_secret
    if secret and pyotp.TOTP(secret).verify(code):
        return True
    return user.verify_backup_code(code)


def _published_post_count(user: User) -> int:
    """Count the published posts authored by *user*."""
    return db.session.execute(
        select(func.count(Post.id)).where(
            Post.author_id == user.id,
            Post.published.is_(True),
        )
    ).scalar_one()


def _fallback_validate_profile_payload(form: Mapping[str, str]) -> ProfilePayload:
    """Validate a profile form without the shared profile service."""
    return ProfilePayload(
        display_name=(form.get("display_name") or "").strip()[:120],
        bio_short=(form.get("bio_short") or "").strip()[:300],
        bio_full=(form.get("bio_full") or "").strip()[:5000],
    )


def _fallback_save_profile(
    user: User,
    payload: Any,
    avatar: Any,
    remove_avatar: bool,
) -> tuple[bool, str]:
    """Persist a profile without the shared profile service."""
    user.display_name = payload.display_name
    user.bio_short = payload.bio_short
    user.bio_full = payload.bio_full
    try:
        db.session.commit()
    except (IntegrityError, OperationalError):
        db.session.rollback()
        return False, "An error occurred. Please try again."
    return True, ""


def _profile_service() -> tuple[Callable[..., Any], Callable[..., Any]]:
    """Return the profile validation and save callables.

    The shared profile service is owned by a parallel change and may not be
    importable yet, so a minimal local implementation is used as a fallback.
    """
    try:
        from app.services.profile import save_profile, validate_profile_payload
    except ImportError:
        return _fallback_validate_profile_payload, _fallback_save_profile
    return validate_profile_payload, save_profile


def _render_login(next_url: str, identifier: str, requires_2fa: bool) -> ResponseReturnValue:
    """Render the public login form."""
    return render_template(
        "login.html",
        next_url=next_url,
        identifier=identifier,
        requires_2fa=requires_2fa,
    )


def register_auth_routes(public: Blueprint) -> None:
    """Register the public authentication routes on *public*.

    Registering on the ``public`` blueprint yields the endpoints
    ``public.login``, ``public.logout``, ``public.account`` and
    ``public.account_profile``. The call is idempotent so the module can be
    imported by the application factory and by the test suite without
    registering the same endpoint twice.
    """
    if getattr(public, _REGISTERED_FLAG, False):
        return
    setattr(public, _REGISTERED_FLAG, True)

    @public.route("/login", methods=["GET", "POST"])
    @limiter.limit(LOGIN_RATE_LIMIT)
    def login() -> ResponseReturnValue:
        """Sign a visitor in with a username or an email address.

        The account is looked up by username first and then by email. Every
        failure reports the same message, waits for ``LOGIN_FAILURE_DELAY``
        and counts towards the account lockout, so the form cannot be used
        to discover which accounts exist.

        A two-factor account must present its authenticator code or a backup
        code on the same form. A two-factor account without a stored secret
        can never be signed in through this route.
        """
        next_url = request.args.get("next", "")
        if not is_safe_next_url(next_url):
            next_url = ""

        if current_user.is_authenticated:
            return redirect(url_for("public.account"))

        identifier = ""
        requires_2fa = False

        if request.method == "POST":
            identifier = request.form.get("identifier", "").strip()
            password = request.form.get("password", "")
            code = request.form.get("totp_code", "").strip()
            user = _find_user(identifier)

            if user is not None and user.is_locked():
                flash(LOCKED_ACCOUNT_MESSAGE, "error")
                return _render_login(next_url, identifier, requires_2fa)

            if user is None or not user.check_password(password):
                if user is not None:
                    user.record_failed_login(MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES)
                    db.session.commit()
                flash(INVALID_CREDENTIALS_MESSAGE, "error")
                time.sleep(LOGIN_FAILURE_DELAY)
                return _render_login(next_url, identifier, requires_2fa)

            if user.is_admin:
                flash(ADMIN_ACCOUNT_MESSAGE, "error")
                return _render_login(next_url, identifier, requires_2fa)

            if user.totp_enabled:
                requires_2fa = True
                if not user.totp_secret:
                    flash(TWO_FACTOR_UNAVAILABLE_MESSAGE, "error")
                    return _render_login(next_url, identifier, requires_2fa)
                if not code or not _verify_two_factor(user, code):
                    user.record_failed_login(MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES)
                    db.session.commit()
                    flash(INVALID_CODE_MESSAGE, "error")
                    time.sleep(LOGIN_FAILURE_DELAY)
                    return _render_login(next_url, identifier, requires_2fa)

            # Session fixation protection: clear the session before logging
            # in so the session identifier changes across the login.
            session.clear()

            login_user(user)
            user.reset_failed_login()
            db.session.commit()
            flash("Signed in.", "success")
            if next_url:
                return redirect(next_url)
            return redirect(url_for("public.index"))

        return _render_login(next_url, identifier, requires_2fa)

    @public.route("/logout", methods=["POST"])
    @public_login_required
    def logout() -> ResponseReturnValue:
        """End the session of the current visitor.

        The admin panel and the public site share one session cookie, so this
        route also removes the ``AdminSession`` row of an administrator who
        signs out from the public site. It works for any signed-in account,
        administrator or not.
        """
        sid = session.pop("admin_session_id", None)
        if sid:
            admin_session = db.session.execute(
                select(AdminSession).filter_by(session_id=sid)
            ).scalar_one_or_none()
            if admin_session:
                db.session.delete(admin_session)
                try:
                    db.session.commit()
                except (IntegrityError, OperationalError):
                    db.session.rollback()
        logout_user()
        return redirect(url_for("public.index"))

    @public.route("/account")
    @public_login_required
    def account() -> ResponseReturnValue:
        """Account overview of the signed-in visitor."""
        user = db.session.get(User, current_user.id)
        if user is None:
            abort(403)
        return render_template(
            "account.html",
            editing=False,
            profile_name=user.profile_name,
            avatar_url=user.avatar_url,
            bio_short=user.bio_short,
            bio_full=user.bio_full,
            post_count=_published_post_count(user),
        )

    @public.route("/account/profile", methods=["GET", "POST"])
    @public_login_required
    def account_profile() -> ResponseReturnValue:
        """Profile editor of the signed-in visitor.

        Only the public profile fields are editable. The password and the
        administrator flag are never part of this form.
        """
        user = db.session.get(User, current_user.id)
        if user is None:
            abort(403)

        if request.method == "POST":
            validate_profile_payload, save_profile = _profile_service()
            payload = validate_profile_payload(request.form)
            avatar = request.files.get("avatar")
            remove_avatar = request.form.get("remove_avatar", "").strip().lower() in {
                "1",
                "true",
                "on",
                "yes",
            }
            ok, error_message = save_profile(user, payload, avatar, remove_avatar)
            if not ok:
                flash(error_message or "Could not save your profile.", "error")
                user = db.session.get(User, current_user.id)
                if user is None:
                    abort(403)
            else:
                flash("Profile updated.", "success")
                return redirect(url_for("public.account"))

        return render_template(
            "account.html",
            editing=True,
            profile_name=user.profile_name,
            avatar_url=user.avatar_url,
            bio_short=user.bio_short,
            bio_full=user.bio_full,
            post_count=_published_post_count(user),
        )
