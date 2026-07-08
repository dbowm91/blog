# Milestone B Plan: Deployment Documentation and Support Matrix Cleanup

## Objective

Align DevLog's public documentation with the deployment topology and support boundaries selected in Milestone A. The goal is to remove ambiguity for first-time users and prevent experimental paths from being mistaken for stable production guidance.

This is a documentation-first milestone, but it should be treated as release-critical. Public-release failure often comes from inconsistent operator instructions rather than missing code. README, DEPLOY.md, `.env.example`, Docker comments, and CI usage should describe one coherent product.

## Current issues to address

The current docs and config have several mismatches that need cleanup:

- README states Docker production can be accessed at `http://localhost:5000`, while Compose may route through nginx or expose only internal app ports depending on profile behavior.
- DEPLOY.md mixes quick-start local development, Granian, Docker production, nginx, and external TLS responsibilities without a single canonical path at the top.
- Celery appears in the production Compose profile, but docs also characterize Celery + Redis as experimental or not CI-tested.
- PostgreSQL migration instructions are present even though SQLite is the only clearly stable deployment database and some health/search checks are SQLite-specific.
- `.env.example` has minor formatting issues and should more clearly distinguish required, recommended production, optional, and experimental settings.
- First-admin bootstrap behavior needs explicit documentation so users understand whether `ADMIN_PASSWORD` is only used on initial creation.

## Files to inspect and modify

Primary files:

- `README.md`
- `DEPLOY.md`
- `.env.example`
- `docker-compose.yml`
- `docker-compose.ci.yml`
- `.github/workflows/ci.yml`

Secondary files if needed:

- `docs/openapi.yaml`
- `config.toml.example`
- `nginx/README.md` if created
- `CHANGELOG.md` if release notes are added in the same pass

## Documentation architecture

Use this hierarchy:

1. README: concise product summary, stable feature list, five-minute quick start, supported deployment statement, links to detailed docs.
2. DEPLOY.md: complete operator guide for the supported topology first, then advanced/manual/experimental sections.
3. `.env.example`: safe, commented template for the supported topology.
4. Optional docs: reverse proxy examples, backup/restore guide, API integration guide.

Avoid making README carry every operational detail. It should get users to a working deployment and then route to DEPLOY.md.

## Support matrix design

Add a short matrix near the top of README and DEPLOY.md.

Recommended content:

| Area | v1 status | Notes |
|---|---|---|
| Single-server Docker Compose | Supported | Recommended public-release deployment path |
| SQLite WAL | Supported | Default and stable for single-host deployments |
| Local filesystem uploads | Supported | Stored in the `blog_uploads` volume or local upload path |
| Redis cache/rate limit/task broker | Supported | Used by production Compose profile |
| Celery worker | Supported if retained in production profile | Clarify exact supported tasks and operational assumptions |
| APScheduler | Supported with one owner | Keep disabled by default unless explicitly enabled |
| External TLS reverse proxy | Supported/recommended | Caddy/nginx/Traefik examples acceptable |
| Bundled nginx | Optional or supported, depending on Milestone A | Do not leave ambiguous |
| PostgreSQL | Experimental or unsupported for v1 | Do not present as production-stable until fully tested |
| S3-compatible storage | Experimental | Requires separate validation and dependency notes |
| Multi-host scaling | Unsupported for v1 | SQLite and scheduler locking are single-host assumptions |

If Celery remains in the production profile, do not call it experimental in the support matrix. If Celery is genuinely experimental, move it to an optional profile and update Compose accordingly.

## Implementation steps

### Step 1: Rewrite README quick start

Ensure README contains exactly one production Docker quick start matching Milestone A.

Include:

- Clone command.
- Copy `.env.example`.
- Required secret generation commands.
- Docker Compose command.
- Exact URL to open.
- Admin login path.
- TLS/reverse proxy one-sentence guidance.
- Link to DEPLOY.md.

Also keep a separate local development path using `./setup.sh` or equivalent, but explicitly mark it as local development and not production.

### Step 2: Rewrite DEPLOY.md opening sections

The first half of DEPLOY.md should be operator-facing and deterministic.

Recommended top-level structure:

1. Supported v1 topology.
2. Prerequisites.
3. Production quick start.
4. Environment variables.
5. Reverse proxy and TLS.
6. Data persistence.
7. Backups and restore.
8. Upgrades.
9. Health and monitoring.
10. Scheduler and background jobs.
11. Security checklist.
12. Experimental features.
13. Manual/systemd deployment.

Move PostgreSQL instructions into the experimental section unless Milestone D promotes it to supported.

### Step 3: Normalize `.env.example`

Clean up formatting and group variables by operational importance.

Recommended groups:

- Required first-run secrets.
- Public site configuration.
- Production security.
- Redis/cache/rate limiting.
- Background jobs and scheduler.
- Health and metrics.
- Email/newsletter.
- Storage.
- Backups.
- Experimental.

Make comments operationally precise. Example:

```env
# Required. Used only to create the first admin user when the database has no users.
ADMIN_PASSWORD=
```

If `SESSION_COOKIE_SECURE=true` is default, add a clear note that local HTTP login requires setting it to `false`.

### Step 4: Align Docker comments

Update comments in `docker-compose.yml` so they do not contradict docs. Comments should state:

- Which service owns the scheduler.
- Whether nginx is optional or default.
- Whether Celery is supported or optional.
- Which port/path operators should proxy to.

### Step 5: Clarify first-admin bootstrap

Document:

- On first startup with an empty database, DevLog creates the first admin from `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
- Once any user exists, these environment variables do not overwrite existing users.
- Operators should log in and rotate/change credentials if the bootstrap password was temporary.
- `ADMIN_PASSWORD` should still be present if the application currently requires it at startup; if later code relaxes that, update the docs in the same patch.

### Step 6: Clarify scheduler and Celery

Document the exact background-job model.

Topics:

- What APScheduler does.
- Why `ENABLE_SCHEDULER=false` is the safe default.
- Why exactly one scheduler owner is required.
- What Celery handles.
- Whether newsletter sends are scheduler-triggered, Celery-executed, or both.
- How to validate Celery is healthy.

Do not state that Celery is both production-default and experimental unless the production profile is changed accordingly.

### Step 7: Move or downgrade PostgreSQL documentation

Until Milestone D completes backend-sensitive behavior, mark PostgreSQL as experimental or planned.

Use wording such as:

"SQLite WAL is the supported v1 production database for single-server deployments. PostgreSQL support is experimental and should not be used for production until search, health checks, backup/restore, and migration workflows are fully validated."

## Testing and validation

Docs-only changes still need validation.

Run or ask the implementer to run:

```bash
python -m pytest tests/ --ignore=tests/e2e -v
docker build -t devlog:docs-check .
docker compose --profile production config
```

If docs mention a specific Compose command, run that command in a clean checkout where possible.

Optional docs validation:

- Run a markdown link checker if available.
- Grep docs for old URLs such as `localhost:5000` and ensure every instance is still correct.
- Grep docs for `PostgreSQL` and confirm each reference is labeled experimental unless promoted by code.
- Grep docs for `experimental` and ensure it is not applied to supported production components.

## Acceptance criteria

- README and DEPLOY.md describe the same production deployment path.
- The documented access URL matches actual Compose behavior.
- `.env.example` is cleanly formatted and safe for public users.
- The support matrix is present and matches implementation reality.
- Celery, scheduler, nginx/TLS, PostgreSQL, S3, and multi-host scaling each have a clear support status.
- First-admin bootstrap semantics are explicit.
- No production-stable section instructs users to rely on an experimental feature.

## Suggested commit scope

Keep this milestone largely documentation and configuration-comment oriented. If code behavior must change to make docs true, keep that change minimal and document it. Larger runtime changes belong in Milestones C, D, and E.
