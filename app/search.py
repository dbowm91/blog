"""Full-text search using SQLite FTS5 with LIKE fallback."""

import html
import re
import threading

__all__ = [
    "init_fts",
    "rebuild_fts",
    "sync_fts",
    "sync_fts_batch",
    "remove_fts",
    "search",
    "reset_fts_available",
    "get_did_you_mean",
    "highlight_query",
    "get_indexed_terms",
]

import difflib
import logging
import nh3
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, DatabaseError
from app.extensions import db
from app.config import FTS_RESULT_LIMIT

logger = logging.getLogger(__name__)

_fts_enabled: bool | None = None
_fts_check_time: float = 0
_FTS_CHECK_TTL = 300
_fts_lock = threading.Lock()

_ESCAPE_SPECIAL_CHARS_RE = re.compile(r'[()*+:+"<>\-]')
_ESCAPE_WHITESPACE_RE = re.compile(r"\s+")


def reset_fts_available() -> None:
    """Reset FTS availability flag. For testing and cache invalidation."""
    global _fts_enabled, _fts_check_time
    _fts_enabled = None
    _fts_check_time = 0


def _check_fts_enabled() -> bool:
    """Check if FTS5 table exists with caching."""
    global _fts_enabled, _fts_check_time
    import time

    now = time.monotonic()
    if _fts_enabled is None or (now - _fts_check_time) > _FTS_CHECK_TTL:
        with _fts_lock:
            if _fts_enabled is None or (now - _fts_check_time) > _FTS_CHECK_TTL:
                check = db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
                ).fetchone()
                _fts_enabled = bool(check)
                _fts_check_time = now
    return _fts_enabled


def init_fts() -> None:
    """Create FTS5 virtual table and populate with existing posts. Idempotent."""
    try:
        posts_exist = db.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        ).fetchone()
        if not posts_exist:
            return

        db.session.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5("
                "title, body, summary, prefix='2 3 4'"
                ")"
            )
        )
        db.session.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts_vocab USING fts5vocab(posts_fts, 'row')"
            )
        )
        db.session.commit()
        if posts_exist:
            db.session.execute(
                text(
                    "INSERT OR IGNORE INTO posts_fts(rowid, title, body, summary) "
                    "SELECT id, title, body, summary FROM posts WHERE published = 1"
                )
            )
            db.session.commit()
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        db.session.rollback()
        logger.warning(
            "FTS5 initialization failed; search will use LIKE fallback (error=%s, operation=init)",
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


def sync_fts(post_id: int, title: str, body: str, summary: str, published: bool) -> bool:
    """Sync a single post to the FTS index. Call before db.session.commit().

    Returns True on success, False on failure. On failure, caller should
    rollback the transaction to maintain FTS/DB consistency.
    """
    try:
        if published:
            db.session.execute(
                text(
                    "INSERT OR REPLACE INTO posts_fts(rowid, title, body, summary) VALUES(:id, :title, :body, :summary)"
                ),
                {"id": post_id, "title": title, "body": body, "summary": summary},
            )
        else:
            db.session.execute(text("DELETE FROM posts_fts WHERE rowid = :id"), {"id": post_id})
        return True
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.warning("FTS sync failed for post %s: %s", post_id, e)
        return False


def sync_fts_batch(items: list[tuple]) -> bool:
    """Batch sync multiple posts to FTS index. Call before db.session.commit().

    Args:
        items: List of (post_id, title, body, summary, published) tuples.

    Returns True on success, False on failure. On failure, caller should
    rollback the transaction to maintain FTS/DB consistency.
    """
    if not items:
        return True
    try:
        published_items = [item for item in items if item[4]]
        unpublished_ids = [item[0] for item in items if not item[4]]

        if unpublished_ids:
            db.session.execute(
                text("DELETE FROM posts_fts WHERE rowid = :id"),
                [{"id": pid} for pid in unpublished_ids],
            )
        if published_items:
            db.session.execute(
                text(
                    "INSERT OR REPLACE INTO posts_fts(rowid, title, body, summary) VALUES(:id, :title, :body, :summary)"
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
        return True
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.warning("FTS batch sync failed: %s", e)
        return False


def remove_fts(post_id: int) -> bool:
    """Remove a post from the FTS index. Call before db.session.commit().

    Returns True on success, False on failure. On failure, caller should
    rollback the transaction to maintain FTS/DB consistency.
    """
    try:
        db.session.execute(text("DELETE FROM posts_fts WHERE rowid = :id"), {"id": post_id})
        return True
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.warning("FTS remove failed for post %s: %s", post_id, e)
        return False


def _escape_fts_term(term: str) -> str:
    term = term.strip()
    term = _ESCAPE_SPECIAL_CHARS_RE.sub(" ", term)
    term = _ESCAPE_WHITESPACE_RE.sub(" ", term)
    term = term.replace('"', '""')
    return term if term else ""


def search(query: str) -> list[tuple[int, float]]:
    """Search using FTS5 with bm25 ranking. Returns list of (post_id, rank) tuples or empty list if unavailable."""
    try:
        if not _check_fts_enabled():
            return []

        terms = [_escape_fts_term(w) for w in query.split()]
        terms = [t for t in terms if t]
        fts_query = " OR ".join(f'"{t}"*' for t in terms)
        if not fts_query:
            return []
        result = db.session.execute(
            text(
                "SELECT rowid, bm25(posts_fts) as rank FROM posts_fts "
                "WHERE posts_fts MATCH :q ORDER BY bm25(posts_fts) LIMIT :limit"
            ),
            {"q": fts_query, "limit": FTS_RESULT_LIMIT},
        ).fetchall()
        return [(row[0], row[1]) for row in result]
    except (OperationalError, ProgrammingError, DatabaseError):
        return []


def get_indexed_terms() -> list[str]:
    """Get all indexed terms using fts5vocab table for efficiency."""
    try:
        result = db.session.execute(
            text("SELECT DISTINCT term FROM posts_fts_vocab WHERE term IS NOT NULL ORDER BY term")
        ).fetchall()
        return [row[0] for row in result]
    except (OperationalError, ProgrammingError):
        return get_indexed_terms_fallback()


def get_indexed_terms_fallback() -> list[str]:
    """Fallback get_indexed_terms when fts5vocab is not available."""
    try:
        if not _check_fts_enabled():
            return []
        result = db.session.execute(text("SELECT title FROM posts WHERE published = 1")).fetchall()
        terms = []
        for row in result:
            if row[0]:
                words = str(row[0]).split()
                terms.extend(words)
        return list(set(terms))
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
    """Generate search snippets using FTS5 native snippet() function.

    Returns a dict mapping post_id to highlighted snippet string.
    """
    snippets: dict[int, str] = {}
    if not posts or not query or not _check_fts_enabled():
        return snippets

    post_ids = [p.id for p in posts]
    terms = [_escape_fts_term(w) for w in query.split()]
    terms = [t for t in terms if t]
    fts_query = " OR ".join(f'"{t}"*' for t in terms)
    if not fts_query:
        return snippets

    _SQLITE_MAX_VARS = 500

    def _fetch_snippets(ids: list[int]) -> list[tuple]:
        if len(ids) == 1:
            query_str = (
                "SELECT rowid, snippet(posts_fts, 1, '<mark>', '</mark>', '...', 30) "
                "FROM posts_fts WHERE rowid = :id AND posts_fts MATCH :q"
            )
            params = {"id": ids[0], "q": fts_query}
        else:
            placeholders = ", ".join([f":id{i}" for i in range(len(ids))])
            query_str = (
                f"SELECT rowid, snippet(posts_fts, 1, '<mark>', '</mark>', '...', 30) "
                f"FROM posts_fts WHERE rowid IN ({placeholders}) AND posts_fts MATCH :q"
            )
            params = {f"id{i}": pid for i, pid in enumerate(ids)}
            params["q"] = fts_query
        return db.session.execute(text(query_str), params).fetchall()

    try:
        for i in range(0, len(post_ids), _SQLITE_MAX_VARS):
            batch = post_ids[i : i + _SQLITE_MAX_VARS]
            for row in _fetch_snippets(batch):
                snippets[row[0]] = nh3.clean(row[1], tags={"mark"})
    except (OperationalError, ProgrammingError, DatabaseError) as e:
        logger.error("FTS snippet query failed: %s", e)
    return snippets


def get_did_you_mean(query: str, indexed_terms: list[str], max_suggestions: int = 3) -> str | None:
    """Get a 'Did you mean?' suggestion using fuzzy matching.

    Args:
        query: The search query that had no results
        indexed_terms: List of terms from the search index to match against
        max_suggestions: Maximum number of suggestions to consider

    Returns:
        A suggested alternative query string, or None if no good match found.
    """
    if not query or not indexed_terms:
        return None

    query_lower = query.lower()
    terms_lower = [t.lower() for t in indexed_terms]

    matches = difflib.get_close_matches(query_lower, terms_lower, n=max_suggestions, cutoff=0.6)

    if not matches:
        return None

    for term in indexed_terms:
        if term.lower() == matches[0]:
            return term

    return matches[0]


def highlight_query(text: str, query: str) -> str:
    """Add <mark> tags around query terms in text for highlighting.

    Args:
        text: The text to highlight within (may contain HTML)
        query: The search query (may contain multiple words)

    Returns:
        The text with <mark> tags around matched terms, with HTML entities escaped
    """
    if not text or not query:
        return text

    pattern = re.compile(re.escape(query), re.IGNORECASE)

    def _replace_with_mark(match: re.Match) -> str:
        return f"<mark>{html.escape(match.group(0))}</mark>"

    result = pattern.sub(_replace_with_mark, html.escape(text))
    return result
