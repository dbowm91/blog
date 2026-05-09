# Services Architecture Review

## Backup Service (`app/services/backup.py`)

### Verified Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| Compression (gzip) | ✅ Verified | `app/services/backup.py:68-78` |
| AES-256-GCM encryption | ✅ Verified | `app/backup_encryption.py:91-134` uses AES-256-GCM with PBKDF2 (600k iterations) |
| Retention policy (default 7) | ✅ Verified | `app/services/backup.py:21` `BACKUP_RETENTION_COUNT = 7` |
| Uses SQLite `backup()` API | ✅ Verified | `app/services/backup.py:57` `source.backup(dest)` |
| `blog_*.db` naming for `create_backup()` | ✅ Verified | `app/services/backup.py:45` |

### Discrepancies

**1. `run_daily_backup()` naming convention not documented**

The doc shows `run_daily_backup()` in the API reference, but fails to document that it uses `backup_*.db` naming (not `blog_*.db`).

**Evidence:**
- `app/services/backup.py:166-167`: Uses `f"backup_{timestamp}.db"`
- `app/services/backup.py:149-154`: Docstring explicitly states different naming

**2. Two separate backup implementations not documented**

The architecture doc only covers `app/services/backup.py`, but doesn't explain:
- `create_backup()` - Used by Celery task, supports encryption/compression, `blog_*.db` naming
- `run_daily_backup()` - Used by APScheduler, no encryption/compression, `backup_*.db` naming

**3. `cleanup_old_backups()` only cleans `blog_*` files**

**Bug:** `app/services/backup.py:132-133` filters with `f.startswith("blog_")` but `run_daily_backup()` creates `backup_*.db` files. Result: APScheduler backups are never cleaned up by retention policy.

**4. Encryption documentation error**

`backup.md:8` states "AES-256-GCM encryption with PBKDF2 key derivation (not GPG)" but then `backup.md:33` table says `encrypt` parameter is "GPG encryption". The code uses **AES-256-GCM**, not GPG.

---

## Serialization Service (`app/services/serialization.py`)

### Verified Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| Export posts, subscribers, pages, tags | ✅ Verified | `app/services/serialization.py:77-86` |
| Batch processing | ✅ Verified | Functions accept `Sequence[]` types |

### Discrepancies

None significant. Documentation is sparse but accurate.

---

## Slug Service (`app/services/slug.py`)

### Verified Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| URL-safe slug generation | ✅ Verified | `app/services/slug.py:29` calls `generate_slug()` |
| Collision detection | ✅ Verified | `app/services/slug.py:32-39` loop with counter |
| Suffix enumeration | ✅ Verified | `app/services/slug.py:38` `f"{base_slug}-{counter}"` |
| UUID fallback at 100 tries | ✅ Verified | `app/services/slug.py:40-41` |

### Discrepancies

None. Documentation is minimal but accurate.

---

## Tag Service (`app/services/tag.py`)

### Verified Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| Create, read, delete tags | ✅ Verified | `get_or_create_tags`, `get_tag_by_slug`, `get_all_tags`, `delete_tag_if_unused` |
| Post count queries | ✅ Verified | `app/services/tag.py:48-55` |
| Slug generation | ✅ Verified | `app/services/tag.py:23` calls `generate_slug()` |

### Discrepancies

None. Documentation is accurate.

---

## Bugs Found

### Bug 1: APScheduler backup retention never executes

**File:** `app/services/backup.py:132-133`

```python
if f.startswith("blog_") and (f.endswith(".db") or f.endswith(".db.gz") or f.endswith(".db.gpg")):
```

`run_daily_backup()` creates `backup_*.db` files which don't match `blog_` prefix, so `cleanup_old_backups()` never removes them. Backup directory grows indefinitely.

**Fix:** Either:
1. Change `cleanup_old_backups()` to also match `backup_*.db` files
2. Or change `run_daily_backup()` to use `blog_*.db` naming (breaking change for existing installs)

---

### Bug 2: Documentation claims GPG encryption but code uses AES-256-GCM

**File:** `architecture/services/backup.md:33`

The `encrypt` parameter description says "GPG encryption" but `app/backup_encryption.py` uses **AES-256-GCM** with PBKDF2. This is contradictory.

---

## Recommendations

### 1. Document dual backup implementations
**File:** `architecture/services/backup.md`

Add section explaining:
- `create_backup()` for Celery tasks with encryption/compression
- `run_daily_backup()` for APScheduler without encryption/compression
- Different naming conventions (`blog_*` vs `backup_*`)

### 2. Fix APScheduler backup retention
**File:** `app/services/backup.py:132-133`

Replace hardcoded `blog_` prefix check with a pattern that matches both naming conventions, or standardize on one naming scheme.

### 3. Correct encryption documentation
**File:** `architecture/services/backup.md:8,33`

Change "GPG encryption" to "AES-256-GCM encryption with PBKDF2 key derivation" for consistency with actual implementation.

### 4. Add `run_daily_backup()` to scheduler documentation cross-reference
**File:** `architecture/services/backup.md:101`

The "See Also" references APScheduler but doesn't mention the naming difference.

---

## Summary

| Service | Docs Accuracy | Notes |
|---------|---------------|-------|
| Backup | ⚠️ Partial | Missing dual implementation details, cleanup bug, encryption type contradiction |
| Serialization | ✅ Verified | Accurate but sparse |
| Slug | ✅ Verified | Accurate but sparse |
| Tag | ✅ Verified | Accurate but sparse |

**Critical bug:** APScheduler backup retention is non-functional due to filename prefix mismatch.
