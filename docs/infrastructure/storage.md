# Storage Infrastructure

## Image Storage Backend

The blog uses a pluggable storage backend system for handling media uploads:

- **LocalStorageBackend**: Stores files on the local filesystem under `app/static/uploads/`
- **S3StorageBackend**: Stores files in S3-compatible object storage

## Responsive Image Variants

The system generates responsive image variants for uploaded images:

- 400w, 800w, 1200w width variants
- WebP format for all variants
- Original format preservation (JPEG, PNG, etc.)

## AVIF Support

AVIF variant generation is **planned but not yet implemented**.

The `post_image_avif_url_stub` filter currently returns `None`. To enable AVIF support:

1. Implement AVIF encoding in `generate_image_variants()` task
2. Add AVIF file generation alongside WebP variants
3. Update the `post_image_avif_url_stub` filter to return the actual URL

## Upload Configuration

- Maximum upload size: 10MB (configurable via `max_upload_size`)
- Maximum files per upload batch: 1000 (configurable via `media_max_files`)
- Supported formats: JPEG, PNG, GIF, WebP

## S3 Configuration

The S3 storage backend reads configuration from environment variables, NOT from config files:

| Variable | Description |
|----------|-------------|
| `S3_BUCKET` | S3 bucket name |
| `S3_REGION` | AWS region |
| `S3_ENDPOINT` | S3 endpoint URL (for S3-compatible services) |
| `S3_ACCESS_KEY` | AWS access key |
| `S3_SECRET_KEY` | AWS secret key |
| `S3_PUBLIC_URL` | Public URL for serving files |

From `app/storage.py:41`:
```python
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
S3_PUBLIC_URL = os.environ.get("S3_PUBLIC_URL")
```

## Backup Filename Validation

Database backups must match the pattern `blog_\d{8}_\d{6}\.db(\.gz)?(\.gpg)?` to prevent path traversal attacks.

The regex `BACKUP_FILENAME_RE` in `app/routes/admin/helpers/shared.py:14` validates all backup filenames:

```python
BACKUP_FILENAME_RE = re.compile(r"^blog_\d{8}_\d{6}\.db(\.gz)?(\.gpg)?$")
```

This validation is applied at:
- `app/routes/admin/backup.py:95`
- `app/routes/admin/backup.py:120`
- `app/routes/admin/backup.py:182`
- `app/routes/admin/backup.py:213`