"""Database-backed leases that give one worker ownership of a project sync.

The lease lives on the project row so that acquiring it is a single
conditional ``UPDATE``. Two workers racing for the same project and scope
therefore observe one winner: the loser reads a row count of zero and reports
the conflict instead of interleaving its work with the active holder.

The lease is advisory and time-bounded. A worker that dies without releasing
it blocks the scope until the lease expires, so the expiry is short and a
long-running worker renews it while it still holds it. A lease that could
expire mid-synchronisation would let a second worker start and reintroduce the
concurrency the lease exists to prevent.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import or_, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Project

logger = logging.getLogger(__name__)

DOCS_SCOPE = "docs"
RELEASES_SCOPE = "releases"


@dataclass(frozen=True)
class LeasePolicy:
    """How long a scope's lease lives and how often its holder renews it.

    ``renew_interval`` is ``None`` for scopes whose request count is bounded
    well below the lease lifetime, so they never need to renew.
    """

    ttl: timedelta
    renew_interval: timedelta | None = None


_SCOPE_POLICIES = {
    DOCS_SCOPE: LeasePolicy(
        ttl=timedelta(minutes=10),
        renew_interval=timedelta(minutes=3),
    ),
    RELEASES_SCOPE: LeasePolicy(ttl=timedelta(minutes=30)),
}

_SCOPE_COLUMNS = {
    DOCS_SCOPE: ("docs_sync_lease_owner", "docs_sync_lease_expires_at"),
    RELEASES_SCOPE: ("releases_sync_lease_owner", "releases_sync_lease_expires_at"),
}


class SyncLeaseError(RuntimeError):
    """Raised when another worker holds the lease for the requested scope."""


class SyncLeaseLost(SyncLeaseError):
    """Raised when a lease the caller held was taken over by another worker."""


def _owner_token() -> str:
    return f"{os.getpid()}-{uuid.uuid4().hex[:12]}"


def _columns(scope: str) -> tuple[str, str]:
    try:
        return _SCOPE_COLUMNS[scope]
    except KeyError as exc:
        raise ValueError(f"Unknown sync scope: {scope}") from exc


def _policy(scope: str) -> LeasePolicy:
    try:
        return _SCOPE_POLICIES[scope]
    except KeyError as exc:
        raise ValueError(f"Unknown sync scope: {scope}") from exc


def policy(scope: str) -> LeasePolicy:
    """Return the lease policy for a scope."""
    return _policy(scope)


def acquire(project_id: int, scope: str, *, ttl: timedelta | None = None) -> str:
    """Take the lease for a project scope and return the owner token.

    The lease is committed immediately so that a competing worker sees it.
    Callers must not hold pending changes when they acquire a lease, because
    committing the lease also commits them.
    """
    owner_column, expiry_column = _columns(scope)
    owner = _owner_token()
    now = datetime.now(UTC)
    expires_at = now + (ttl or _policy(scope).ttl)
    result = cast(
        "CursorResult[Any]",
        db.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .where(
                or_(
                    getattr(Project, owner_column).is_(None),
                    getattr(Project, expiry_column).is_(None),
                    getattr(Project, expiry_column) <= now,
                )
            )
            .values({owner_column: owner, expiry_column: expires_at})
            .execution_options(synchronize_session=False)
        ),
    )
    if result.rowcount != 1:
        db.session.rollback()
        raise SyncLeaseError("Another synchronization is already running for this project.")
    db.session.commit()
    return owner


def renew(project_id: int, scope: str, owner: str, *, ttl: timedelta | None = None) -> bool:
    """Extend a lease the caller still owns.

    Returns ``False`` when the lease is no longer held by ``owner``, which
    means it expired and another worker took it over.
    """
    owner_column, expiry_column = _columns(scope)
    now = datetime.now(UTC)
    expires_at = now + (ttl or _policy(scope).ttl)
    result = cast(
        "CursorResult[Any]",
        db.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .where(getattr(Project, owner_column) == owner)
            .values({expiry_column: expires_at})
            .execution_options(synchronize_session=False)
        ),
    )
    if result.rowcount != 1:
        db.session.rollback()
        return False
    db.session.commit()
    return True


def release(project_id: int, scope: str, owner: str) -> None:
    """Release a lease held by ``owner``.

    Releasing a lease that is no longer held, or that expired and was taken by
    another worker, leaves that other worker's lease untouched.
    """
    owner_column, expiry_column = _columns(scope)
    try:
        db.session.execute(
            update(Project)
            .where(Project.id == project_id)
            .where(getattr(Project, owner_column) == owner)
            .values({owner_column: None, expiry_column: None})
            .execution_options(synchronize_session=False)
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.warning("Could not release the %s sync lease for project %s", scope, project_id)
        raise


def holder(project_id: int, scope: str) -> str | None:
    """Return the owner token currently holding the lease, if any."""
    owner_column, _ = _columns(scope)
    project = db.session.get(Project, project_id)
    if project is None:
        return None
    return getattr(project, owner_column)
