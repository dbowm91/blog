# Backup Service (`app/services/backup.py`)

Unified backup service for CLI, scheduler, and cron jobs.

## Features

- **Compression**: Gzip compression support
- **Encryption**: AES-256-GCM encryption with PBKDF2 key derivation (600,000 iterations)
- **Retention**: Configurable backup retention (default: 7)
- **API**: Uses SQLite's native `backup()` API for consistency

## Core Functions

### `resolve_database_file()` and `resolve_backup_dir()`

```python
def resolve_database_file(app: Any) -> str | None
def resolve_backup_dir(app: Any) -> str
```

The single authority for the two data paths. `resolve_database_file()` reads the
live `SQLALCHEMY_DATABASE_URI` (which `create_app()` sets from
`cfg.database.uri`, i.e. `<data_dir>/devlog.sqlite3`) and returns the SQLite
file, or `None` when the backend is not SQLite. `resolve_backup_dir()` resolves
`backup.data_backup_dir` — absolute as configured, otherwise relative to the
directory holding the database, so backups land beside the database.

Every producer and consumer uses these: the admin backup routes
(`_resolve_database_path()`, `_get_backup_dir()` in
`app/routes/admin/helpers/shared.py`), the operational service in
`app/services/operations/backup.py`, the Celery task in `app/tasks.py`, the
scheduled job, and the `/health` backup-freshness check. Never derive either
path independently — that is what previously made the admin UI and the
scheduled job act on different files.

### `create_backup()`

```python
def create_backup(
    db_path: str,
    backup_dir: str,
    compress: bool = False,
    keep: int = 7,
    encrypt: bool = False
) -> Optional[str]:
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `db_path` | `str` | required | Path to source database |
| `backup_dir` | `str` | required | Backup directory |
| `compress` | `bool` | `False` | Gzip compression |
| `keep` | `int` | `7` | Retention count |
| `encrypt` | `bool` | `False` | AES-256-GCM encryption with PBKDF2-HMAC-SHA256 key derivation |

**Returns:** Path to backup file or `None` on failure

**Parameter Mutual Exclusivity:** The `compress` and `encrypt` parameters are mutually exclusive in the implementation. When `encrypt=True`, compression is skipped — the code uses `elif compress:` (`app/services/backup.py:72`), meaning only one operation is applied. If both are `True`, encryption takes precedence and compression is ignored.

### `cleanup_old_backups()`

```python
def cleanup_old_backups(backup_dir: str, keep: int) -> None
```

Removes old backups, keeping only the most recent `keep` backups.

### `run_daily_backup()`

```python
def run_daily_backup(app: Any) -> None
```

Service-level daily backup designed for scheduler and CLI use. **Creates plain (unencrypted) backups only.** Unlike `create_backup()`, this does **not** support compression or encryption — use the Celery task `run_backup_task` for encrypted/compressed backups.

**Behavior:**
- Creates plain `.db` backups (no encryption, no compression)
- `create_backup()` deletes the unencrypted file and fails if encryption fails (error logged)
- `run_daily_backup()` does NOT support encryption or compression

### Backup Type Summary

| Function | Backup Type | Encryption | Compression |
|----------|-------------|------------|-------------|
| `run_daily_backup()` | Plain `.db` | No | No |
| `create_backup(encrypt=True)` | Encrypted `.db.gpg` | AES-256-GCM | No |
| `create_backup(compress=True)` | Compressed `.db.gz` | No | Gzip |
| `run_backup_task` (Celery) | Plain `.db` | No | Gzip |

## Encryption Behavior

When `encrypt=True` is passed to `create_backup()`:

1. Backup is created as unencrypted `.db` file
2. `_encrypt_backup_file()` is called to encrypt in-place
3. If encryption fails (key not loadable, cryptography library missing, or other error), the unencrypted file is **removed**, `create_backup()` returns `None`, and an error is logged
4. Backup creation DOES fail on encryption errors — no unencrypted backup is left on disk

**Note:** If `BACKUP_ENCRYPTION_KEY` is set but cannot be loaded, `_encrypt_backup_file()`
logs a warning and returns `False`; `create_backup()` then removes the plain file and logs
`Backup encryption failed, discarding unencrypted backup`. Encryption therefore never
degrades silently to an unencrypted backup.

### `decrypt_backup_file()`

```python
def decrypt_backup_file(input_path: str, output_path: Optional[str] = None) -> bool
```

Decrypts an AES-256-GCM-encrypted backup file.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `input_path` | `str` | required | Path to encrypted backup file |
| `output_path` | `str` | `None` | Output path. **Default behavior**: for `.gpg` files (AES-256-GCM encrypted) removes `.gpg` extension; for non-`.gpg` files appends `.decrypted` suffix (e.g., `backup.db.enc` → `backup.db.enc.decrypted`) |

**Returns:** `True` on success, `False` on failure

## Encryption Modules

Three separate encryption modules exist with different key derivation strategies:

### `app/backup_encryption.py` — Backup Encryption

- **Key derivation**: PBKDF2-HMAC-SHA256, 600,000 iterations (NIST SP 800-132)
- **Salt**: 16-byte random salt per encryption
- **Key size**: 32 bytes (AES-256)
- **Nonce**: 12 bytes (AES-GCM recommended)
- **Cipher**: AES-256-GCM (authenticated encryption)
- **Min password**: 12 characters
- **Key source**: `BACKUP_ENCRYPTION_KEY` environment variable only
- **File format**: `salt(16) + nonce(12) + ciphertext + tag(16)`
- **Functions**: `encrypt_backup()`, `decrypt_backup()`, `encrypt_backup_file()`, `decrypt_backup_file()`, `is_encryption_available()`

### Key Configuration

The backup encryption key is loaded from the `BACKUP_ENCRYPTION_KEY` environment variable only. If the key is set but cannot be loaded (cryptography library unavailable or key validation fails), the encryption attempt fails and the plain backup is discarded rather than kept.

### `app/services/encryption.py` — TOTP Secret Encryption

- **Key derivation**: None (direct key from `SECRET_KEY` config)
- **Key handling**: Encodes `SECRET_KEY` as UTF-8, pads/truncates to 32 bytes
- **Cipher**: AES-256-GCM via `AESGCM` (cryptography library)
- **Output**: Base64-encoded `nonce(12) + ciphertext + tag`
- **Used for**: Encrypting TOTP secrets at rest

### `app/webhook_encryption.py` — Webhook Secret Encryption

- **Key derivation**: None (direct 32-byte key from `WEBHOOK_ENCRYPTION_KEY`)
- **Key format**: Accepts 32-byte raw string or 64-character hex string
- **Cipher**: AES-256-GCM via `AESGCM` (cryptography library)
- **Output**: Base64-encoded `nonce(12) + ciphertext + tag`
- **Used for**: Encrypting webhook secrets at rest

## Backup File Naming

```
blog_YYYYMMDD_HHMMSS.db       # Plain
blog_YYYYMMDD_HHMMSS.db.gz     # Compressed (create_backup with compress=True)
blog_YYYYMMDD_HHMMSS.db.gpg    # Encrypted with AES-256-GCM (create_backup with encrypt=True)
```

**Note:** The `.gpg` extension is historical. Backup encryption uses AES-256-GCM via `app/backup_encryption.py`, not GPG/PGP.

## Retention Policy

Default: Keep 7 most recent backups.

## Usage

### CLI
```bash
python backup.py
```

### Celery Task
```python
from app.tasks import run_backup_task
run_backup_task.delay()
```

### Direct Call
```python
from app.services.backup import create_backup
backup_path = create_backup("/path/to/blog.db", "/backups", compress=True)
```

## See Also
- [APScheduler](../tasks/scheduler.md) - Scheduled backups (`run_daily_backup()` at `app/scheduler.py:262`)
- [Celery Tasks](../tasks/celery-tasks.md) - Async task queue