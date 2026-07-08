# DevLog Public Release Readiness Roadmap

## Purpose

This roadmap covers the implementation work needed to move DevLog from a feature-complete private/self-hosted blog CMS toward an easier, safer, and more coherent public release. The current codebase already has many release-grade components: Docker production support, Vite asset builds, CI, e2e tests, security headers, CSRF protection, rate limiting, 2FA, health checks, backups, feeds, comments, analytics, a REST API, and admin tooling. The remaining work is less about adding broad new functionality and more about removing ambiguity, tightening defaults, correcting edge-case behavior, and making first-time deployment reliable.

The roadmap is intentionally ordered. Milestones A through E should land before broader polish work because they affect first-run deployment correctness, public operational exposure, support boundaries, and API authorization semantics.

## Release posture

The intended v1 public-release posture should be explicit:

DevLog v1 supports a single-server self-hosted deployment using Docker Compose, SQLite in WAL mode, local filesystem uploads, Redis for production cache/rate-limit/task broker support, one Celery worker, and exactly one scheduler owner. External TLS termination through Caddy, nginx, Traefik, a cloud load balancer, or another administrator-managed reverse proxy should be the recommended production boundary unless the project commits to maintaining a bundled TLS-capable nginx path.

Experimental features should remain visible but clearly separated from the supported path. PostgreSQL, S3-compatible storage, multi-host scaling, Celery Beat, external schedulers, and horizontally scaled app containers can remain planned or experimental, but public-release docs should not imply that they are equivalent to the supported path.

## Milestone A: Canonical single-server deployment path

Goal: make the default deployment topology unambiguous and reproducible.

The repository currently has conflicting signals around Docker exposure, nginx, TLS, and access URL. Docker Compose exposes the app internally, publishes nginx on ports 80 and 443, and the docs also state that the blog will be available at localhost:5000. The deployment guide also says the included nginx expects TLS to be handled externally. This must be normalized before public release.

The implementation should choose one canonical topology and make code, compose files, README, and deployment docs all match it. The recommended option for release simplicity is an external reverse-proxy topology: the app binds to localhost for host-level reverse proxying, nginx is moved out of the default production profile or documented as optional, and TLS termination is explicitly outside the core stack. If bundled nginx remains in the production profile, then the project needs complete nginx/TLS instructions and the README access URL must match the published ports.

Primary deliverables:

- Canonical production topology decision.
- Updated Docker Compose profile behavior.
- Matching README and DEPLOY quick-start commands.
- Smoke validation for the exact documented deployment command.
- Clear scheduler ownership and worker-count notes in the deployment quick start.

Acceptance criteria:

- A fresh user can clone the repo, copy `.env.example`, set required secrets, run one documented command, and reach the site at the documented URL.
- The documented URL matches the actual Compose port exposure.
- The docs do not simultaneously recommend incompatible nginx/TLS models.
- CI or a local release check exercises the same Compose path described in the README.

## Milestone B: Deployment documentation and support matrix cleanup

Goal: make public documentation match the product's actual supported surface.

The docs should present a short, concrete support matrix early, before advanced topics. The matrix should state what is stable, what is experimental, and what is not recommended. Users should not need to infer this from scattered warnings. This milestone should also clean up `.env.example` formatting, environment-variable descriptions, backup path descriptions, Celery status, scheduler caveats, PostgreSQL caveats, and first-admin bootstrap semantics.

Primary deliverables:

- README deployment section rewritten to match Milestone A.
- DEPLOY.md deployment guide rewritten for the canonical topology.
- `.env.example` normalized with no odd indentation and with production-safe comments.
- A concise supported/experimental/unsupported matrix.
- A v1 release checklist section.

Acceptance criteria:

- README and DEPLOY.md use the same commands, topology names, and access URLs.
- Experimental features are not described as production-stable.
- First-admin bootstrap behavior is explicitly documented.
- Celery's status is consistent across Compose, README, DEPLOY.md, and support matrix.
- PostgreSQL is either clearly unsupported for v1 or fully covered by backend-aware implementation work.

## Milestone C: Metrics and health hardening

Goal: prevent accidental public exposure of operational data.

Basic `/health` can remain public for Docker and uptime monitors. Detailed health and `/metrics` should require explicit opt-in and authentication in production. The current metrics behavior permits public metrics when neither `METRICS_SECRET` nor `HEALTH_CHECK_SECRET` is configured. That is too permissive for public release.

This milestone should introduce explicit enablement and secret requirements for metrics in production. It should also prefer header-based secrets over query-string secrets while preserving a compatibility path if desired. Detailed health should remain protected when `HEALTH_CHECK_SECRET` is set and should fail closed in production if detailed mode is enabled without an authentication mechanism.

Primary deliverables:

- `ENABLE_METRICS` config flag or equivalent explicit enablement.
- Production guard that rejects or disables metrics without a secret.
- Header-based authentication support for metrics and detailed health.
- Tests for public basic health, unauthorized detailed health, authorized detailed health, disabled metrics, unauthorized metrics, and authorized metrics.
- Documentation updates for monitoring setup.

Acceptance criteria:

- `/metrics` is not public by default in production.
- Production startup warns or fails when metrics are enabled without a secret.
- Detailed health does not reveal operational details without authorization.
- The Docker health check continues to use unauthenticated basic health successfully.

## Milestone D: Database support boundary and backend-sensitive health checks

Goal: make database support honest and prevent SQLite-specific checks from misbehaving on other engines.

The cleanest v1 public-release stance is SQLite WAL as the supported database for single-server deployments, with PostgreSQL marked experimental or planned. The code should still avoid crashing when a non-SQLite URI is configured, but it should not imply full PostgreSQL readiness unless search, backup, health, migrations, and docs are validated.

Health checks currently include SQLite-specific FTS and integrity checks. These should be gated by SQLAlchemy dialect. For SQLite, retain the current `sqlite_master`, FTS5, and `PRAGMA integrity_check` behavior. For PostgreSQL or other engines, return `unsupported`, `not_applicable`, or a simple connection check unless real support is implemented.

Primary deliverables:

- Database support policy in README and DEPLOY.md.
- Backend/dialect detection helper.
- Backend-aware search health check.
- Backend-aware integrity check.
- Tests that validate SQLite behavior and non-SQLite graceful handling.

Acceptance criteria:

- SQLite remains fully supported and tested.
- Non-SQLite configuration does not trigger SQLite-only health queries.
- Docs do not instruct users to deploy PostgreSQL as a supported v1 production option unless implementation and tests are completed.
- Health responses distinguish `ok`, `error`, and `unsupported/not_applicable` states clearly.

## Milestone E: API authorization correctness

Goal: ensure API token scopes behave as documented and are safe to use for integrations.

The API scope registry includes `admin:*`, but `require_scope()` currently checks exact scope membership only. That means wildcard tokens will not satisfy scoped endpoint checks unless every exact scope is also present. This is a correctness bug and a documentation hazard.

This milestone should define scope semantics, implement deterministic wildcard matching, and add focused tests for legacy API keys, scoped tokens, wildcard scopes, revoked/expired tokens, missing scopes, and unauthenticated requests.

Primary deliverables:

- Scope matching helper with exact, category wildcard, and `admin:*` behavior.
- Tests for all API auth paths.
- Documentation of legacy API key vs scoped API tokens.
- Optional admin UI/API cleanup so generated tokens expose scopes clearly.

Acceptance criteria:

- `admin:*` satisfies all scoped API routes.
- Category wildcards such as `posts:*` satisfy `posts:read` and `posts:write` if the project chooses to support category wildcards.
- Missing scopes still fail closed.
- Legacy `API_KEY` behavior remains backward-compatible.
- API docs match runtime behavior.

## Later milestones after A-E

After A-E, the next release-hardening sequence should be:

Milestone F: First-admin bootstrap hardening. Preserve easy deployment but document that bootstrap credentials are only used when no users exist. Add logs/tests that existing users are never overwritten by changed environment variables.

Milestone G: Public comment and spam hardening. Keep moderation-by-default. Add optional Turnstile/hCaptcha provider abstraction, configurable banned domains, stricter URL thresholds, spam reason visibility, and tests.

Milestone H: Runtime/process model cleanup. Validate Granian ASGI-over-WSGI shutdown behavior, scheduler ownership, worker count recommendations, and Celery/scheduler interaction.

Milestone I: Release validation suite. Add `scripts/release_check.sh` or equivalent to run lint, format, type check, unit tests, frontend build, Docker build, Compose smoke test, health checks, admin-login e2e, and docs/link validation.

Milestone J: Public repository polish. Add or revise `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, issue templates, release checklist, screenshots, architecture notes, and secret/private-hostname scrub.

## Suggested execution order

The recommended order is A, B, C, D, E. Milestone A should land first because it determines the deployment shape that all docs and tests must describe. Milestone B should immediately follow to prevent stale instructions from persisting. Milestones C and D reduce public operational risk and support ambiguity. Milestone E closes a concrete API correctness bug before integrations are documented for public users.

Each milestone should be completed with code changes, tests, and documentation in the same pass. Public-release readiness depends less on any single feature and more on keeping runtime behavior, docs, and validation synchronized.
