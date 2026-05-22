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