# Deployment Architecture Review

## Overview

Reviewed the four deployment architecture documents and verified against actual implementation.

## Verified Claims

### Docker Compose Services
- **docker.md:11** - Claims `redis:alpine`, actual implementation uses `redis:7-alpine` (`docker-compose.yml:56`)
- docker-compose.yml correctly defines profiles: `production`, `backup`

### Security Headers Alignment
Flask (`app/__init__.py:344,347`) and nginx (`nginx/conf.d/blog.conf:25,31`) both set:
- `X-Frame-Options: DENY`
- `Cross-Origin-Opener-Policy: same-origin`

This claim in `security.md:43,46` is verified correct.

### CI/CD Workflows
- test.yml structure (`test.yml:8-160`) matches cicd.md claims for `lint-and-type`, `test`, `security-audit`, `e2e-tests`
- Minimum 80% coverage requirement (`test.yml:68`) matches cicd.md:19

## Discrepancies

### docker.md vs Actual Implementation

| Claim (docker.md) | Actual (docker-compose.yml) | Issue |
|-------------------|----------------------------|-------|
| Line 11: `redis:alpine` | `redis:7-alpine` | Version mismatch |
| Line 32: "Resource limits" in Dockerfile | Resource limits in docker-compose.yml:26-30 | Location incorrect |
| Line 48: `DATABASE_URL` env var | docker-compose.yml doesn't expose DATABASE_URL | Production uses SQLite by default |

### nginx.conf Structure Bug
`nginx/nginx.conf:39-70` - Duplicate `http {}` block. The second block (lines 39-70) completely overrides the first (lines 10-37). This means:
- `error_log` from line 3 is overridden by line 47's duplicate definition
- `pid` directive (line 4) may be lost
- Brotli comments in first block (lines 26-34) are effectively unreachable code

## Bugs Found

### Bug 1: Duplicate HTTP Block in nginx.conf
**File:** `nginx/nginx.conf:39`
The second `http {}` block (lines 39-70) shadows the first (lines 10-37). Any directives in the first block that aren't repeated in the second are lost.

### Bug 2: e2e-tests Workflow Redis Health Check Missing
**File:** `.github/workflows/test.yml:119-124`
e2e-tests starts redis without waiting for it to be healthy before starting blog:
```yaml
docker-compose up -d redis
sleep 2  # Arbitrary sleep, not health-based
docker-compose up -d blog
```
docker-compose.yml:55-62 shows redis has a healthcheck, but the workflow doesn't use it.

### Bug 3: e2e-tests Uses Default Profile Instead of Production
**File:** `.github/workflows/test.yml:117-124`
`docker-compose up -d blog` uses the default profile, not the `production` profile. This means nginx and celery are not started during e2e tests, creating an incomplete environment.

### Bug 4: docker-compose.yml Missing SMTP_USER/SMTP_PASSWORD Environment
**File:** `docker-compose.yml:7-14`
blog service defines `SMTP_USER` and `SMTP_PASSWORD` env vars, but the `celery` service (line 34-53) does not, despite needing them for email tasks.

## Improvement Recommendations

### REC-1: Fix nginx.conf Duplicate HTTP Block
**File:** `nginx/nginx.conf:39`
Merge the two `http {}` blocks into one, removing the duplication.

### REC-2: Fix e2e-tests Redis Health Check
**File:** `.github/workflows/test.yml:119-124`
Change to wait for redis health:
```yaml
- name: Start services
  run: docker-compose up -d redis
  wait: redis
```

### REC-3: Add Production Profile to e2e-tests
**File:** `.github/workflows/test.yml:117-124`
Use `docker-compose up -d --profile production` or explicitly include services needed for testing.

### REC-4: Add SMTP Environment to Celery Service
**File:** `docker-compose.yml:34-53`
Add SMTP_USER and SMTP_PASSWORD environment variables to the celery service.

### REC-5: Update docker.md for Accuracy
- Line 11: Change `redis:alpine` to `redis:7-alpine`
- Line 32: Clarify resource limits are in docker-compose.yml, not Dockerfile
- Line 48: Note DATABASE_URL is optional; SQLite is default

### REC-6: Add DATABASE_URL to Production Profile
**File:** `docker-compose.yml:1-33`
If PostgreSQL is intended for production, add DATABASE_URL to the blog service environment in the production profile.

## Security Notes

No security issues found. Security headers are correctly aligned between Flask and nginx. CSRF protection uses `hmac.compare_digest` (timing-safe). Account lockout and TOTP implementation match documentation.
