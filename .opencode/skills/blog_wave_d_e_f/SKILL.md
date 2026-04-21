---
name: blog_wave_d_e_f
description: "Blog CMS Wave D-F - Type hints, exception handling, CSRF rotation, REST API, password reset, scheduled posts UI, post revisions, advanced search, preview links, API docs, dev scripts, CLI commands, test coverage, faster tests. Triggers: type hints, exception handling, CSRF sliding window, REST API endpoints, password reset flow, post revisions, advanced search snippets, shareable preview links, CLI export/import/seed, toast notifications, dashboard charts."
metadata:
  requires: "python>=3.12, flask>=3.1"
  homepage: "https://github.com/sugarwookie/blog"
---

## Wave D: Code Quality

### D1: Complete Type Hint Coverage

Type hints added throughout codebase:
- `app/routes/admin/posts.py` — return type `-> Response` for route handlers
- `app/routes/admin/subscribers.py` — parameter types
- `app/routes/admin/media.py` — return types and parameter types

### D2: Consistent Error Handling Patterns

Specific exceptions used (no bare `except Exception`):
- File operations: `OSError`, `IOError`, `FileNotFoundError`
- Database: `IntegrityError`, `OperationalError`
- Network: `smtplib.SMTPException`, `OSError`

### D3: Per-Request CSRF Token Rotation

Sliding window of 5 valid tokens in `app/csrf.py`:
- `generate_csrf_token()` — creates new token, adds to list (max 5)
- `validate_csrf_token()` — checks if token in valid set, removes on use

### D4: Helper Module Exports

`app/routes/admin/helpers/__init__.py` re-exports:
- `slug`: `_generate_unique_slug`
- `tags`: `validate_tag_name`, `_cleanup_orphan_tags`, `_get_or_create_tags`
- `images`: `_detect_image_type`, `_allowed_file`, `_save_image`
- `shared`: `ALLOWED_EXTENSIONS`, `TAG_NAME_REGEX`, etc.

## Wave E: Feature Completeness

### E1: REST API

**Blueprint**: `app/routes/api.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts (paginated) |
| GET | `/api/posts/<id>` | Get single post |
| POST | `/api/posts` | Create post |
| PUT | `/api/posts/<id>` | Update post |
| DELETE | `/api/posts/<id>` | Delete post |
| GET | `/api/subscribers` | List subscribers (paginated) |
| POST | `/api/subscribers` | Create subscriber |
| DELETE | `/api/subscribers/<id>` | Delete subscriber |
| GET | `/api/stats` | Dashboard statistics |

**Authentication**: `X-API-Key` header (env var `API_KEY`)

### E2: Password Reset

**Routes**:
- `GET/POST /admin/forgot-password`
- `GET/POST /admin/reset/<token>`

**Model changes** (`User`):
- `reset_token` — hashed token
- `reset_token_expires_at` — UTCDateTime, nullable

**Features**:
- Token expires in 1 hour
- Password complexity validation (same as user creation)
- Invalidates all admin sessions after reset
- Fake success pattern to prevent username enumeration

### E3: Scheduled Post Management UI

- Dashboard filter: `?status=scheduled`
- Badge showing "Scheduled for {datetime}"
- Bulk "Unschedule" action
- Individual "Unschedule" button per post

### E4: Post Revisions

**Model**: `PostRevision`
- `id`, `post_id`, `title`, `slug`, `body`, `summary`, `created_at`, `author_id`
- Index: `ix_post_revisions_post_created`

**Routes**:
- `GET /admin/posts/<id>/revisions`
- `POST /admin/posts/<id>/revisions/<rev_id>/restore`

**Behavior**:
- Revisions saved ONLY on publish events (not draft saves)
- Restore creates a new revision before restoring

### E5: Advanced Search

`app/search.py` enhancements:
- `get_did_you_mean(query, indexed_terms)` — fuzzy suggestions via `difflib.get_close_matches()`
- `highlight_query(text, query)` — adds `<mark>` tags around matched terms
- `get_indexed_terms()` — extracts unique terms from FTS index

### E6: Shareable Preview Links

**Token generation** (`app/routes/admin/posts.py`):
- `_generate_preview_token()` — HMAC-SHA256 signature
- `_build_preview_url()` — constructs full URL

**Public route** (`app/routes/public.py`):
- `GET /preview/<post_id>?token=<hmac>&expires=<ts>`
- Timing-safe validation via `hmac.compare_digest()`
- Returns 410 for expired, 403 for invalid

## Wave F: Developer Experience

### F1: API Documentation

`docs/openapi.yaml` — OpenAPI 3.0.3 specification documenting all REST API endpoints.

### F2: Development Environment Script

`scripts/dev.sh` — New developer setup script:
```bash
./scripts/dev.sh
```

### F3: CLI Commands

`app/cli.py`:
- `flask export-data <output_file>` — JSON export
- `flask import-data <input_file>` — JSON import with `--skip-confirmed/--include-confirmed`
- `flask promote-admin <username>` — non-interactive
- `flask check-integrity` — `PRAGMA integrity_check`
- `flask seed` — sample data with `--posts N --subscribers N --published/--draft`

### F4: Test Coverage Improvement

`tests/test_coverage.py`:
- Error handler tests (404, 500, 413)
- FTS LIKE fallback tests

### F5: Faster Test Suite

`tests/conftest.py` additions:
- `pytest.mark.slow` marker
- `mock_smtp` fixture — comprehensive SMTP mock
- `mock_email` fixture — combined render + SMTP mock

## Tests

```bash
cd /home/sugarwookie/projects/blog && source .venv/bin/activate
ADMIN_PASSWORD=test SECRET_KEY=test-test-test-test-test-test-test-test-test python -m pytest tests/ -v
```