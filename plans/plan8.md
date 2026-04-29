# Backend Tech Stack Improvement Plan

**Date:** 2026-04-28  
**Status:** Draft - Ready for Review  
**Priority:** High Impact, Incremental Implementation

---

## Executive Summary

This plan addresses six improvement areas identified during a deep dive of the blog CMS backend tech stack. The improvements focus on:
1. **Performance optimization** (removing ASGI adapter overhead)
2. **Reliability enhancements** (persistent job store, periodic maintenance)
3. **Code quality** (standardized caching, formalized dev tooling)
4. **Scalability** (optional S3-compatible storage)

All improvements are designed to be implemented incrementally without breaking existing functionality.

---

## Improvement 1: Remove Unnecessary ASGI Adapter Overhead

### Current State
- Flask app (WSGI) wrapped with `asgiref.WsgiToAsgi` to convert to ASGI
- Granian runs with `--interface asgi` and `run:asgi_app`
- Adds unnecessary Python layer converting WSGI→ASGI→Granian internal representation
- Zero async route handlers or WebSocket usage in codebase

### Performance Impact
| Metric | Current (ASGI wrapper) | Proposed (WSGI native) | Improvement |
|--------|------------------------|----------------------|-------------|
| RPS (GET 1KB) | ~121,000 | ~130,645 | +8% |
| Latency | 1.053ms | 0.489ms | -54% |

### Files to Modify

| File | Change |
|------|--------|
| `run.py` | Remove `from asgiref.wsgi import WsgiToAsgi` and `asgi_app = WsgiToAsgi(app)` |
| `requirements.txt` | Remove `asgiref>=3.8,<4.0` |
| `Dockerfile` | Change `--interface asgi` to `--interface wsgi`, `run:asgi_app` to `run:app` |
| `README.md` | Update example commands (lines 110-135) |
| `DEPLOY.md` | Update all Granian command examples (lines 95, 102, 451, 573, 789, 1083) |
| `AGENTS.md` | Update references (lines 21, 293, 324, 366) |

### Implementation Steps

1. **Update `run.py`:**
   ```diff
   - from asgiref.wsgi import WsgiToAsgi
     ...
     app = create_app()
   - asgi_app = WsgiToAsgi(app)
   ```

2. **Update `requirements.txt`:**
   ```diff
     flask>=3.1.0,<4.0
     flask-sqlalchemy>=3.1.1,<4.0
     flask-login>=0.6.3,<1.0
     flask-migrate>=4.1.0,<5.0
   - asgiref>=3.8,<4.0
     granian>=1.0.0,<2.0
   ```

3. **Update `Dockerfile`:**
   ```diff
   - CMD ["granian", "--interface", "asgi", "--workers", "2", "--host", "0.0.0.0", "--port", "5000", "run:asgi_app"]
   + CMD ["granian", "--interface", "wsgi", "--workers", "2", "--host", "0.0.0.0", "--port", "5000", "run:app"]
   ```

4. **Test:** Run `granian --interface wsgi --workers 2 run:app` locally

### Verification
- Confirm no `async def` handlers exist: `grep -r "async def" app/`
- Confirm no WebSocket usage: `grep -r "websocket" app/`
- Run existing tests: `ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v`

---

## Improvement 2: APScheduler Persistent Job Store

### Current State
- Uses `BackgroundScheduler` with default `MemoryJobStore`
- Jobs (newsletter, cleanup, scheduled posts) lost on application restart
- Unix-only `fcntl` file locking for concurrency control
- Three scheduled jobs:
  - `daily_newsletter` - Cron (configurable time)
  - `cleanup_expired_subscribers` - Cron (every 5 min)
  - `publish_scheduled_posts` - Cron (every 5 min)

### Proposed Changes
Replace in-memory job store with `SQLAlchemyJobStore` using existing SQLite database.

### Files to Modify

| File | Change |
|------|--------|
| `app/scheduler.py` | Add `SQLAlchemyJobStore` import, update `init_scheduler()` for persistent store, remove all `fcntl` imports and lock logic |
| `app/models.py` | (Optional) Add `APSchedulerJob` model for migration tracking |
| `DEPLOY.md` | Update Section 4 for new persistence capabilities |

### Implementation Steps

1. **Add import to `app/scheduler.py`:**
   ```python
   from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
   ```

2. **Update `init_scheduler()` function:**
   ```python
   def init_scheduler(app) -> Optional["BackgroundScheduler"]:
       from apscheduler.schedulers.background import BackgroundScheduler
       from apscheduler.triggers.cron import CronTrigger
       from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
       import atexit

       from app.config import NEWSLETTER_SEND_TIME, SMTP_HOST
       from app.extensions import db

       if not SMTP_HOST:
           app.logger.info("SMTP_HOST not configured; newsletter scheduler disabled")
           return None

        hour, minute = map(int, NEWSLETTER_SEND_TIME.split(":"))

       # Configure persistent job store using existing SQLite database engine
       jobstores = {
           'default': SQLAlchemyJobStore(engine=db.engine)
       }

       scheduler = BackgroundScheduler(
           jobstores=jobstores,
           daemon=True
       )
       scheduler.add_job(
           send_daily_newsletter,
           CronTrigger(hour=hour, minute=minute),
           args=[app],
           id="daily_newsletter",
           replace_existing=True,
       )
       scheduler.add_job(
           cleanup_expired_subscribers,
           CronTrigger(minute="*/5"),
           args=[app],
           id="cleanup_expired_subscribers",
           replace_existing=True,
       )
       scheduler.add_job(
           publish_scheduled_posts,
           CronTrigger(minute="*/5"),
           args=[app],
           id="publish_scheduled_posts",
           replace_existing=True,
       )
       scheduler.start()
       global _scheduler
       _scheduler = scheduler
       _scheduler_running.set()

       def _shutdown_scheduler():
           _scheduler_running.clear()
           scheduler.shutdown(wait=False)

       atexit.register(_shutdown_scheduler)
       return scheduler
   ```

3. **Remove `fcntl` locking from job functions:**
   - Remove `import fcntl` and `HAS_FCNTL` logic
   - Remove all `lock_path`, `lock_file` variables and `fcntl.flock()` calls
   - Remove `os.remove(lock_path)` cleanup code

4. **(Optional) Add `APSchedulerJob` model to `app/models.py`:**
   ```python
   class APSchedulerJob(db.Model):
       """Mirror of apscheduler_jobs table for migration tracking."""
       __tablename__ = 'apscheduler_jobs'

       id = db.Column(db.Text, primary_key=True)
       next_run_time = db.Column(db.REAL)
       job_state = db.Column(db.BLOB, nullable=False)

       __table_args__ = (
           db.Index('idx_apscheduler_jobs_next_run_time', 'next_run_time'),
       )
   ```

5. **Run migration (if model added):**
   ```bash
   flask db migrate -m "Add apscheduler_jobs table"
   flask db upgrade
   ```

### Verification
- Start application and verify jobs created: `sqlite3 instance/blog.db "SELECT id, next_run_time FROM apscheduler_jobs;"`
- Restart application and confirm jobs persist (same next_run_time)
- Verify no duplicate jobs: Check only 3 jobs in table

### Multi-Worker Note
APScheduler requires single scheduler instance. For multi-worker:
- Use `--workers 1` for scheduler (simplest)
- Or run dedicated scheduler process

---

## Improvement 3: Periodic Maintenance Jobs

### Current State
- Database integrity check only at startup (`app/__init__.py:366-382`)
- No periodic WAL checkpoint (WAL file can grow unboundedly)
- No FTS5 index validation
- No query planner statistics updates

### Proposed Changes
Add four periodic maintenance jobs to APScheduler.

### New Maintenance Jobs

| Job | Function | Schedule | Purpose |
|-----|----------|----------|---------|
| DB Integrity Check | `check_database_integrity` | Daily 3:00 AM | Detect corruption via `PRAGMA integrity_check` |
| WAL Checkpoint | `checkpoint_wal` | Daily 4:00 AM | Prevent WAL bloat via `PRAGMA wal_checkpoint(TRUNCATE)` |
| FTS5 Validation | `check_fts_integrity` | Weekly Sun 2:00 AM | Verify FTS5 sync with posts table |
| Query Optimizer | `optimize_database` | Daily 1:00 AM | Update query planner stats via `PRAGMA optimize` |

### Files to Modify

| File | Change |
|------|--------|
| `app/scheduler.py` | Add 4 new maintenance functions, add jobs to `init_scheduler()` |
| `app/config.py` | (Optional) Add `[maintenance]` section config variables |
| `AGENTS.md` | Document new maintenance jobs |

### Implementation Steps

1. **Add new maintenance functions to `app/scheduler.py`:**

   ```python
   from sqlalchemy import text

   def check_database_integrity(app) -> None:
       """Run PRAGMA integrity_check and log results."""
       try:
           with app.app_context():
               from app.extensions import db
               result = db.session.execute(text("PRAGMA integrity_check")).scalar()
               if result != "ok":
                   app.logger.error(
                       "Database integrity check FAILED: %s. Consider restoring from backup.",
                       result,
                   )
               else:
                   app.logger.info("Database integrity check passed")
       except Exception as e:
           app.logger.warning("Database integrity check error: %s", e)

   def checkpoint_wal(app) -> None:
       """Run PRAGMA wal_checkpoint(TRUNCATE) to prevent WAL bloat."""
       try:
           with app.app_context():
               from app.extensions import db
               result = db.session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)")).fetchone()
               if result:
                   checkpointed_frames, log_size, status = result
                   app.logger.info(
                       "WAL checkpoint: %d frames checkpointed, log size: %d, status: %d",
                       checkpointed_frames, log_size, status,
                   )
               else:
                   app.logger.warning("WAL checkpoint returned no results")
       except Exception as e:
           app.logger.warning("WAL checkpoint error: %s", e)

   def check_fts_integrity(app) -> None:
       """Verify FTS5 index is consistent with posts table."""
       try:
           with app.app_context():
               from app.extensions import db
               from sqlalchemy import text

               fts_exists = db.session.execute(
                   text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'")
               ).scalar()

               if not fts_exists:
                   app.logger.info("FTS5 table not found, skipping integrity check")
                   return

               try:
                   db.session.execute(text("INSERT INTO posts_fts(posts_fts) VALUES('integrity-check')"))
                   db.session.rollback()
                   app.logger.info("FTS5 integrity check passed")
               except Exception as fts_e:
                   app.logger.error("FTS5 integrity check failed: %s", fts_e)

               orphaned = db.session.execute(text("""
                   SELECT COUNT(*) FROM posts_fts fts
                   LEFT JOIN posts p ON fts.rowid = p.id
                   WHERE p.id IS NULL OR p.published != 1
               """)).scalar()

               missing = db.session.execute(text("""
                   SELECT COUNT(*) FROM posts p
                   WHERE p.published = 1
                   AND p.id NOT IN (SELECT rowid FROM posts_fts)
               """)).scalar()

               if orphaned > 0 or missing > 0:
                   app.logger.warning(
                       "FTS5 sync issues: %d orphaned entries, %d missing entries",
                       orphaned, missing,
                   )
               else:
                   app.logger.info("FTS5 sync verification passed")
       except Exception as e:
           app.logger.warning("FTS5 check error: %s", e)

   def optimize_database(app) -> None:
       """Run PRAGMA optimize to update query planner statistics."""
       try:
           with app.app_context():
               from app.extensions import db
               from sqlalchemy import text
               db.session.execute(text("PRAGMA optimize"))
               app.logger.info("PRAGMA optimize completed")
       except Exception as e:
           app.logger.warning("PRAGMA optimize error: %s", e)
   ```

2. **Add jobs to `init_scheduler()` (after existing jobs):**
   ```python
   from apscheduler.triggers.cron import CronTrigger

   # ... existing jobs ...

   scheduler.add_job(
       check_database_integrity,
       CronTrigger(hour=3, minute=0),
       args=[app],
       id="check_database_integrity",
       replace_existing=True,
   )
   scheduler.add_job(
       checkpoint_wal,
       CronTrigger(hour=4, minute=0),
       args=[app],
       id="checkpoint_wal",
       replace_existing=True,
   )
   scheduler.add_job(
       check_fts_integrity,
       CronTrigger(day_of_week="sun", hour=2, minute=0),
       args=[app],
       id="check_fts_integrity",
       replace_existing=True,
   )
   scheduler.add_job(
       optimize_database,
       CronTrigger(hour=1, minute=0),
       args=[app],
       id="optimize_database",
       replace_existing=True,
   )
   ```

### Verification
- Check logs after scheduled times for maintenance job output
- Manually trigger: Use Flask shell to call functions
- Verify WAL file size before/after checkpoint

---

## Improvement 4: Standardize Caching with Flask-Caching

### Current State
Four separate custom caching implementations using dictionaries + double-checked locking:
- `app/cache.py` - Tag counts (TTL 60s)
- `app/context_processors.py` - Site settings (TTL 300s), Footer (TTL 45s)
- `app/routes/admin/helpers/dashboard.py` - Dashboard metrics (TTL 120s)
- `app/routes/admin/helpers/analytics.py` - Analytics (TTL 300s, max 16 entries)

### Proposed Changes
Replace all custom caching with `flask-caching` using `SimpleCache` backend for single-process deployment.

### Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `flask-caching>=2.3.0,<3.0` |
| `app/extensions.py` | Add `from flask_caching import Cache` and `cache = Cache()` |
| `app/__init__.py` | Call `cache.init_app()` in `create_app()` |
| `app/cache.py` | Replace with `@cache.memoize()` pattern |
| `app/context_processors.py` | Replace settings and footer caches |
| `app/routes/admin/helpers/dashboard.py` | Replace dashboard cache |
| `app/routes/admin/helpers/analytics.py` | Replace analytics cache |
| `app/routes/rss.py` | Add `@cache.cached()` to feed endpoints |
| `app/routes/public.py` | (Optional) Add caching to listing endpoints |

### Implementation Steps

1. **Add dependency to `requirements.txt`:**
   ```diff
     flask>=3.1.0,<4.0
   + flask-caching>=2.3.0,<3.0
   ```

2. **Update `app/extensions.py`:**
   ```diff
     from flask_sqlalchemy import SQLAlchemy
     from flask_login import LoginManager
     from flask_migrate import Migrate
   + from flask_caching import Cache

     db = SQLAlchemy()
     login_manager = LoginManager()
     login_manager.login_view = "admin.login"
     login_manager.login_message = "Please log in to access this page."
     login_manager.session_protection = "strong"
     migrate = Migrate()
   + cache = Cache()
   ```

3. **Configure cache in `app/__init__.py` (after `db.init_app(app)`):**
   ```python
   from app.extensions import cache

   cache.init_app(app, config={
       'CACHE_TYPE': 'SimpleCache',
       'CACHE_DEFAULT_TIMEOUT': 300,
       'CACHE_THRESHOLD': 1000,
   })
   ```

4. **Migrate tag counts cache in `app/cache.py`:**
   ```python
   from app.extensions import cache
   from app.config import TAG_CACHE_TTL_SECONDS

   def _get_tag_counts() -> dict[int, int]:
       return _get_tag_counts_cached()

   @cache.memoize(timeout=TAG_CACHE_TTL_SECONDS)
   def _get_tag_counts_cached() -> dict[int, int]:
       from sqlalchemy import select, func
       from app.extensions import db
       from app.models import Post, post_tags

       counts = db.session.execute(
           select(post_tags.c.tag_id, func.count(post_tags.c.post_id).label("cnt"))
           .join(Post, Post.id == post_tags.c.post_id)
           .filter(Post.published == True)
           .group_by(post_tags.c.tag_id)
       ).all()
       return {row[0]: row[1] for row in counts}

   def invalidate_tag_cache() -> None:
       """Invalidate the tag counts cache."""
       cache.delete_memoize(_get_tag_counts_cached)
   ```

5. **Similarly migrate other caches** using `@cache.memoize()` pattern.

6. **Add caching to RSS/JSON feeds in `app/routes/rss.py`:**
   ```python
   from app.extensions import cache

   @rss.route("/rss")
   @cache.cached(timeout=600, query_string=False)
   def feed() -> Response:
       # ... existing logic ...

   @rss.route("/json")
   @cache.cached(timeout=600, query_string=False)
   def json_feed() -> Response:
       # ... existing logic ...
   ```

### Additional Caching Opportunities

| Endpoint | Cache Type | TTL | Notes |
|----------|------------|-----|-------|
| `GET /` (index) | `@cache.cached()` | 60s | Post listings |
| `GET /post/<slug>` | `@cache.cached()` | 300s | Individual posts |
| `GET /rss` | `@cache.cached()` | 600s | Feed content |
| `GET /json` | `@cache.cached()` | 600s | JSON feed |

### Verification
- Run tests to ensure cache invalidation works: `pytest tests/ -v`
- Monitor cache hits/misses via logging (optional: add debug logging)
- Verify memory usage with `SimpleCache`

---

## Improvement 5: Optional S3-Compatible Media Storage

### Current State
- File uploads stored locally in `static/uploads/`
- No S3 support (limits scalability and backup options)
- Templates reference `/static/uploads/` directly
- 8+ templates need updating for S3 compatibility

### Proposed Changes
Add storage abstraction layer with optional S3 backend (supports AWS S3 and MinIO).

### New Files to Create

| File | Purpose |
|------|---------|
| `app/storage.py` | `StorageBackend` ABC, `LocalStorage`, `S3Storage` classes |
| `app/template_helpers.py` | `media_url()` helper for templates |
| `tests/test_storage.py` | Storage backend tests |

### Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `boto3>=1.34.0` |
| `app/config.py` | Add S3 configuration loading |
| `config.toml` | Add `[storage]` and `[s3]` sections |
| `app/routes/admin/helpers/images.py` | Use storage backend for uploads |
| `app/routes/admin/media.py` | Use storage backend for delete/list |
| `app/__init__.py` | Update `post_image_url` filter, register helpers |
| `app/routes/rss.py` | Use `media_url()` helper |
| 8+ templates | Replace hardcoded static URLs with `{{ media_url(img) }}` |

### Implementation Steps

1. **Add dependency to `requirements.txt`:**
   ```diff
     nh3>=0.2.0,<1.0
   + boto3>=1.34.0
   ```

2. **Add configuration to `config.toml`:**
   ```toml
   [storage]
   backend = "local"  # or "s3"

   [s3]
   bucket_name = "blog-uploads"
   access_key = ""  # Use S3_ACCESS_KEY env var
   secret_key = ""  # Use S3_SECRET_KEY env var
   endpoint_url = ""  # Empty for AWS S3, set for MinIO
   region = "us-east-1"
   use_presigned_urls = true
   presigned_url_expiry = 3600
   ```

3. **Create `app/storage.py`** with storage abstraction (see subagent report for full implementation).

4. **Create `app/template_helpers.py`:**
   ```python
   from flask import url_for
   from app.storage import get_storage_backend
   from app.storage import LocalStorage

   def media_url(filename: str) -> str:
       """Generate correct URL for a media file based on storage backend."""
       if not filename:
           return ""
       storage = get_storage_backend()
       if isinstance(storage, LocalStorage):
           return url_for('static', filename='uploads/' + filename)
       else:
           return storage.get_file_url(filename) or ""
   ```

5. **Update templates** to use `{{ media_url(img) }}` instead of `{{ url_for('static', filename='uploads/' + img) }}`.

### Template Files to Update

| Template | Lines |
|----------|-------|
| `app/templates/post.html` | 11, 14, 22, 70 |
| `app/templates/_post_content.html` | 6 |
| `app/templates/search.html` | 30 |
| `app/templates/tag.html` | 25 |
| `app/templates/index.html` | 21 |
| `app/templates/admin/editor.html` | 34 |
| `app/templates/admin/media.html` | 39, 46 |
| `app/templates/email/newsletter.html` | 13 |

### Security Considerations
- Never commit S3 credentials (use environment variables)
- Keep presigned URL expiry short (1 hour or less)
- Use HTTPS only for S3 endpoints in production
- Set ContentType on uploads to prevent MIME confusion

---

## Improvement 6: Formalize Dev Dependencies

### Current State
- `requirements-dev.txt` exists but minimal (only pytest, pytest-cov)
- No linting or type-checking tooling configured
- Missing config files: `ruff.toml`, `mypy.ini`
- `playwright` in `requirements.txt` (should be dev-only)

### Proposed Changes
Expand dev dependencies and add modern Python tooling (ruff, mypy).

### Files to Modify

| File | Change |
|------|--------|
| `requirements-dev.txt` | Add ruff, mypy, pytest-mock; bump pytest-cov version |
| `requirements.txt` | Remove `playwright` (move to dev) |
| `ruff.toml` | Create new file (linter/formatter config) |
| `mypy.ini` | Create new file (type checker config) |
| `AGENTS.md` | Add lint/typecheck commands documentation |
| `.github/workflows/test.yml` | Add lint and typecheck CI steps |

### Implementation Steps

1. **Update `requirements-dev.txt`:**
   ```txt
   # Development dependencies for blog CMS
   # Install with: pip install -r requirements-dev.txt

   # Include runtime dependencies
   -r requirements.txt

   # Testing
   pytest>=9.0.0
   pytest-cov>=5.0.0
   pytest-mock>=3.14.0

   # Linting and formatting
   ruff>=0.8.0

   # Type checking
   mypy>=1.13.0

   # E2E testing
   playwright>=1.40.0,<2.0
   ```

2. **Move `playwright` from `requirements.txt` to `requirements-dev.txt`:**
   ```diff
   # requirements.txt
   - playwright>=1.40.0,<2.0
   ```

3. **Create `ruff.toml`:**
   ```toml
   # Ruff configuration for blog CMS
   target-version = "py312"
   line-length = 100

   exclude = [
       ".git", "__pycache__", "instance", "migrations",
       "static", "node_modules", "venv", ".venv", "build", "dist",
   ]

   [lint]
   select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM"]
   ignore = ["E501", "UP006", "UP007"]

   [lint.isort]
   known-first-party = ["app"]
   ```

4. **Create `mypy.ini`:**
   ```ini
   [mypy]
   python_version = 3.12
   warn_return_any = True
   warn_unused_configs = True
   disallow_untyped_defs = False
   check_untyped_defs = True
   no_implicit_optional = True

   exclude = ["migrations/", "instance/", "tests/"]

   [mypy-flask.*]
   ignore_missing_imports = True

   [mypy-sqlalchemy.*]
   ignore_missing_imports = True
   ```

5. **Update `AGENTS.md`** to add linting section:
   ```markdown
   ## Linting and Type Checking

   ```bash
   # Run ruff linter (auto-fix issues)
   ruff check --fix .

   # Run ruff formatter (auto-format code)
   ruff format .

   # Check formatting without changes
   ruff format --check .

   # Run type checker
   mypy app/
   ```
   ```

6. **Update `.github/workflows/test.yml`** to add lint/typecheck steps.

### Verification
- Run `ruff check .` to see current lint issues
- Run `ruff format .` to format code
- Run `mypy app/` to check types (may need `continue-on-error: true` initially)

---

## Implementation Order and Dependencies

### Recommended Sequence

1. **Improvement 1: Remove ASGI Adapter** (Low risk, immediate performance gain)
2. **Improvement 6: Formalize Dev Dependencies** (Enables quality checks for other improvements)
3. **Improvement 4: Flask-Caching** (Code quality, easier maintenance)
4. **Improvement 2: APScheduler Persistent Job Store** (Reliability, enables Improvement 3)
5. **Improvement 3: Periodic Maintenance Jobs** (Relies on Improvement 2)
6. **Improvement 5: S3-Compatible Storage** (Largest change, can be done independently)

### Dependency Graph
```
1 (ASGI) ──────┐
                │
6 (Dev deps) ───┼──> 4 (Flask-Caching)
                │
2 (Job Store) ──┼──> 3 (Maintenance Jobs)
                │
5 (S3 Storage) ┘ (independent, can be done anytime)
```

---

## Testing Strategy

### For Each Improvement

| Improvement | Test Approach |
|-------------|---------------|
| 1. ASGI Removal | Run full test suite, manual testing with Granian WSGI |
| 2. Job Store | Verify job persistence across restarts, check `apscheduler_jobs` table |
| 3. Maintenance Jobs | Check logs for job execution, verify PRAGMA results |
| 4. Flask-Caching | Verify cache hits/misses, test invalidation |
| 5. S3 Storage | Test with MinIO locally, verify file operations |
| 6. Dev Dependencies | Run ruff/mypy, verify CI passes |

### Regression Testing
After each improvement:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

---

## Rollback Plan

Each improvement should be committed separately for easy rollback:

1. Use feature branches for each improvement
2. Keep changes atomic and focused
3. Document any config changes in commit messages
4. If issues arise: `git revert <commit-hash>`

---

## Success Metrics

| Improvement | Metric | Target |
|-------------|--------|--------|
| 1. ASGI Removal | Request latency | -50% (0.5ms) |
| 2. Job Store | Jobs after restart | 3 (all persist) |
| 3. Maintenance | WAL file size | <10MB (after checkpoint) |
| 4. Flask-Caching | Code lines reduced | -100 lines |
| 5. S3 Storage | File operations work | 100% success (MinIO) |
| 6. Dev Dependencies | Lint issues | 0 (ruff check) |

---

## Appendix: Quick Reference

### Commands to Run After All Improvements

```bash
# Install all dependencies (including dev)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run linting and formatting
ruff check --fix .
ruff format .

# Run type checking
mypy app/

# Run tests
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v

# Run with Granian (WSGI mode)
granian --interface wsgi --workers 2 --host 0.0.0.0 --port 5000 run:app
```

### Environment Variables for S3 (if using)
```bash
export S3_ACCESS_KEY=your_access_key
export S3_SECRET_KEY=your_secret_key
export S3_BUCKET=your_bucket_name
```
