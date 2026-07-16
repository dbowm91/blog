# Scripts Agent Override

Specialized handling for shell scripts and DevOps automation.

## Key Scripts

- `install.sh` — One-shot native/Docker installer for production
- `setup-dev.sh` — Development environment setup (formerly `setup.sh` at repo root)
- `release_check.sh` — Release validation (lint, typecheck, tests, build, Docker, Compose)
- `generate_checksums.py` — Generate SHA-256 checksums for release artifacts
- `check_release_artifacts.py` — Verify wheel contents and checksums
- `sync_backups.sh` — Off-site backup sync (rclone/S3)
- `dev.sh` — Legacy development setup (use `setup-dev.sh` instead)

## Development Setup

```bash
./scripts/setup-dev.sh
```

## Installer

```bash
# Native install
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --native

# Docker install
curl -fsSL https://raw.githubusercontent.com/dbowm91/blog/main/scripts/install.sh | bash -s -- --docker
```

## Backup Sync

The `sync_backups.sh` script uses rclone to sync backups to S3 or other storage backends.
