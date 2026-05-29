# Blog Public-Release Polish Plan

Target repository: `dbowm91/blog`  
Audience: smaller implementation agent, likely MiMo v2.5  
Goal: prepare the private Flask blog/CMS repository for a clean public release without changing product direction or introducing large new features.

## Operating Principles

This plan is primarily a polish and consistency pass. Do not rewrite the application architecture. Do not remove working features. Do not invent major product features. Focus on making the repo coherent, reproducible, trustworthy, and approachable for outside users.

Treat documentation drift as the highest-risk issue. The repository already has substantial documentation, CI, security features, deployment guidance, and agent notes. The main work is aligning those surfaces with the actual codebase.

Before editing, inspect the current files and confirm paths still exist. Prefer small, focused commits. After each phase, run the relevant tests/checks.

Recommended baseline commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
mypy app
ADMIN_PASSWORD=test SECRET_KEY=test-secret-key-that-is-at-least-32-chars-long python -m pytest tests/ --ignore=tests/e2e -v --cov=app
python scripts/validate_openapi.py
```

If Node dependencies are present:

```bash
npm install
npm run build
```

## Phase 1: Establish Public Project Identity

### Objective

Make the public identity consistent across the repository. The project currently appears under multiple names, including `DevLog`, `blog`, and `blog-cms`. Pick one canonical public name and apply it consistently.

Recommended public name: `DevLog`, unless the maintainer prefers otherwise.

### Files to inspect and likely edit

- `README.md`
- `package.json`
- `config.toml`
- `DEPLOY.md`
- `USAGE.md`
- `ARCHITECTURE.md`
- `docs/openapi.yaml`
- `docker-compose.yml`
- `Dockerfile`
- Any docs under `docs/`, `architecture/`, and `plans/`

### Tasks

1. Search for inconsistent names:
   ```bash
   rg -n "DevLog|blog-cms|Blog CMS|blog platform|/opt/blog|repo-url|<repo-url>"
   ```

2. Decide whether `DevLog` is the public name. If yes:
   - Keep README title as `# DevLog`.
   - Change `package.json` name from `blog-cms` to a consistent package identifier such as `devlog` or `devlog-blog`.
   - Ensure descriptions consistently say something like:
     `A self-hosted Flask blog CMS for technical writing, newsletters, feeds, analytics, and admin-managed content.`
   - Update deployment examples so clone paths and service names are coherent.

3. Add a short positioning section near the top of `README.md`:
   - What it is.
   - Who it is for.
   - What it is not.
   - Core feature list.

4. Add repository badges near the top of `README.md` if appropriate:
   - CI status badge.
   - Python version badge.
   - License badge.
   - Optional Docker badge if images are published.

### Acceptance Criteria

- A repository-wide search no longer shows avoidable name drift.
- README, package metadata, deployment docs, and config defaults use the same product name.
- The README immediately communicates the purpose of the project to a new visitor.

## Phase 2: Fix Documentation Drift and Known Inconsistencies

### Objective

Align README, DEPLOY, USAGE, OpenAPI, architecture docs, and agent notes with the actual implementation.

### Files to inspect and likely edit

- `README.md`
- `DEPLOY.md`
- `USAGE.md`
- `ARCHITECTURE.md`
- `SECURITY.md`
- `AGENTS.md`
- `docs/openapi.yaml`
- `architecture/**/*.md`
- `plans/**/*.md`

### Tasks

1. Search for explicit drift markers:
   ```bash
   rg -n "NOT |not exist|does NOT|actual|Actual|deprecated|DEPRECATED|may claim|TODO|FIXME|placeholder|<repo-url>|config.toml config.toml"
   ```

2. Correct the deployment quick start bug:
   - If the project intends to track `config.toml` as the default config, remove the bogus command `cp config.toml config.toml`.
   - If the project should use an example config, create `config.example.toml`, move public-safe defaults there, and update docs to say:
     ```bash
     cp config.example.toml config.toml
     ```

3. Align Python version documentation:
   - `pyproject.toml` targets Python 3.12.
   - CI currently tests Python 3.12 and 3.13.
   - Deployment docs should not claim Python 3.14+ unless the application truly requires it.
   - Recommended public statement:
     `Python 3.12 or 3.13 is supported.`
   - Update `DEPLOY.md`, `README.md`, and any other prerequisites.

4. Verify route documentation against actual Flask routes:
   - Search route decorators:
     ```bash
     rg -n "@.*\.route|Blueprint\("
     ```
   - Compare against README API endpoint table and `docs/openapi.yaml`.
   - Remove or correct references to routes that do not exist.
   - Pay specific attention to:
     - `/api/auth`
     - `/api/subscribers/export`
     - API post publish routes
     - admin new/edit post routes
     - comment submission routes
     - subscribe GET vs POST behavior

5. Align newsletter and scheduler docs:
   - Confirm default newsletter retry count.
   - Confirm confirmation expiry.
   - Confirm APScheduler job timings.
   - Confirm behavior when SMTP is not configured.
   - Update README, DEPLOY, USAGE, and architecture docs.

6. Align backup documentation:
   - Confirm backup implementations:
     - Celery/service backup.
     - APScheduler backup.
   - Confirm encryption mechanism: AES-256-GCM with PBKDF2 vs GPG.
   - Update `DEPLOY.md`, `SECURITY.md`, and architecture docs so they do not conflict.

7. Align template/filter documentation:
   - Confirm actual filters in `app/filters.py`.
   - Remove docs for missing filters.
   - Mark deprecated filters clearly only if they remain for compatibility.

8. Run OpenAPI validation after edits:
   ```bash
   python scripts/validate_openapi.py
   ```

### Acceptance Criteria

- No obvious self-contradictions remain between `AGENTS.md` notes and public docs.
- README endpoint table, OpenAPI schema, and implemented routes agree.
- Deployment prerequisites match CI-tested Python versions.
- `rg` searches for drift markers show only intentional references.

## Phase 3: Split Public Agent Guidance from Maintainer/Internal Notes

### Objective

Keep useful AI-agent guidance while avoiding a public repo that reads like a private scratchpad.

### Files to inspect and likely edit

- `AGENTS.md`
- `app/**/AGENTS.override.md`
- `docs/AGENTS.override.md`
- `architecture/AGENTS.override.md`
- `plans/AGENTS.override.md`
- New file, likely `docs/internals/maintainer-notes.md` or `docs/internals/agent-maintainer-notes.md`

### Tasks

1. Keep root `AGENTS.md` short and stable:
   - Project overview.
   - Setup and test commands.
   - Security invariants.
   - Code style.
   - Where to find module-specific overrides.
   - Rule to verify routes/docs against code before editing.

2. Move volatile implementation-history notes into an internal doc:
   - Previously fixed broad exceptions.
   - “Actual route is X, not Y” notes after public docs are corrected.
   - Backup implementation caveats.
   - Scheduler limitations.
   - Deprecated implementation notes.
   - Test interference notes.
   - Future-agent reminders.

3. Add links from `AGENTS.md` to the internal note file:
   - Use language like:
     `For historical implementation caveats and maintainer context, see docs/internals/agent-maintainer-notes.md.`
   - Do not bury important production caveats only in agent notes.

4. Elevate production-impacting caveats into public deployment docs:
   - APScheduler file-lock limitation in multi-container deployments.
   - SQLite write-concurrency limitations.
   - Need for Redis/Celery coordination for background jobs if scaling horizontally.
   - Backup encryption behavior.

### Acceptance Criteria

- `AGENTS.md` remains useful to coding agents but is concise enough for a public repo.
- Internal/historical notes are moved to a clearly labeled maintainer document.
- Production-impacting caveats are documented in `DEPLOY.md`, not only in agent notes.

## Phase 4: Improve Reproducible Setup and Dependency Metadata

### Objective

Make installation predictable for external users and future contributors.

### Files to inspect and likely edit

- `requirements.txt`
- `requirements-dev.txt`
- `pyproject.toml`
- `README.md`
- `CONTRIBUTING.md`
- Optional: `requirements.lock`, `uv.lock`, or `requirements-dev.lock`

### Tasks

1. Decide the dependency management strategy.
   - Minimal approach: keep `requirements.txt` and `requirements-dev.txt`, add clear docs, and optionally generate lockfiles.
   - Better approach: expand `pyproject.toml` to include project metadata and dependency groups.
   - Avoid introducing a new toolchain unless the repository already uses or wants it.

2. Expand `pyproject.toml` minimally:
   - Add project metadata if appropriate:
     - name
     - version
     - description
     - readme
     - requires-python
     - license
   - Keep Ruff and mypy config.
   - Consider adding pytest config:
     ```toml
     [tool.pytest.ini_options]
     testpaths = ["tests"]
     ```

3. Decide whether to lock dependencies.
   - If using `pip-tools`:
     - Add `requirements.in` and `requirements-dev.in`.
     - Generate locked `requirements.txt` and `requirements-dev.txt`.
   - If using `uv`:
     - Add `uv.lock`.
     - Document `uv sync` workflow.
   - If keeping current loose ranges:
     - Clearly state that the app uses compatible dependency ranges and CI validates current combinations.

4. Verify Playwright handling:
   - If E2E tests require browser installation, document:
     ```bash
     playwright install --with-deps
     ```
   - Keep E2E tests optional if they are heavy.

### Acceptance Criteria

- A new contributor can determine the correct setup command path without guessing.
- Python version metadata agrees with CI and docs.
- Dependency strategy is explicit.
- Tests still pass.

## Phase 5: Expand and Sanitize Environment Configuration Examples

### Objective

Make `.env.example` and config docs complete enough for real self-hosting while avoiding unsafe defaults.

### Files to inspect and likely edit

- `.env.example`
- `config.toml` or `config.example.toml`
- `README.md`
- `DEPLOY.md`
- `docker-compose.yml`

### Tasks

1. Expand `.env.example` to include major supported env vars:
   - `SECRET_KEY`
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
   - `SESSION_COOKIE_SECURE`
   - `PROXY_COUNT`
   - `API_KEY`
   - `DATABASE_URL`
   - `SMTP_HOST`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
   - `REDIS_URL`
   - `CACHE_REDIS_URL`
   - `CELERY_BROKER_URL`
   - `HEALTH_CHECK_SECRET`
   - `PAGE_VIEW_BUFFER_SIZE`
   - `PAGE_VIEW_FLUSH_INTERVAL`
   - `STORAGE_BACKEND`
   - `S3_BUCKET`
   - `S3_REGION`
   - `S3_ACCESS_KEY`
   - `S3_SECRET_KEY`
   - `S3_ENDPOINT`
   - `S3_PUBLIC_URL`
   - `BACKUP_ENCRYPTION_KEY`
   - `WEBHOOK_ENCRYPTION_KEY`, if actually required/supported

2. Replace unsafe placeholders:
   - Avoid `ADMIN_PASSWORD=changeme`.
   - Use:
     ```bash
     ADMIN_PASSWORD=replace-with-generated-password
     SECRET_KEY=replace-with-output-of-python-secrets-token-hex
     ```

3. Add generation commands:
   ```bash
   python3 -c 'import secrets; print(secrets.token_hex(32))'
   ```

4. Ensure Docker Compose variables and `.env.example` agree.

5. Ensure docs explain which vars are required for:
   - local development
   - production
   - newsletter/email
   - S3/object storage
   - Celery/Redis
   - backup encryption
   - detailed health checks

### Acceptance Criteria

- `.env.example` is usable as a starting point for Docker Compose and local development.
- No placeholder implies a safe production secret.
- Deployment docs and compose variables agree.

## Phase 6: Public Security and Disclosure Polish

### Objective

Make the security posture externally credible and avoid vague vulnerability-reporting instructions.

### Files to inspect and likely edit

- `SECURITY.md`
- `README.md`
- `DEPLOY.md`
- Optional: `.github/SECURITY.md` if preferred

### Tasks

1. Add a concrete vulnerability reporting path:
   - GitHub private vulnerability reporting, if enabled.
   - Security email address, if the maintainer has one.
   - Expected initial response window, such as 7 days.
   - Supported versions/branches.

2. Add a “Security Boundaries” section:
   - Self-hosted blog/CMS.
   - Admin interface should be restricted to trusted users.
   - Not designed as a multi-tenant SaaS isolation boundary unless that is explicitly implemented.
   - Users are responsible for TLS termination and secure secret management in production.

3. Ensure listed security features are accurate:
   - Password hashing method.
   - 2FA behavior.
   - Session fixation protection.
   - Session IP binding behavior.
   - Rate limiting.
   - CSP nonces.
   - HTML/CSS sanitization.
   - Backup/webhook encryption mechanisms.

4. Add production checklist items:
   - Set strong `SECRET_KEY`.
   - Set strong `ADMIN_PASSWORD`.
   - Enable `SESSION_COOKIE_SECURE=true`.
   - Use HTTPS behind a reverse proxy.
   - Set correct `PROXY_COUNT`.
   - Configure backup encryption.
   - Confirm file upload limits.
   - Restrict admin route exposure if desired.
   - Keep dependencies updated.

5. Consider adding a `.github/dependabot.yml` for:
   - Python package ecosystem.
   - GitHub Actions.
   - npm, if frontend dependencies are present.
   - Docker, if useful.

### Acceptance Criteria

- `SECURITY.md` has a concrete reporting path.
- Security feature claims are accurate and not overstated.
- Production checklist is actionable.
- Dependabot or equivalent update strategy is documented or configured.

## Phase 7: Docker and Deployment Onboarding

### Objective

Make the public deployment path less fragile and easier to validate.

### Files to inspect and likely edit

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `DEPLOY.md`
- `nginx/**`
- Optional: new `docs/deployment/caddy.md`

### Tasks

1. Verify Dockerfile correctness.
   - Pay attention to the builder stage:
     - It installs packages with `pip install --user`.
     - It copies `/home/blog/.local` from the builder.
     - Confirm this path exists in the builder image before runtime copy.
   - If not correct, use a more conventional virtualenv or copy from `/root/.local`.

2. Add or improve `.dockerignore`.
   Suggested entries:
   ```text
   .git
   .venv
   __pycache__
   *.pyc
   .pytest_cache
   .mypy_cache
   .ruff_cache
   node_modules
   dist
   .env
   instance
   logs
   backups
   app/static/uploads
   ```

3. Add Docker labels if useful:
   - source repo
   - license
   - description

4. Update `DEPLOY.md` with exact Docker Compose commands:
   ```bash
   cp .env.example .env
   # edit .env
   docker compose --profile production up -d --build
   docker compose --profile production logs -f
   ```

5. Document profiles:
   - `production`
   - `backup`
   - any others

6. Document production caveats:
   - SQLite single-writer behavior.
   - APScheduler multi-container limitation.
   - Need for Redis/Celery for asynchronous jobs.
   - Reverse proxy TLS responsibility.
   - Upload storage persistence.

7. Consider adding a Caddy example as a simpler alternative to nginx:
   - This is optional.
   - Do not remove nginx config if it works.

### Acceptance Criteria

- Docker image builds successfully.
- Compose deployment instructions work from a fresh checkout.
- `.dockerignore` prevents secrets/local state from entering image build context.
- Deployment docs clearly state scaling limitations.

## Phase 8: CI and Quality Gate Improvements

### Objective

Make CI cover the same paths public contributors will touch.

### Files to inspect and likely edit

- `.github/workflows/ci.yml`
- New optional workflows:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/docker.yml`
  - `.github/dependabot.yml`

### Tasks

1. Keep existing checks:
   - Ruff.
   - mypy.
   - OpenAPI validation.
   - Unit tests with coverage.
   - Python 3.12 and 3.13 matrix.

2. Add frontend build check if `package.json` is present:
   ```yaml
   - uses: actions/setup-node@v4
     with:
       node-version: "20"
       cache: "npm"
   - run: npm ci
   - run: npm run build
   ```

3. Add Docker build check:
   ```yaml
   docker build .
   ```

4. Add optional dependency/security scanning:
   - Dependabot for update PRs.
   - `pip-audit` or GitHub dependency review for PRs.
   - Avoid failing CI on advisory noise unless the maintainer wants strict security gates.

5. Consider moving E2E tests to separate workflow:
   - Trigger manually or nightly.
   - Install Playwright browsers.
   - Avoid making every simple PR slow unless desired.

6. Add scheduled CI:
   ```yaml
   on:
     schedule:
       - cron: "0 8 * * 1"
   ```

### Acceptance Criteria

- CI validates backend, frontend build, OpenAPI, and Docker build.
- CI remains reasonably fast for normal PRs.
- Dependency update/security posture is at least minimally automated.

## Phase 9: Public README and User-Facing Presentation

### Objective

Make the repository landing page readable and persuasive for outside users.

### Files to inspect and likely edit

- `README.md`
- Optional: `docs/screenshots/`
- Optional: `docs/demo.md`

### Tasks

1. Reorganize README into a public-friendly structure:
   - Project title and one-sentence summary.
   - Screenshot or demo GIF placeholder.
   - Feature overview.
   - Quick start.
   - Docker quick start.
   - Configuration.
   - Development setup.
   - Documentation links.
   - Security note.
   - License.

2. Add a feature matrix:
   - Markdown posts.
   - Admin dashboard.
   - Drafts/scheduled posts.
   - Static pages.
   - Tags.
   - Media uploads.
   - RSS feed.
   - JSON feed.
   - Newsletter.
   - Subscribers.
   - Analytics/page views.
   - REST API.
   - 2FA.
   - Backups.
   - Theming.

3. Add screenshots.
   - Do not include secrets, private posts, private analytics, real subscriber emails, or private domains.
   - Suggested screenshots:
     - Homepage.
     - Post page with table of contents.
     - Admin dashboard.
     - Post editor.
     - Subscriber management.
     - Theme settings.

4. Add “Project Status.”
   - Example:
     `This is a self-hosted blog CMS extracted from a personal production project. It is suitable for technically comfortable self-hosters. Public APIs and deployment docs are being stabilized.`
   - Adjust wording to match maintainer intent.

5. Add “Non-goals.”
   - Not a hosted SaaS.
   - Not a WordPress replacement for non-technical users.
   - Not intended for untrusted multi-tenant use unless explicitly deployed that way.

### Acceptance Criteria

- README looks like a public open-source project, not only an internal manual.
- Quick start is still concise.
- Screenshots or placeholders are present.
- Documentation links remain intact.

## Phase 10: Contribution, Issue, and Release Hygiene

### Objective

Make external collaboration predictable without overburdening the maintainer.

### Files to inspect and likely edit/create

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`, optional
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/pull_request_template.md`
- `CHANGELOG.md`
- `ROADMAP.md`, optional
- `plans/plan.md`

### Tasks

1. Clean `CONTRIBUTING.md`:
   - Remove or soften internal-only branch naming such as `waveN-description`.
   - Replace with conventional examples:
     - `fix/login-rate-limit`
     - `docs/docker-quickstart`
     - `feature/rss-cache`
   - Keep clear commands for setup, tests, lint, type check, and frontend build.

2. Decide what to do with `plans/`.
   - If public, make it clearly a maintainer roadmap.
   - If too internal/stale, move active items to `ROADMAP.md` or GitHub issues.
   - Avoid requiring external contributors to update `plans/plan.md` unless that is genuinely desired.

3. Add issue templates:
   - Bug report with reproduction, expected behavior, logs, environment.
   - Feature request with use case and proposed behavior.
   - Security issue template should point to `SECURITY.md`, not public issues.

4. Add PR template:
   - Summary.
   - Test plan.
   - Screenshots, if UI change.
   - Migration/config impact.
   - Security/privacy impact.

5. Add `CHANGELOG.md`:
   - Start with `Unreleased`.
   - Add initial public release section once ready.

6. Optional: add `CODE_OF_CONDUCT.md`.
   - If added, use a standard compact contributor covenant or simpler maintainer-defined conduct file.

### Acceptance Criteria

- External contributors can submit issues and PRs with enough structure.
- Internal planning conventions do not leak as mandatory public process.
- There is a clear place for release notes.

## Phase 11: License, Repository Metadata, and GitHub Settings

### Objective

Complete public trust and discoverability signals.

### Files/settings to inspect and likely edit

- `LICENSE`
- `README.md`
- GitHub repository About section
- GitHub topics
- GitHub security settings
- Branch protection settings

### Tasks

1. Update license year if appropriate.
   - Current license year appears to be 2024.
   - If publishing in 2026 and the maintainer wants current coverage, update to:
     `Copyright (c) 2024-2026 David Bowman`
   - Confirm with maintainer preference.

2. Add repository About metadata:
   - Description:
     `Self-hosted Flask blog CMS with admin dashboard, Markdown posts, newsletter, feeds, analytics, and theming.`
   - Topics:
     `flask`, `blog`, `cms`, `self-hosted`, `rss`, `newsletter`, `python`, `sqlite`, `postgresql`, `granian`

3. Enable GitHub features if desired:
   - Issues.
   - Discussions, optional.
   - Private vulnerability reporting.
   - Dependabot alerts.
   - Secret scanning, if available.

4. Add branch protection:
   - Require CI before merge.
   - Require PRs for main branch if maintainer wants.
   - Allow maintainer override as preferred.

### Acceptance Criteria

- Repo metadata communicates the project clearly.
- Security reporting path is enabled and documented.
- License is accurate.

## Phase 12: Final Verification Pass

### Objective

Catch broken links, stale references, missing files, and setup regressions.

### Tasks

1. Run repository-wide checks:
   ```bash
   rg -n "<repo-url>|changeme|TODO|FIXME|config.toml config.toml|Python 3.14|blog-cms|does NOT|may claim"
   ```

2. Run backend checks:
   ```bash
   ruff check .
   mypy app
   ADMIN_PASSWORD=test SECRET_KEY=test-secret-key-that-is-at-least-32-chars-long python -m pytest tests/ --ignore=tests/e2e -v --cov=app
   python scripts/validate_openapi.py
   ```

3. Run frontend checks:
   ```bash
   npm install
   npm run build
   ```

4. Run Docker checks:
   ```bash
   docker build .
   docker compose --profile production config
   ```

5. Validate docs links manually or with a markdown link checker if available.

6. Verify no secrets or private data:
   ```bash
   git grep -n "password\|secret\|token\|key\|gmail\|smtp\|subscriber" -- ':!*.md'
   ```
   Manually distinguish placeholders from real secrets.

7. If screenshots were added, inspect them for private content.

### Acceptance Criteria

- Backend checks pass.
- Frontend build passes, if frontend is in scope.
- Docker build passes.
- Docs contain no obvious placeholders or broken quick-start steps.
- No secrets/private content are present.

## Suggested Commit Structure

Use small commits with clear scope:

1. `docs: align public project identity`
2. `docs: fix deployment and route documentation drift`
3. `docs: split agent maintainer notes`
4. `chore: clarify python and dependency metadata`
5. `docs: expand environment configuration examples`
6. `docs: improve security policy and production checklist`
7. `build: harden docker and compose onboarding`
8. `ci: add frontend and docker validation`
9. `docs: improve public readme presentation`
10. `chore: add issue and pull request templates`
11. `chore: update repository release metadata`

## Do Not Do

- Do not rewrite the Flask app.
- Do not replace SQLite/PostgreSQL abstractions.
- Do not remove working security features.
- Do not introduce a new frontend framework.
- Do not add hosted/SaaS assumptions.
- Do not remove AGENTS guidance entirely; split and stabilize it.
- Do not claim production scalability beyond what the scheduler, SQLite, and background-job architecture actually support.
- Do not publish real secrets, private analytics, private posts, or subscriber information in examples/screenshots.

## Public Release Readiness Checklist

The repo is public-ready when all of the following are true:

- Project name and description are consistent.
- README has a clear pitch, quick start, feature list, and docs links.
- Python version support is consistent across docs, CI, and metadata.
- Route/API docs match implementation and OpenAPI.
- `.env.example` is complete and safe.
- Deployment docs include Docker and non-Docker paths.
- Scheduler/background-job scaling caveats are visible in deployment docs.
- Security policy has a concrete reporting path.
- CI passes.
- Frontend build is validated.
- Docker build is validated.
- Contribution docs are not overly internal.
- Issue/PR templates exist.
- License and repository metadata are correct.
- No secrets or private data are present.

