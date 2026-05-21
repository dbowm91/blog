# Serialization Service (`app/services/serialization.py`)

JSON export/import for blog data.

## Functions

| Function | Description |
|----------|-------------|
| `serialize_post(post)` | Serialize Post to dict (title, slug, body, summary, image, dates, tags) |
| `serialize_subscriber(subscriber, include_email=False)` | Serialize Subscriber (id, confirmed, dates, optional email) |
| `serialize_page(page)` | Serialize Page to dict |
| `serialize_tag(tag)` | Serialize Tag to dict (name, slug) |
| `export_data_to_dict(posts, subscribers, tags, pages, version=1)` | Export all data to dict |

## Import

Import is handled via `app/cli.py:import_data_command` (CLI command `import-data`).

## See Also
- [Backup Service](services/backup.md) - Database backups
