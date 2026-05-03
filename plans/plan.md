# Consolidated Improvement Plan

**Date:** 2026-05-03
**Status:** In Progress
**Consolidated From:** multiple source plans

## Completed Items
1. ✅ Fixed RSS endpoint references (rss.feed → rss.atom_feed) in templates
2. ✅ Added tests for series routes (coverage 17% → 74%)
3. ✅ Added tests for tasks (coverage 18% → 67%)
4. ✅ Added tests for CLI commands (coverage 27% → 69%)
5. ✅ Added tests for admin comments (coverage 36% → 89%)
6. ✅ Added tests for public comments (coverage 31% → 86%)
7. ✅ Added tests for scheduler (coverage 48% → 61%)
8. ✅ Added tests for utils (coverage 46% → 67%)
9. ✅ Added tests for validators (coverage 32% → 88%)
10. ✅ Added tests for backup service (coverage 50% → 72%)
11. ✅ Added tests for storage (coverage 46% → 52%)
12. ✅ Increased total test coverage from 53% → ~74%

## Remaining Items
1. ⏳️ Increase app/routes/admin/users.py coverage from 49% to 80%+
2. ⏳️ Increase app/filters.py coverage from 47% to 80%+
3. ⏳️ Increase app/page_view_buffer.py coverage from 39% to 80%+
4. ⏳️ Increase app/storage.py coverage from 52% to 80%+
5. ⏳️ Increase app/scheduler.py coverage from 61% to 80%+
6. ⏳️ Handle unused/low-coverage files (backup_encryption, backup_integrity, webhooks, celery_app)
7. ⏳️ Achieve 80%+ total test coverage goal

---

- Admin Blueprint type annotations added
