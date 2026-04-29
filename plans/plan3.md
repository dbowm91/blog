# Security Improvement Plan - Blog CMS

**Date:** 2026-04-28  
**Scope:** Application-level security hardening based on comprehensive security audit

---

## Executive Summary

The codebase demonstrates strong security posture with robust CSRF protection, SQL injection prevention, and XSS mitigations. However, **application-level rate limiting** and **account lockout mechanisms** are missing, relying entirely on reverse proxy configuration. This plan addresses 16 identified security improvements across HIGH, MEDIUM, and LOW priorities.

**Key Statistics:**
- 3 HIGH priority items (critical gaps)
- 5 MEDIUM priority items (important enhancements)
- 8 LOW priority items (defense in depth)

---

## HIGH Priority Items

### 1. Application-Level Rate Limiting

**Current State:** No rate limiting in application code. AGENTS.md explicitly states: "This codebase intentionally does not include application-level rate limiting. Configure at reverse proxy/WAF level."

**Risk:** If reverse proxy misconfigured or bypassed, brute-force and abuse attacks succeed.

**Implementation Plan:**

#### Dependencies
```diff
# requirements.txt
+ flask-limiter>=4.1.0,<5.0
```

Optional for production:
```
redis>=5.0.0  # For multi-worker deployments
```

#### Configuration Changes (`app/config.py`)

Add to `__all__` list:
```python
"LOGIN_RATE_LIMIT",
"API_RATE_LIMIT", 
"ADMIN_RATE_LIMIT",
"PUBLIC_RATE_LIMIT",
"RATELIMIT_STORAGE_URI",
"RATELIMIT_STRATEGY",
```

Add after line 116:
```python
LOGIN_RATE_LIMIT = _env("LOGIN_RATE_LIMIT", "5 per minute")
API_RATE_LIMIT = _env("API_RATE_LIMIT", "100 per hour")
ADMIN_RATE_LIMIT = _env("ADMIN_RATE_LIMIT", "20 per minute")
PUBLIC_RATE_LIMIT = _env("PUBLIC_RATE_LIMIT", "100 per minute")
RATELIMIT_STORAGE_URI = _env("RATELIMIT_STORAGE_URI", "memory://")
RATELIMIT_STRATEGY = _env("RATELIMIT_STRATEGY", "moving-window")
```

Add to `_validate_config()`:
```python
for key in ["login_rate_limit", "api_rate_limit", "admin_rate_limit", "public_rate_limit"]:
    val = config.get("app", {}).get(key)
    if val is not None:
        import re
        if not re.match(r'^\d+\s+(per\s+)?(second|minute|hour|day|month|year)s?$', val, re.IGNORECASE):
            errors.append(f"Invalid {key}: {val}. Expected format like '5 per minute'")
```

#### App Initialization (`app/__init__.py`)

Add after line 22 (imports):
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
```

In `create_app()`, after `db.init_app(app)` (around line 154):
```python
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    strategy=os.environ.get("RATELIMIT_STRATEGY", "moving-window"),
    default_limits=[],
    headers_enabled=True,
)
app.extensions["limiter"] = limiter
```

Add custom 429 error handler after `set_security_headers`:
```python
@app.errorhandler(429)
def ratelimit_handler(e):
    from flask import request
    if request.path.startswith("/api/"):
        return jsonify({
            "error": "Rate limit exceeded",
            "retry_after": e.description,
            "limit": str(e.limit)
        }), 429
    flash("Too many requests. Please try again later.", "error")
    return redirect(request.referrer or url_for("public.index"))
```

#### Route Decorators

**`app/routes/admin/auth.py`:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# After login route definition
@admin.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", key_func=get_remote_address)
def login():
    ...

@admin.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per hour", key_func=get_remote_address)
def forgot_password():
    ...
```

**`app/routes/api.py`:**
```python
from flask_limiter import Limiter

api_limiter = Limiter(
    key_func=lambda: request.headers.get("X-API-Key", get_remote_address()),
    storage_uri="memory://",
)

# Apply to API routes
@api.route("/posts", methods=["GET"])
@require_api_key
@api_limiter.limit("100 per hour")
def list_posts():
    ...
```

**`app/routes/public.py` (subscribe endpoint):**
```python
@public.route("/subscribe", methods=["POST"])
@limiter.limit("3 per hour", key_func=get_remote_address)
def subscribe():
    ...
```

#### Environment Variables
```bash
LOGIN_RATE_LIMIT=5 per minute
API_RATE_LIMIT=100 per hour
ADMIN_RATE_LIMIT=20 per minute
PUBLIC_RATE_LIMIT=100 per minute
RATELIMIT_STORAGE_URI=memory://  # or redis://localhost:6379
RATELIMIT_STRATEGY=moving-window
```

#### Tests
Add to test suite:
```python
def test_login_rate_limit(client):
    for _ in range(6):
        response = client.post("/admin/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 429
```

---

### 2. Account Lockout Mechanism

**Current State:** Only 50ms delay on failed login (`time.sleep(0.05)` in `auth.py:60`). No tracking of failed attempts, no lockout logic.

**Risk:** Brute-force attacks can try unlimited passwords with minimal delay.

**Implementation Plan:**

#### Model Changes (`app/models.py`)

Add after line 29 (after `reset_token_expires_at`):
```python
failed_login_count = db.Column(db.Integer, default=0, nullable=False)
locked_until = db.Column(UTCDateTime, nullable=True)

__table_args__ = (
    db.Index("ix_users_locked_until", "locked_until"),
)
```

Add helper methods to `User` class:
```python
def is_locked(self) -> bool:
    """Check if account is temporarily locked."""
    if self.locked_until is None:
        return False
    return datetime.now(timezone.utc) < self.locked_until.replace(tzinfo=timezone.utc)

def record_failed_login(self, max_attempts: int, lockout_minutes: int) -> None:
    """Record a failed login attempt. Lock account if threshold reached."""
    self.failed_login_count += 1
    if self.failed_login_count >= max_attempts:
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)

def reset_failed_login(self) -> None:
    """Reset failed login counter (called on successful login)."""
    self.failed_login_count = 0
    self.locked_until = None
```

#### Migration
```bash
flask db migrate -m "add failed login tracking fields to User"
flask db upgrade
```

#### Configuration Changes (`app/config.py`)

Add to `__all__`:
```python
"MAX_FAILED_ATTEMPTS",
"LOCKOUT_DURATION_MINUTES",
```

Add after line 116:
```python
MAX_FAILED_ATTEMPTS = int(_config["app"].get("max_failed_attempts", 5))
LOCKOUT_DURATION_MINUTES = int(_config["app"].get("lockout_duration_minutes", 15))
```

Add to `_validate_config()`:
```python
max_attempts = config.get("app", {}).get("max_failed_attempts")
if max_attempts is not None:
    try:
        val = int(max_attempts)
        if val < 1:
            raise ValueError
    except (ValueError, TypeError):
        errors.append(f"Invalid max_failed_attempts: {max_attempts}. Must be a positive integer")

lockout_mins = config.get("app", {}).get("lockout_duration_minutes")
if lockout_mins is not None:
    try:
        val = int(lockout_mins)
        if val < 1:
            raise ValueError
    except (ValueError, TypeError):
        errors.append(f"Invalid lockout_duration_minutes: {lockout_mins}. Must be a positive integer")
```

#### Route Changes (`app/routes/admin/auth.py`)

Modify `login()` function (around line 38):
```python
if request.method == "POST":
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    user = db.session.execute(
        select(User).filter_by(username=username)
    ).scalar_one_or_none()

    # Check lockout BEFORE password check (saves CPU on hashing)
    if user and user.is_locked():
        flash("Account temporarily locked due to too many failed attempts. Try again later.", "error")
        return render_template("admin/login.html")

    if user and user.check_password(password) and user.is_admin:
        # Success: reset failed login tracking
        user.reset_failed_login()
        db.session.commit()
        session.clear()
        login_user(user)
        sid = secrets.token_hex(32)
        admin_session = AdminSession(
            user_id=user.id,
            session_id=sid,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:256],
        )
        db.session.add(admin_session)
        db.session.commit()
        session["admin_session_id"] = sid
        session["admin_session_ip"] = request.remote_addr
        return redirect(url_for("admin.dashboard"))
    
    # Failure: record attempt if user exists (prevents username enumeration)
    if user:
        user.record_failed_login(MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES)
        db.session.commit()
    
    flash("Invalid credentials.", "error")
    time.sleep(0.05)
```

#### Config File (`config.toml`)
Add under `[app]` section:
```toml
max_failed_attempts = 5
lockout_duration_minutes = 15
```

---

### 3. API Rate Limiting & Audit Logging

**Current State:** API uses single `X-API-Key` header with `hmac.compare_digest()`. No rate limiting, no audit trail.

**Implementation Plan:**

#### Rate Limiting
Same Flask-Limiter setup as Item #1. Apply to all API routes with stricter limits for write operations:
```python
# Read endpoints
@api.route("/posts", methods=["GET"])
@require_api_key
@api_limiter.limit("100 per hour")
def list_posts():
    ...

# Write endpoints - stricter
@api.route("/posts", methods=["POST"])
@require_api_key
@api_limiter.limit("20 per hour")
def create_post():
    ...
```

#### API Key Rotation Support (`app/routes/api.py`)

Modify `require_api_key` to support multiple keys:
```python
import os
import hmac

API_KEYS = [k.strip() for k in os.environ.get("API_KEYS", os.environ.get("API_KEY", "")).split(",") if k.strip()]

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEYS:
            return jsonify({"error": "API not configured"}), 503

        provided = request.headers.get("X-API-Key", "")
        if not provided:
            return jsonify({"error": "Missing API key"}), 401
        
        # Timing-safe comparison against all valid keys
        key_valid = False
        for valid_key in API_KEYS:
            if hmac.compare_digest(provided, valid_key):
                key_valid = True
                break
        
        if not key_valid:
            # Audit log failure
            audit_log("api_auth_failure", extra={"api_key_hash": hashlib.sha256(provided.encode()).hexdigest()[:16]})
            return jsonify({"error": "Invalid API key"}), 401
        
        # Audit log success
        audit_log("api_auth_success", extra={"api_key_hash": hashlib.sha256(provided.encode()).hexdigest()[:16]})
        return f(*args, **kwargs)
    return decorated
```

#### Audit Logging Decorator

Create `app/audit.py`:
```python
import logging
from functools import wraps
from flask import request

audit_logger = logging.getLogger("audit")

def audit_log(event_type: str, extra: dict = None):
    """Log a security-relevant event."""
    if extra is None:
        extra = {}
    audit_logger.info(event_type, extra={
        "event_type": event_type,
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "")[:256],
        "path": request.path,
        "method": request.method,
        **extra
    })

def audit_api_call(f):
    """Decorator to audit API calls."""
    @wraps(f)
    def decorated(*args, **kwargs):
        result = f(*args, **kwargs)
        audit_log("api_call", extra={
            "endpoint": f.__name__,
            "status_code": result[1] if isinstance(result, tuple) else 200
        })
        return result
    return decorated
```

#### Logging Configuration (`app/__init__.py`)

Update `configure_logging()`:
```python
def configure_logging(app):
    # ... existing code ...
    
    # Add audit log handler
    if not app.debug and not app.testing:
        audit_handler = RotatingFileHandler(
            os.path.join(log_dir, "audit.log"),
            maxBytes=10240000,
            backupCount=10
        )
        audit_handler.setFormatter(StructuredLogFormatter())
        audit_handler.setLevel(logging.INFO)
        
        audit_logger = logging.getLogger("audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False  # Don't duplicate to root logger
```

#### Environment Variables
```bash
API_KEYS=key1,key2,key3  # Comma-separated for rotation
```

---

## MEDIUM Priority Items

### 4. Session IP Binding Enforcement

**Current State:** IP stored in `AdminSession` and `session["admin_session_ip"]`, but only logs warning on mismatch - no enforcement.

**Implementation Plan:**

#### Configuration (`app/config.py`)

Add to `__all__`:
```python
"SESSION_IP_BINDING",
```

Add after `SESSION_LIFETIME_HOURS`:
```python
SESSION_IP_BINDING = _config["app"].get("session_ip_binding", "log")
```

Add to `_validate_config()`:
```python
ip_binding = config.get("app", {}).get("session_ip_binding", "log")
if ip_binding not in ("off", "log", "enforce"):
    errors.append(
        f"Invalid session_ip_binding: {ip_binding}. Must be 'off', 'log', or 'enforce'"
    )
```

#### Code Changes (`app/routes/admin/__init__.py`)

Update `admin_required` decorator:
```python
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)

        from app.extensions import db
        from app.models import AdminSession
        from flask import current_app

        sid = session.get("admin_session_id")
        if sid:
            stored_ip = session.get("admin_session_ip")
            current_ip = request.remote_addr
            if stored_ip and current_ip and stored_ip != current_ip:
                logger.warning(
                    "IP address changed for admin session %s: expected %s, got %s",
                    sid, stored_ip, current_ip,
                )
                # Enforce mode: invalidate session and redirect
                if current_app.config.get("SESSION_IP_BINDING") == "enforce":
                    from flask_login import logout_user
                    from sqlalchemy.exc import IntegrityError, OperationalError

                    try:
                        db.session.execute(
                            delete(AdminSession).where(AdminSession.session_id == sid)
                        )
                        db.session.commit()
                    except (IntegrityError, OperationalError):
                        db.session.rollback()
                    session.clear()
                    logout_user()
                    flash("Session invalidated due to IP address change. Please log in again.", "warning")
                    return redirect(url_for("admin.login"))

        return f(*args, **kwargs)
    return decorated
```

#### Config File (`config.toml`)
```toml
[app]
session_ip_binding = "log"  # Options: off, log, enforce
```

**Note:** Use `log` mode default - `enforce` can cause issues for mobile admins switching WiFi/cellular.

---

### 5. Backup Encryption

**Current State:** No encryption. Backups are plaintext `.db` or gzip-compressed.

**Implementation Plan:**

#### Recommended Approach: GPG (Asymmetric)

**Dependencies:**
```diff
# requirements.txt
+ python-gnupg==0.5.5
```

System package:
```bash
apt install gnupg  # Debian/Ubuntu
```

**Environment Variables:**
```bash
BACKUP_GPG_RECIPIENT=admin@example.com  # GPG public key email/ID
# OR for symmetric encryption:
BACKUP_GPG_PASSPHRASE=<passphrase>
```

**Code Changes (`app/routes/admin/backup.py`):**

Add encrypt option to `create_backup()`:
```python
import gnupg
import os
from flask import current_app

@admin.route("/backup/create", methods=["POST"])
@admin_required
def create_backup():
    from app.backup import create_backup as _create_backup
    compress = "compress" in request.form
    encrypt = "encrypt" in request.form
    
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_path = db_uri.replace("sqlite:///", "/") if db_uri.startswith("sqlite:///") else os.path.join(current_app.instance_path, "blog.db")
    backup_dir = _get_backup_dir()
    
    result = _create_backup(db_path, backup_dir, compress=compress, keep=10)
    
    if result:
        backup_path = result
        
        if encrypt:
            gpg = gnupg.GPG()
            recipient = current_app.config.get("BACKUP_GPG_RECIPIENT")
            
            with open(backup_path, "rb") as f:
                if recipient:
                    status = gpg.encrypt_file(
                        f,
                        recipients=[recipient],
                        output=f"{backup_path}.gpg",
                        armor=False
                    )
                else:
                    status = gpg.encrypt_file(
                        f,
                        symmetric="AES256",
                        passphrase=current_app.config.get("BACKUP_GPG_PASSPHRASE"),
                        output=f"{backup_path}.gpg",
                        armor=False
                    )
            
            if status.ok:
                safe_delete_file(backup_path)
                flash("Encrypted backup created successfully.", "success")
            else:
                flash(f"Encryption failed: {status.stderr}", "error")
        
        if not encrypt:
            flash("Backup created successfully.", "success")
    else:
        flash("Backup failed.", "error")
    
    return redirect(url_for("admin.backup"))
```

**Update Template (`app/templates/admin/backup.html`):**
Add encrypt checkbox:
```html
<form method="POST">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <label>
    <input type="checkbox" name="compress"> Compress (gzip)
  </label>
  <label>
    <input type="checkbox" name="encrypt"> Encrypt (GPG)
  </label>
  <button type="submit">Create Backup</button>
</form>
```

**Update `scripts/sync_backups.sh`:**
Add `.gpg` to find patterns.

---

### 6. CSS Sanitization with tinycss2

**Current State:** Regex-based `sanitize_css()` in `app/utils.py:90-129`. Known bypass risks.

**Risk:** Regex patterns can be bypassed via whitespace variations, comment insertion, encoding tricks.

**Implementation Plan:**

#### Dependencies
```diff
# requirements.txt
+ tinycss2>=1.3.0,<2.0
```

#### Code Changes (`app/utils.py`)

Replace `sanitize_css()` (lines 90-129):
```python
import tinycss2
from tinycss2 import serialize, parse_blocks_contents

SAFE_CSS_PROPERTIES = {
    # Text styling
    "color", "background-color", "font-family", "font-size",
    "font-weight", "font-style", "text-decoration", "text-align",
    "line-height", "letter-spacing", "text-transform",
    
    # Box model
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "width", "height", "min-width", "min-height", "max-width", "max-height",
    
    # Borders
    "border", "border-width", "border-style", "border-color",
    "border-top", "border-right", "border-bottom", "border-left",
    "border-radius",
    
    # Layout (safe subset)
    "display", "visibility", "opacity", "vertical-align",
    
    # Background (without url())
    "background-color", "background-repeat", "background-position",
    
    # Lists
    "list-style", "list-style-type",
    
    # Tables
    "border-collapse", "border-spacing",
}

DANGEROUS_PREFIXES = ("mso-", "-webkit-text-security", "-moz-binding")


def sanitize_css(css_text: str) -> str:
    """Sanitize custom CSS using tinycss2 parser with property allowlist."""
    if not css_text:
        return ""
    
    try:
        nodes = parse_blocks_contents(css_text, skip_comments=True, skip_whitespace=True)
    except Exception:
        return ""
    
    safe_nodes = []
    for node in nodes:
        if node.type == "declaration":
            prop_lower = node.name.lower()
            
            # Skip dangerous prefixes
            if any(prop_lower.startswith(p) for p in DANGEROUS_PREFIXES):
                continue
            
            # Skip if not in allowlist
            if prop_lower not in SAFE_CSS_PROPERTIES:
                continue
            
            # Check value for dangerous patterns
            value_str = serialize(node.value).lower()
            if "url(" in value_str or "expression(" in value_str or "javascript:" in value_str:
                continue
            
            safe_nodes.append(node)
        
        elif node.type == "qualified-rule":
            # Allow simple selector rules with safe declarations only
            safe_content = []
            try:
                inner_nodes = parse_blocks_contents(
                    serialize(node.content), skip_comments=True, skip_whitespace=True
                )
                for inner in inner_nodes:
                    if inner.type == "declaration":
                        prop_lower = inner.name.lower()
                        if any(prop_lower.startswith(p) for p in DANGEROUS_PREFIXES):
                            continue
                        if prop_lower not in SAFE_CSS_PROPERTIES:
                            continue
                        value_str = serialize(inner.value).lower()
                        if "url(" in value_str or "expression(" in value_str:
                            continue
                        safe_content.append(inner)
            except Exception:
                continue
            
            if safe_content:
                node.content = [n for n in safe_content]
                safe_nodes.append(node)
    
    return serialize(safe_nodes).strip()
```

#### Critical Fix (`app/routes/admin/settings.py`)

Currently, `sanitize_css()` is NOT called on `settings_obj.custom_css` before saving (line 53). Fix:
```python
from app.utils import sanitize_css

# Line 53 - before:
# settings_obj.custom_css = request.form.get("custom_css", "").strip()

# After:
settings_obj.custom_css = sanitize_css(request.form.get("custom_css", "").strip())
```

#### Tests
Create `tests/test_css_sanitization.py`:
```python
from app.utils import sanitize_css

def test_sanitize_css_allows_safe_properties():
    css = "color: red; font-size: 16px; margin: 10px;"
    result = sanitize_css(css)
    assert "color:" in result
    assert "font-size:" in result

def test_sanitize_css_blocks_dangerous_properties():
    css = "content: 'evil'; behavior: url(...); direction: rtl;"
    result = sanitize_css(css)
    assert "content:" not in result
    assert "behavior:" not in result

def test_sanitize_css_blocks_url_values():
    css = "background: url(http://evil.com/img.png);"
    result = sanitize_css(css)
    assert "url(" not in result

def test_sanitize_css_handles_nested_css():
    css = "@media (max-width: 600px) { color: red; }"
    result = sanitize_css(css)
    assert "@media" not in result
```

---

### 7. Token Enumeration Delay Optimization

**Current State:** `TOKEN_ENUMERATION_DELAY = 0.1` (100ms) in `config.py:112`, only applied on invalid path (`auth.py:158`).

**Risk:** Timing attack - valid vs invalid paths have different timing (invalid sleeps, valid doesn't).

**Implementation Plan:**

#### Configuration (`app/config.py`)
Change default (line 112):
```python
TOKEN_ENUMERATION_DELAY = float(_config["app"].get("token_enumeration_delay", 0.5))
```

#### Code Changes (`app/routes/admin/auth.py`)

Apply delay on BOTH paths for uniform timing:
```python
@admin.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        if not identifier:
            flash("Please enter your username or email address.", "error")
            return redirect(url_for("admin.forgot_password"))

        user = db.session.execute(
            select(User).filter_by(username=identifier)
        ).scalar_one_or_none()

        if user and user.is_admin:
            token = secrets.token_hex(32)
            user.reset_token = _hash_token(token)
            user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            try:
                db.session.commit()
                send_password_reset(user, token)
            except (IntegrityError, OperationalError):
                db.session.rollback()
                flash("An error occurred. Please try again.", "error")
                time.sleep(TOKEN_ENUMERATION_DELAY)
                return redirect(url_for("admin.forgot_password"))
            
            flash("If that account exists, a password reset email has been sent.", "success")
            time.sleep(TOKEN_ENUMERATION_DELAY)  # Uniform delay
            return redirect(url_for("admin.login"))

        # Invalid path - same message and delay
        flash("If that account exists, a password reset email has been sent.", "success")
        time.sleep(TOKEN_ENUMERATION_DELAY)
        return redirect(url_for("admin.login"))

    return render_template("admin/forgot-password.html")
```

---

### 8. CSP `unsafe-inline` Removal

**Current State:** `style-src-attr 'unsafe-inline'` in CSP header (`__init__.py:293`).

**Implementation Plan:**

#### Templates - Replace Inline Styles

**A. Conditional Display (`style="display: none"`)`

Add to main CSS file:
```css
.hidden { display: none !important; }
```

Then update templates:
```html
<!-- Before -->
<div style="{% if condition %}display: none;{% endif %}">

<!-- After -->
<div class="{% if condition %}hidden{% endif %}">
```

Affected files: `admin/settings.html:48`, `admin/editor.html:34,41`

**B. Dynamic Chart Heights**

Use nonce-protected `<style>` block in templates:
```html
<style nonce="{{ csp_nonce }}">
{% for day in daily_views %}
.chart-bar:nth-child({{ loop.index }}) { height: {{ (day.views / max_views * 100)|round }}%; }
{% endfor %}
</style>
```

Then remove `style="..."` from `.chart-bar` elements.

Affected: `admin/dashboard.html:51`, `admin/analytics.html:49`

**C. Theme Preset Preview Colors**

Generate CSS classes per preset:
```html
<style nonce="{{ csp_nonce }}">
{% for preset_id, preset in theme_presets.items() %}
.preset-{{ preset_id }} { background: {{ preset.bg }}; border-color: {{ preset.border }}; }
{% endfor %}
</style>
```

#### JavaScript - Replace Style Manipulations

**Toggle Visibility:**
```javascript
// Before
element.style.display = 'none';

// After
element.classList.add('hidden');
// or
element.classList.remove('hidden');
```

**Body Scroll Lock:**
```javascript
// Before
document.body.style.overflow = 'hidden';

// After
document.body.classList.add('no-scroll');
```

Add CSS:
```css
.no-scroll { overflow: hidden; }
```

#### Expected CSP Change (`app/__init__.py`)

After refactoring:
```python
response.headers["Content-Security-Policy"] = (
    f"default-src 'self'; "
    f"style-src 'self' 'nonce-{nonce}'; "
    f"style-src-attr 'none'; "  # Changed from 'unsafe-inline'
    f"font-src 'self'; "
    f"img-src 'self' data:; "
    f"script-src 'self' 'nonce-{nonce}'; "
    f"connect-src 'self'; "
    f"frame-src 'none'; "
    f"frame-ancestors 'none'"
)
```

**Note:** This is a significant refactoring effort. Consider keeping `style-src-attr 'unsafe-inline'` for admin routes only via different CSP per route.

---

## LOW Priority Items

### 9. Login Delay Increase

Increase `time.sleep(0.05)` to `time.sleep(0.25)` in `auth.py:60` as secondary defense alongside rate limiting.

### 10. Config File Permission Checks

Add to `app/config.py`:
```python
import stat

def check_config_permissions(config_path: str) -> None:
    """Warn if config file has insecure permissions."""
    try:
        st = os.stat(config_path)
        mode = stat.S_IMODE(st.st_mode)
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            logger.warning(
                "Config file %s is world- or group-readable (perms=%o). "
                "Consider 'chmod 600 %s' to protect secrets.",
                config_path, mode, config_path
            )
    except OSError:
        pass
```

Call in `create_app()` after config load.

### 11. Security Audit Logging

Add logging for these events:
- Failed logins (with username, IP)
- CSRF failures (with path, IP)
- Permission denials (with user_id, path)
- Privilege changes (promote/demote/make-owner)

Use the `audit_log()` function from Item #3.

### 12. Email Security Improvements

**Fix `with` statement gotcha in `app/email.py`:**
```python
def _send_email(to, subject, html_body, text_body=None):
    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        # ... rest of email sending
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass
```

**Document:** Never put `SMTP_PASSWORD` in `config.toml` - use environment variable only.

### 13. File Upload Enhancements

**Add image dimension validation (`app/routes/admin/helpers/images.py`):**
```python
from PIL import Image
from io import BytesIO

MAX_IMAGE_DIMENSION = 5000

def _validate_image_dimensions(file_data: bytes) -> bool:
    """Validate image dimensions to prevent zip bombs."""
    try:
        with Image.open(BytesIO(file_data)) as img:
            img.verify()
            width, height = img.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                return False
            return True
    except Exception:
        return False
```

**Optional ClamAV integration:**
```python
try:
    import clamd
    cd = clamd.ClamdUnixSocket()
    result = cd.instream(BytesIO(file_data))
    if result.get("stream", ["", ""])[0] == "FOUND":
        return None, "File failed virus scan."
except ImportError:
    pass  # ClamAV not installed
```

### 14. Search Highlighting XSS Prevention

Fix `highlight_query()` in `app/search.py`:
```python
import nh3

def highlight_query(text: str, query: str) -> str:
    """Add <mark> tags around query terms. Sanitizes HTML first."""
    if not text or not query:
        return text
    
    # Strip HTML tags first to prevent XSS in search snippets
    safe_text = nh3.clean(text, tags=set(), attributes={})
    
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe_text)
```

Also sanitize query in `search()`:
```python
def search(query: str) -> list[tuple[int, int]]:
    query = nh3.clean(query, tags=set(), attributes={})
    # ... rest of function
```

### 15. Backup File Permission Hardening

Add to backup creation function:
```python
import os

def create_backup(db_path, backup_dir, compress=False, keep=10):
    # ... backup creation code ...
    
    # Secure the backup file - owner read/write only
    os.chmod(backup_path, 0o600)
    
    return backup_path
```

### 16. CSP report-uri Implementation

**Add endpoint (`app/__init__.py`):**
```python
@app.route("/csp-violation", methods=["POST"])
def csp_violation():
    """Log CSP violation reports."""
    try:
        report = request.get_json(force=True)
        logger.warning(
            "csp_violation", extra={
                "event_type": "csp_violation",
                "report": report,
                "ip_address": request.remote_addr,
            }
        )
    except Exception:
        pass
    return "", 204
```

**Update CSP header:**
```python
response.headers["Content-Security-Policy"] = (
    f"default-src 'self'; "
    f"style-src 'self' 'nonce-{nonce}'; "
    f"style-src-attr 'unsafe-inline'; "
    f"font-src 'self'; "
    f"img-src 'self' data:; "
    f"script-src 'self' 'nonce-{nonce}'; "
    f"connect-src 'self'; "
    f"frame-src 'none'; "
    f"frame-ancestors 'none'; "
    f"report-uri /csp-violation"
)
```

---

## Dependencies Summary

| Package | Version | Purpose | Priority |
|---------|----------|---------|----------|
| `flask-limiter` | `>=4.1.0,<5.0` | Rate limiting | HIGH |
| `tinycss2` | `>=1.3.0,<2.0` | CSS sanitization | MEDIUM |
| `python-gnupg` | `==0.5.5` | Backup encryption (GPG) | MEDIUM |
| `cryptography` | `>=48.0.0` | Backup encryption (AES alternative) | MEDIUM |
| `pillow` | `>=10.0.0` | Image dimension validation | LOW |
| `pyclamd` | latest | Virus scanning (optional) | LOW |
| `redis` | `>=5.0.0` | Rate limiting storage (optional) | HIGH (if multi-worker) |

---

## Implementation Order

### Phase 1: Critical Security Gaps (Week 1)
1. **Flask-Limiter setup** - Add to requirements.txt, initialize in `app/__init__.py`
2. **Apply rate limits** - Decorate login (5/min), forgot-password (3/hour), API endpoints
3. **Account lockout** - Migrate User model, update auth.py, add config variables
4. **API audit logging** - Create `audit.py`, add audit log handler

### Phase 2: Important Enhancements (Week 2)
5. **CSS sanitization** - Install tinycss2, replace `sanitize_css()`, fix settings.py
6. **Session IP binding** - Add config variable, update `admin_required` decorator
7. **Backup encryption** - Install python-gnupg, modify backup.py, update template
8. **Token delay fix** - Change default to 0.5s, apply uniformly

### Phase 3: Defense in Depth (Week 3-4)
9. **CSP unsafe-inline removal** - Refactor templates and JS (effort: high)
10. **Remaining LOW priority items** - Implement as time permits

---

## Testing Strategy

1. **Unit tests** - Test new functions (lockout logic, CSS sanitization, etc.)
2. **Integration tests** - Test rate limiting, account lockout flows
3. **Security tests** - Verify CSP headers, test XSS prevention
4. **E2E tests** - Test login flow with lockout, API with rate limits

Run existing tests after each phase:
```bash
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v
```

---

## Rollback Plan

1. **Rate limiting** - Set `RATELIMIT_STORAGE_URI=memory://` and restart
2. **Account lockout** - Run `flask db downgrade` to revert migration
3. **CSS sanitization** - Revert to regex version if tinycss2 causes issues
4. **Backup encryption** - Don't pass `encrypt` parameter in form

---

## Documentation Updates

1. **AGENTS.md** - Update "Rate Limiting" section to document app-level limits
2. **DEPLOY.md** - Document new environment variables
3. **config.toml.example** - Add new config variables with comments
4. **README.md** - Note new security features

---

## Notes

- All code examples provided are based on deep-dive agent research
- Test thoroughly after each phase before proceeding
- Consider feature flags for gradual rollout (e.g., `SESSION_IP_BINDING=off|log|enforce`)
- Backup encryption requires GPG key generation - document this process for admins
