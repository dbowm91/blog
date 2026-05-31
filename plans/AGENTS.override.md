# Plans Module Override

## Overview

This module contains the consolidated implementation plan and architecture review findings.

## Plan Status

**ACTIVE** - New consolidated plan created from May 31, 2026 architecture review.

The consolidated plan `plans/plan.md` contains 153 tasks across 6 waves, organized for parallel execution via sub-agents. Previous completed plans have been archived.

## Architecture Review Findings (May 31, 2026)

A comprehensive architecture review was conducted across all modules. Findings are consolidated in `plans/plan.md`.

### Key Statistics

| Category | Count |
|----------|-------|
| Verified Claims | 124 |
| Discrepancies | 51 |
| Missing Documentation | 30 |
| Potential Bugs | 24 |
| Action Items | 153 |

### Critical Findings

1. **CRITICAL:** Nginx `proxy_pass` uses `127.0.0.1` instead of service name `blog`
2. **HIGH:** RSS cache invalidation incomplete (atom/json feeds not invalidated)
3. **HIGH:** Global rate limit bypass via X-Forwarded-For spoofing
4. **HIGH:** `decrypt_backup_file()` missing RuntimeError catch
5. **HIGH:** `S3StorageBackend.save()` lacks error handling
6. **HIGH:** Admin Prism CSS hardcoded to okaidia (ignores user setting)
7. **HIGH:** Prism double-loading on admin pages
8. **HIGH:** Template inheritance diagram is factually wrong
9. **HIGH:** Widespread test password inconsistency ("testpassword" vs "test-password")
10. **HIGH:** Documentation claims features that don't exist (LIKE fallback, PostgreSQL fallback, email health check, exponential backoff)

### Plan Waves

| Wave | Focus | Tasks | Parallelizable |
|------|-------|-------|----------------|
| 1 | Critical Source Code Fixes | 12 | Yes |
| 2 | High Priority Documentation Corrections | 48 | Yes |
| 3 | Medium Priority Improvements | 33 | Yes |
| 4 | Low Priority Cleanup | 27 | Yes |
| 5 | Architecture Pruning | 12 | Partially |
| 6 | AGENTS.md Cleanup | 21 | No |

### Historical Context

Previous implementation plan (May 29, 2026) contained ~90 items across 6 waves, all completed and verified. The current plan addresses new findings from the May 31 review.

## Key Files for Reference

| Item | Location |
|------|----------|
| Nginx proxy_pass bug | `nginx/conf.d/blog.conf:52,65,75,84` |
| RSS cache invalidation | `app/routes/rss.py:103-105` |
| X-Forwarded-For bypass | `app/__init__.py:45-49`, `app/routes/public/comments.py:24-32` |
| Backup encryption bug | `app/backup_encryption.py:237` |
| S3 save error handling | `app/storage.py:182-184` |
| Admin Prism CSS hardcode | `app/templates/admin/base.html:9` |
| Prism double-loading | `app/templates/admin/base.html:9,162-163`, `app/static/js/main.js:97-111` |
| Test password inconsistency | `tests/` directory (24 occurrences) |
| Template inheritance | `app/templates/admin/base.html:1` (standalone, not extending base.html) |
| marked.min.js loading | `app/templates/admin/base.html:164` (url_for, not vite_asset) |

## Maintenance Notes

When updating code that affects documented behavior:
1. Update the relevant AGENTS.override.md for that module
2. If adding new behavior, consider updating AGENTS.md Important Notes
3. If documentation becomes stale, update architecture docs or add a note in agent-maintainer-notes.md
4. After completing wave items, update this file to reflect progress