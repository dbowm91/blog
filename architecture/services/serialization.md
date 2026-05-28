# Serialization Service (`app/services/serialization.py`)

JSON export/import for blog data.

## Functions

| Function | Description |
|----------|-------------|
| `serialize_post(post)` | Serialize Post to dict: `title`, `slug`, `body`, `summary`, `image`, `created_at`, `updated_at`, `published`, `published_at`, `scheduled_publish_at`, `tags` |
| `serialize_subscriber(subscriber, include_email=False)` | Serialize Subscriber to dict: `id`, `confirmed`, `created_at`, `expires_at`, `unsubscribed_at`; optionally includes `email` when `include_email=True` |
| `serialize_page(page)` | Serialize Page to dict: `title`, `slug`, `body`, `created_at`, `updated_at`, `published` |
| `serialize_tag(tag)` | Serialize Tag to dict: `name`, `slug` |
| `export_data_to_dict(posts, subscribers, tags, pages, version=1)` | Export all data to dict |

## Import

No `deserialize_*` functions exist in the serialization module. Import is handled inline in the CLI `import-data` command (`app/cli.py:140`). The `import_data_command` function reads JSON, validates version, and creates model instances directly (tags first, then posts with tag associations, subscribers, and pages). Skips existing records by slug/email lookup.

## See Also
- [Backup Service](services/backup.md) - Database backups
