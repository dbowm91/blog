# Merged Improvement Plan

Consolidated from plan2–plan5, deduplicated, reordered, and verified against the codebase.

---

## COMPLETED ITEMS

### HIGH Priority

- [DONE] #1. Re-send confirmation email for unconfirmed subscribers
- [DONE] #2. Fix token enumeration on confirm endpoint
- [DONE] #3. Invalidate tag cache on post create/edit/delete
- [DONE] #4. Add IntegrityError handling to edit_post

### MEDIUM Priority

- [DONE] #8. Order RSS feed by published_at
- [DONE] #10. Add pagination to media gallery
- [DONE] #11. Narrow broad exception handling in email module
- [DONE] #12. Extract duplicate tag validation

### LOW Priority

- [DONE] #15. Tag cache thread safety
- [DONE] #17. Set SESSION_COOKIE_HTTPONLY explicitly
- [DONE] #18. Escape single quotes in xml_escape
- [DONE] #19. Remove deprecated X-XSS-Protection header
- [DONE] #20. Fix newsletter test email address
- [DONE] #21. Add `__all__` exports

---

## REMAINING ITEMS

See deferred.md for items that were skipped.

## HIGH Priority (Remaining)

### 5. Replace in-memory rate limiting with Redis

**File:** `app/rate_limit.py`

**Problem:** Rate limiting uses Python dicts (`_lockouts`, `_attempts`) which are not shared across workers, lost on restart, and ineffective in multi-worker deployments.

**Fix:** Implement Redis-based rate limiting. Use `REDIS_URL` env var, fall back to in-memory if Redis unavailable. Keep `app/rate_limit.py` as fallback module.

**Tasks:**
- Add Redis dependency to `requirements.txt`
- Create Redis connection utility (new `app/cache.py` or `app/redis_rate_limit.py`)
- Add `USE_REDIS` config option in `config.toml`
- Rewrite rate limit functions to use Redis
- Update tests to mock Redis

---

### 6. Add account lockout after repeated failures

**File:** `app/rate_limit.py`

**Problem:** After lockout expires, attackers can retry indefinitely. No permanent ban after N lockouts.

**Fix:** Track number of lockouts per IP. After N lockouts (e.g., 3), apply longer cooldown or require admin intervention. Add admin route to clear permanent bans.

---

### 7. Wrap delete operations in try/except with rollback

**Files:** `app/routes/admin.py:290-304` (delete_post), `app/routes/admin.py:679-688` (bulk delete)

**Problem:** `delete_post()` deletes the image file from disk before `db.session.commit()`. If the commit fails, the image is already gone. Neither delete_post nor bulk delete has error handling.

**Fix:** Wrap database operations in try/except with `db.session.rollback()` on error. Consider deleting the image file *after* the DB commit succeeds. Add flash error message on failure.

**Tests:**
- Add tests for delete failure scenarios

---

## MEDIUM Priority (Remaining)

### 9. Add search performance safeguards

**File:** `app/routes/public.py:149-161`

**Problem:** `ILIKE` on `body` column is a full table scan with no query timeout. Will degrade with scale.

**Fix:**
- Add search query timeout using SQLAlchemy `execution_options`
- Add index on `posts.title` and `posts.summary` for LIKE queries
- Consider SQLite FTS5 integration (keep fallback to LIKE)
- Document that search performance degrades at scale

---

### 13. Rotate subscriber tokens after use

**Files:** `app/routes/public.py`, `app/models.py`

**Problem:** Subscriber tokens are static UUID hex — if compromised, valid indefinitely (though `expires_at` limits unsubscribe).

**Fix:** Rotate token after confirmation. Add `token_version` column (optional). Generate migration for new field.

---

### 14. Make upload size configurable

**Files:** `app/__init__.py:53,83`, `config.toml`

**Problem:** Hardcoded 16MB limit and error message.

**Fix:** Add `max_upload_size` to config.toml `[app]` section, load in `config.py`, use in `create_app()`, make error message dynamic.

---

## LOW Priority (Remaining)

### 16. Admin password mismatch warning

**File:** `app/__init__.py:196-201`

**Problem:** Only logs a warning if `ADMIN_PASSWORD` env var doesn't match stored hash. Old password remains active, which is confusing.

**Fix:** Add admin dashboard warning banner when password doesn't match env var, or add a startup flag to track mismatch state.

---

## FUTURE / INFRASTRUCTURE

### 22. Health check endpoint

Add `/health` returning JSON status with DB connectivity check. Return 200 if healthy, 503 if degraded. Consider auth for sensitive info.

### 23. Add CI/CD pipeline

GitHub Actions for tests (pytest), linting (ruff), type checking (mypy), Docker image build.

### 24. Containerization

Dockerfile with multi-stage build, docker-compose.yml, .dockerignore. Mount `instance/` and `logs/` as volumes.

### 25. Automated backups with verification

Cron job for daily backups. Add SQLite `PRAGMA integrity_check`, checksum verification, optional S3 upload.

### 26. Request ID logging

Middleware to generate UUID per request. Include in log messages and `X-Request-ID` response header.

### 27. Monitoring and error tracking

Optional Sentry integration, request logging middleware, Prometheus-compatible `/metrics` endpoint.

### 28. Requirements lock file

Generate `requirements.lock` with pinned versions for reproducible builds.

### 29. Process management configuration

Systemd service file, Gunicorn config, log rotation, restart policy.

### 30. Database connection pooling pragmas

SQLite: `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `PRAGMA synchronous=NORMAL`. Document PostgreSQL migration path.

### 31. Handle email bounces

Track `bounce_count` per subscriber. After N bounces, mark as inactive. Add admin UI for bounce status.

---

## Verification

After each phase, run:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ -v
```

## Documentation Updates

After implementation, update:
- `AGENTS.md` with new patterns and config
- `README.md` with new features
- `.env.example` with new environment variables