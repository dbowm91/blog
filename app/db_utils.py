"""Database dialect helpers for backend-sensitive health checks."""

from app.extensions import db


def get_database_dialect() -> str:
    """Return the active SQLAlchemy dialect name."""
    try:
        return db.engine.dialect.name
    except Exception:
        return "unknown"


def is_sqlite_database() -> bool:
    """Return True if the active database is SQLite."""
    return get_database_dialect() == "sqlite"
