"""Database and search service functions — reusable logic for integrity checks and search rebuilds."""

from __future__ import annotations

import logging

from sqlalchemy import func, select, text
from sqlalchemy.exc import DatabaseError, OperationalError, ProgrammingError

from app.db_utils import get_database_dialect, is_sqlite_database
from app.extensions import db
from app.search import rebuild_fts
from app.services.operations.results import DatabaseCheckResult, SearchRebuildResult

logger = logging.getLogger(__name__)


def check_database_integrity() -> DatabaseCheckResult:
    """Run database integrity check.

    SQLite: PRAGMA integrity_check.
    Non-SQLite: returns unsupported status.

    Returns DatabaseCheckResult with ok=True if healthy, ok=False if degraded or unsupported.
    """
    backend = get_database_dialect()

    if not is_sqlite_database():
        return DatabaseCheckResult(
            ok=False,
            code="db.integrity.unsupported",
            summary=f"Integrity check not supported for {backend} backend.",
            backend=backend,
            healthy=False,
            details={"dialect": backend},
            remediation=["Use the native integrity check tool for this database backend."],
        )

    try:
        result = db.session.execute(text("PRAGMA integrity_check"))
        row = result.scalar()
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        db.session.rollback()
        return DatabaseCheckResult(
            ok=False,
            code="db.integrity.error",
            summary=f"Integrity check failed: {e}",
            backend=backend,
            healthy=False,
            details={"dialect": backend, "error": str(e)},
            remediation=["Consider restoring from a backup."],
        )
    finally:
        db.session.remove()

    if row == "ok":
        return DatabaseCheckResult(
            ok=True,
            code="db.integrity.ok",
            summary="Database integrity check passed.",
            backend=backend,
            healthy=True,
            details={"result": row},
        )

    return DatabaseCheckResult(
        ok=False,
        code="db.integrity.failed",
        summary=f"Database integrity check failed: {row}",
        backend=backend,
        healthy=False,
        details={"result": row},
        remediation=["Consider restoring from a backup."],
    )


def rebuild_search_index() -> SearchRebuildResult:
    """Rebuild the FTS5 search index from scratch.

    Returns SearchRebuildResult with the count of indexed published posts.
    """
    from app.models import Post

    try:
        rebuild_fts()
    except Exception as e:
        logger.warning("FTS5 rebuild raised: %s", e)
        return SearchRebuildResult(
            ok=False,
            code="db.search.rebuild_error",
            summary=f"Search rebuild failed: {e}",
            indexed_count=0,
            details={"error": str(e)},
            remediation=["Check database connectivity and FTS5 availability."],
        )

    try:
        count = db.session.execute(
            select(func.count(Post.id)).where(Post.published == True)  # noqa: E712
        ).scalar()
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        db.session.rollback()
        logger.warning("Failed to count indexed posts: %s", e)
        count = 0
    finally:
        db.session.remove()

    return SearchRebuildResult(
        ok=True,
        code="db.search.rebuilt",
        summary=f"Search index rebuilt. {count} post(s) indexed.",
        indexed_count=count,
        details={"dialect": get_database_dialect()},
    )
