# Admin Routes

## Authentication

All admin routes require authentication via session cookie. Some routes have additional rate limits.

---

## Post Editor Routes

### POST /admin/preview-markdown

Render markdown preview for live editing. Used by the admin editor to preview markdown before saving.

**Location:** `app/routes/admin/posts/editor.py:328`

**Authentication:** Admin required

**Request Body:**
```json
{
  "text": "# Markdown content to preview"
}
```

**Response:**
```json
{
  "html": "<h1>Markdown content to preview</h1>"
}
```

**Constraints:**
- Maximum payload size: 1MB
- Returns 413 if payload too large

---

## Series Routes

### POST /admin/series/<int:series_id>/reorder

Update the order of posts in a series via AJAX.

**Location:** `app/routes/admin/series.py:259`

**Authentication:** Admin required

**Request Body:**
```json
{
  "post_ids": [3, 1, 2]
}
```

**Response:**
```json
{
  "success": true
}
```

---

## Tag Routes

### POST /admin/tags/delete/<id>

Delete a tag. Note: Uses POST method, not DELETE.

**Location:** `app/routes/admin/tags.py:87`

**Authentication:** Admin required

---

## Series Delete

### POST /admin/series/<id>/delete

Delete a series and its post associations. Note: Uses POST method, not DELETE.

**Location:** `app/routes/admin/series.py:132`

**Authentication:** Admin required

---

## Backup Filename Validation

Backups must match pattern `blog_\d{8}_\d{6}\.db(\.gz)?` to prevent path traversal attacks.

The regex `BACKUP_FILENAME_RE` in `app/routes/admin/helpers/shared.py` validates all backup filenames.

**Locations:**
- `app/routes/admin/backup.py:95`
- `app/routes/admin/backup.py:120`
- `app/routes/admin/backup.py:182`
- `app/routes/admin/backup.py:213`