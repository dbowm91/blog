# Implementation Plan - Blog CMS (Consolidated)

**Project:** Blog CMS
**Status:** WAVE M - ALL ITEMS COMPLETED
**Last Updated:** May 2026

---

## Overview

This file contains the consolidated implementation plan for the Blog CMS project. It was created by merging findings from 8 architecture review modules (routes, infrastructure, services, frontend, overview, core, deployment, testing, tasks) into a single actionable plan.

**Status Summary:** All Wave M items have been verified as completed. This file is retained for historical reference and agent guidance.

---

## Quick Reference: Critical Bugs (FIXED)

| ID | Description | Impact | Status |
|----|-------------|--------|--------|
| M-1.1 | `image-review.js` import should be `image-preview.js` | Admin image preview broken | FIXED |
| M-1.2 | Email task retry logic broken | Exceptions swallowed, no auto-retry | FIXED |
| M-2.8 | docker-compose.yml SESSION_COOKIE_SECURE string vs boolean | Config issue | FIXED |
| M-2.9 | Celery missing blog_logs volume mount | Logs not persisted | FIXED |

---

## Completed Items Summary

### Wave M-1: CRITICAL BUGS
- **M-1.1**: image-preview.js import - FIXED (already correct in code)
- **M-1.2**: Email task retry logic - FIXED (already correct in code)
- **M-1.3**: S3StorageBackend credential clearing - ALREADY FIXED (no action needed)
- **M-1.4**: SMTP context manager exception safety - FALSE POSITIVE (no action needed)

### Wave M-2: HIGH-PRIORITY DOCUMENTATION
- **M-2.1**: Add Missing API Endpoint Documentation - COMPLETED
- **M-2.2**: Fix Webhook Model Documentation - COMPLETED
- **M-2.3**: Add WebhookEvent delivery_status Documentation - COMPLETED
- **M-2.4**: Create Search Provider Documentation - COMPLETED
- **M-2.5**: Document Two Backup Implementations - COMPLETED
- **M-2.6**: Add HEALTH_CHECK_SECRET Documentation - COMPLETED
- **M-2.7**: Add Optional Health Checks Clarification - COMPLETED
- **M-2.8**: Fix docker-compose.yml SESSION_COOKIE_SECURE - COMPLETED
- **M-2.9**: Add blog_logs Volume to Celery - COMPLETED
- **M-2.10**: Fix image-preview.js Documentation - COMPLETED

### Wave M-3: MEDIUM-PRIORITY DOCUMENTATION
- **M-3.1a**: Document POST /admin/preview-markdown - COMPLETED
- **M-3.1b**: Document POST /admin/series/<int:series_id>/reorder - COMPLETED
- **M-3.1c**: Document GET /confirm/<token> and GET /unsubscribe/<token> - COMPLETED
- **M-3.2a**: Tag delete uses POST not DELETE - COMPLETED
- **M-3.2b**: Series delete uses POST not DELETE - COMPLETED
- **M-3.3**: Clarify Tag Pagination - COMPLETED
- **M-3.4**: Document Feed Caching - COMPLETED
- **M-3.5**: Add Missing Configuration Options - COMPLETED
- **M-3.6**: Document AdminSession.last_activity - COMPLETED
- **M-3.7**: Document PostRevision.author_id - COMPLETED
- **M-3.8**: Clarify RATE_LIMIT_STORAGE_URI Logic - COMPLETED
- **M-3.9**: Add Account Lockout Configuration - COMPLETED
- **M-3.10**: Document Backup Filename Security - COMPLETED
- **M-3.11**: Add Series Relationship Ordering Note - COMPLETED
- **M-3.12**: Remove STORAGE_BACKEND from Environment Table - COMPLETED

### Wave M-4: LOW-PRIORITY IMPROVEMENTS
- **M-4.1**: Remove Dead Code extract_snippet() - NOT NEEDED (used in tests)
- **M-4.2**: Document AVIF Status - COMPLETED
- **M-4.3**: Add Multi-Container Deployment Warning - COMPLETED
- **M-4.4**: Document Email Wrapper Task Pattern - COMPLETED
- **M-4.5**: Add Celery Task Failure Logging - COMPLETED
- **M-4.6**: Document Slug Collision Limit - COMPLETED
- **M-4.7**: Document APScheduler Daemon Mode - COMPLETED
- **M-4.8**: Document Newsletter Retry Configuration - COMPLETED
- **M-4.9**: Add E2E Server Startup Race Condition Note - COMPLETED
- **M-4.10**: Document celery --concurrency=1 - COMPLETED
- **M-4.11**: Add docker wait redis Documentation - COMPLETED
- **M-4.12**: Document FakeSubscriber Dataclass - COMPLETED
- **M-4.13**: Clarify mock_email Fixture Chaining - COMPLETED
- **M-4.14**: Document clean_db Nested Transaction Pattern - COMPLETED

### Previously Verified Items (Wave L)
- L-1.1 through L-4.2 - All verified correct

---

## Important Context for Future Agents

### Key Implementation Patterns

**Backup Implementations:**
- `app/services/backup.py:create_backup()` - Celery task with AES-256-GCM encryption
- `app/scheduler.py:run_daily_backup()` - APScheduler version, no encryption

**APScheduler Jobs:**
- `cleanup_expired_subscribers` - every 5 minutes (`minute="*/5"`)
- `run_daily_backup` - at 02:00 UTC (`hour=2, minute=0`)
- `send_daily_newsletter` - only runs when SMTP_HOST is configured

**Health Check:**
- Critical checks: database, scheduler, search, disk_space, db_integrity
- Optional checks: backup_freshness, email, redis, celery (don't affect status)

**Email Task Retry:**
- `send_confirmation_task` and `send_password_reset_task` catch exceptions and return False
- This makes `max_retries=3` ineffective (fixed in M-1.2)

**Webhook Encryption:**
- `Webhook.secret` uses AES-256-GCM via `app/webhook_encryption.py`
- Stored as `webhook_secret_encrypted` (LargeBinary) in database

**Search Provider:**
- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` - current default using FTS5
- `PostgreSQLSearchProvider` - stub for future

**Slug Generation:**
- Collision limit is 100 tries before UUID fallback
- UUID format: `{base_slug}-{8_char_hex}`

**Context Processors:**
- `inject_csrf()` - csrf_token and csp_nonce
- `inject_config()` - site config variables
- `inject_theme()` - theme settings and custom_css
- `inject_footer_data()` - footer links and data
- `inject_show_footer_posts()` - show_footer_posts boolean

**Template Filters:**
- `markdown_safe`, `reading_time`, `sanitize_css`
- `post_image_url`, `post_image_srcset`, `post_image_avif_url_stub`

---

*Last updated: May 2026 - Wave M all items completed*