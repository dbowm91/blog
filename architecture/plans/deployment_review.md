# Deployment Module Architecture Review

**Review Date:** 2026-05-09
**Reviewer:** deployment_reviewer
**Files Reviewed:**
- `/Users/davidbowman/projects/blog/architecture/deployment/overview.md`
- `/Users/davidbowman/projects/blog/architecture/deployment/docker.md`
- `/Users/davidbowman/projects/blog/architecture/deployment/cicd.md`
- `/Users/davidbowman/projects/blog/architecture/deployment/security.md`

**Cross-Referenced Against:**
- `docker-compose.yml`
- `Dockerfile`
- `nginx/nginx.conf`
- `nginx/conf.d/blog.conf`
- `.github/workflows/test.yml`
- `.dockerignore`
- `AGENTS.md`

---

## Verified Accurate Claims

### Security Headers (X-Frame-Options and COOP)
- **Claim (security.md):** "X-Frame-Options: DENY # Both Flask and nginx set DENY"
- **Verification:** CONFIRMED
  - Flask sets `DENY` in `app/__init__.py:344`
  - Nginx sets `DENY` in `nginx/conf.d/blog.conf:25`
- **Claim (security.md):** "Cross-Origin-Opener-Policy: same-origin # Both Flask and nginx set same-origin"
- **Verification:** CONFIRMED
  - Flask sets `same-origin` in `app/__init__.py:347`
  - Nginx sets `same-origin` in `nginx/conf.d/blog.conf:31`

### Celery PYTHONPATH
- **Claim (docker.md):** Environment variables table mentions `PYTHONPATH` for Celery configuration
- **Verification:** CONFIRMED - `docker-compose.yml:41` sets `PYTHONPATH=/home/blog` for the celery service

### Docker Compose Profiles
- **Claim (docker.md):** Profiles table correctly maps:
  - Default: `blog`, `redis` (development)
  - Production: `blog`, `celery`, `redis`, `nginx`
  - Backup: `blog` (backup only)
- **Verification:** CONFIRMED - All profiles match in `docker-compose.yml`

### Non-root User in Dockerfile
- **Claim (docker.md):** "Non-root user (blog)"
- **Verification:** CONFIRMED - `Dockerfile:23` creates `blog` user, `Dockerfile:31` switches to it

### critical.css
- **Claim (review_plan.md):** critical.css was created
- **Verification:** CONFIRMED - `app/static/css/critical.css` exists (1532 bytes) and is referenced in `app/templates/base.html:22`

---

## Inaccurate/Outdated Claims

### 1. nginx.conf Location
- **Doc Claim (docker.md):** "Located in `nginx/`"
- **Actual Location:** `nginx/nginx.conf` and `nginx/conf.d/` (subdirectory)
- **Correction:** nginx config is at `nginx/nginx.conf` with additional configs in `nginx/conf.d/blog.conf`

### 2. nginx user Directive
- **Doc Claim (docker.md):** Mentions "Rate limiting" in nginx configuration section but does not mention user directive
- **Actual Behavior:** `nginx/nginx.conf:1` has `user nginx;` - this is the default nginx user, but the Docker container runs nginx as root
- **Issue:** nginx runs as root by default in the `nginx:alpine` image. The `user nginx;` directive in the config file is ignored unless nginx is started with appropriate permissions or in a different configuration.

### 3. Backup Entry Point
- **Doc Claim (docker.md):** Backup service uses entrypoint `["python3", "backup.py"]`
- **Actual:** `docker-compose.yml:94` shows `entrypoint: ["python3", "backup.py"]` with `working_dir: /home/blog`
- **Issue:** `backup.py` at repository root expects to be run from the project root, but `working_dir` is `/home/blog`. The backup.py imports from `app.services.backup` which would fail unless PYTHONPATH is set correctly.

### 4. CI/CD Workflows Documentation
- **Doc Claim (cicd.md):** Only `test.yml` workflow exists
- **Actual:** `.github/workflows/test.yml` contains lint-and-type, test, security-audit, and e2e-tests jobs
- **Correction:** Documentation is incomplete - it lists the jobs within test.yml but doesn't clarify this is a single workflow file with multiple jobs

### 5. Brotli Configuration Status
- **Doc Claim (docker.md):** "Located in `nginx/`: ... Gzip compression"
- **AGENTS.md (line 119-120):** "Brotli compression - COMPLETED - Wave E (commented config)"
- **Actual:** Brotli is commented out in `nginx/nginx.conf:26-34` - requires custom nginx image
- **Note:** This is correctly noted in AGENTS.md but NOT in the deployment documentation

### 6. Referrer-Policy Mismatch
- **Doc Claim (security.md):** `Referrer-Policy: strict-origin-when-cross-origin`
- **Actual:**
  - Flask: `strict-origin-when-cross-origin` (`app/__init__.py:348`)
  - Nginx: `no-referrer-when-downgrade` (`nginx/conf.d/blog.conf:28`)
- **Issue:** Mismatch between Flask and nginx configuration

---

## Missing Documentation

### 1. Backup Service Working Directory Issue
- `docker-compose.yml:93` sets `working_dir: /home/blog` for backup service
- `backup.py` expects to be run from project root (uses `instance/blog.db` relative path)
- No documentation explains this discrepancy or the required PYTHONPATH setup

### 2. Nginx Security Headers Specifics
- Missing documentation on:
  - `X-XSS-Protection` header (set by nginx at line 27)
  - `X-Download-Options` header (set by Flask at line 345)
  - `X-Permitted-Cross-Domain-Policies` header (set by Flask at line 346)
- These are implemented but not documented

### 3. SSL Certificate Paths
- `nginx/conf.d/blog.conf:18-19` references `/etc/letsencrypt/live/blog.example.com/`
- Documentation does not mention SSL certificate setup or renewal process

### 4. celery Command Uses Default PYTHONPATH
- Docker compose sets `PYTHONPATH=/home/blog` for celery, but the base image `python:3.12-slim` doesn't have a `/home/blog` directory by default
- The Dockerfile creates this directory and copies files there, but this needs explicit documentation

### 5. Health Check Endpoint
- `/health` endpoint is configured in nginx (line 82-86 of blog.conf) but not documented in deployment docs
- No mention of the health check in docker.md or overview.md

### 6. Rate Limiting Zones
- nginx config defines `login` and `admin` rate limiting zones
- Only `/admin/login` and `/admin/` paths are rate limited in nginx
- Documentation doesn't specify which paths are protected or the limits (5r/m for login, 20r/m for admin)

---

## Potential Issues

### 1. BUG: backup.py Working Directory Mismatch (HIGH)
```
docker-compose.yml backup service:
  working_dir: /home/blog
  entrypoint: ["python3", "backup.py"]
  
backup.py line 24:
  return os.path.join("instance", "blog.db")
```
The backup.py looks for `instance/blog.db` relative to current working directory. With `working_dir: /home/blog`, it would look for `/home/blog/instance/blog.db` which is correct IF the volume is mounted. However, the volume mount is:
```
volumes:
  - blog_data:/home/blog/instance:ro
```
This mounts to `/home/blog/instance`, so the path would be `/home/blog/instance/blog.db`. This SHOULD work, but the relationship is confusing and poorly documented.

### 2. SECURITY: nginx Runs as Root
- `nginx/nginx.conf:1` has `user nginx;` but nginx container runs as root
- The nginx alpine image doesn't support running as non-root without custom configuration
- Security best practice would be to run nginx as non-root user

### 3. SECURITY: Referrer-Policy Mismatch
- Flask sets `strict-origin-when-cross-origin`
- Nginx sets `no-referrer-when-downgrade`
- This inconsistency could lead to unexpected behavior

### 4. Missing: SSL Certificate Documentation
- SSL certificates are referenced but no documentation on how to obtain/renew them
- No mention of Let's Encrypt or certbot in deployment docs

### 5. CRITICAL: No Documentation for Celery in Production
- docker-compose.yml shows `celery` service for production profile
- No documentation on:
  - How Celery tasks are registered
  - How to scale Celery workers
  - Queue configuration (images, newsletter, webhooks, email, backup as per AGENTS.md)

### 6. INFO: Redis Image Tag
- `docker-compose.yml:56` uses `redis:7-alpine`
- Documentation at `docker.md:11` says `redis:alpine` (no version specified)

---

## Recommended Improvements

### Priority 1: Fix Working Directory Documentation
1. Document that backup service runs with `working_dir: /home/blog`
2. Clarify that `blog_data` volume mounts to `/home/blog/instance`
3. Consider adding `PYTHONPATH` to backup service if needed

### Priority 2: Security Header Alignment
1. Align Referrer-Policy between Flask and nginx
2. Recommend running nginx as non-root user
3. Document all security headers in one place

### Priority 3: Complete CI/CD Documentation
1. Document that all jobs (lint-and-type, test, security-audit, e2e-tests) are in `test.yml`
2. Add information about Playwright E2E test requirements
3. Document Docker-based test environment

### Priority 4: Nginx Configuration Documentation
1. Add section on nginx security headers
2. Document rate limiting configuration
3. Add SSL/TLS setup instructions
4. Document Brotli (as commented, requiring custom image)

### Priority 5: Add Missing operational Documentation
1. Health check endpoint documentation
2. Celery task queue overview
3. Backup/restore procedures
4. Logging configuration

### Priority 6: Update Version References
1. Specify Redis version (`redis:7-alpine`)
2. Clarify Python version (3.12 in Dockerfile, 3.12/3.13 in CI)

---

## Summary

The deployment documentation is partially accurate but has several gaps and inconsistencies:

**Accurate:**
- Security headers (X-Frame-Options, COOP) are correctly aligned
- Docker Compose profiles match actual configuration
- Dockerfile non-root user is correctly documented
- critical.css exists and is properly integrated

**Needs Correction:**
- nginx.conf location (should note it's in nginx/ subdirectory)
- Referrer-Policy mismatch between Flask and nginx
- backup.py working directory relationship needs clarification

**Missing:**
- Celery operational documentation
- SSL certificate setup
- Health check documentation
- Rate limiting details
- Brotli configuration status

**Bugs:**
- backup.py working directory configuration is confusing but functional
- nginx runs as root (security concern)
