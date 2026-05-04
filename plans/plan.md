# Improvement Plan

This plan outlines the roadmap for security, performance, and architectural improvements. It is organized into parallelizable "Waves".

---

## Wave 1: Security & Stability (Immediate/Critical)
*Target: Fix high-risk vulnerabilities and stabilize the test suite.*

### 1.1 Critical Security Remediations
- **[ ] Fix SQL Injection Risk in FTS Search (S-1):** 
    - **Current state:** `app/search.py` constructs FTS queries using string concatenation.
    - **Action:** Refactor `search` function to use SQLAlchemy's `bindparam` or ensure all components are strictly validated/escaped using `tinycss2` or similar where applicable (for FTS syntax).
    - **Note:** Refer to `app/search.py:204`.
- **[ ] Fix CSS Injection via Custom CSS (S-2):**
    - **Current state:** `app/utils.py:sanitize_css` uses regex-based sanitization which is prone to bypass.
    - **Action:** Replace regex with `tinycss2` to properly parse and sanitize CSS, using a strict allowlist of properties.
- **[ ] Encrypt Webhook Secrets at Rest (S-3):**
    - **Current state:** Webhook secrets are stored in plaintext.
    - **Action:** Implement AES-256-GCM encryption in `app/webhook_encryption.py`. Update `app/models.py` and migration to handle encrypted fields.
- **[ ] Fix Broad Exception Handling (CQ-3):**
    - **Current state:** ~16 instances of `except Exception` remain (e.g., `app/routes/public/meta.py`, `app/email.py`).
    - **Action:** Replace with specific exceptions (SQLAlchemyError, OSError, etc.) to prevent swallowing system signals.

### 1.2 Test Suite Stability & Reliability
- **[ ] Database Session Compliance:** Replace non-compliant `db.session.refresh()` calls in tests with the re-query pattern.
- **[ ] Test Isolation (Page View Buffer):**
    - Implement a session-scoped autouse fixture in `tests/conftest.py` to disable the buffer globally during testing.
    - Update `test_search.py` and `test_api.py` to explicitly shutdown the buffer.
- **[ ] Remove Duplicate Fixtures:** Delete the redundant `mock_image_processing` fixture in `tests/conftest.py`.
- **[ ] Restore Missing Tests:** Re-enable and update `tests/test_page_view_buffer.py`.

### 1.3 Module Coverage (Goal: 80%+)
- **[ ]** `app/routes/admin/users.py` (Current: 49%)
- **[ ]** `app/filters.py` (Current: 47%)
- **[ ]** `app/page_view_buffer.py` (Current: 39%)
- **[ ]** `app/storage.py` (Current: 52%)
- **[ ]** `app/scheduler.py` (Current: 61%)

---

## Wave 2: Refactoring & Performance (Short-term)
*Target: Optimize database access and modularize the codebase.*

### 2.1 Database & Query Optimization
- **[ ] Eliminate N+1 Queries:** Refactor Series Admin route (`app/routes/admin/series.py`) and public browse/series routes to use `joinedload` for related counts/relationships.
- **[ ] Add Missing Indexes:** Create explicit indexes for `webhook_events.webhook_id` and `comments.parent_id`.
- **[ ] FTS5 Performance:** Implement `fts5vocab` virtual table for efficient search term indexing.

### 2.2 Codebase Architecture & Maintenance
- **[ ] Modularize API (Task 2.1):** 
    - Split `app/routes/api.py` (546 lines) into `app/routes/api/` package with `posts.py`, `subscribers.py`, and `stats.py`.
- **[ ] Consolidate Utility Logic:**
    - Centralize `generate_slug` in `app/utils.py` and remove duplicates from models.
    - Move webhook signing logic to `app/utils.py`.
    - Consolidate image variant generation in `app/routes/admin/media.py`.
- **[ ] Improve Logging:** Replace `print()` in `app/services/backup.py` with standard `logging`.

---

## Wave 3: Features & Future (Long-term)
*Target: Infrastructure enhancements and advanced security.*

### 3.1 Infrastructure & Security Hardening
- **[ ] Static Asset CDN Support:** Update `vite_asset()` and `post_image_srcset` to support a configurable `CDN_URL`.
- **[ ] S3 Security Hardening:** Improve memory handling for S3 credentials to minimize the lifetime of sensitive data.
- **[ ] Performance Benchmarking:** Establish automated performance regression tests.

### 3.2 Cleanup & Documentation
- **[ ] Audit Unused Modules:** Review `backup_encryption`, `backup_integrity`, `webhooks`, and `celery_app` for potential removal or refactoring.
- **[ ] Documentation Overhaul:** Update API docs and developer guides for the new modular structure.

---

## Execution Guidelines for Agents
- **Parallelization:** Waves can be executed in parallel by different agents, provided they don't modify the same files simultaneously.
- **Testing:** Every change must be accompanied by relevant unit or integration tests.
- **Security:** Prioritize S-1, S-2, and S-3 in Wave 1.
