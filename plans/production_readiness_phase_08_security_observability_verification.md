# Phase 8: Security, Observability, and Final Verification

## Objective

Close the production-readiness pass with explicit security hardening, observability validation, backup/restore verification, and end-to-end release smoke tests. This phase should turn the previous implementation phases into a defensible public release candidate.

## Problems to Address

The app has several good security controls already: secure cookies, CSRF, rate limiting, security headers, 2FA, session tracking, token delays, and backup encryption. The remaining risk is that some controls depend on deployment assumptions, especially trusted proxy headers and scheduler/background behavior. Observability exists in fragments through health checks, logs, and Prometheus counters, but the release should document how operators verify the app is healthy.

## Scope

This phase covers trusted proxy/IP handling, rate limit assumptions, health/metrics docs, structured logs, backup restore drills, dependency/security audit closure, and a final release candidate smoke test. It does not add a full monitoring stack.

## Implementation Steps

1. Normalize client IP handling.

   Review all places that derive client IP:

   - Global limiter key function.
   - Comment limiter key function.
   - Admin session IP binding.
   - Analytics/page views if relevant.
   - Audit logging if relevant.

   Prefer using Flask/Werkzeug's proxy-normalized `request.remote_addr` after `ProxyFix` rather than reading raw `X-Forwarded-For` directly. If raw XFF is ever used, only trust it when the immediate peer is a configured trusted proxy.

2. Document trusted proxy assumptions.

   Add deployment docs for:

   - `PROXY_COUNT` meaning.
   - Required reverse proxy behavior: sanitize/overwrite `X-Forwarded-For`, `X-Forwarded-Proto`, and `Host`.
   - Consequences of misconfiguration: spoofed IPs can bypass rate limits or confuse session IP binding.

3. Verify security headers.

   Add a focused test for key headers on a public route and an admin route:

   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy`
   - `Permissions-Policy`
   - `Content-Security-Policy`
   - `Strict-Transport-Security` when not debug/testing and secure-cookie production mode is active.

   Ensure CSP remains compatible with Vite assets, Prism, admin editor, and inline styles that are intentionally allowed via nonce or narrow directives.

4. Review rate limits.

   Confirm Flask-Limiter storage uses Redis in production and memory only in development/testing. Document proxy-level rate limiting as defense in depth, not as a substitute for app-level limits. Ensure API write endpoints have sensible limits.

5. Verify health endpoints.

   Ensure `/health` supports a safe unauthenticated liveness response for Docker and reverse proxy checks. If detailed health requires `HEALTH_CHECK_SECRET`, document header/query usage. Include status for DB, cache, scheduler state, Celery/broker if supported, and storage only when checks are cheap and non-invasive.

6. Document Prometheus metrics.

   The app defines Prometheus request counters/histograms. Confirm whether a `/metrics` endpoint exists. If it exists, document it and any access-control recommendations. If it does not exist, either add a minimal protected endpoint or remove/avoid docs that imply scrape support.

7. Validate structured logging.

   Confirm production logs include timestamps, level, request id, and message. Avoid logging usernames, emails, secrets, API keys, reset tokens, backup encryption keys, SMTP passwords, or raw authorization headers. Update AGENTS.md/security docs with any new logging constraints.

8. Backup and restore drill.

   Execute and document a minimal backup/restore procedure for SQLite/local media:

   - Create a post and upload media.
   - Create backup.
   - Verify backup integrity.
   - Restore into a fresh instance or test database.
   - Confirm post/media/admin login still work.

   If encrypted backups are stable, include one encrypted backup verification with `BACKUP_ENCRYPTION_KEY`.

9. Dependency and secret hygiene.

   Run dependency audit against project requirements. Search for accidental committed secrets or local files. Confirm `.gitignore` covers local config, databases, uploads, backups, logs, venvs, node_modules, and build/test caches.

10. Final Docker Compose release smoke.

   On a clean checkout or CI runner:

   - Copy `.env.example` to `.env`.
   - Fill only required secrets and any documented required production values.
   - Start production profile.
   - Wait for health.
   - Visit public index.
   - Log in to admin.
   - Create, edit, publish, and view a post.
   - Submit a comment.
   - Upload media.
   - Exercise API-key create/update/delete.
   - Verify RSS/Atom/JSON feed endpoints.
   - Verify scheduler state according to `ENABLE_SCHEDULER`.
   - Shut down cleanly.

11. Add a release candidate issue or checklist.

   If the project uses GitHub issues, create a release checklist issue. If not, add `RELEASE.md` checklist from phase 7 and mark all manual checks with dates/commands in the PR description.

## Tests to Add or Update

- Security header tests.
- Trusted proxy/client IP tests.
- API rate-limit tests if feasible without slow timing.
- Health endpoint tests for basic and detailed modes.
- Metrics endpoint tests if implemented.
- Backup integrity tests if not already covered.
- Docker smoke script if the repo has a scripts directory suitable for this.

## Verification Commands

Core quality gate:

```bash
ruff check .
ruff format --check .
mypy app
npm ci
npm run build
ADMIN_PASSWORD=test-password-123 SECRET_KEY=test-secret-key-test-secret-key-1234 python -m pytest tests/ --ignore=tests/e2e -v --cov=app --cov-fail-under=80
pip-audit -r requirements.txt
docker build .
```

Security grep examples:

```bash
git grep -n "SECRET_KEY\|ADMIN_PASSWORD\|SMTP_PASSWORD\|API_KEY\|BACKUP_ENCRYPTION_KEY\|WEBHOOK_ENCRYPTION_KEY" -- ':!plans/*' ':!.env.example' ':!README.md' ':!DEPLOY.md' ':!SECURITY.md' ':!AGENTS.md'
git ls-files | grep -E '(^|/)(\.env|instance/|logs/|backups/|app/static/uploads/|.*\.db$)' && exit 1 || true
```

Docker Compose smoke:

```bash
cp .env.example .env
# Fill required values.
docker compose --profile production up -d --build
docker compose ps
docker compose logs blog --tail=100
curl -f http://localhost/health || curl -f http://localhost:5000/health
# Run E2E tests if configured to target the Compose stack.
docker compose --profile production down -v
```

Manual browser smoke:

1. Open public index.
2. Log in to `/admin/login`.
3. Create draft post.
4. Publish post.
5. Confirm post appears on homepage and feed.
6. Submit comment and moderate it.
7. Upload media and confirm it renders.
8. Log out and confirm logout does not 403 with a valid CSRF token.

## Acceptance Criteria

All release-gate commands pass. Security headers are tested. Client IP handling no longer trusts spoofable proxy headers outside the configured proxy model. Health and metrics behavior is documented and tested. Backup/restore has been smoke-tested. Docker Compose production profile starts from a clean checkout. The repository is free of local/secrets artifacts. The release checklist is complete.

## Risks

Some checks require a real reverse proxy or browser. Keep automated tests focused on deterministic behavior, and document manual checks that cannot be fully automated. Do not block release on adding a full monitoring system; the target is enough observability for a self-hosted operator to detect basic failure modes.
