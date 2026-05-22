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

APScheduler-friendly daily backup function.
- **Naming**: Uses `blog_*.db` pattern (same as `create_backup()`)
- **No encryption/compression**: Plain SQLite backup
- **Retention**: Same pattern, managed by `cleanup_old_backups()` which handles `blog_*.db` files

**Note**: Both `run_daily_backup()` and `create_backup()` use `blog_*.db` naming. `cleanup_old_backups()` handles retention for both.

## Dual Backup Implementations

This service provides two distinct backup implementations:

| Aspect | `create_backup()` (Celery) | `run_daily_backup()` (APScheduler) |
|--------|---------------------------|----------------------------------|
| Trigger | Celery task `run_backup_task` | APScheduler job at 02:00 |
| Creates | `blog_YYYYMMDD_HHMMSS.db` | `blog_YYYYMMDD_HHMMSS.db` |
| Manages retention | Via `cleanup_old_backups()` | Via `cleanup_old_backups()` |
| Encryption | AES-256-GCM with PBKDF2 | None |
| Compression | Optional gzip | None |
| Use case | On-demand encrypted backups | Scheduled daily backups |

### `decrypt_backup_file()`

```python
def decrypt_backup_file(input_path: str, output_path: Optional[str] = None) -> bool
```

Decrypts an AES-256-GCM-encrypted backup file.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `input_path` | `str` | required | Path to encrypted backup file |
| `output_path` | `str` | `None` | Output path (for `.gpg` files: removes `.gpg`; for others: appends `.decrypted`) |

**Returns:** `True` on success, `False` on failure

## Backup File Naming

```
blog_YYYYMMDD_HHMMSS.db       # Plain (both create_backup and run_daily_backup)
blog_YYYYMMDD_HHMMSS.db.gz     # Compressed (create_backup with compress=True)
blog_YYYYMMDD_HHMMSS.db.gpg    # Encrypted (create_backup with encrypt=True)
```

**Note**: Both `create_backup()` and `run_daily_backup()` use `blog_*.db` naming. The extension varies based on compression/encryption.

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
- [APScheduler](../tasks/scheduler.md) - Scheduled backups
- [Celery Tasks](../tasks/celery-tasks.md) - Async task queue
