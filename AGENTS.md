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
| Routes | `app/routes/AGENTS.override.md` | Public routes, API, RSS |
| Admin Routes | `app/routes/admin/AGENTS.override.md` | Admin dashboard, post/subscriber/user management |
| Frontend | `app/static/AGENTS.override.md` | JS/CSS assets, Vite build |
| Templates | `app/templates/AGENTS.override.md` | Jinja2 templates, filters |
| Tests | `tests/AGENTS.override.md` | Testing patterns, fixtures |
| OpenCode Config | `.opencode/AGENTS.override.md` | Agent tool configuration |
| Documentation | `docs/AGENTS.override.md` | Documentation structure |
| Scripts | `scripts/AGENTS.override.md` | Shell scripts, DevOps |

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
| API routes | `app/routes/api.py` (SINGLE FILE, not `app/routes/api/` directory) |
| Validators | `app/validators.py` (NOT `app/core/validators.py`) |
| Backup logic | `app/scheduler.py:run_daily_backup()` (NOT separate `app/backup.py`) |
| Admin Audit Log model | `app/models.py:397-417` |
| PostRevision model | `app/models.py:173` |
| User model `__repr__` | `app/models.py:63-64` |

## High-Risk Files (Broad Exception Handling)

These files need careful review when modifying exception handling:
- `app/backup_encryption.py:243,268`
- `app/webhooks.py:83`
- `app/tasks.py:115,228,246`
- `app/page_view_buffer.py:129,190`
- `app/routes/admin/series.py` (multiple flash with exception details)

## Skills

Load specialized skills using the `skill` tool with the skill name.

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform | Flask app, SQLAlchemy, session, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard, Docker, Vite |
| `e2e_testing` | E2E browser testing with Playwright | E2E tests, playwright, browser tests, pytest-playwright |
| `ainews` | AI news pipeline with Celery/LLM | pipeline, celery, newsletter, article, source, subscriber |
