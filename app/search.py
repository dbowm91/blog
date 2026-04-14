"""Full-text search using SQLite FTS5 with LIKE fallback."""

__all__ = ["init_fts", "rebuild_fts", "sync_fts", "remove_fts", "search"]

import logging
import re
from sqlalchemy import text
from app.extensions import db
from app.config import FTS_RESULT_LIMIT

logger = logging.getLogger(__name__)


def init_fts():
    """Create FTS5 virtual table and populate with existing posts. Idempotent."""
    try:
        db.session.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5("
                "title, body, summary, content='posts', content_rowid='id'"
                ")"
            )
        )
        db.session.execute(
            text(
                "INSERT OR IGNORE INTO posts_fts(rowid, title, body, summary) "
                "SELECT id, title, body, summary FROM posts WHERE published = 1"
            )
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning(
            "FTS5 initialization failed; search will use LIKE fallback (post_ids=%s, operation=init)",
            e,
        )


def rebuild_fts():
    """Rebuild the FTS5 index from scratch."""
    try:
        db.session.execute(text("INSERT INTO posts_fts(posts_fts) VALUES('rebuild')"))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("FTS5 rebuild failed (operation=rebuild): %s", e)


def sync_fts(post_id: int, title: str, body: str, summary: str, published: bool):
    """Sync a single post to the FTS index. Call before db.session.commit()."""
    try:
        db.session.execute(
            text("DELETE FROM posts_fts WHERE rowid = :id"), {"id": post_id}
        )
        if published:
            db.session.execute(
                text(
                    "INSERT INTO posts_fts(rowid, title, body, summary) VALUES(:id, :title, :body, :summary)"
                ),
                {"id": post_id, "title": title, "body": body, "summary": summary},
            )
    except Exception as e:
        logger.warning("FTS sync failed for post %s: %s", post_id, e)


def remove_fts(post_id: int):
    """Remove a post from the FTS index. Call before db.session.commit()."""
    try:
        db.session.execute(
            text("DELETE FROM posts_fts WHERE rowid = :id"), {"id": post_id}
        )
    except Exception as e:
        logger.warning("FTS remove failed for post %s: %s", post_id, e)


def _escape_fts_term(term: str) -> str:
    term = term.strip()
    term = re.sub(r'[()*:+\-"<>]', " ", term)
    term = re.sub(r"\s+", " ", term)
    term = term.replace('"', '""')
    return term if term else ""


def search(query: str):
    """Search using FTS5. Returns list of (post_id, rank) tuples or empty list if unavailable."""
    try:
        check = db.session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
            )
        ).fetchone()
        if not check:
            return []

        terms = [_escape_fts_term(w) for w in query.split()]
        terms = [t for t in terms if t]
        fts_query = " OR ".join(f'"{t}"' for t in terms)
        if not fts_query:
            return []
        result = db.session.execute(
            text(
                "SELECT rowid, rank FROM posts_fts WHERE posts_fts MATCH :q ORDER BY rank LIMIT :limit"
            ),
            {"q": fts_query, "limit": FTS_RESULT_LIMIT},
        ).fetchall()
        return [(row[0], row[1]) for row in result]
    except Exception:
        return []
