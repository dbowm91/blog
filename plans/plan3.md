# Performance Improvement Plan

**Date:** 2026-04-28  
**Scope:** Blog CMS Performance Review and Optimization  
**Status:** Planning Phase (not yet implemented)

---

## Executive Summary

A comprehensive performance review of the Blog CMS codebase identified 10 performance-related issues across database queries, caching, search, and asset handling. This plan prioritizes fixes by impact and implementation complexity.

**Key Findings:**
- 4 High priority issues (1 bug, 3 optimizations)
- 4 Medium priority issues (query optimizations, indexing)
- 2 Low priority issues (minor optimizations)

**Estimated Total Effort:** 4-6 hours

---

## High Priority Items

### 1. Fix `yield_per()` Defeated by `.all()` — `app/scheduler.py:112`

**Severity:** High  
**Type:** Bug / Performance  
**Estimated Effort:** 5 minutes

**Problem:**  
The scheduler uses `yield_per(100)` to stream posts in batches, but immediately calls `.all()` which materializes all rows into a Python list. This defeats the purpose of `yield_per()` and loads all matching posts into memory.

```python
# CURRENT (broken)
posts = (
    db.session.execute(
        select(Post)
        .filter(...)
        .order_by(Post.published_at.desc())
        .yield_per(100)
    )
    .scalars()
    .all()  # Loads EVERYTHING into memory
)
```

**Solution:**  
Since the dataset (unpublished posts needing newsletter) is typically small, remove `yield_per()` entirely:

```python
# FIXED
posts = list(
    db.session.execute(
        select(Post)
        .filter(
            Post.published == True,
            Post.published_at != None,
            Post.newsletter_sent_at == None,
            Post.newsletter_attempts < NEWSLETTER_MAX_RETRY_ATTEMPTS,
        )
        .order_by(Post.published_at.desc())
    ).scalars()
)
```

**Verification:** Run `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "scheduler or newsletter"` (if such tests exist).

---

### 2. Fix Empty `footer_tag_counts` — `app/context_processors.py:100`

**Severity:** High  
**Type:** Bug  
**Estimated Effort:** 10 minutes

**Problem:**  
The `footer_tag_counts` variable is always set to `{}`, never populated. The import `from app.cache import _get_tag_counts` exists at line 27 but is never called. Additionally, `footer_tag_counts` is not used in any template.

**Solution:**  
Populate `footer_tag_counts` with actual data and optionally update templates to display counts.

**File: `app/context_processors.py`**
```python
# Lines 97-101: Fix _get_footer_data()
data = {
    "recent_posts_footer": list(recent_posts),
    "footer_tags": list(footer_tags),
    "footer_tag_counts": _get_tag_counts(),  # Call the function
}
```

**Optional: Update `app/templates/base.html`** (around line 109) to display tag counts:
```jinja2
{% for tag in footer_tags[:10] %}
<a href="{{ url_for('public.tag', slug=tag.slug) }}" class="tag tag-sidebar">
    {{ tag.name }}{% if footer_tag_counts.get(tag.id) %} ({{ footer_tag_counts.get(tag.id) }}){% endif %}
</a>
{% endfor %}
```

**Verification:** Check that footer renders with tag counts (if template updated).

---

### 3. Fix N+1 Query in Revisions Route — `app/routes/admin/posts.py:683-691`

**Severity:** High  
**Type:** Performance (N+1 Query)  
**Estimated Effort:** 10 minutes

**Problem:**  
The `PostRevision` query doesn't eager load the `author` relationship. Since `PostRevision.author` has `lazy="select"` (line 162 in models.py), each access to `revision.author` in the template triggers a separate query. For N revisions, this causes N+1 queries.

**Solution:**  
Add `joinedload(PostRevision.author)` to the query.

**File: `app/routes/admin/posts.py`**
```python
from sqlalchemy.orm import joinedload

# Lines 683-691
revisions = (
    db.session.execute(
        select(PostRevision)
        .filter(PostRevision.post_id == post_id)
        .order_by(PostRevision.created_at.desc())
        .options(joinedload(PostRevision.author))  # ADD THIS
    )
    .scalars()
    .all()
)
```

**Verification:** Run `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "revision"`

---

## Medium Priority Items

### 4. Combine Redundant COUNT Queries — `app/routes/admin/helpers/dashboard.py:79-94`

**Severity:** Medium  
**Type:** Performance (Multiple DB Round Trips)  
**Estimated Effort:** 20 minutes

**Problem:**  
Four separate `SELECT COUNT(*)` queries run sequentially. These can be combined into a single query using `scalar_subquery()`.

**Current Code:**
```python
total_views = db.session.execute(select(func.count(PageView.id))).scalar_one() or 0
total_posts = db.session.execute(select(func.count(Post.id)).filter(Post.published == True)).scalar_one() or 0
total_shares = db.session.execute(select(func.count(ShareEvent.id))).scalar_one() or 0
total_subscribers = db.session.execute(select(func.count(Subscriber.id)).filter(Subscriber.confirmed == True)).scalar_one() or 0
```

**Solution:**  
Combine into a single query using `scalar_subquery()` for each count:

**File: `app/routes/admin/helpers/dashboard.py`**
```python
from sqlalchemy import select, func

stmt = select(
    select(func.count(PageView.id)).scalar_subquery().label('total_views'),
    select(func.count(Post.id)).where(Post.published == True).scalar_subquery().label('total_posts'),
    select(func.count(ShareEvent.id)).scalar_subquery().label('total_shares'),
    select(func.count(Subscriber.id)).where(Subscriber.confirmed == True).scalar_subquery().label('total_subscribers')
)
result = db.session.execute(stmt).one()

total_views = result.total_views or 0
total_posts = result.total_posts or 0
total_shares = result.total_shares or 0
total_subscribers = result.total_subscribers or 0
```

**Performance Impact:** Reduces DB round trips from 4 to 1. Estimated 2-4x speedup for this section.

**Verification:** Run dashboard tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "dashboard"`

---

### 5. Fix Regex Recompilation in Loop — `app/search.py:306`

**Severity:** Medium  
**Type:** Performance (Unnecessary Recomputation)  
**Estimated Effort:** 15 minutes

**Problem:**  
`highlight_query()` is called in a loop from `get_search_snippets()`, and `re.compile()` runs each time. For N posts, the same pattern compiles N times unnecessarily.

**Solution:**  
Precompile the regex pattern once in `get_search_snippets()` and pass it to `highlight_query()`.

**File: `app/search.py`**

Modify `get_search_snippets()` (note: `re` is already imported at top of `app/search.py`):
```python
def get_search_snippets(posts: list, query: str) -> dict[int, str]:
    """Generate search snippets for a list of posts with query highlighting.

    Returns a dict mapping post_id to highlighted snippet string.
    """
    snippets: dict[int, str] = {}
    pattern = None
    if query:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
    
    for post in posts:
        snippet_text = post.summary if post.summary else post.body
        raw_snippet = extract_snippet(snippet_text, query)
        if pattern:
            snippets[post.id] = highlight_query(raw_snippet, pattern=pattern)
        else:
            snippets[post.id] = raw_snippet
    return snippets
```

Modify `highlight_query()`:
```python
def highlight_query(text: str, query: str = "", pattern: re.Pattern | None = None) -> str:
    """Add <mark> tags around query terms in text for highlighting.

    Args:
        text: The text to highlight within
        query: The search query (may contain multiple words). Ignored if pattern is provided.
        pattern: Precompiled regex pattern for matching query terms.

    Returns:
        The text with <mark> tags around matched terms
    """
    if not text:
        return text
    if pattern is None:
        if not query:
            return text
        pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
```

**Verification:** Run search tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v -k "search"`

---

### 6. Add Reverse Index on `post_tags.tag_id`

**Severity:** Medium  
**Type:** Database Indexing  
**Estimated Effort:** 30 minutes

**Problem:**  
The `post_tags` table has a composite primary key on `(post_id, tag_id)`, which creates an index with `post_id` as the leading column. Queries filtering on `tag_id` alone cannot use this index efficiently.

**Affected Queries:**
- `app/cache.py:51-56`: Groups by `post_tags.c.tag_id`
- `app/routes/admin/helpers/tags.py:25-29`: Finds orphaned tags via outer join
- Tag-based post listing: `WHERE tag_id = ?`

**Solution:**  
Add an explicit index on `tag_id` in the model definition.

**File: `app/models.py`**
```python
post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
    db.Index("ix_post_tags_tag_id", "tag_id"),  # ADD THIS
)
```

Then run:
```bash
flask db migrate -m "add index on post_tags.tag_id"
flask db upgrade
```

**Verification:** Check migration applies cleanly and index exists:
```bash
sqlite3 instance/blog.db ".indices post_tags"
```

---

### 7. Blocking `time.sleep()` for Token Enumeration Prevention

**Severity:** Medium (Low impact for low-traffic blog)  
**Type:** Concurrency  
**Estimated Effort:** 1-2 hours (if refactoring)

**Problem:**  
The app uses WSGI wrapped as ASGI (`WsgiToAsgi` in `run.py`), so `time.sleep()` blocks a thread in the pool. This occurs in:
- `app/routes/public.py:620,660` — confirm/unsubscribe (0.1s delay)
- `app/routes/admin/auth.py:54` — login failure (0.05s)
- `app/routes/admin/auth.py:152` — forgot password (0.1s)

**Impact:** For a low-traffic blog, this is acceptable. Under DoS attack, could exhaust thread pool.

**Options:**

**A. Keep Current Approach (Recommended for now)**
- Minimal risk for blog traffic
- 0.1s delay is short

**B. Constant-Time Operation (Better than sleep)**
```python
import hashlib

def constant_time_delay(token: str, iterations: int = 5000):
    """Burn CPU in predictable time instead of sleeping."""
    data = token.encode()
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()
```
- Still blocks thread but more predictable timing
- No thread scheduling variance

**C. Full Async Conversion (Major refactor)**
- Convert routes to `async def`
- Requires async-compatible DB sessions
- Significant effort, not recommended unless already planning async migration

**Recommendation:** Keep current approach. If improvement desired, use Option B.

---

## Low Priority Items

### 8. Simplify `get_indexed_terms()` — `app/search.py:201-219`

**Severity:** Low  
**Type:** Redundant Query  
**Estimated Effort:** 10 minutes

**Problem:**  
The query uses `UNION` to get terms from both `posts` and `posts_fts` tables. Since `posts_fts` already contains all published posts' data, the `posts` table query is redundant. Also, only `title` is queried, missing `body` and `summary`.

**Solution:**  
Query `posts_fts` only and include all indexed columns.

**File: `app/search.py`**
```python
def get_indexed_terms() -> list[str]:
    """Get all unique terms from the FTS index for 'Did you mean?' suggestions.

    Returns a list of unique terms from all indexed columns (title, body, summary).
    """
    try:
        if not _check_fts_enabled():
            return []
        result = db.session.execute(
            text("SELECT title, body, summary FROM posts_fts")
        ).fetchall()
        terms = []
        for row in result:
            for col in row:
                if col:
                    terms.extend(str(col).split())
        return list(set(terms))
    except (OperationalError, ProgrammingError, DatabaseError):
        return []
```

---

### 9. Add Asset Minification/Bundling

**Severity:** Low  
**Type:** Asset Optimization  
**Estimated Effort:** 1-2 hours

**Problem:**  
No build tools exist. CSS (`style.css` = 4018 lines) and JS are served unminified. No cache busting strategy.

**Recommendation (Python-based, no Node.js):**

1. Add to `requirements.txt`:
```
csscompressor>=0.9.4
rjsmin>=1.2.1
```

2. Create `scripts/build_assets.py`:
```python
import os
import re
from csscompressor import compress as css_compress
from rjsmin import jsmin

static_dir = "app/static"

# Minify CSS
for f in ["css/style.css", "css/prism-okaidia.css"]:
    path = os.path.join(static_dir, f)
    if os.path.exists(path):
        with open(path) as src, open(path.replace(".css", ".min.css"), "w") as dst:
            dst.write(css_compress(src.read()))

# Minify JS (skip already minified)
for root, _, files in os.walk(f"{static_dir}/js"):
    for f in files:
        if f.endswith(".js") and not f.endswith(".min.js"):
            path = os.path.join(root, f)
            with open(path) as src, open(path.replace(".js", ".min.js"), "w") as dst:
                dst.write(jsmin(src.read()))
```

3. Add `ASSET_VERSION` to `app/config.py`:
```python
# In app/config.py, add:
ASSET_VERSION = os.environ.get("ASSET_VERSION", "1.0.0")
```

4. Update templates to use `.min` files in production (with a config flag).

5. Add cache busting via query parameter in `app/__init__.py`:
```python
@app.context_processor
def inject_asset_version():
    from app.config import ASSET_VERSION
    return dict(asset_version=ASSET_VERSION)
```

**Verification:** Compare file sizes before/after minification.

---

## Implementation Order

Recommended order based on impact vs. effort:

1. **Fix N+1 in revisions** (High, 10 min) — `app/routes/admin/posts.py`
2. **Fix empty footer_tag_counts** (High, 10 min) — `app/context_processors.py`
3. **Fix yield_per().all()** (High, 5 min) — `app/scheduler.py`
4. **Combine COUNT queries** (Medium, 20 min) — `app/routes/admin/helpers/dashboard.py`
5. **Fix regex recompilation** (Medium, 15 min) — `app/search.py`
6. **Add post_tags.tag_id index** (Medium, 30 min) — `app/models.py` + migration
7. **Simplify get_indexed_terms()** (Low, 10 min) — `app/search.py`
8. **Add asset minification** (Low, 1-2 hours) — New script + requirements.txt
9. **Evaluate time.sleep() alternatives** (Medium, 1-2 hours) — Optional

---

## Notes

- **tags.name index:** Investigation confirmed that `unique=True` on `tags.name` automatically creates a UNIQUE index in SQLite (`sqlite_autoindex_tags_1`). No explicit index needed.
  
- **Testing:** Run full test suite after changes: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

- **Migration:** Items requiring migration (item 6) should be applied to a test database first. Backup production database before applying migrations.

- **Code Style:** Follow existing patterns - use `db.paginate()` for pagination, `db.session.get()` for single record lookups, and SQLAlchemy 2.0 query patterns throughout.

---

## Files Requiring Changes

| File | Items | Priority |
|------|-------|----------|
| `app/scheduler.py` | #1 | High |
| `app/context_processors.py` | #2 | High |
| `app/routes/admin/posts.py` | #3 | High |
| `app/routes/admin/helpers/dashboard.py` | #4 | Medium |
| `app/search.py` | #5, #8 | Medium/Low |
| `app/models.py` | #6 | Medium |
| `migrations/versions/` (new) | #6 | Medium |
| `scripts/build_assets.py` | #9 | Low |
| `requirements.txt` | #9 | Low |
| `app/templates/base.html` | #2 (optional) | High |

---

**End of Plan**
