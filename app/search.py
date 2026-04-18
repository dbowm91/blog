"""Full-text search using SQLite FTS5 with LIKE fallback."""

__all__ = ["init_fts", "rebuild_fts", "sync_fts", "sync_fts_batch", "remove_fts", "search", "reset_fts_available"]

import logging
import re
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, DatabaseError
from app.extensions import db
from app.config import FTS_RESULT_LIMIT

logger = logging.getLogger(__name__)


def reset_fts_available() -> None:
    """Reset FTS availability flag. For testing only - no-op in original implementation."""
    pass


def init_fts() -> None:
    """Create FTS5 virtual table and populate with existing posts. Idempotent."""
    try:
        db.session.execute(text("DROP TABLE IF EXISTS posts_fts"))
        db.session.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5("
                "title, body, summary"
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
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        db.session.rollback()
        try:
            db.session.execute(text("DROP TABLE IF EXISTS posts_fts"))
            db.session.commit()
        except Exception:
            db.session.rollback()
        logger.warning(
            "FTS5 initialization failed; search will use LIKE fallback (post_ids=%s, operation=init)",
            e,
        )


def rebuild_fts() -> None:
    """Rebuild the FTS5 index from scratch."""
    try:
        db.session.execute(text("INSERT INTO posts_fts(posts_fts) VALUES('rebuild')"))
        db.session.commit()
    except (OperationalError, ProgrammingError, DatabaseError) as e:
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
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.warning("FTS sync failed for post %s: %s", post_id, e)


def sync_fts_batch(items: list[tuple]):
    """Batch sync multiple posts to FTS index. Call before db.session.commit().

    Args:
        items: List of (post_id, title, body, summary, published) tuples.
    """
    if not items:
        return
    try:
        post_ids = [item[0] for item in items]
        db.session.execute(
            text("DELETE FROM posts_fts WHERE rowid IN :ids"),
            {"ids": tuple(post_ids)},
        )
        published_items = [item for item in items if item[4]]
        if published_items:
            db.session.execute(
                text(
                    "INSERT INTO posts_fts(rowid, title, body, summary) VALUES(:id, :title, :body, :summary)"
                ),
                [
                    {
                        "id": item[0],
                        "title": item[1],
                        "body": item[2],
                        "summary": item[3],
                    }
                    for item in published_items
                ],
            )
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.warning("FTS batch sync failed: %s", e)


def remove_fts(post_id: int):
    """Remove a post from the FTS index. Call before db.session.commit()."""
    try:
        db.session.execute(
            text("DELETE FROM posts_fts WHERE rowid = :id"), {"id": post_id}
        )
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.warning("FTS remove failed for post %s: %s", post_id, e)


def _escape_fts_term(term: str) -> str:
    term = term.strip()
    term = re.sub(r'[()*:+\-"<>]', " ", term)
    term = re.sub(r"\s+", " ", term)
    term = term.replace('"', '""')
    return term if term else ""


def search(query: str) -> list[tuple[int, int]]:
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
    except (OperationalError, ProgrammingError, DatabaseError):
        return []


def extract_snippet(text: str, query: str, context_chars: int = 200) -> str:
    """Extract a snippet from text around the first query match.

    Returns a string of approximately context_chars length containing
    the query term, with leading/trailing ellipsis if the match is
    not at the start/end of the text.
    """
    if not text:
        return ""

    query_lower = query.lower()
    text_lower = text.lower()

    idx = text_lower.find(query_lower)
    if idx == -1:
        return text[:context_chars] + ("..." if len(text) > context_chars else "")

    start = max(0, idx - context_chars // 2)
    end = min(len(text), idx + len(query) + context_chars // 2)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def get_search_snippets(posts: list, query: str) -> dict[int, str]:
    """Generate search snippets for a list of posts.

    Returns a dict mapping post_id to snippet string.
    """
    snippets: dict[int, str] = {}
    for post in posts:
        snippet_text = post.summary if post.summary else post.body
        snippets[post.id] = extract_snippet(snippet_text, query)
    return snippets
