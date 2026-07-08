# Production Readiness Final CI Closure Plan

## Context

The production-readiness corrective pass closed the major release blockers: dotenv loading, tracked config cleanup, API scope enforcement, split health diagnostics, metrics secret naming, and release classifier posture. A follow-up review found two remaining release-validation items that should be closed before public release:

1. The E2E workflow appears to curl `http://localhost:5000/health`, but the Compose production stack only exposes the `blog` service internally and publishes nginx ports `80` and `443` to the host. Unless a CI-only port mapping exists, `localhost:5000` is not reachable from the Actions host.
2. The rewritten CI workflow no longer includes the dependency security audit job that previously ran `pip-audit -r requirements.txt --fail-on=all`.

This plan is intentionally narrow. It should produce a small patch and then require a real green GitHub Actions run.

## Objective

Make CI a reliable release gate by fixing the E2E service reachability path and restoring dependency audit coverage. The final state should demonstrate that a clean checkout can lint, typecheck, test, build frontend assets, build the Docker image, run the production Compose stack, pass E2E smoke tests, and audit runtime dependencies.

## Non-Goals

Do not redesign deployment topology, change the application runtime model, add new product features, change API semantics, or rewrite E2E tests beyond the host/port wiring needed for CI. Do not mark the package as production/stable in this pass unless CI has already passed and the release checklist has been completed.

## Phase A: Fix E2E Host/Port Reachability

### Current Concern

The production Compose service uses:

- `blog.expose: 5000`, which exposes the port to other Compose services but does not publish it to the GitHub Actions host.
- `nginx.ports: 80:80` and `443:443`, which are host-reachable.

The current E2E wait step curls `http://localhost:5000/health`. That is likely wrong for the production profile because host port 5000 is not published.

### Preferred Fix

Route E2E checks through nginx on port 80, matching the production Compose topology.

Implementation steps:

1. Update `.github/workflows/ci.yml` E2E wait loop to curl `http://localhost/health` instead of `http://localhost:5000/health`.
2. Confirm nginx config forwards `/health` to the `blog` upstream. If not, update nginx config or select the correct published endpoint.
3. Ensure E2E tests target the same base URL. If tests use an env var such as `BASE_URL`, set it explicitly to `http://localhost`. If tests currently hardcode `localhost:5000`, update fixtures to respect an env var and default to `http://localhost` under Compose.
4. Keep `SESSION_COOKIE_SECURE=false` in CI `.env` so browser tests over HTTP can authenticate.
5. Preserve `ENABLE_SCHEDULER=false` in CI unless E2E explicitly validates scheduled jobs.

### Alternative Fix

Publish the app port only in CI:

1. Add a CI-only Compose override file, for example `docker-compose.ci.yml`, with:

   ```yaml
   services:
     blog:
       ports:
         - "5000:5000"
   ```

2. Run:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.ci.yml --profile production up -d --build
   ```

This is acceptable, but it tests a topology that differs from production. Prefer curling through nginx unless the E2E suite is explicitly designed to bypass nginx.

### Acceptance Criteria

- CI waits on a host-reachable URL.
- The selected URL matches E2E test configuration.
- The wait loop prints useful diagnostics on failure: `docker compose ps`, `docker compose logs blog`, `docker compose logs nginx`, and optionally `docker compose logs redis`.
- The fix does not require opening port 5000 in production documentation unless that is intentionally supported.

## Phase B: Restore Dependency Security Audit

### Current Concern

The current CI workflow has lint/type, tests, frontend build, Docker build, and E2E jobs, but no `security-audit` job. The release gate should audit runtime dependencies.

### Implementation Steps

1. Add a `security-audit` job to `.github/workflows/ci.yml`.
2. Use current official action versions consistent with the rest of the workflow.
3. Install `pip-audit` without installing the full application unless needed.
4. Audit runtime requirements:

   ```bash
   pip-audit -r requirements.txt --fail-on=all
   ```

5. Decide whether to audit dev requirements separately. If included, add a second step:

   ```bash
   pip-audit -r requirements-dev.txt --fail-on=all
   ```

   Runtime audit is mandatory. Dev audit is optional but useful.

6. If a known advisory is accepted temporarily, do not silently ignore it. Add a documented ignore with advisory ID, reason, and expiry condition. Avoid broad ignore lists.

### Recommended Job Shape

```yaml
security-audit:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install pip-audit
      run: |
        python -m pip install --upgrade pip
        pip install pip-audit

    - name: Audit runtime dependencies
      run: pip-audit -r requirements.txt --fail-on=all
```

### Acceptance Criteria

- CI includes a required dependency audit job.
- The audit checks `requirements.txt` directly.
- Any ignored advisories are specific and documented.
- The release checklist references this audit as part of the public-release gate.

## Phase C: Tighten CI Job Dependencies and Diagnostics

### Implementation Steps

1. Make E2E depend on the relevant upstream jobs:

   ```yaml
   needs: [test, docker-build]
   ```

   Consider also including `frontend-build` and `security-audit` in the release gate, but E2E only needs the built runtime path.

2. Ensure Docker build and E2E do not do redundant expensive work unnecessarily. If E2E rebuilds the image, that is acceptable for simplicity. If build time becomes a problem later, introduce image caching or artifact handoff.

3. On E2E failure, print targeted diagnostics:

   ```bash
   docker compose ps
   docker compose logs blog
   docker compose logs nginx
   docker compose logs redis
   docker compose logs celery || true
   ```

4. Confirm cleanup uses the same Compose files/profile as startup.

5. If a CI override file is introduced, use it consistently for startup, logs, and cleanup.

### Acceptance Criteria

- E2E waits only after unit tests and Docker build pass.
- E2E failure logs include enough information to identify whether nginx, blog, Redis, or app health caused the failure.
- Cleanup reliably tears down services and volumes.

## Phase D: Local Verification Before Pushing

Run the same commands expected in CI.

```bash
ruff check .
ruff format --check .
mypy app/
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
npm ci
npm run build
pip-audit -r requirements.txt --fail-on=all
docker build -t devlog:ci-closure .
docker run --rm devlog:ci-closure test -f /app/app/static/dist/.vite/manifest.json
```

Then verify Compose topology locally:

```bash
cat > .env <<'EOF'
SECRET_KEY=test-secret-key-test-secret-key-1234
ADMIN_PASSWORD=test-password-123
SESSION_COOKIE_SECURE=false
ENABLE_SCHEDULER=false
EOF

docker compose --profile production up -d --build
docker compose ps
curl -f http://localhost/health
docker compose logs blog --tail=100
docker compose logs nginx --tail=100
docker compose --profile production down -v
```

If the chosen fix is a CI-only port override, verify with the override command instead and document why CI bypasses nginx.

## Phase E: GitHub Actions Verification

After pushing the patch, confirm a real workflow run exists and passes on the latest commit.

Required green jobs:

- `lint-and-type`
- `test`
- `security-audit`
- `frontend-build`
- `docker-build`
- `e2e-tests`

If Actions do not trigger automatically on the commit, manually trigger a workflow dispatch only if the workflow supports it. Otherwise push an empty docs-safe commit or open a PR to trigger CI through the normal `pull_request` path.

## Release Readiness Criteria After This Plan

The repository can be considered a credible release candidate when:

1. E2E service startup and health wait use a host-reachable URL.
2. CI contains a runtime dependency audit job.
3. All CI jobs pass on the latest main commit or release PR commit.
4. Docker image contains built Vite manifest.
5. Production Compose profile starts from `.env.example` plus required secrets.
6. Basic `/health` succeeds through the same route used by CI.
7. No new broad release-blocking findings appear in logs or tests.

## Files Likely to Change

- `.github/workflows/ci.yml`
- Optional: `tests/e2e/conftest.py` or equivalent E2E base URL fixture
- Optional: `docker-compose.ci.yml` if choosing a CI-only published app port
- Optional: `RELEASE.md` if the release checklist needs the restored audit job mentioned explicitly
- Optional: `DEPLOY.md` only if docs currently imply the wrong CI/Compose health URL

## Handoff Notes

Prefer the nginx path first. It exercises the production-facing route, avoids publishing an app port only for tests, and verifies the reverse proxy health path. Only introduce a CI override if nginx health routing is not ready or if E2E tests intentionally target the Flask app directly.

Do not mark the project as `Development Status :: 5 - Production/Stable` in this patch. Treat this as final validation closure; stable classifier can be restored in a separate release commit after green CI and manual smoke verification.
