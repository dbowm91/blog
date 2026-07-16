# Release 1 Closure

**Date:** 2026-07-16 (updated)

## Summary

Release 1 delivers a self-hosted Flask blog CMS with admin dashboard, newsletter scheduling, FTS5 search, custom CSS theming (Halloy migration), 2FA, comments, post series, multi-admin sessions, and a standalone CLI. Seven workstreams were completed:

1. **Core blog CMS** — Markdown posts, pages, tags, series, comments, analytics, media library
2. **Newsletter system** — Subscriber management, scheduled sends, retry logic, SMTP integration
3. **Halloy theme migration** — 50 bundled themes, admin selector, dark/light scheme, accessibility validation
4. **Standalone CLI (`devlog`)** — Config management, admin ops, DB maintenance, data import/export, backup, theme commands
5. **Typed configuration** — 20 frozen dataclasses, multi-layer validation, deployment profiles, TOML/JSON output
6. **Service extraction** — Operational logic moved from Flask CLI into `app/services/operations/`, consumed by both CLI and Flask commands
7. **CI hardening** — 11-job pipeline with dependency consistency checks and package smoke tests

## CI Jobs

| Job | Description |
|-----|-------------|
| `lint-and-type` | ruff lint/format + mypy on `app/` and `devlog_cli/` |
| `test` | pytest with coverage (80% threshold) |
| `theme-policy` | WCAG accessibility strict checks |
| `migration-chain` | Alembic migration verification |
| `theme-package-verification` | Wheel build + theme package audit |
| `frontend-build` | Vite asset build |
| `security-audit` | pip-audit on runtime deps |
| `docker-build` | Docker image build + manifest verification |
| `e2e-tests` | Playwright browser tests against Docker |
| `dependency-consistency` | pyproject.toml ↔ requirements.txt sync |
| `release1-package-smoke` | Wheel build → isolated venv → CLI + app-context smoke |

## Test Results

- All unit tests passing (excluding E2E which requires Docker)
- Coverage above 80% threshold
- mypy on `app/` and `devlog_cli/` (9 pre-existing errors in app/ documented in AGENTS.md)
- ruff lint and format clean
- Docker build succeeds with Vite manifest present
- Migration chain tests pass (alembic migration + drop_theme_preset)
- Package smoke test passes: CLI commands and app-context operations verified
- Dependency manifest consistency check passes

## Known Limitations

- **PostgreSQL**: Experimental — health checks report unsupported for SQLite-specific features
- **S3 storage**: Experimental — not CI-tested
- **Multi-container scheduler**: Requires `ENABLE_SCHEDULER=true` on exactly one container
- **E2E tests**: Require Docker Compose; not runnable in pure CI without container support
- **Single-server only**: No built-in clustering or multi-tenant support

## Release 2 Readiness

Release 2 is ready for planning. Priorities under consideration:

- PostgreSQL production hardening
- S3 storage CI coverage
- Plugin/extension architecture
- Enhanced analytics and reporting
- Performance benchmarks for large post catalogs

The codebase is stable, well-tested, and CI-enforced. Release 1 provides a solid foundation for incremental improvements.

## Gap Closure (2026-07-16)

The following gaps from the initial closure pass were addressed:

1. **CI mypy coverage** — `lint-and-type` now runs `mypy app/ devlog_cli/` (was `mypy app/`)
2. **config_legacy refactor** — Module now projects from typed loader (`load_effective_config`) instead of independently parsing config.toml. Deprecation warning emitted on import. Removed dead `load_config()` and `_validate_config()` functions.
3. **Closure doc** — Updated with migration chain test results and dependency consistency check
