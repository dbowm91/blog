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