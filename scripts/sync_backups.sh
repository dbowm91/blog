#!/usr/bin/env bash
# Off-site Backup Sync Script
#
# Syncs local backups to remote storage (S3, rclone-compatible, etc.)
# Supports both Amazon S3 and any rclone-supported remote storage.
#
# Usage:
#   ./scripts/sync_backups.sh                    # Interactive mode
#   ./scripts/sync_backups.sh --dry-run         # Preview changes
#   ./scripts/sync_backups.sh --verify          # Verify after sync
#   ./scripts/sync_backups.sh --cleanup 7       # Keep only last 7 local backups
#
# Environment Variables:
#   BACKUP_DIR         Local backup directory (default: ./backups)
#   REMOTE_TYPE        Remote type: "s3" or "rclone"
#   RCLONE_REMOTE      Rclone remote name (e.g., "s3:my-bucket/backups")
#   AWS_S3_BUCKET      S3 bucket name (for native S3)
#   AWS_ACCESS_KEY_ID  AWS access key
#   AWS_SECRET_ACCESS_KEY  AWS secret key
#   AWS_REGION         S3 region (default: us-east-1)
#   RETENTION_DAYS     Local backup retention in days (default: 7)
#   RCLONE_CONFIG      Path to rclone.conf (default: ~/.config/rclone/rclone.conf)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DRY_RUN=""
VERIFY_AFTER=""
CLEANUP_LOCAL=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Sync local backups to off-site storage.

OPTIONS:
    --dry-run         Preview changes without syncing
    --verify          Verify backups after sync
    --cleanup DAYS    Remove local backups older than DAYS (default: 7)
    --help            Show this help message

ENVIRONMENT:
    BACKUP_DIR         Local backup directory (default: ./backups)
    REMOTE_TYPE        Remote type: "s3" or "rclone" (default: rclone)
    RCLONE_REMOTE      Rclone remote name (e.g., "s3:my-bucket/backups")
    AWS_S3_BUCKET      S3 bucket name (for native S3)
    AWS_ACCESS_KEY_ID  AWS access key
    AWS_SECRET_ACCESS_KEY  AWS secret key
    AWS_REGION         S3 region (default: us-east-1)
    RETENTION_DAYS     Local backup retention in days (default: 7)
    RCLONE_CONFIG      Path to rclone.conf (default: ~/.config/rclone/rclone.conf)

EXAMPLES:
    # Sync with rclone to S3
    export RCLONE_REMOTE="s3:my-backups/blog"
    ./scripts/sync_backups.sh

    # Sync with rclone to Google Drive
    export RCLONE_REMOTE="gdrive:backups/blog"
    ./scripts/sync_backups.sh --dry-run --verify

    # Native AWS CLI to S3
    export REMOTE_TYPE="s3"
    export AWS_S3_BUCKET="my-backups"
    ./scripts/sync_backups.sh --cleanup 14

EOF
    exit 0
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --verify)
            VERIFY_AFTER="1"
            shift
            ;;
        --cleanup)
            CLEANUP_LOCAL="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ ! -d "$BACKUP_DIR" ]]; then
    error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

BACKUP_COUNT=$(find "$BACKUP_DIR" -name "blog_*.db*" -type f | wc -l)
if [[ $BACKUP_COUNT -eq 0 ]]; then
    error "No backups found in $BACKUP_DIR"
    exit 1
fi

log "Found $BACKUP_COUNT backup(s) in $BACKUP_DIR"

REMOTE_TYPE="${REMOTE_TYPE:-rclone}"

do_sync_rclone() {
    local remote="$1"
    local rclone_config="${RCLONE_CONFIG:-}"

    if [[ -z "$remote" ]]; then
        error "RCLONE_REMOTE not set"
        return 1
    fi

    local rclone_cmd="rclone"
    if [[ -n "$rclone_config" ]]; then
        rclone_cmd="rclone --config $rclone_config"
    fi

    log "Syncing to rclone remote: $remote"

    if [[ -n "$DRY_RUN" ]]; then
        log "DRY RUN - showing what would be synced:"
        eval "$rclone_cmd sync $BACKUP_DIR $remote --include 'blog_*.db*' -vv 2>&1" || true
    else
        eval "$rclone_cmd sync $BACKUP_DIR $remote --include 'blog_*.db*' 2>&1"
        log "Sync completed successfully"
    fi

    if [[ -n "$VERIFY_AFTER" ]]; then
        log "Verifying remote backups..."
        eval "$rclone_cmd ls $remote --include 'blog_*.db*' 2>&1" || true
    fi
}

do_sync_s3() {
    local bucket="$1"
    local region="${AWS_REGION:-us-east-1}"

    if [[ -z "$AWS_ACCESS_KEY_ID" ]] || [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
        error "AWS credentials not set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
        return 1
    fi

    log "Syncing to S3 bucket: s3://$bucket (region: $region)"

    if [[ -n "$DRY_RUN" ]]; then
        log "DRY RUN - showing what would be synced:"
        aws s3 sync "$BACKUP_DIR" "s3://$bucket" \
            --exclude "*" \
            --include "blog_*.db*" \
            --region "$region" \
            --dryrun 2>&1 || true
    else
        aws s3 sync "$BACKUP_DIR" "s3://$bucket" \
            --exclude "*" \
            --include "blog_*.db*" \
            --region "$region" \
            --sse AES256 2>&1
        log "Sync completed successfully"
    fi

    if [[ -n "$VERIFY_AFTER" ]]; then
        log "Verifying S3 backups..."
        aws s3 ls "s3://$bucket" --region "$region" 2>&1 || true
    fi
}

case "$REMOTE_TYPE" in
    s3)
        if [[ -z "${AWS_S3_BUCKET:-}" ]]; then
            error "AWS_S3_BUCKET not set"
            exit 1
        fi
        do_sync_s3 "$AWS_S3_BUCKET"
        ;;
    rclone|*)
        if [[ -z "${RCLONE_REMOTE:-}" ]]; then
            error "RCLONE_REMOTE not set"
            exit 1
        fi
        do_sync_rclone "$RCLONE_REMOTE"
        ;;
esac

if [[ -n "$CLEANUP_LOCAL" ]]; then
    log "Cleaning up local backups older than $CLEANUP_LOCAL days..."
    if [[ -n "$DRY_RUN" ]]; then
        find "$BACKUP_DIR" -name "blog_*.db*" -type f -mtime "+$CLEANUP_LOCAL" -ls 2>&1 || true
    else
        deleted=$(find "$BACKUP_DIR" -name "blog_*.db*" -type f -mtime "+$CLEANUP_LOCAL" -delete -print 2>&1 | wc -l)
        log "Deleted $deleted old backup(s)"
    fi
fi

log "Backup sync completed"
