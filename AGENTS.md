# Agent Guidelines

Quick reference for AI agents working on this codebase.

## Agent Override Convention

This codebase uses a **module-level override system** for agent context. Each module (directory with a specific purpose) may contain an `AGENTS.override.md` file that provides specialized handling instructions for that module.

When an agent operates within a module, it should:
1. Read the root `AGENTS.md` for general guidance
2. Check for `AGENTS.override.md` in the current module for specialized handling
3. Override files take precedence over root-level guidance when working within that module

## Module Override Files

| Module | Override File | Purpose |
|--------|---------------|---------|
| App Core | `app/AGENTS.override.md` | Flask app, models, extensions, core utilities |
| Routes | `app/routes/AGENTS.override.md` | General routing concerns, API authentication, RSS feeds, error handlers |
| Admin Routes | `app/routes/admin/AGENTS.override.md` | Admin dashboard, post/subscriber/user management |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| OpenCode Config | `.opencode/AGENTS.override.md` | Agent tool configuration |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |
| Services | `app/services/AGENTS.override.md` | Backup, slug, serialization, tag services |
| Plans | `plans/AGENTS.override.md` | Roadmap, execution waves, project planning |

## Structure Convention

When adding agent guidance for a specific module:
1. Create `AGENTS.override.md` inside that module directory
2. Do not create a separate "agents" directory
3. Override files should be focused on module-specific concerns
4. Update this index when adding new override files

## Codebase Structure Reference

Important actual file locations (verify before assuming):

| Item | Actual Location |
|------|-----------------|
| API routes | `app/routes/api/` (PACKAGE with posts.py, subscribers.py, stats.py, auth.py) |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Backup logic | `app/services/backup.py` (centralized service) |
| Admin Audit Log model | `app/models.py:397-417` |
| PostRevision model | `app/models.py:173` |
| User model `__repr__` | `app/models.py:63-64` |
| Comment model | `app/models.py` |
| Services | `app/services/` (backup, slug, serialization, tag) |

## Security & Privacy Rules

- **Log ID, not Username**: When logging user actions or system events, always use `user.id`. Never log raw User objects or usernames to prevent PII leakage.
- **Credential Protection**: Never log `SECRET_KEY`, `ADMIN_PASSWORD`, or API keys.

## High-Risk Files (Error Handling)

These files previously used broad `except Exception` clauses. All have been replaced with specific exceptions:
- `app/routes/public/meta.py`
- `app/email.py`
- `app/backup_integrity.py`
- `app/webhooks.py`
- `app/tasks.py`
- `app/page_view_buffer.py`

## Test Interference Notes

### Page View Buffer Test Issues
- The page view buffer (`app/page_view_buffer.py`) can cause test interference when running full suite
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0` and call `shutdown_page_view_buffer()`
- The `conftest.py` session-scoped `app` fixture may allow buffer restart - use autouse fixture in `tests/conftest.py` to ensure disabled.
- The `ensure_buffer_disabled` fixture is at `tests/conftest.py:185-193`

### Test Database Session Issues
- `db.session.refresh()` fails if object isn't in current session
- Fix: Re-query object from database instead of using `refresh()`.

## Deferred Items

These items were previously deferred but are now COMPLETED:

| Item | Status |
|------|--------|
| TOTP encryption (2FA) | COMPLETED - Wave A |
| 2FA backup codes | COMPLETED - Wave A |
| Admin rate limiting | COMPLETED - Wave B |
| PostgreSQL FTS abstraction | COMPLETED - Wave C (stub) |
| Vite code splitting | COMPLETED - Wave D |
| AVIF support | COMPLETED - Wave D (stub) |
| Brotli compression | COMPLETED - Wave E (commented config) |

### Future Waves (F-I)
New waves organized for execution (see `plans/plan.md`):
- **Wave F**: Bug Fixes (12 items - security and functional)
- **Wave G**: Code Quality (5 items)
- **Wave H**: Documentation (37 items)
- **Wave I**: Enhancements (0 items currently)

## Implemented Features Notes

### 2FA Implementation (Wave A)
- TOTP secrets are encrypted at rest using AES-256-GCM (`app/services/encryption.py`)
- `User.totp_secret` is now a property that decrypts on access
- Backup codes are SHA-256 hashed and single-use
- Routes: `/2fa/setup`, `/2fa/verify`, `/2fa/backup-codes`, `/2fa/disable`

### Rate Limiting (Wave B)
- `ADMIN_RATE_LIMITS` defined in `app/config.py`
- `app/middleware/rate_limit.py` provides `AdminRateLimiter` class
- Flask-Limiter already integrated with `key_func=get_client_ip`

### Search Abstraction (Wave C)
- `SearchProvider` abstract class in `app/services/search/__init__.py`
- `SQLiteSearchProvider` wraps existing FTS5 functionality
- `PostgreSQLSearchProvider` is a stub for future implementation
- `get_search_provider()` factory function selects provider by `SEARCH_PROVIDER` config

### Frontend (Wave D)
- Vite configured for code splitting with `manualChunks`
- `post_image_avif_url` filter added (returns None until AVIF encoding is enabled)

### Brotli (Wave E)
- Nginx configuration includes commented Brotli settings
- Requires custom nginx image with `--with-http_brotli_module`

## Important Notes for Future Agents

### Backup Implementations
There are two separate backup implementations:
- `app/services/backup.py:create_backup()` - Used by Celery task, supports encryption/compression, uses `blog_*.db` naming
- `app/scheduler.py:run_daily_backup()` - Used by APScheduler, no encryption/compression, uses `backup_*.db` naming

### Slug Generation
Slug collision limit is hardcoded to 100 tries before falling back to UUID suffix (`app/services/slug.py`).

### APScheduler Job Schedules
- `cleanup_expired_subscribers` runs every 5 minutes (`minute="*/5"`), NOT hourly
- `run_daily_backup` runs at 02:00 (`hour=2, minute=0`), NOT midnight

### Email Retry Count
Newsletter retry count default is 5 (not 3 as some documentation may claim).

### Context Processors
Actual context processor function names (not the injected variable names):
- `inject_csrf()` - Injects `csrf_token` and `csp_nonce`
- `inject_config()` - Injects site config variables
- `inject_theme()` - Injects theme settings and `custom_css`
- `inject_footer_data()` - Injects footer links and data
- `inject_show_footer_posts()` - Injects `show_footer_posts` boolean

### Template Filters
Actual filters (defined in `app/filters.py`):
- `markdown_safe`, `reading_time`, `sanitize_css`, `post_image_url`, `post_image_srcset`
- NOT `format_date`, `markdown`, `slugify` (these don't exist)

### Celery Queue Names
Tasks use specific queues: `images`, `newsletter`, `webhooks`, `email`, `backup` (see `app/tasks.py` lines 29, 129, 192, 264, 285, 306)

### Actual Routes
When documenting or referring to routes, verify against actual implementation:
- New post: `/admin/new` (NOT `/admin/posts/new`)
- Edit post: `/admin/edit/<id>` (NOT `/admin/posts/<id>/edit`)
- Tag delete: `POST /admin/tags/delete/<id>` (NOT `DELETE`)
- Comment submission: `POST /post/<slug>/comment` (NOT `/comment/<int:post_id>`)
- Subscribe: Only `POST /subscribe` exists (no GET handler)
- API post publish: Use `PUT /api/posts/<id>` with `{"published": true}` body (NOT `POST /api/posts/<id>/publish`)

### User Model `__repr__`
Returns `<User id={self.id}>` for PII/security reasons, not username.

## New Patterns

### Comment Model Relationships
The Comment model uses `back_populates` for parent/child relationships:
```python
parent = db.relationship("Comment", remote_side=[id], back_populates="replies")
replies = db.relationship("Comment", back_populates="parent", lazy="select")
```

### Health Check Status Logic
Health check only considers critical checks for overall status (optional services don't affect degraded):
```python
critical_checks = {
    k: v for k, v in checks.items()
    if k in ("database", "scheduler", "search", "disk_space", "db_integrity")
}
```

### Snippet Batching
For SQLite parameter limits, batch post_ids:
```python
chunk_size = 500
for i in range(0, len(post_ids), chunk_size):
    chunk = post_ids[i:i + chunk_size]
```

### Backup Isolation
Run backups as Celery tasks to avoid blocking web requests:
```python
@celery_task
def run_backup_task(backup_dir, compress):
    from app.services.backup import create_backup
    return create_backup(db_path, backup_dir, compress=compress)
```

### Webhook Event Triggering
Webhook events are triggered at key state transitions:
```python
# Post publish/unpublish in app/routes/api/posts.py
if "published" in data and was_published != post.published:
    from app.webhooks import create_webhook_event
    create_webhook_event(
        event_type="post.published" if post.published else "post.unpublished",
        payload={"post_id": post.id, "title": post.title, "slug": post.slug},
        target_id=post.id,
        target_type="post"
    )

# Subscriber confirmation in app/routes/public/subscribe.py
sub.confirmed = True
# ... after commit ...
create_webhook_event(
    event_type="subscriber.confirmed",
    payload={"subscriber_id": sub.id, "email": sub.email},
    target_id=sub.id,
    target_type="subscriber"
)
```

### Feed Endpoints
Three feed endpoints available:
- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

## Skills

Load specialized skills using the `skill` tool with the skill name.

| Skill | Description | Triggers |
|-------|-------------|---------|
| `blog_cms` | Blog CMS - Flask-based blogging platform with admin dashboard, newsletter scheduling, FTS5 search, multi-admin sessions, custom CSS theming, syntax highlighting themes, post series, Atom feed, 2FA, Comments, Audit Log, Post Revision Diff | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler, 2FA, Comments, Audit Log |
| `e2e_testing` | End-to-end browser testing with Playwright | E2E tests, playwright, browser tests, pytest-playwright, UI testing |
| `ainews` | AI news pipeline — Flask backend, Celery workers, LLM pipeline (select→research→write→edit), subagent system, SQLite/WAL, Granian ASGI | pipeline, celery, newsletter, article, source, subscriber, admin, config, health, metrics |
| `nara` | Nara chain CLI agent — free PoMI mining, wallet, transfer, quest, on-chain skills, ZK ID, agent registry | NARA, quest, mining, airdrop, earn/claim/collect NARA, wallet, balance, transfer, skills, zkid, agent, referral, PoMI, keypair, mnemonic, faucet, deposit, withdraw |
| `osinit` | OSINIT Dashboard - FastAPI backend with 24 intelligence sources, React/TypeScript frontend with 3D globe | build, test, deploy, run, data source, panel, SSE, sweep, synthesis, authentication, rate limiting, cache, delta, VIX, SSRF, circuit breaker, routers, Granian |

## Skills Directory Note

Skills are stored in `.skills/` which may be a symlink to an external location.
If the symlink is broken (shows as "broken symbolic link"), skills are not available.
To fix: `rm .skills && ln -s /actual/path/to/skills .skills`

## Implementation Plan

See `plans/plan.md` for future implementation waves organized for parallel execution:
- **Wave A-E**: COMPLETED (2FA, Rate Limiting, Search, Frontend, Brotli)
- **Wave F**: Bug Fixes (12 items - security and functional)
- **Wave G**: Code Quality (5 items)
- **Wave H**: Documentation (37 items)
- **Wave I**: Enhancements (0 items currently)

### Wave Execution Pattern
When executing multi-wave implementation plans:
1. **Create separate branches** for each parallel wave to avoid conflicts
2. **Use subagents** with separate branches to parallelize work
3. **Merge to main** after each wave completes
4. **Update plan status** in plan.md after each wave

### Branch Naming Convention
```
wave-a-totp-encryption
wave-b-rate-limiting
wave-c-postgres-search
wave-d-frontend
wave-e-brotli
wave-f-bugfixes
wave-g-code-quality
wave-h-documentation
wave-i-enhancements
```

### Subagent Usage
- Launch subagents in parallel for independent wave items
- Each subagent works on its own branch
- Review completed work before merging
- Do not let subagents overwrite each other's changes
- Within a wave, items can be parallelized by module (e.g., F.1-F.6 in parallel, F.7-F.12 in parallel)