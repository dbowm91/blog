# Scripts Agent Override

Specialized handling for shell scripts and DevOps automation.

## Key Scripts

- `dev.sh` - Development environment setup script
- `sync_backups.sh` - Off-site backup sync script (rclone/S3)

## Development Setup

```bash
./scripts/dev.sh
```

## Backup Sync

The `sync_backups.sh` script uses rclone to sync backups to S3 or other storage backends.