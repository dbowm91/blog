# Follow-Up Plan: A/B Deployment Documentation Cleanup, CI Verification, and Release Polish

## Objective

Close the remaining release-readiness gaps after the initial A-E implementation pass. The main implementation work for Milestones C, D, and E appears to have landed: metrics and detailed health are hardened, database support is now backend-aware with SQLite as the v1 supported path, and API scope matching supports exact scopes, `admin:*`, and category wildcards. The remaining risk is concentrated around Milestones A and B: deployment topology language, nginx/TLS profile semantics, documentation consistency, and CI/status verification.

This plan is a focused cleanup pass. It should not introduce broad new features. It should make the supported deployment story boring, reproducible, and impossible to misread.

## Current state summary

Recent commits after the plan files indicate:

- `ENABLE_METRICS` was added and `/metrics` is disabled by default.
- Detailed health now supports header/Bearer/query authentication and fails closed in production without a health secret.
- SQLite is explicitly documented as the v1 supported production database.
- SQLite-only health checks are gated by database dialect.
- API scope matching now supports `scope_allows()`, exact scopes, `admin:*`, and category wildcards.
- Production Compose/docs were partially shifted toward `blog + celery + redis` with an optional `reverse-proxy` profile.

Remaining cleanup:

- Documentation still contains potentially contradictory language around whether the Docker stack terminates TLS and whether the optional nginx profile handles TLS termination.
- A/B did not appear as a dedicated implementation pass; the changes landed incidentally through C/D docs updates.
- CI/status checks were not visible through the GitHub connector for the latest commit, so validation must be explicitly confirmed or made easier to run locally.
- Public-release docs need one final consistency sweep across README, DEPLOY.md, architecture docs, `.env.example`, Compose comments, and CI notes.

## Recommended product decision

Use this as the canonical v1 production topology:

- `production` profile starts `blog`, `celery`, and `redis`.
- The app binds to `127.0.0.1:5000` on the host.
- TLS is the operator's responsibility and should usually be handled by an external reverse proxy such as Caddy, host-level nginx, Traefik, cloud load balancer, or equivalent.
- The repository's nginx service, if retained, is optional and not the default supported TLS path unless its certificate story is complete and validated.
- SQLite WAL is the supported v1 database.
- Local filesystem uploads are supported.
- S3, PostgreSQL, multi-host scaling, and bundled TLS automation remain experimental/planned.

The key wording distinction: the core Docker production stack does not terminate TLS. An optional nginx profile may be provided as an example or advanced option, but it should not be described as both outside the core stack and the default TLS terminator.

## Files to inspect and update

Primary files:

- `README.md`
- `DEPLOY.md`
- `.env.example`
- `docker-compose.yml`
- `docker-compose.ci.yml`
- `.github/workflows/ci.yml`

Secondary files:

- `AGENTS.md`
- `RELEASE.md`
- `SECURITY.md`
- `architecture/deployment/docker.md`
- `architecture/deployment/cicd.md`
- `architecture/infrastructure/overview.md`
- `architecture/overview.md`
- `nginx/nginx.conf`
- `nginx/conf.d/*`

Tests and validation scripts if present:

- `tests/e2e/*`
- `tests/test_health.py`
- `tests/test_metrics.py`
- `scripts/*release*`
- `scripts/*check*`

## Workstream 1: Normalize nginx/TLS language

### Problem

Docs currently trend in the right direction, but some wording can still be read as contradictory. One example pattern to eliminate is:

- "The Docker stack does not terminate TLS."
- "The included nginx config (`--profile reverse-proxy`) handles TLS termination, rate limiting, and security headers."

Both can be true only if the docs clearly define "core production stack" versus "optional nginx profile." Without that precision, new users may not know whether they need to configure certificates outside the repo.

### Required changes

In README and DEPLOY.md, define terms once and reuse them consistently:

- **Core production profile**: `docker compose --profile production up -d --build`; starts app, Celery, Redis; binds app to localhost; does not terminate TLS.
- **Optional reverse-proxy profile**: `docker compose --profile production --profile reverse-proxy up -d --build`; starts included nginx if the operator has configured certificates and nginx config correctly.
- **Recommended public deployment**: external host-level reverse proxy such as Caddy/nginx/Traefik forwards HTTPS traffic to `http://127.0.0.1:5000`.

Suggested wording:

"The core production profile does not terminate TLS. For public internet deployment, terminate TLS with a host-level reverse proxy such as Caddy, nginx, or Traefik and proxy to `http://127.0.0.1:5000`. The repository also includes an optional nginx Compose profile for operators who want to manage nginx inside Compose, but it is not required for the supported single-host path and must be configured with valid certificates before public use."

### Acceptance criteria

- No doc states that the default `production` profile includes nginx.
- No doc implies TLS certificates are automatic.
- Optional nginx is clearly optional and advanced.
- Every command that includes `--profile reverse-proxy` explains what else must be configured.
- Every command that uses only `--profile production` explains that public TLS requires an external proxy.

## Workstream 2: Verify Compose topology and comments

### Required checks

Inspect `docker-compose.yml` and ensure:

- `blog` publishes `127.0.0.1:5000:5000` for the production profile, or the docs match whatever actual mapping exists.
- `nginx` is under `profiles: [reverse-proxy]`, not `production`, unless the docs deliberately choose bundled nginx as the default.
- `celery` and `redis` are under `profiles: [production]` if they are part of supported v1 production.
- `backup` remains under `profiles: [backup]`.
- Compose comments no longer call nginx part of the production stack if it is optional.
- `ENABLE_METRICS` is included in the app environment block if the app uses environment-driven config from Compose.
- `HEALTH_CHECK_SECRET` and `METRICS_SECRET` comments match the new fail-closed behavior.

Inspect `docker-compose.ci.yml` and ensure:

- It only overrides what CI needs.
- It still exposes `5000:5000` in CI if CI cannot use localhost-bound mapping.
- It does not rely on nginx logs or nginx service when nginx is not in the CI profile.

### Acceptance criteria

- `docker compose --profile production config` matches README/DEPLOY claims.
- `docker compose --profile production --profile reverse-proxy config` has coherent nginx service configuration.
- CI workflow diagnostics do not reference nginx unless the reverse-proxy profile is used in that workflow.

## Workstream 3: Final support matrix cleanup

### Required changes

Ensure README and DEPLOY.md contain a consistent support matrix.

Recommended matrix values:

| Area | v1 status | Notes |
|---|---|---|
| Single-host Docker Compose | Supported | Recommended deployment path |
| SQLite WAL | Supported | Default production database for v1 |
| Local uploads | Supported | Stored in persistent volume/local upload path |
| Redis | Supported | Cache, rate-limit storage, Celery broker/result as configured |
| Celery worker | Supported | Included in production profile if retained there |
| APScheduler | Supported with one owner | Disabled by default; enable in exactly one app/scheduler owner |
| External TLS reverse proxy | Supported/recommended | Caddy/nginx/Traefik/cloud proxy to localhost app |
| Included nginx profile | Optional/advanced | Requires explicit reverse-proxy profile and certificate configuration |
| Metrics endpoint | Supported when explicitly enabled | Disabled by default; secret required in production |
| Detailed health | Supported when protected | Basic health remains public; detailed health requires secret in production |
| PostgreSQL | Experimental/planned | Not recommended for v1 production |
| S3-compatible media | Experimental | Not recommended for v1 production unless manually validated |
| Multi-host scaling | Unsupported for v1 | SQLite and scheduler assumptions are single-host |

### Acceptance criteria

- README and DEPLOY matrix statuses match exactly or intentionally use a shorter README version with the same semantics.
- No feature is `Stable` in one file and `Experimental` in another.
- PostgreSQL and S3 are consistently not recommended for v1 production.
- Celery is not described as both production-supported and experimental.

## Workstream 4: First-run and cookie documentation polish

### Issue

The docs mention first-admin bootstrap and localhost binding. They should also make the interaction with `SESSION_COOKIE_SECURE=true` unavoidable for local HTTP testing.

### Required changes

Add a short note near quick start and `.env.example`:

- Production behind HTTPS: keep `SESSION_COOKIE_SECURE=true`.
- Local HTTP testing at `http://localhost:5000`: set `SESSION_COOKIE_SECURE=false` or admin login cookies may not persist.
- This should not be recommended for public HTTP deployment.

Clarify first-admin behavior:

- `ADMIN_PASSWORD` is required at startup by current app validation.
- It is used to create the initial admin only when no user exists.
- It does not rotate an existing admin password.
- Use admin settings or password reset flow after bootstrap.

### Acceptance criteria

- New users can understand why login might fail on plain HTTP with secure cookies.
- Docs do not encourage insecure cookies in production.
- Bootstrap password semantics are present in README, DEPLOY.md, and `.env.example` comments.

## Workstream 5: CI/status verification and local release check

### Problem

The GitHub connector did not show workflow/status checks for the latest implementation commit. This does not mean CI failed, but it means the repo's current state could not be verified from status metadata during review.

### Required changes

At minimum, document the exact validation commands in `RELEASE.md` or a new `scripts/release_check.sh`.

Preferred implementation: add `scripts/release_check.sh` that runs:

```bash
#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
mypy app/
python -m pytest tests/ --ignore=tests/e2e -v
npm ci
npm run build
docker build -t devlog:release-check .
docker compose --profile production config
```

Optional Docker smoke extension:

```bash
cp .env.example .env.release-check
# generate temporary SECRET_KEY and ADMIN_PASSWORD or use exported env vars
COMPOSE_PROJECT_NAME=devlog_release_check docker compose --profile production up -d --build
curl -f http://127.0.0.1:5000/health
COMPOSE_PROJECT_NAME=devlog_release_check docker compose --profile production down -v
```

Keep destructive cleanup safe and scoped to a unique Compose project name.

### CI workflow check

Inspect `.github/workflows/ci.yml` and ensure it still covers:

- Ruff lint.
- Ruff format check.
- Mypy.
- Unit tests with coverage threshold.
- Frontend build.
- pip-audit.
- Docker image build.
- E2E tests against the actual app URL used in CI.

If workflows are not triggering because the repo is private, branch settings are unusual, or connector cannot see them, document local validation as the authoritative fallback.

### Acceptance criteria

- There is a documented one-command local release check or a precise set of release validation commands.
- CI diagnostics no longer reference services outside the selected profiles.
- CI e2e base URL matches the service actually exposed in CI.
- Maintainers can verify A-E functionality without relying on external status metadata.

## Workstream 6: Grep-based stale reference sweep

Run a systematic grep over docs and configs for stale or contradictory strings.

Suggested checks:

```bash
grep -R "production.*nginx\|nginx.*production" -n README.md DEPLOY.md architecture AGENTS.md RELEASE.md docker-compose.yml .github/workflows || true
grep -R "localhost:5000\|127.0.0.1:5000" -n README.md DEPLOY.md architecture AGENTS.md RELEASE.md || true
grep -R "METRICS_SECRET.*HEALTH_CHECK_SECRET\|fallback.*HEALTH_CHECK_SECRET\|public metrics\|metrics.*public" -n README.md DEPLOY.md architecture AGENTS.md RELEASE.md app tests || true
grep -R "PostgreSQL\|postgres" -n README.md DEPLOY.md architecture AGENTS.md RELEASE.md .env.example || true
grep -R "Celery.*experimental\|experimental.*Celery" -n README.md DEPLOY.md architecture AGENTS.md RELEASE.md || true
grep -R "S3" -n README.md DEPLOY.md architecture AGENTS.md RELEASE.md .env.example || true
```

For each result, decide whether it is correct. Do not blindly delete references; the goal is consistency.

### Acceptance criteria

- No stale metrics fallback language remains.
- No stale default `production = blog + celery + redis + nginx` language remains unless bundled nginx is deliberately restored as default.
- No stale PostgreSQL production recommendation remains.
- No stale Celery experimental label remains if Celery is supported in production profile.
- No stale CI nginx log references remain if nginx is not part of the CI profile.

## Workstream 7: Optional nginx profile decision point

If the optional nginx profile is kept, decide whether it is a maintained feature or merely an example.

### If maintained

- Add `nginx/README.md` with exact certificate volume expectations.
- Ensure Compose mounts certificate paths if needed.
- Add an nginx config syntax validation command.
- Consider adding a CI job that validates nginx config without needing real certificates.
- Document whether nginx handles HTTP-to-HTTPS redirect, static files, upload size limits, rate limits, and proxy headers.

### If example-only

- Rename profile or docs language to make it clear this is a sample.
- Consider moving nginx config under `examples/nginx/` instead of active Compose service.
- Keep the supported path as host-level external reverse proxy.

### Acceptance criteria

- Users know whether the repo-maintained nginx profile is expected to work as-is.
- Certificate requirements are explicit.
- There is no implication that TLS is automatic.

## Validation checklist

After implementation, run:

```bash
ruff check .
ruff format --check .
mypy app/
python -m pytest tests/ --ignore=tests/e2e -v
npm ci
npm run build
docker build -t devlog:cleanup-check .
docker compose --profile production config
docker compose --profile production --profile reverse-proxy config
```

If local Docker smoke is possible:

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="temporary-test-password-123A!"
export SESSION_COOKIE_SECURE=false
COMPOSE_PROJECT_NAME=devlog_cleanup_check docker compose --profile production up -d --build
curl -f http://127.0.0.1:5000/health
curl -i http://127.0.0.1:5000/metrics
COMPOSE_PROJECT_NAME=devlog_cleanup_check docker compose --profile production down -v
```

Expected metrics result with defaults: `404` or the documented disabled response.

## Definition of done

This cleanup pass is complete when:

- The default production deployment path is described identically across README, DEPLOY.md, Compose comments, and architecture docs.
- Optional nginx/TLS wording is precise and non-contradictory.
- Support matrix statuses are synchronized.
- `.env.example` is safe and operationally clear.
- CI/local release validation commands are documented or scripted.
- Stale references to old metrics fallback, nginx-in-production default, or PostgreSQL production readiness are removed or explicitly marked experimental.
- No code behavior from C, D, or E is regressed.

## Suggested commit message

`docs: close deployment topology and release validation gaps`

If a release-check script is added, use:

`chore: add release validation script and deployment docs cleanup`
