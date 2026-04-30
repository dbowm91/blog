# Plan: Complete Remaining Items

**Date:** 2026-04-30
**Status:** IN PROGRESS

---

## Remaining Items

### Item 6.5: Add Celery Worker to Dockerfile [P2]
- **Issue:** Dockerfile CMD only runs `granian` (ASGI server). Docker deployments cannot use async tasks (newsletter, image processing, webhooks).
- **Fix:** Add Celery worker startup to Dockerfile or create separate docker-compose service.
- **Impact:** Docker-based deployments can use async task processing.

### Item 4.3: Add Type Hints to Admin Routes [P3]
- **Issue:** 7 of 11 admin route files lack type hints, inconsistent with the 4 that have them.
- **Files missing type hints:**
  - `app/routes/admin/users.py`
  - `app/routes/admin/tags.py`
  - `app/routes/admin/pages.py`
  - `app/routes/admin/sessions.py`
  - `app/routes/admin/backup.py`
  - `app/routes/admin/analytics.py`
  - `app/routes/admin/newsletter.py`
  - `app/routes/admin/settings.py`
- **Fix:** Add `from __future__ import annotations` and `-> Response` return type hints to all route handlers.
- **Impact:** Consistent code quality across admin routes.

---

## Implementation Order

| # | Item | Files | Status |
|---|------|-------|--------|
| 1 | Celery Worker in Dockerfile | Dockerfile, docker-compose.yml | Pending |
| 2 | Type Hints in Admin Routes | 8 files | Pending |

---

## Notes

- Celery worker in Dockerfile: Options are (a) add to CMD script, (b) separate docker-compose service, or (c) just document how to run separately
- Type hints: Use `-> Response` for Flask route handlers, add `from __future__ import annotations` at top of each file