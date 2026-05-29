# Backup Service (`app/services/backup.py`)

Unified backup service for CLI, scheduler, and cron jobs.

## Features

- **Compression**: Gzip compression support
- **Encryption**: AES-256-GCM encryption with PBKDF2 key derivation (600,000 iterations)
- **Retention**: Configurable backup retention (default: 7)
- **API**: Uses SQLite's native `backup()` API for consistency

## Core Functions

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

### `cleanup_old_backups()`

```python
def cleanup_old_backups(backup_dir: str, keep: int) -> None
```

Removes old backups, keeping only the most recent `keep` backups.

### `run_daily_backup()`

```python
def run_daily_backup(app: Any) -> None
```

Service-level daily backup designed for scheduler and CLI use. Unlike `create_backup()`, this does **not** support compression or encryption — use the Celery task `run_backup_task` for encrypted/compressed backups.

**Behavior:**
- Uses `sqlite3.backup()` for WAL mode consistency
- Naming pattern: `blog_YYYYMMDD_HHMMSS.db`
- Retention: 7 backups (via `BACKUP_RETENTION_COUNT`)
- Reads `DATA_BACKUP_DIR` from config for backup directory

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
- **Min password**: 12 characters (`BACKUP_ENCRYPTION_KEY` env var)
- **File format**: `salt(16) + nonce(12) + ciphertext + tag(16)`
- **Functions**: `encrypt_backup()`, `decrypt_backup()`, `encrypt_backup_file()`, `decrypt_backup_file()`, `is_encryption_available()`

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