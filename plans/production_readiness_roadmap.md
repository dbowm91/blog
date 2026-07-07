# Production Readiness Roadmap

## Context

This roadmap covers the final hardening pass required to take DevLog from a feature-complete private repository to a public, production-ready self-hosted Flask blog CMS release. The current codebase has a broad feature surface: posts, pages, tags, series, admin dashboard, REST API, newsletter scheduling, comments, feeds, FTS5 search, analytics, media, 2FA, backups, Docker, CI, and extensive documentation. The remaining work is less about adding large features and more about making the default installation path reliable, internally consistent, and verifiable.

The inspection that produced this roadmap was source-based through the GitHub connector. It did not execute the full test suite or Docker stack locally. Every phase below should therefore include both code fixes and concrete verification commands.

## Release Goal

The release target is a public repository state where a new operator can clone the project, follow the documented setup path, run tests, build Docker, start the production Compose profile, access the blog/admin UI, exercise basic API writes, upload media, create backups, and understand which features are stable versus experimental.

The default path should be safe for a single-server deployment using SQLite, Redis, one web container, one Celery worker, and an explicit single scheduler owner. Optional features such as S3 storage and PostgreSQL should either be fully supported with dependencies/tests/docs or explicitly marked experimental/deferred.

## Priority Model

P0 items block public production release because they can break the default deployment, CI, API writes, or core admin POST workflows.

P1 items should be completed before announcing production readiness because they affect Docker fidelity, asset correctness, documented configuration, and optional backend truthfulness.

P2 items polish public release quality: docs consistency, release checklists, dependency audit determinism, smoke tests, observability, and security hardening.

## Phase Overview

### Phase 1: Deployment Configuration Correctness

Fix empty environment variable handling, normalize database/cache/Redis configuration, align `DATABASE_URL` and `SQLALCHEMY_DATABASE_URI`, and make setup-created `.env` files actually usable. This phase protects the default Docker and manual setup paths.

Detailed plan: `plans/production_readiness_phase_01_deployment_config.md`.

### Phase 2: CI and Test Harness Reliability

Make CI green and deterministic. Fix invalid test secrets, align agent/test documentation with actual startup requirements, ensure audit jobs inspect project dependencies, and add smoke tests for configuration defaults.

Detailed plan: `plans/production_readiness_phase_02_ci_test_harness.md`.

### Phase 3: CSRF, API Authentication, and POST Semantics

Remove duplicate CSRF validation, exempt API-token routes from browser-session CSRF, preserve CSRF protection for browser forms, and add regression tests for logout, comments, API POST, and admin mutations.

Detailed plan: `plans/production_readiness_phase_03_csrf_api_auth.md`.

### Phase 4: Scheduler and Background Job Ownership

Stop unconditionally starting APScheduler in every web worker. Introduce explicit scheduler ownership, make shutdown lifecycle coherent, document the supported production topology, and add tests that prove the scheduler is disabled by default where intended.

Detailed plan: `plans/production_readiness_phase_04_scheduler_jobs.md`.

### Phase 5: Docker, Frontend Assets, and Runtime Image Fidelity

Make Docker production behavior match documentation and CI. Decide whether Vite assets are built into the image or intentionally served through fallback paths; prefer a multi-stage Docker build with Node assets and a Python runtime image.

Detailed plan: `plans/production_readiness_phase_05_docker_frontend_assets.md`.

### Phase 6: Storage and Database Feature Scope

Resolve the S3 and PostgreSQL support boundary. Either fully wire dependencies, backend-specific behavior, tests, and docs, or mark them experimental and keep the release promise scoped to local storage plus SQLite.

Detailed plan: `plans/production_readiness_phase_06_storage_database_scope.md`.

### Phase 7: Documentation, Packaging, and Public Release Cleanup

Replace local/operator config with example config conventions, correct stale setup/deployment docs, add public release artifacts, and ensure README claims match default behavior.

Detailed plan: `plans/production_readiness_phase_07_docs_release_packaging.md`.

### Phase 8: Security, Observability, and Final Verification

Tighten trusted proxy/IP handling, health/metrics documentation, security checklist, backup restore drill, and final end-to-end smoke verification.

Detailed plan: `plans/production_readiness_phase_08_security_observability_verification.md`.

## Recommended Execution Order

Execute phases 1 through 4 first. These fix blockers that can invalidate downstream tests and documentation. Execute phase 5 next so Docker and CI reflect real production behavior. Execute phase 6 after phase 5 because storage/database decisions influence documentation and smoke tests. Execute phase 7 after the code behavior is stable. Execute phase 8 as the closure pass.

Do not merge a documentation-only claim of production readiness until all P0 and P1 verification commands pass in CI and at least one local or CI Docker Compose smoke test proves the documented production profile starts.

## Release Acceptance Criteria

The release candidate is acceptable when all of the following are true:

1. `python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80` passes with valid test secrets.
2. E2E tests pass or any intentionally skipped E2E subset is explicitly documented with rationale.
3. `ruff check .`, `ruff format --check .`, and `mypy app` pass.
4. `npm ci` and `npm run build` pass.
5. `docker build .` succeeds and the resulting image contains whatever assets production expects.
6. `docker compose --profile production up -d --build` starts healthy services with a fresh `.env` and without requiring undocumented env vars.
7. A fresh browser session can log in, log out, create/edit/publish a post, submit a comment, upload media, and view feeds.
8. API-key JSON writes work without CSRF tokens while browser form POSTs remain CSRF-protected.
9. Only the intended scheduler owner executes scheduled jobs in the supported production topology.
10. Documentation consistently names the canonical database env var and setup path.
11. Optional S3/PostgreSQL support is either verified or explicitly marked experimental.
12. The public repository does not contain operator-local config, generated secrets, local database files, uploaded media, or stale plan claims.

## Non-Goals for This Roadmap

This pass should not add a plugin system, multi-tenant SaaS features, WYSIWYG editing, native mobile apps, or real-time collaboration. Those are outside the current product boundary. This pass should also avoid broad UI redesign unless it directly improves production correctness, public onboarding, or release trust.

## Handoff Notes

Use small PRs when possible. The safest PR boundaries are one phase per PR, with phase 1 and phase 3 split further if the test impact is large. Each PR should update or add tests next to the behavior it changes. Avoid line-number references in docs; refer to functions, files, routes, and environment variables by name.
