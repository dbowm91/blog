# Security Improvement Plan - Blog CMS

**Date**: April 28, 2026
**Status**: Planning Phase (Not yet implemented)
**Scope**: Addresses findings from comprehensive security audit

---

## Executive Summary

Based on the security audit, this plan addresses 7 identified security concerns. Per project requirements:

- **Rate Limiting**: Keep reverse proxy only (nginx) - no application-level rate limiting
- **API Usage**: Internal admin automation only - no third-party access needed
- **Backup Integrity**: Implement checksum + SQLite integrity verification
- **Priority Focus**: Fix confirmed vulnerabilities first, add improvements second

---

## 🔴 CRITICAL (Fix Immediately)

### 1. API Key Timing Attack Fix

**File**: `app/routes/api.py` (line 32)
**Severity**: HIGH - Allows full API key extraction via side-channel
**Estimated Effort**: 5 minutes

**Current Vulnerable Code**:
```python
# Line 32
if not provided or provided != API_KEY:
```

**Problem**: Python `!=` operator uses short-circuit evaluation. Attackers can extract the API key character-by-character by measuring response time differences.

**Fix**:
```python
# Add to imports (line 8 area)
import hmac

# Replace line 32
if not hmac.compare_digest(provided, API_KEY):
```

**Why This Works**: `hmac.compare_digest()` uses constant-time comparison regardless of input match/mismatch, preventing timing attacks.

**Verification**: The codebase already uses this pattern in:
- `app/csrf.py:56` - CSRF token validation
- `app/routes/public.py:450` - Preview token validation
- `app/routes/public.py:853` - Health check secret validation

**Files to Modify**:
- `app/routes/api.py` (add `import hmac`, change line 32)

---

## 🟡 HIGH PRIORITY (Fix This Sprint)

### 2. Backup Integrity Verification

**Files**: `backup.py`, `app/routes/admin/backup.py`
**Severity**: MEDIUM-HIGH - Corrupted/malicious backups can be restored without detection
**Estimated Effort**: 2-3 hours

**Current State**:
- Backups created via SQLite backup API (good)
- No checksum verification
- No SQLite integrity check on backup or restore
- Tests confirm corrupted backups restore without error (`test_backup.py`)

**Implementation Plan**:

#### Step 1: Create `app/backup_integrity.py` (New Module)

```python
"""Backup integrity verification for DevLog blog."""

import hashlib
import gzip
import sqlite3
import os
import tempfile
from typing import Optional, Tuple


def calculate_sha256(file_path: str, chunk_size: int = 8192) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        if hasattr(hashlib, "file_digest"):
            return hashlib.file_digest(f, "sha256").hexdigest()
        else:
            while chunk := f.read(chunk_size):
                h.update(chunk)
            return h.hexdigest()


def verify_sha256(file_path: str, expected_hash: str) -> bool:
    """Verify a file's SHA-256 hash using timing-safe comparison."""
    import hmac
    actual_hash = calculate_sha256(file_path)
    return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())


def write_checksum_file(backup_path: str, checksum_path: Optional[str] = None) -> str:
    """Write SHA-256 checksum to a file (compatible with sha256sum format)."""
    if checksum_path is None:
        checksum_path = backup_path + ".sha256"

    hash_value = calculate_sha256(backup_path)
    filename = os.path.basename(backup_path)

    with open(checksum_path, "w") as f:
        f.write(f"{hash_value}  {filename}\n")

    return checksum_path


def check_sqlite_integrity(db_path: str) -> Tuple[bool, str]:
    """Run SQLite PRAGMA integrity_check on a database file."""
    try:
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            return (result == "ok", result)
        finally:
            conn.close()
    except sqlite3.Error as e:
        return (False, str(e))


def verify_backup_integrity(backup_path: str) -> Tuple[bool, str]:
    """Comprehensive backup integrity verification.

    Performs:
    1. SHA-256 checksum verification (if .sha256 file exists)
    2. SQLite integrity check
    """
    if not os.path.exists(backup_path):
        return (False, "Backup file not found")

    # Verify checksum if .sha256 file exists
    checksum_path = backup_path + ".sha256"
    if os.path.exists(checksum_path):
        # Read expected hash
        try:
            with open(checksum_path, "r") as f:
                line = f.readline().strip()
                parts = line.split(None, 1)
                if parts:
                    expected_hash = parts[0].lower()
                    if not verify_sha256(backup_path, expected_hash):
                        return (False, "SHA-256 checksum verification failed")
        except (IOError, OSError):
            pass  # Checksum file unreadable, continue with SQLite check

    # For gzipped files, decompress temporarily to check SQLite integrity
    temp_db_path = None
    db_to_check = backup_path

    try:
        if backup_path.endswith(".gz"):
            temp_db_path = backup_path + ".temp_check"
            try:
                with gzip.open(backup_path, "rb") as f_in:
                    with open(temp_db_path, "wb") as f_out:
                        while chunk := f_in.read(8192):
                            f_out.write(chunk)
                db_to_check = temp_db_path
            except (gzip.BadGzipFile, OSError) as e:
                return (False, f"Failed to decompress gzipped backup: {e}")

        # Run SQLite integrity check
        is_valid, result = check_sqlite_integrity(db_to_check)
        if not is_valid:
            return (False, f"SQLite integrity check failed: {result}")

        return (True, "Backup integrity verified")

    finally:
        # Clean up temp file
        if temp_db_path and os.path.exists(temp_db_path):
            os.remove(temp_db_path)
```

#### Step 2: Update `backup.py` (Standalone Script)

Modify the `create_backup()` function to:
1. Generate SHA-256 checksum file after backup
2. Run SQLite `PRAGMA integrity_check` on the backup
3. Only report success if both pass
4. Delete backup if integrity check fails

Key changes:
```python
from app.backup_integrity import (
    write_checksum_file,
    verify_backup_integrity,
    check_sqlite_integrity
)

def create_backup(db_path, backup_dir, compress=False, keep=7):
    # ... existing backup creation code ...

    # After backup file is created:
    print("Verifying backup integrity...")
    is_valid, message = verify_backup_integrity(backup_path)
    if not is_valid:
        print(f"ERROR: Backup integrity check failed: {message}")
        # Clean up invalid backup
        if os.path.exists(backup_path):
            os.remove(backup_path)
        checksum_path = backup_path + ".sha256"
        if os.path.exists(checksum_path):
            os.remove(checksum_path)
        return None

    print(f"Backup integrity verified: {message}")
    return backup_path
```

#### Step 3: Update `app/routes/admin/backup.py`

Modify `restore_backup()` function to:
1. Verify SHA-256 checksum before restore (if checksum file exists)
2. Run SQLite integrity check on backup before restore
3. Abort restore if any check fails

Key changes:
```python
from app.backup_integrity import verify_backup_integrity

@admin.route("/backup/restore/<filename>", methods=["POST"])
@admin_required
def restore_backup(filename):
    # ... existing path validation ...

    # Verify backup integrity before restoring
    is_valid, message = verify_backup_integrity(real_path)
    if not is_valid:
        flash(f"Backup integrity verification failed: {message}", "error")
        return redirect(url_for("admin.backup"))

    flash(f"Backup integrity verified: {message}", "info")

    # ... proceed with restore ...
```

#### Step 4: Update `requirements.txt`

Add (if not already present):
```
# No new dependencies required - uses Python standard library (hashlib, gzip, sqlite3)
```

**Files to Create/Modify**:
- `app/backup_integrity.py` (NEW - ~100 lines)
- `backup.py` (modify create_backup function)
- `app/routes/admin/backup.py` (modify restore_backup function)
- `tests/test_backup.py` (add integrity verification tests)

---

### 3. Password Reset Token Hashing

**Files**: `app/models.py`, `app/routes/admin/auth.py`
**Severity**: MEDIUM - DB compromise exposes active reset tokens
**Estimated Effort**: 30 minutes

**Current State**: Reset tokens stored as plaintext in `User.reset_token` column.

**Risk**: If database is compromised, attacker can see all active reset tokens (1-hour window to use them).

**Implementation Plan**:

#### Step 1: Update `app/routes/admin/auth.py` - `forgot_password()`

```python
import hashlib  # Add at top of file

def forgot_password() -> Response:
    # ... existing code ...

    if user and user.is_admin:
        token = secrets.token_hex(32)
        # Store SHA-256 hash instead of plaintext
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user.reset_token = token_hash  # Store hash
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        try:
            db.session.commit()
            send_password_reset(user, token)  # Send plaintext token in email
            flash("If that account exists, a password reset email has been sent.", "success")
        except (IntegrityError, OperationalError):
            db.session.rollback()
            flash("An error occurred. Please try again.", "error")
```

#### Step 2: Update `app/routes/admin/auth.py` - `reset_password()`

```python
def reset_password(token: str) -> Response:
    # Hash the incoming token and look up by hash
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    user = db.session.execute(
        select(User).filter_by(reset_token=token_hash)  # Compare hashes
    ).scalar_one_or_none()

    # ... rest of function unchanged ...
```

#### Step 3: Migration Considerations

- No formal migration needed - tokens expire after 1 hour
- After deployment, old plaintext tokens become invalid (they won't match the new SHA-256 lookup)
- Users with pending resets will need to request a new reset (they'll get the new hashed-token flow)
- After 1 hour, all old plaintext tokens will have expired anyway

**Why SHA-256 (Not Bcrypt/Werkzeug)**:
- Reset tokens have 256 bits of entropy (from `secrets.token_hex(32)`)
- No need for key stretching (bcrypt's purpose is to slow down weak password guessing)
- SHA-256 is sufficient for high-entropy tokens
- Allows efficient database indexing and lookup

**Files to Modify**:
- `app/routes/admin/auth.py` (lines 140-142 in `forgot_password()`, lines 168-170 in `reset_password()`)

---

## 🟢 MEDIUM PRIORITY (Fix When Time Permits)

### 4. API Response Filtering (Draft Posts)

**File**: `app/routes/api.py`
**Severity**: LOW-MEDIUM (Internal admin only, but best practice)
**Estimated Effort**: 1 hour

**Current State**: API returns all posts (published + drafts) to any valid API key.

**User Decision**: API is for internal admin automation only - no third-party access.

**Recommendation**: At minimum, add a note in documentation that API key grants full access. Consider adding draft filtering if needed:

```python
# Optional: Filter drafts by default in list_posts()
def list_posts() -> Response:
    # ...
    if published_filter is not None:
        published_val = published_filter.lower() in ("true", "1", "yes")
        query = query.filter(Post.published == published_val)
    else:
        # By default, only show published posts via API
        query = query.filter(Post.published == True)
    # ...
```

**Files to Modify** (Optional):
- `app/routes/api.py` (modify `list_posts()` default behavior)

---

### 5. Scheduler Cross-Platform Locking

**File**: `app/scheduler.py`
**Severity**: LOW (Unix-only, Windows not supported)
**Estimated Effort**: 1-2 hours

**Current State**: Uses `fcntl` (Unix only). Windows sets `HAS_FCNTL = False` and skips locking.

**User Decision**: Not a priority (Windows deployment not needed).

**Recommendation**: If Windows support is ever needed, use `portalocker` library:

```python
# Future implementation:
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False
```

**Files to Modify** (When Needed):
- `requirements.txt` (add `portalocker>=3.2.0,<4.0`)
- `app/scheduler.py` (replace `fcntl` with `portalocker`)

---

## 🔵 LOW PRIORITY (Nice to Have)

### 6. Health Check Information Leak

**File**: `app/routes/public.py` (lines 828-917)
**Severity**: LOW
**Estimated Effort**: 30 minutes

**Current State**: Detailed health check requires `HEALTH_CHECK_SECRET` + uses `hmac.compare_digest()`. Exposes `database_latency_ms`, `scheduler_next_run`.

**Recommendations**:
1. Add `HEALTH_CHECK_SECRET` validation in `create_app()` (like `SECRET_KEY` check)
2. Log detailed health check access
3. Consider removing detailed view (minimal operational value)

**Files to Modify** (Optional):
- `app/__init__.py` (add validation)
- `app/routes/public.py` (add logging)

---

## Implementation Order

### Phase 1: Critical Fix (Today)
1. **API Key Timing Attack** - 5 minute fix, 1 file

### Phase 2: High Priority (This Week)
2. **Backup Integrity Verification** - 2-3 hours, 3 files + 1 new module
3. **Password Reset Token Hashing** - 30 minutes, 1 file

### Phase 3: Medium Priority (Next Sprint)
4. **API Draft Filtering** (Optional) - 1 hour
5. **Scheduler Cross-Platform** (If Windows needed)

### Phase 4: Low Priority (When Needed)
6. **Health Check Hardening** (Optional)

---

## Testing Strategy

### For API Timing Fix:
```python
# tests/test_api.py
def test_api_key_timing_safe(app, client):
    """Test that API key comparison uses hmac.compare_digest."""
    # This is a code review test - verify the source uses hmac.compare_digest
    import inspect
    from app.routes.api import require_api_key
    source = inspect.getsource(require_api_key)
    assert "hmac.compare_digest" in source
```

### For Backup Integrity:
```python
# tests/test_backup.py
def test_backup_creates_checksum(app, db, authenticated_client):
    """Test that backup creation generates checksum file."""
    response = authenticated_client.post("/admin/backup/create")
    assert response.status_code == 302

    backup_dir = os.path.join(app.instance_path, "backups")
    checksum_files = [f for f in os.listdir(backup_dir) if f.endswith(".sha256")]
    assert len(checksum_files) >= 1

def test_restore_rejects_corrupted_backup(app, db, authenticated_client):
    """Test that corrupted backups are rejected on restore."""
    backup_dir = os.path.join(app.instance_path, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # Create corrupted backup
    corrupted_name = "blog_20260101_000000.db"
    corrupted_path = os.path.join(backup_dir, corrupted_name)
    with open(corrupted_path, "wb") as f:
        f.write(b"this is not a valid sqlite database")

    # Try to restore - should fail
    response = authenticated_client.post(f"/admin/backup/restore/{corrupted_name}")
    assert response.status_code == 302
    # Should have error flash message
```

### For Password Reset Token:
```python
# tests/test_auth.py
def test_reset_token_hashed_in_db(app, db, authenticated_client):
    """Test that reset tokens are stored as SHA-256 hashes."""
    # Request password reset
    response = authenticated_client.post(
        "/admin/forgot-password",
        data={"identifier": "admin"}
    )

    # Check that reset_token in DB is a 64-char hex string (SHA-256)
    from app.models import User
    user = db.session.execute(select(User)).scalar_one()
    assert user.reset_token is not None
    assert len(user.reset_token) == 64  # SHA-256 hex digest
    # Verify it's a valid hex string
    int(user.reset_token, 16)  # Should not raise ValueError
```

---

## Rollback Plan

If any change causes issues:

1. **API Timing Fix**: Revert `app/routes/api.py` to use `!=` (not recommended, but possible)

2. **Backup Integrity**:
   - Remove import of `app.backup_integrity`
   - Revert `backup.py` and `app/routes/admin/backup.py` to original

3. **Password Reset Token**:
   - Revert `app/routes/admin/auth.py` to store plaintext
   - Note: Users with hashed tokens in DB will need to request new resets

---

## Success Criteria

- [ ] API key timing attack eliminated (verified via code review)
- [ ] Backup integrity verification prevents corrupted/malicious restores
- [ ] Password reset tokens are hashed in database
- [ ] All changes pass existing 487 unit tests
- [ ] No new external dependencies added (uses Python stdlib)
- [ ] Rate limiting remains at reverse proxy level (no Flask-Limiter added)
- [ ] API remains internal admin only (no role-based keys added)

---

## Notes

- This plan respects the project's philosophy of minimal dependencies and reverse-proxy security
- All fixes use Python standard library (no new pip packages required)
- Changes are backward compatible where possible (e.g., old backups without checksums can still be restored)
- The plan can be executed in phases, with critical fixes first
