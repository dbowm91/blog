# Comprehensive Improvement Plan

All improvements for the DevLog blog platform, consolidated from codebase review findings.
SQLite is retained as the database backend. Items are organized by priority and dependency order.

**Total items: 18** — 3 bugs, 4 security, 5 performance/code quality, 6 features/test coverage.

---

## Phase 1: Bug Fixes (High Priority) ✅ COMPLETED

### 1.1 Fix Broken Migration (`f439f3e05654`) ✅

**Severity:** High — will fail on any database that has run the initial migration.

**File:** `migrations/versions/f439f3e05654_add_referrer_column_to_pageview.py`

**Problem:** The auto-generated migration recreates all tables (`CREATE TABLE posts`, etc.) instead of only adding the `referrer` column to `page_views`. The initial migration `a1b2c3d4e5f6` already creates all tables, so this fails with "table already exists."

**Fix:** Replace `upgrade()` and `downgrade()` with only the column addition/removal:

```python
def upgrade():
    op.add_column("page_views", sa.Column("referrer", sa.String(512), nullable=True))

def downgrade():
    op.drop_column("page_views", "referrer")
```

**Risk:** If any production database has already run this migration successfully (unlikely), the migration history would need manual repair.

---

### 1.2 Fix `media()` Route mtime Bug ✅

**Severity:** High — media library shows wrong file modification dates.

**File:** `app/routes/admin.py:533`

**Problem:** The route calls `os.stat(filepath)` and gets `stat.st_mtime`, but ignores it and uses `utc_now()` instead:

```python
stat = os.stat(filepath)
files.append({"mtime": utc_now()})  # BUG: should use stat.st_mtime
```

**Fix:** Convert the epoch timestamp to a datetime object:

```python
from datetime import datetime  # add to existing import on line 11

stat = os.stat(filepath)
files.append({
    "name": filename,
    "size": stat.st_size,
    "mtime": datetime.fromtimestamp(stat.st_mtime),
})
```

---

### 1.3 Fix GIF Image Validation (GIF89a Rejected) ✅

**Severity:** Medium — functional bug blocking common GIF uploads.

**File:** `app/routes/admin.py:27`

**Problem:** `_detect_image_type()` only accepts GIF87a format, rejecting the more common GIF89a:

```python
if header[:4] == b"GIF8" and header[5:6] == b"a":  # matches GIF87a only
```

**Fix:** Accept both GIF87a and GIF89a:

```python
if header[:3] == b"GIF" and header[3:6] in (b"87a", b"89a"):
    return "gif"
```

---

## Phase 2: Security Fixes ✅ COMPLETED

### 2.1 Fix Unsubscribe Timing Attack ✅

**Severity:** Medium — enables token enumeration via timing side-channel.

**File:** `app/routes/public.py:249-268`

**Problem:** Invalid and expired tokens get a 0.1s delay, but valid tokens respond immediately. An attacker can distinguish "valid token" (fast) from "invalid/expired" (slow).

**Fix:** Add consistent delay for all cases:

```python
def unsubscribe(token):
    sub = Subscriber.query.filter_by(token=token).first()
    _time.sleep(0.1)  # Always sleep for constant time
    if not sub or (sub.expires_at and sub.expires_at < utc_now()):
        flash("You have been unsubscribed.", "success")
    else:
        db.session.delete(sub)
        db.session.commit()
        flash("You have been unsubscribed.", "success")
    return redirect("/")
```

---

### 2.2 Fix Broad Exception Catch in `subscribe()` ✅

**Severity:** Medium — masks programming bugs as email failures.

**File:** `app/routes/public.py:233`

**Problem:** Catches bare `Exception` from `send_confirmation()`, swallowing `TypeError`, `AttributeError`, etc.

**Fix:** Catch only expected SMTP exceptions:

```python
import smtplib

try:
    send_confirmation(sub)
    flash("Check your inbox to confirm your subscription.", "success")
except (smtplib.SMTPException, ConnectionError, OSError) as e:
    logger.exception("Failed to send confirmation email to %s", email)
    flash("Subscribed, but confirmation email could not be sent.", "error")
```

---

### 2.3 Subscriber Soft Delete (Audit Trail) ✅

**Severity:** Medium — data retention and re-subscription support.

**Files:** `app/models.py`, `app/routes/public.py`, `app/scheduler.py`, `app/routes/admin.py`

**Problem:** `unsubscribe()` permanently deletes the subscriber record, losing history and preventing re-subscription.

**Fix:**

1. Add `unsubscribed_at` column to `Subscriber` in `app/models.py`:
   ```python
   unsubscribed_at = db.Column(db.DateTime, nullable=True)
   ```

2. Change `unsubscribe()` in `public.py` to soft-delete:
   ```python
   sub.unsubscribed_at = utc_now()
   sub.confirmed = False
   db.session.commit()
   ```

3. Update `subscribe()` in `public.py` to handle re-activation:
   ```python
   existing = Subscriber.query.filter_by(email=email).first()
   if existing:
       if existing.unsubscribed_at:
           existing.unsubscribed_at = None
           existing.confirmed = False
           existing.token = uuid.uuid4().hex
           existing.expires_at = utc_now() + timedelta(days=365)
           db.session.commit()
           send_confirmation(existing)
           flash("Check your inbox to confirm your subscription.", "success")
       elif existing.confirmed:
           flash("You're already subscribed.", "success")
       else:
           flash("Check your inbox to confirm your subscription.", "success")
       return redirect(request.referrer or "/")
   ```

4. Update newsletter scheduler query in `scheduler.py` to exclude soft-deleted:
   ```python
   subscribers = Subscriber.query.filter_by(confirmed=True).filter(
       Subscriber.unsubscribed_at.is_(None)
   ).all()
   ```

5. Add `unsubscribed` filter option to admin subscribers list in `admin.py`:
   ```python
   elif filter_status == "unsubscribed":
       query = query.filter(Subscriber.unsubscribed_at.isnot(None))
   ```

6. Generate migration:
   ```bash
   flask db migrate -m "add unsubscribed_at to subscribers"
   flask db upgrade
   ```

**Requires adding `uuid` and `timedelta` to imports in `public.py`.**

---

### 2.4 Slug Generation Race Condition ✅ (Already present)

**Severity:** Low — data integrity under concurrent requests.

**File:** `app/models.py:80`, `app/routes/admin.py:40-53`

**Problem:** `_generate_unique_slug()` checks for existence then inserts. Between check and insert, another request could create the same slug. The `slug` column has an index but no UNIQUE constraint.

**Fix:** Add `unique=True` to `Post.slug` in `app/models.py`:

```python
slug = db.Column(db.String(256), unique=True, nullable=False)
```

The `IntegrityError` handling in `new_post()` already exists (~line 220 in admin.py). Add similar handling to `edit_post()` if missing. Generate migration after the model change.

**Note:** `unique=True` was already present in the model. No changes needed.

---

## Phase 3: Code Quality & Performance ✅ COMPLETED

### 3.1 Extract Shared `nh3.clean()` Config ✅

**Severity:** Medium — code duplication with drift risk.

**Files:** `app/__init__.py:92-103`, `app/routes/admin.py:505-516`

**Problem:** The allowed tags and attributes are duplicated verbatim. Updating one without the other causes preview/render divergence.

**Fix:** Create `app/markdown_config.py` with shared constants:

```python
MARKDOWN_ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "s", "code", "pre", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td", "hr", "span", "div",
}

MARKDOWN_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "span": {"class"},
    "div": {"class"},
    "*": {"class"},
}
```

Update `app/__init__.py` and `app/routes/admin.py` to import from `app/markdown_config.py`.

---

### 3.2 Add Database Indexes for Analytics ✅

**Severity:** Medium — performance at scale.

**File:** `app/models.py`

**Problem:** Analytics queries group by `created_at`, join on `post_id`, and group by `share_events.post_id`. None of these columns have indexes.

**Fix:** Add indexes to `PageView` and `ShareEvent`:

```python
class PageView(db.Model):
    __table_args__ = (
        db.Index("ix_page_views_post_id", "post_id"),
        db.Index("ix_page_views_created_at", "created_at"),
    )

class ShareEvent(db.Model):
    __table_args__ = (
        db.Index("ix_share_events_post_id", "post_id"),
    )
```

Generate migration: `flask db migrate -m "add indexes for analytics queries"`

---

### 3.3 Session Timeout Timezone Handling ✅ COMPLETED

**Severity:** Low — edge case if server timezone changes.

**File:** `app/__init__.py:121-130`

**Problem:** Session `last_activity` stored as ISO string, compared with `datetime.utcnow()`. Timezone changes between sessions can cause premature expiry.

**Fix:** Changed to store Unix timestamp (`time.time()`) instead of ISO string. Added backward compatibility for existing sessions (ISO strings are parsed as UTC and converted to timestamp). Timezone‑aware comparisons are no longer needed.

**Status:** Completed. Session now uses numeric timestamps, eliminating timezone dependency.

---

### 3.4 Separate Dev Dependencies ✅

**Severity:** Low — packaging hygiene.

**Files:** `requirements.txt`, `requirements-dev.txt` (new)

**Problem:** `pytest>=9.0.2` is in the main `requirements.txt`. Production doesn't need test frameworks.

**Fix:**

1. Create `requirements-dev.txt`:
   ```
   -r requirements.txt
   pytest>=9.0.2
   ```
2. Remove `pytest>=9.0.2` from `requirements.txt`.
3. Update `setup.sh` to install from `requirements-dev.txt`.

---

### 3.5 Fix `setup.sh` Python Version Check ✅

**Severity:** Low — misleading minimum version.

**File:** `setup.sh:11`

**Problem:** Checks for Python 3.11+ but dependencies (Flask 3.1+, etc.) need 3.12+. README states 3.14+.

**Fix:** Update minimum to 3.12:

```bash
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]); then
    echo "Error: Python 3.12 or higher is required. Found: Python $PYTHON_VERSION"
    exit 1
fi
```

---

## Phase 4: Test Coverage & Quality ✅ COMPLETED

### 4.1 Add Health-Check Endpoint ✅

**File:** `app/routes/public.py`

**Steps:**
1. Add `GET /health` route returning JSON:
   ```json
   {"status": "ok", "database": "connected", "timestamp": "2026-03-27T12:34:56Z"}
   ```
2. Check DB connectivity via `db.session.execute(text('SELECT 1'))`.
3. No rate limiting, no authentication required.
4. Add tests for success and DB failure scenarios.

---

### 4.2 Fix Test Code Quality Issues ✅

**File:** `tests/conftest.py`, `tests/test_rate_limit.py`

**Items:**

1. **Remove redundant `_datetime_now()` in conftest** — it's a wrapper that just calls `utc_now()`. Replace all usages with `utc_now()` directly and remove the function.

2. **Fix test importing private rate limit state** — `test_rate_limit.py:16-17` imports `_attempts` and `_lockouts`. Add a `clear_all()` function to `app/rate_limit.py`:
   ```python
   def clear_all() -> None:
       """Clear all rate limit state. For testing only."""
       _attempts.clear()
       _lockouts.clear()
   ```
   Then use `from app.rate_limit import clear_all` in tests.

---

### 4.3 Add Missing Tests ✅ COMPLETED

Extended `tests/test_coverage.py` and other test files for untested scenarios:

| Scenario | Test File | Status |
|----------|-----------|--------|
| Unsubscribe timing consistency (valid, invalid, expired tokens all take ~0.1s) | `test_public.py` | ✅ Added `test_unsubscribe_timing_constant` |
| GIF89a upload accepted | `test_admin.py` | ✅ Added `test_upload_gif87a_image`, `test_upload_gif89a_image` |
| Slug collision handling (`_generate_unique_slug` appends counters) | `test_admin.py` | ✅ Added `test_slug_collision_handling` |
| Tag validation (Unicode, long names, duplicates) | `test_coverage.py` | ✅ Already covered (`test_create_tag_invalid_name`) |
| Newsletter reset for unsent post | `test_coverage.py` | ✅ Already covered (`test_newsletter_reset`) |
| Expired subscriber token unsubscribe | `test_coverage.py` | ✅ Already covered (included in timing test) |
| SMTP failure mock in newsletter sending | `test_email.py` | ✅ Added `test_send_newsletter_smtp_failure`, `test_send_newsletter_smtp_disconnected`, `test_send_newsletter_generic_smtp_error` |
| Image upload with corrupted headers | `test_admin.py` | ✅ Added `test_upload_invalid_gif_header` |
| API rate limiting (`/api/track-share`) | `test_rate_limit.py` | ✅ Added `test_api_rate_limit` |
| `POST /admin/preview-markdown` valid/invalid input | `test_admin.py` | ✅ Added `test_preview_markdown`, `test_preview_markdown_invalid` |
| `POST /admin/media/delete/<filename>` auth, traversal, 404 | `test_admin.py` | ✅ Added `test_delete_media_requires_auth`, `test_delete_media_authenticated` |
| `GET /admin/subscribers/export` CSV output | `test_admin.py` | ✅ Added `test_export_subscribers_requires_auth`, `test_export_subscribers_csv` |
| `POST /admin/subscribers/delete/<id>` auth required | `test_admin.py` | ✅ Added `test_delete_subscriber_requires_auth`, `test_delete_subscriber_authenticated` |

Run tests:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

**Status:** Completed (82 tests pass). All low‑priority tests added.

---

### 4.4 SQLite Backup Utility ✅

**File:** `backup.py` (new, project root)

**Steps:**
1. Load config to locate `instance/blog.db`.
2. Create timestamped backup in `backups/` directory.
3. Use SQLite's `.backup` API via `sqlite3` module for consistent snapshots.
4. Optional `--compress` flag for gzip, `--keep N` to retain last N backups (default 7).

**Verification:** `python backup.py && ls backups/`

---

## Phase 5: Features (Future / Deferred)

The following are documented for future consideration but are deferred to avoid scope creep:

| Feature | Notes |
|---------|-------|
| Multi-worker rate limiting | Document limitation in AGENTS.md (already done). Options: file-based locking, SQLite-backed, or accept single-worker. |
| Search pagination | Add pagination to `/search` results |
| Type hints on route handlers | Large mechanical change; apply incrementally |
| Structured security event logging | Add `security_log()` helper with IP, event type, context |
| Newsletter reconnection retry | Track failed subscribers, retry once before aborting |
| Content versioning | `PostRevision` model, save on edit, restore UI |
| Draft scheduling | `scheduled_at` field, auto-publish via scheduler |
| Caching layer | Flask-Caching with SimpleCache for tag lists, popular posts |
| Session timeout timezone handling | Use timezone-aware datetimes or Unix timestamps for `last_activity` |
| Add missing tests | Extended test coverage for edge cases (see 4.3) |

---

## Execution Order

| # | Item | Phase | Effort | Status |
|---|------|-------|--------|--------|
| 1 | Fix broken migration (1.1) | 1 | 15 min | ✅ Completed |
| 2 | Fix media mtime bug (1.2) | 1 | 10 min | ✅ Completed |
| 3 | Fix GIF89a validation (1.3) | 1 | 10 min | ✅ Completed |
| 4 | Fix unsubscribe timing (2.1) | 2 | 15 min | ✅ Completed |
| 5 | Fix broad exception catch (2.2) | 2 | 10 min | ✅ Completed |
| 6 | Subscriber soft delete (2.3) | 2 | 45 min | ✅ Completed |
| 7 | Slug unique constraint (2.4) | 2 | 20 min | ✅ Already present |
| 8 | Extract nh3 config (3.1) | 3 | 20 min | ✅ Completed |
| 9 | Analytics indexes (3.2) | 3 | 15 min | ✅ Completed |
| 10 | Session timezone fix (3.3) | 3 | 15 min | ✅ Completed |
| 11 | Separate dev dependencies (3.4) | 3 | 10 min | ✅ Completed |
| 12 | Fix setup.sh version check (3.5) | 3 | 5 min | ✅ Completed |
| 13 | Health-check endpoint (4.1) | 4 | 30 min | ✅ Completed |
| 14 | Fix test code quality (4.2) | 4 | 15 min | ✅ Completed |
| 15 | Add missing tests (4.3) | 4 | 2 hrs | ✅ Completed |
| 16 | Backup utility (4.4) | 4 | 45 min | ✅ Completed |

**Total completed:** 16 items | **Deferred:** 0 items (low‑priority tests can be added later)

---

## Verification

After each phase, run the full test suite:

```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

After schema changes, verify migrations apply cleanly on a fresh database:

```bash
rm -f instance/blog.db
flask db upgrade
```

Verify the app starts:

```bash
python run.py
```

---

## Out of Scope

- PostgreSQL/MySQL migration
- Redis for caching/sessions/rate limiting
- Celery/task queues (APScheduler already in place)
- External CDN or asset hosting
- Horizontal scaling features
