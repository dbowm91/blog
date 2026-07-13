# OpenCode Config Agent Override

Specialized handling for agent tool configuration.

## Skills Directory

The `.opencode/skills/` directory contains specialized skills:

| Skill | Description | Triggers |
|-------|-------------|----------|
| `blog_cms` | Blog CMS - Flask-based blogging platform | Flask app, SQLAlchemy, session management, CSRF, newsletter, APScheduler, FTS5, REST API, password reset, post revisions, preview links, toasts, dashboard charts, graceful shutdown, Docker deployment, Vite bundler |
| `e2e_testing` | End-to-end browser testing with Playwright | E2E tests, playwright, browser tests, pytest-playwright, UI testing |
| `ainews` | AI news pipeline — Flask backend, Celery workers, LLM pipeline | pipeline, celery, newsletter, article, source, subscriber, admin, config, health, metrics |
| `malu_mesh` | MaluWAF mesh & DHT architecture | mesh, WAF, DHT, upstream routing, service discovery |
| `nara` | Nara chain CLI agent — wallet, transfer, quest, on-chain skills | NARA, quest, mining, airdrop, wallet, balance, transfer, zkid, agent |
| `osinit` | OSINIT Dashboard - FastAPI backend with React/TypeScript frontend | build, test, deploy, data source, panel, SSE, synthesis, authentication, rate limiting, cache |
| `slapper-agent` | Slapper autonomous agent development | agent, constraint, scan, schedule, trigger_event, dispatch, alert, portfolio, memory |

Load a skill using the `skill` tool with the skill name (e.g., `skill: blog_cms`).

## Agent Override Convention

This codebase uses a **module-level override system** for agent context. Each module (directory with a specific purpose) may contain an `AGENTS.override.md` file that provides specialized handling instructions for that module.

When an agent operates within a module, it should:
1. Read the root `AGENTS.md` for general guidance
2. Check for `AGENTS.override.md` in the current module for specialized handling
3. Override files take precedence over root-level guidance when working within that module

## Package.json

Minimal Node.js configuration for Vite frontend build.

## Implementation Planning

When working on the consolidated improvement plan (`plans/plan.md`):

### Parallelization Strategy
- **Wave 1A (Backend Bugs)**: BUG-1 through BUG-5, P0-1, P0-2 - Can run in parallel
- **Wave 1B (Frontend Bugs)**: FE-BUG-1, FE-BUG-2, FE-BUG-3 - Can run in parallel (separate agent)
- **Wave 2 (Security)**: SEC-1 through SEC-6 - Can run in parallel
- **Wave 3 (Config)**: CFG-1 through CFG-4 - Can run in parallel
- **Wave 4, 5, 6, 7**: Can be split across 4 sub-agents working in parallel
- **Wave 8, 9, 10**: Sequential work, can have 1 sub-agent handle all

### Critical Path Dependencies
1. Wave 1 (Bugs) must complete before Wave 4+ (Code Quality)
2. Wave 2 (Security) can run in parallel with Wave 1
3. Wave 3 (Config) can run in parallel with Wave 1-2
4. Wave 8 (Docs) can run anytime (informational)
5. Wave 9 (Features) and Wave 10 (Tech Debt) are independent

### Known Implementation Issues
- `app/static/js/main.js:4` uses variable-based `import(path).then(...)` instead of `import.meta.glob()` - Vite cannot statically analyze
- `app/routes/admin/series.py` has multiple `flash(f"Error ...: {str(e)}")` exposing exception details
- Admin templates use `url_for('static', ...)` instead of `vite_asset()` - bypasses Vite cache-busting
- Nested anchor tags in post cards (`app/templates/index.html:22,40`) - invalid HTML5
- `app/__init__.py:186` uses wrong config key `RATELIMIT_STORAGE_URL` instead of `RATELIMIT_STORAGE_URI`
- `app/scheduler.py` has 8 lock file deletion locations that are dangerous on Linux