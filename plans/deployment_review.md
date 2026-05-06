# Deployment Architecture Review

**Date:** May 6, 2026
**Reviewer:** Architecture Review Agent
**Files Reviewed:**
- `/home/sugarwookie/projects/blog/architecture/deployment/docker.md`
- `/home/sugarwookie/projects/blog/architecture/deployment/cicd.md`
- `/home/sugarwookie/projects/blog/architecture/deployment/security.md`
- `/home/sugarwookie/projects/blog/architecture/deployment/overview.md`

**Implementation Files Verified:**
- `/home/sugarwookie/projects/blog/Dockerfile`
- `/home/sugarwookie/projects/blog/docker-compose.yml`
- `/home/sugarwookie/projects/blog/.github/workflows/test.yml`
- `/home/sugarwookie/projects/blog/nginx/nginx.conf`
- `/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf`
- `/home/sugarwookie/projects/blog/app/webhook_encryption.py`
- `/home/sugarwookie/projects/blog/app/backup_encryption.py`
- `/home/sugarwookie/projects/blog/app/csrf.py`
- `/home/sugarwookie/projects/blog/app/__init__.py`
- `/home/sugarwookie/projects/blog/app/webhooks.py`
- `/home/sugarwookie/projects/blog/app/utils.py` (SSRF protection)

---

## Summary

The deployment documentation is **largely accurate** but contains several discrepancies between documented claims and actual implementation. Most critical issues involve:
1. Backup encryption documentation (GPG vs AES-256-GCM terminology)
2. Security header configuration (Flask app vs nginx)
3. X-Frame-Options value mismatch (DENY vs SAMEORIGIN)
4. Missing Cross-Origin-Opener-Policy header in nginx config

---

## Verified Claims

### Docker Services
| Documented | Actual | Status |
|------------|--------|--------|
| `blog` service (Custom, Flask/Granian) | `/home/sugarwookie/projects/blog/Dockerfile:42` - `granian --interface asgi --workers 4` | VERIFIED |
| `celery` service (Custom) | `/home/sugarwookie/projects/blog/docker-compose.yml:37` - `celery -A app.celery_app worker` | VERIFIED |
| `redis` service (`redis:alpine`) | `/home/sugarwookie/projects/blog/docker-compose.yml:55` - `redis:7-alpine` | VERIFIED |
| `nginx` service (`nginx:alpine`) | `/home/sugarwookie/projects/blog/docker-compose.yml:70` - `nginx:alpine` | VERIFIED |

### Docker Compose Profiles
- Default profile: `blog`, `redis` - **VERIFIED** (`docker-compose.yml:32,67`)
- Production profile: `blog`, `celery`, `redis`, `nginx` - **VERIFIED** (`docker-compose.yml:32,52,67,84`)
- Backup profile: `blog` (backup only) - **VERIFIED** (`docker-compose.yml:97`)

### Multi-Stage Dockerfile
- Builder stage with Python dependencies - **VERIFIED** (`/home/sugarwookie/projects/blog/Dockerfile:1-14`)
- Runtime stage with non-root user - **VERIFIED** (`/home/sugarwookie/projects/blog/Dockerfile:23,31`)
- Health checks - **VERIFIED** (`/home/sugarwookie/projects/blog/Dockerfile:40`)

### CI/CD Workflows
| Documented | Actual | Status |
|------------|--------|--------|
| `test.yml` workflow | `/home/sugarwookie/projects/blog/.github/workflows/test.yml` | VERIFIED |
| lint-and-type job with ruff, mypy | `/home/sugarwookie/projects/blog/.github/workflows/test.yml:31-35` | VERIFIED |
| test job with pytest, 80% coverage | `/home/sugarwookie/projects/blog/.github/workflows/test.yml:37-68` | VERIFIED |
| security-audit with pip-audit | `/home/sugarwookie/projects/blog/.github/workflows/test.yml:70-94` | VERIFIED |
| e2e-tests with Playwright | `/home/sugarwookie/projects/blog/.github/workflows/test.yml:96-160` | VERIFIED |
| Python 3.12, 3.13 | `/home/sugarwookie/projects/blog/.github/workflows/test.yml:16,42` | VERIFIED |

### Session Security
| Documented | Actual | Status |
|------------|--------|--------|
| `SESSION_COOKIE_SECURE = True` | `/home/sugarwookie/projects/blog/app/__init__.py:182-184` | VERIFIED |
| `SESSION_COOKIE_SAMESITE = "Lax"` | `/home/sugarwookie/projects/blog/app/__init__.py:185` | VERIFIED |
| `SESSION_COOKIE_HTTPONLY = True` | `/home/sugarwookie/projects/blog/app/__init__.py:186` | VERIFIED |

### CSRF Protection
| Documented | Actual | Status |
|------------|--------|--------|
| Sliding window of 5 valid tokens | `/home/sugarwookie/projects/blog/app/csrf.py:8,20` - `CSRF_TOKEN_WINDOW_SIZE = 5` | VERIFIED |
| Timing-safe comparison via `hmac.compare_digest` | `/home/sugarwookie/projects/blog/app/csrf.py:56` | VERIFIED |
| Token rotation on privilege changes | `/home/sugarwookie/projects/blog/app/routes/admin/users.py:149,186,236` | VERIFIED |

### Input Sanitization
| Documented | Actual | Status |
|------------|--------|--------|
| HTML via `nh3` allowlist | `/home/sugarwookie/projects/blog/requirements.txt:13` - `nh3>=0.2.0` | VERIFIED |
| CSS via `tinycss2` | `/home/sugarwookie/projects/blog/requirements.txt:26` - `tinycss2>=1.3.0` | VERIFIED |
| SQL via SQLAlchemy 2.0 | `/home/sugarwookie/projects/blog/requirements.txt:3` - `sqlalchemy>=2.0` | VERIFIED |

### SSRF Protection
- URL validation with IP range checking - **VERIFIED** (`/home/sugarwookie/projects/blog/app/utils.py:312-414`)
- Blocks private, loopback, link-local, multicast, AWS metadata - **VERIFIED**

### 2FA via pyotp
- TOTP implementation - **VERIFIED** (`/home/sugarwookie/projects/blog/app/routes/admin/auth.py:4,64-66,263-336`)
- `pyotp>=2.9.0` in requirements - **VERIFIED**

### Account Lockout
- After 5 failed attempts (configurable) - **VERIFIED** (`/home/sugarwookie/projects/blog/app/config.py:142`)
- Lockout duration configurable - **VERIFIED** (`/home/sugarwookie/projects/blog/app/config.py:143`)

### Admin Audit Log
- `AdminAuditLog` model with actor_id, action, target_id - **VERIFIED** (`/home/sugarwookie/projects/blog/app/models.py:407-427`)
- Actor ID logged (not username) - **VERIFIED**

### Webhook Encryption
- AES-256-GCM for webhook secrets - **VERIFIED** (`/home/sugarwookie/projects/blog/app/webhook_encryption.py:9`)
- Base64-encoded storage - **VERIFIED** (`/home/sugarwookie/projects/blog/app/webhook_encryption.py:67-68`)

---

## Discrepancies Found

### 1. Backup Encryption Documentation Error (HIGH)

**Document says:** "Backups | GPG encryption" (`/home/sugarwookie/projects/blog/architecture/deployment/security.md:55`)

**Actual implementation:**
- Backup uses **AES-256-GCM with PBKDF2-HMAC-SHA256** key derivation, NOT GPG
- Implemented in `/home/sugarwookie/projects/blog/app/backup_encryption.py`
- GPG is mentioned in comments/docstrings but actual encryption uses `cryptography` library directly

**Impact:** Security review would be misled about encryption implementation

**Reference:** `/home/sugarwookie/projects/blog/app/backup_encryption.py:1-7` (docstring explicitly describes AES-256-GCM)

---

### 2. X-Frame-Options Header Mismatch (LOW)

**Document says:** `X-Frame-Options: DENY` (`/home/sugarwookie/projects/blog/architecture/deployment/security.md:43`)

**Actual implementation:**
- Flask app sets `X-Frame-Options: DENY` (`/home/sugarwookie/projects/blog/app/__init__.py:344`)
- But nginx config sets `X-Frame-Options: SAMEORIGIN` (`/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf:25`)

**Impact:** Low - Flask header will be set, nginx adds its own (browsers use strictest). However, inconsistency could cause confusion.

---

### 3. Cross-Origin-Opener-Policy Only in Flask App (LOW)

**Document says:** `Cross-Origin-Opener-Policy: same-origin` is a security header (`/home/sugarwookie/projects/blog/architecture/deployment/security.md:46`)

**Actual implementation:**
- Set in Flask app (`/home/sugarwookie/projects/blog/app/__init__.py:347`)
- **NOT set in nginx** (`/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf:24-30`)

**Impact:** Low - Header is set by Flask application, but if nginx serves errors directly before Flask handles them, COOP won't be present.

---

### 4. Permissions-Policy Header Only in Flask App (LOW)

**Document says:** `Permissions-Policy: camera=(), microphone=(), geolocation=()` (`/home/sugarwookie/projects/blog/architecture/deployment/security.md:48`)

**Actual implementation:**
- Set in Flask app (`/home/sugarwookie/projects/blog/app/__init__.py:349-350`)
- **NOT set in nginx config**

**Impact:** Low - Same as COOP, Flask handles but nginx won't for direct error responses.

---

## Bugs Identified

### BUG-1: celery worker may fail due to missing PYTHONPATH (HIGH)

**Location:** `/home/sugarwookie/projects/blog/docker-compose.yml:34-37`

**Issue:** The celery command is:
```yaml
command: celery -A app.celery_app worker --loglevel=info
```

The `-A app.celery_app` flag expects the `app` module to be importable. However, the Dockerfile doesn't install the package in editable mode or add the app directory to PYTHONPATH.

**Verification:** Looking at `/home/sugarwookie/projects/blog/Dockerfile`, the application is copied but not installed as a package. The celery worker may fail to find `app.celery_app`.

**Fix:** Add `PYTHONPATH=/home/blog` to celery service environment.

---

### BUG-2: nginx.conf references non-existent user (HIGH)

**Location:** `/home/sugarwookie/projects/blog/nginx/nginx.conf:1`

**Issue:** The nginx config starts with `user blog;` but the nginx alpine image doesn't have a `blog` user by default. The custom `blog` user is created in the app Dockerfile, not the nginx container.

**Actual:** The nginx service uses the standard `nginx:alpine` image which has `nginx` as user, not `blog`.

**Impact:** nginx may fail to start or run as wrong user.

**Fix:** Change to `user nginx;` or remove the line to use default.

---

### BUG-3: Health check endpoint rate limiting (LOW)

**Location:** `/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf:81-85`

**Issue:** The health check location `/health` passes to Flask but the nginx config has no explicit exemption from rate limiting. The admin zone rate limiting (`/admin/` and `/admin/login`) shouldn't affect `/health`, but there's no explicit bypass.

**Impact:** Low - Health check should be exempt from rate limiting for proper monitoring.

---

## Improvement Recommendations

### Priority: HIGH

#### IMP-1: Fix celery worker Python path

**File:** `/home/sugarwookie/projects/blog/docker-compose.yml`

**Current (lines 34-37):**
```yaml
celery:
  build: .
  restart: unless-stopped
  command: celery -A app.celery_app worker --loglevel=info
```

**Proposed fix:**
```yaml
celery:
  build: .
  restart: unless-stopped
  environment:
    - PYTHONPATH=/home/blog
  command: celery -A app.celery_app worker --loglevel=info
```

**Rationale:** Ensures `app` module is importable when celery starts.

---

#### IMP-2: Fix nginx.conf user directive

**File:** `/home/sugarwookie/projects/blog/nginx/nginx.conf:1`

**Current:**
```nginx
user blog;
```

**Proposed fix:** Remove or change to:
```nginx
user nginx;
```

**Rationale:** The `nginx:alpine` image doesn't have a `blog` user. This could cause nginx startup failure.

---

#### IMP-3: Update backup encryption documentation

**File:** `/home/sugarwookie/projects/blog/architecture/deployment/security.md:55`

**Current:**
```
| Backups | GPG encryption |
```

**Proposed fix:**
```
| Backups | AES-256-GCM encryption with PBKDF2-HMAC-SHA256 key derivation |
```

**Rationale:** Documentation should accurately reflect the encryption mechanism (AES-256-GCM) rather than incorrectly claiming GPG.

---

### Priority: MEDIUM

#### IMP-4: Add Cross-Origin-Opener-Policy to nginx config

**File:** `/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf`

**Add after line 30:**
```nginx
add_header Cross-Origin-Opener-Policy "same-origin" always;
```

**Rationale:** Ensures COOP header is present even for responses that bypass Flask (e.g., nginx error pages).

---

#### IMP-5: Add explicit rate limit bypass for health endpoint

**File:** `/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf`

**Current (lines 81-85):**
```nginx
location = /health {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    access_log off;
}
```

**Proposed fix:**
```nginx
location = /health {
    limit_req zone=login burst=10 nodelay;  # Override admin zone
    limit_req_status 429;
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    access_log off;
}
```

**Rationale:** Health check endpoint should not be rate-limited to ensure reliable monitoring.

---

#### IMP-6: Align X-Frame-Options between Flask and nginx

**Issue:** Flask sets `DENY`, nginx sets `SAMEORIGIN`

**Files:**
- `/home/sugarwookie/projects/blog/app/__init__.py:344`
- `/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf:25`

**Recommendation:** Choose one value consistently. `DENY` is more restrictive. Consider removing from nginx (since Flask will set it anyway) to avoid confusion.

---

### Priority: LOW

#### IMP-7: Add redis dependency documentation for production profile

**File:** `/home/sugarwookie/projects/blog/architecture/deployment/docker.md`

**Add note:** Production profile requires redis for Celery broker and Flask caching.

---

#### IMP-8: Document backup.py entrypoint requirement

**File:** `/home/sugarwookie/projects/blog/architecture/deployment/docker.md`

**Add to backup service description:** Backup service requires the app to be properly installed. Consider adding `PYTHONPATH` or installing the package.

---

## Files Requiring Changes

| File | Changes |
|------|---------|
| `/home/sugarwookie/projects/blog/docker-compose.yml` | Add PYTHONPATH to celery service (IMP-1) |
| `/home/sugarwookie/projects/blog/nginx/nginx.conf` | Fix user directive (IMP-2) |
| `/home/sugarwookie/projects/blog/nginx/conf.d/blog.conf` | Add COOP header (IMP-4), health check rate limit (IMP-5) |
| `/home/sugarwookie/projects/blog/architecture/deployment/security.md` | Update backup encryption description (IMP-3) |
| `/home/sugarwookie/projects/blog/app/__init__.py` | Consider removing X-Frame-Options since nginx sets it (IMP-6) |

---

## Conclusion

The deployment documentation is mostly accurate with only a few significant discrepancies. The most important fixes are:

1. **BUG-1 (HIGH):** Celery worker may fail due to Python path issue
2. **BUG-2 (HIGH):** nginx config references non-existent user
3. **IMP-3 (HIGH):** Backup encryption documentation is incorrect (claims GPG, actual is AES-256-GCM)

These should be addressed before the next deployment to avoid potential failures and security misunderstandings.
