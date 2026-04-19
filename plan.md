# Improvement Plan

All items from waves 1-8 have been completed.

---

## Wave 1: Critical Bugs (COMPLETED)

- Item 1: SMTP Connection Closed Before Use - FIXED (removed finally block)
- Item 2: Footer Cache Never Serves Cached Data - FIXED (double-checked locking)
- Item 3: Missing `func` Import Causes Scheduler Crash - FIXED (added import)
- Item 4: Undefined CSS Variable `--bg-primary` - FIXED (changed to --bg)
- Item 5: Admin Preview Extends Wrong Base Template - FIXED (changed to admin/base.html)

## Wave 2: Security & Session Fixes (COMPLETED)

- Item 6: Logout Endpoint Missing CSRF Validation - FIXED (added validate_csrf_token)
- Item 7: DB Query on Every Admin Request - FIXED (use session for IP check)
- Item 8: ShareEvent Platform Should Use Allowlist Validation - FIXED (added ALLOWED_SHARE_PLATFORMS)
- Item 9: Add List-Unsubscribe Header to Newsletter Emails - FIXED

## Wave 3: Performance Improvements (COMPLETED)

- Item 10: N+1 Query Problem on Admin Dashboard - FIXED (joinedload for tags)
- Item 11: LIKE Fallback Causes Full Table Scans - FIXED (FTS table existence check)
- Item 12: String Replace Per Subscriber in Newsletter - REVERTED (no performance gain, caused test failures)
- Item 13: Bulk Operations N Separate FTS Syncs - FIXED (sync_fts_batch added)
- Item 14: Media Page Full Directory Scan - FIXED (caching with TTL)
- Item 15: Footer Cache Not Invalidated on Post Changes - FIXED (invalidate_footer_cache)
- Item 16: SiteSettings Cache Not Invalidated on Save - FIXED (already working)

## Wave 4: Code Quality Fixes (COMPLETED)

- Item 17: Slug Regeneration Return Value Ignored - FIXED (captured return value)
- Item 18: Error Recovery Block Duplicates Main Logic - FIXED (extracted helper)
- Item 19: Regex Character Class Range Operator Bug - FIXED (hyphen at end)
- Item 20: Missing Database Index - FIXED (added ix_posts_published_slug)
- Item 21: TOCTOU Race Condition in Admin Deletion - FIXED (IntegrityError catch)
- Item 22: FakeSubscriber Dataclass in Route File - FIXED (kept in newsletter.py)
- Item 23: Media File Truncation Off-by-One - FIXED (changed >= to >)
- Item 24: Newsletter Retry Logic Not Implemented - FIXED (_send_email_with_retry)

## Wave 5: Multi-Admin & User Management (COMPLETED)

- Item 25: Cannot Promote/Demote Users to Admin - FIXED (routes and buttons added)
- Item 26: Cannot Transfer Admin Ownership - FIXED (make-owner route added)
- Item 27: Add Type Hints to Model Methods - ALREADY DONE (type hints present)

## Wave 6: UI/Template Fixes (COMPLETED)

- Item 28: Login Page Loads Full Admin Base - FIXED (login_base.html created)
- Item 29: Templates Don't Verify Image File Existence - FIXED (using post_image_url filter)
- Item 30: Duplicate Badge and Status Badge Styles - FIXED (removed duplicates)
- Item 31: Missing Visible Form Labels for Change Password - FIXED
- Item 32: No Password Visibility Toggle - FIXED
- Item 33: Backup Restore Button Not Visually Dangerous - FIXED (btn-danger)
- Item 34: No Admin Breadcrumb Navigation - FIXED (_breadcrumbs.html created)
- Item 35: Breadcrumb Truncation Accessibility Issue - FIXED (max-width 400px)
- Item 36: Archive Grid Layout Breaks on Mobile - FIXED
- Item 37: Share Bar Cluttered on Mobile - FIXED (hidden via CSS)
- Item 38: Author Info Missing from Post Cards - FIXED
- Item 39: No Scheduled Post Indicator - FIXED (badge-scheduled)

## Wave 7: JavaScript & Dead Code Cleanup (COMPLETED)

- Item 40: Missing Error Handling on Dynamic Imports - FIXED (loadModule helper)
- Item 41: Duplicate Focus Trap Logic in Shortcuts Module - FIXED (removed)
- Item 42: Share Tracking Silently Swallows Errors - FIXED (warn logging)
- Item 43: Unused CSS Variable `--text-dim-strong` - FIXED (removed)
- Item 44: Unused CSS Class `.post-card-snippet` - ALREADY IN USE (not a bug)
- Item 45: `_build_newsletter_message` Appears Unused - FIXED (removed)
- Item 46: Related Posts Only Use First Tag - ALREADY WORKING (uses all tags)
- Item 47: No Jinja Macros for Reusable Patterns - FIXED (macros.html created)
- Item 48: Email Templates Not Using Base - FIXED (base_email.html created)

## Wave 8: Minor Improvements (COMPLETED)

- Item 49: SiteSettings Singleton Not Enforced - FIXED (get_instance method)
- Item 50: Inconsistent Relationship Patterns - FIXED (standardized back_populates)
- Item 51: Missing Type Hints on Model Methods - ALREADY DONE
- Item 52: Referrer Index May Be Ineffective - FIXED (removed index)
- Item 53: SELECT Before DELETE on Session Expiry - FIXED (direct DELETE)
- Item 54: Individual Loop Deletes for Expired Subscribers - FIXED (bulk DELETE)
- Item 55: File Read Twice on Upload Rejection - FIXED
- Item 56: Sequential File Deletes in Bulk Operations - OK (typical use)
- Item 57: Error Page Inconsistency - ALREADY FIXED (uses _error.html)
- Item 58: Health Endpoint Missing from AGENTS.md - FIXED (added)
- Item 59: Archive Page Not Documented - FIXED (added)
- Item 60: Static Pages Feature Documentation Incomplete - FIXED (added)
- Item 61: N+1 Query Risk with Dynamic Relationships - FIXED (lazy=select)
- Item 62: `scalar()` Returns None on Empty Result - FIXED (scalar_one_or_none)

---

## Completed Commits

- `8f80056` Wave 1: Fix critical bugs
- `f9635ae` Wave 2: Security & Session Fixes
- `f7289a6` Wave 3: Performance Improvements
- `7aaa6e8` Wave 4: Code Quality Fixes
- `a1bf0e0` Wave 5: Multi-Admin & User Management
- `78e536a` Wave 6: UI/Template Fixes
- `d731b9f` Wave 7: JavaScript & Dead Code Cleanup
- `d8cfc14` Wave 8: Minor Improvements
- `63d6046` Post-Wave 8: Fix FTS sync errors swallowed
- `cd84d35` Post-Wave 8: Add orphaned image cleanup CLI
- `5887924` Post-Wave 8: Improve CSS sanitization

---

## Notes

1. **Item 12 (String Replace Per Subscriber)** was reverted after causing IndexError in tests. The original `.replace()` approach was correct and simpler.

2. **Items 44, 46** were marked as needing fixes but were already working correctly in the codebase.

3. All 297 tests pass after these changes.

4. **Post-Wave 8 items**: All additional items from the "Not Implemented" list have been addressed. CSS sanitization improved, FTS sync now properly returns status and handles failures, orphaned image cleanup CLI command added.

---

## Additional Items (Post-Wave 8)

| Issue | Location | Status | Description |
|-------|----------|--------|-------------|
| Regex-based CSS sanitization | `app/utils.py:sanitize_css()` | IMPROVED | Better regex patterns with additional dangerous properties blocked (-webkit-text-security, unicode-bidi, direction). Full CSS parser library considered but not needed for admin-provided CSS. |
| Newsletter scheduler single-machine lock | `app/scheduler.py` | ACCEPTED | File-based locking only; multi-worker needs Redis. Documented in scheduler docstring and DEPLOY.md. External scheduler recommended for multi-machine deployments. |
| FTS sync errors swallowed | `app/search.py:sync_fts()` | FIXED | sync_fts/sync_fts_batch/remove_fts now return bool; callers check and rollback on failure. DB/FTS consistency maintained. |
| No orphaned image cleanup | `app/routes/admin/media.py` | FIXED | Added cleanup_orphaned_images() function and `flask cleanup-orphaned-images` CLI command. Cleans up orphaned files and missing DB references. |

---

## Related Documentation

- `AGENTS.md` — Project structure and patterns
- `DEPLOY.md` — Deployment guide
- `.opencode/skills/` — Specialized skills for security, performance, and feature documentation