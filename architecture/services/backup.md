# Backup Service (`app/services/backup.py`)

Unified backup service for CLI, scheduler, and cron jobs.

## Features

- **Compression**: Gzip compression support
- **Encryption**: AES-256-GCM encryption with PBKDF2 key derivation (not GPG)
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
| `encrypt` | `bool` | `False` | AES-256-GCM encryption |

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

Scheduler-friendly daily backup function used by APScheduler.
- **Naming**: Uses `blog_*.db` pattern (same as Celery task)
- **No encryption/compression**: For encrypted/compressed backups, use Celery task `run_backup_task`

## Dual Backup Implementations

This service provides two distinct backup implementations:

| Aspect | `create_backup()` (Celery) | `run_daily_backup()` (APScheduler) |
|--------|---------------------------|----------------------------------|
| Trigger | Celery task `run_backup_task` | APScheduler job at 02:00 |
| Naming | `blog_YYYYMMDD_HHMMSS.db` | `blog_YYYYMMDD_HHMMSS.db` |
| Encryption | AES-256-GCM with PBKDF2 | None |
| Compression | Optional gzip | None |
| Use case | On-demand encrypted backups | Scheduled daily backups |

The APScheduler backup uses `blog_*.db` naming (since F.2) and `cleanup_old_backups()` cleans `blog_*.db` files.

### `decrypt_backup_file()`

```python
def decrypt_backup_file(input_path: str, output_path: Optional[str] = None) -> bool
```

Decrypts an AES-256-GCM-encrypted backup file.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `input_path` | `str` | required | Path to encrypted backup file |
| `output_path` | `str` | `None` | Output path (defaults to input_path without `.gpg`) |

**Returns:** `True` on success, `False` on failure

## Backup File Naming

```
blog_YYYYMMDD_HHMMSS.db       # Plain
blog_YYYYMMDD_HHMMSS.db.gz     # Compressed
blog_YYYYMMDD_HHMMSS.db.gpg    # Encrypted
```

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
