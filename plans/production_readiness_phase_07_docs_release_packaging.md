# Phase 7: Documentation, Packaging, and Public Release Cleanup

## Objective

Make the repository suitable for public readers and first-time operators. Documentation should describe actual behavior, setup should be reproducible, local/operator-specific files should not be committed as defaults, and release metadata should be complete.

## Problems to Address

The README is polished but includes at least one inaccurate Quick Start claim. Deployment docs and runtime code disagree on database env var naming. The code expects `config.toml.example` to exist when config is missing, but the repository currently uses a committed `config.toml`. Some docs advertise optional backend support more strongly than the implementation appears to justify. The public release should avoid stale plan claims and operator-local defaults.

## Scope

This phase covers README, DEPLOY.md, USAGE.md, ARCHITECTURE.md, SECURITY.md, CONTRIBUTING.md, AGENTS.md, example config files, packaging metadata, license/release checklist, and public repository hygiene. It does not add new product features.

## Implementation Steps

1. Correct README Quick Start.

   Ensure the quick start accurately says what `./setup.sh` does. If setup does not start the server, do not claim it does. Include the exact command to load `.env` or document dotenv behavior if phase 1 adds it.

2. Add or normalize `config.toml.example`.

   Use safe generic values:

   - Generic author name or placeholder.
   - `base_url = "http://localhost:5000"` for local defaults, with production docs instructing HTTPS public URL.
   - SMTP host blank by default unless the newsletter path intentionally defaults to Gmail.
   - Comments explaining env-only secrets.

   Then update setup to copy example to local `config.toml` when absent.

3. Decide committed `config.toml` policy.

   For public release, prefer:

   - `config.toml.example` committed.
   - `config.toml` ignored.
   - Existing committed `config.toml` removed in a cleanup PR.

   If the project wants a committed default `config.toml`, make it generic and ensure no operator-local identity is embedded.

4. Align environment variable docs.

   Search all docs for:

   - `DATABASE_URL`
   - `SQLALCHEMY_DATABASE_URI`
   - `CELERY_BROKER_URL`
   - `REDIS_URL`
   - `CACHE_REDIS_URL`
   - `ENABLE_SCHEDULER`
   - `SESSION_COOKIE_SECURE`
   - `STORAGE_BACKEND`

   Update docs to one canonical behavior. Mention aliases only if the code supports them.

5. Update deployment topology docs.

   Document the stable default topology:

   - One web service/container.
   - One Redis service if using Docker cache/rate limits/Celery.
   - One Celery worker if async jobs are enabled.
   - Exactly one scheduler owner if scheduled publish/newsletter/backups are enabled.
   - SQLite single-server caveats.
   - Reverse proxy TLS required for production secure cookies.

6. Update feature support matrix.

   Add a clear stable/experimental table for storage/database/search/deployment modes, using the decisions from phase 6.

7. Add release checklist.

   Create `RELEASE.md` or a section in DEPLOY.md that includes:

   - Tests/lint/typecheck/frontend build.
   - Docker build and Compose smoke.
   - Dependency audit.
   - Config/docs audit.
   - Backup/restore smoke.
   - Changelog/tagging process.
   - Public repo hygiene checks.

8. Add or update changelog.

   If there is no `CHANGELOG.md`, add one with an initial `Unreleased` section and a `1.0.0` release-prep section. Keep it factual. Do not overstate support.

9. Review package metadata.

   `pyproject.toml` currently has basic project metadata but does not list dependencies under `[project]`. If the app is not intended to be pip-installable yet, document that requirements files are canonical. If packaging is intended, add dependency metadata and entry points in a separate focused PR.

10. Audit public-facing security docs.

   SECURITY.md should include vulnerability reporting, supported versions, secret handling, CSRF/session protection, proxy assumptions, and responsible disclosure. Avoid claiming formal security certification.

11. Review AGENTS.md after code changes.

   Update agent notes to reflect the new scheduler flag, config env behavior, CSRF/API rules, Docker asset build behavior, and backend support matrix. Remove stale warnings that are fixed.

12. Add docs verification pass.

   Use grep/search for old inaccurate phrases after code changes. Examples:

   - `starts the dev server`
   - `DATABASE_URL` if unsupported
   - `config.toml.example` if missing
   - `workers 4` scheduler language
   - `S3` claims if experimental

## Verification Commands

Documentation grep examples:

```bash
grep -R "DATABASE_URL\|SQLALCHEMY_DATABASE_URI\|CELERY_BROKER_URL\|ENABLE_SCHEDULER" -n README.md DEPLOY.md USAGE.md ARCHITECTURE.md SECURITY.md AGENTS.md docs/ .env.example config.toml.example || true
grep -R "starts the dev server\|production-ready" -n README.md DEPLOY.md docs/ || true
```

Build and tests after docs/config changes:

```bash
ruff check .
ruff format --check .
mypy app
npm ci
npm run build
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ -v --ignore=tests/e2e
```

Public hygiene checks:

```bash
git status --short
git ls-files | grep -E '(^|/)(\.env|instance/|logs/|backups/|app/static/uploads/|.*\.db$)' && exit 1 || true
```

## Acceptance Criteria

A first-time operator can follow README and DEPLOY.md without encountering known mismatches. Public docs accurately identify stable and experimental features. `config.toml.example` and `.env.example` are sufficient to bootstrap a deployment. No operator-local config, secrets, databases, uploads, or generated logs are committed. Release checklist exists and maps to actual commands.

## Risks

Documentation can drift if changed before phases 1–6 land. Execute this phase after behavior stabilizes, then do a final grep-based audit. Avoid broad marketing language until the Docker and CI smoke tests pass.
