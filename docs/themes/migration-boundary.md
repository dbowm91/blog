# Halloy Theme Migration Boundary and Rollback Guide

## Supported Upgrade Boundary

The Halloy theme migration applies three sequential Alembic revisions to `site_settings`:

| Revision | Purpose | down_revision |
|----------|---------|---------------|
| `add_theme_config_to_sitesettings` | Adds `theme_dark_name`, `theme_light_name`, `theme_default_scheme` columns; maps legacy presets to Halloy names | `3328a74db69b` |
| `preserve_legacy_scheme` | Corrects `theme_default_scheme` from `system` to `dark`/`light` for known dark/light presets | `add_theme_config_to_sitesettings` |
| `drop_theme_preset_column` | Removes the legacy `theme_preset` column | `add_comment_spam_fields`, `add_missing_indexes`, `preserve_legacy_scheme` |

### Oldest Supported Revision

The supported upgrade boundary is revision `3328a74db69b`, which is the revision immediately before `add_theme_config_to_sitesettings`. Any database at this revision or later can be upgraded through the full Halloy chain.

The `drop_theme_preset_column` revision has a 3-way merge (`add_comment_spam_fields`, `add_missing_indexes`, `preserve_legacy_scheme`). All three parent revisions must be applied before the drop can proceed. This is a standard Alembic merge head — not a branch conflict.

### Revision Chain

```
3328a74db69b
    └── add_theme_config_to_sitesettings
            └── preserve_legacy_scheme
                    └── drop_theme_preset_column
                            (merge of add_comment_spam_fields, add_missing_indexes, preserve_legacy_scheme)
```

### Supported Databases

- **SQLite**: Fully supported. All migrations use `batch_alter_table` for SQLite-safe DDL. This is the default and recommended database.
- **PostgreSQL**: Not currently supported by deployment documentation or Docker configuration. The application uses SQLite-specific FTS5 for full-text search and WAL mode. While the Alembic migrations themselves are dialect-neutral, the application has not been tested or documented for PostgreSQL production use. The `PostgreSQLSearchProvider` in `app/services/search/postgresql.py` is a stub for future use.

## Upgrade Procedure

### Pre-Upgrade Backup

Always back up the database before upgrading:

```bash
# SQLite
cp data/devlog.sqlite3 data/devlog.sqlite3.pre-halloy-backup

# Or use the built-in backup command
devlog backup create
```

### Upgrade Command

```bash
flask db upgrade
```

This applies all pending migrations including the three Halloy theme revisions.

### Post-Upgrade Verification

```bash
# Verify theme columns exist
flask shell
>>> from app.models import SiteSettings
>>> s = SiteSettings.get_instance()
>>> print(f'Dark: {s.theme_dark_name}')
>>> print(f'Light: {s.theme_light_name}')
>>> print(f'Scheme: {s.theme_default_scheme}')

# Verify theme_preset column is gone
>>> import sqlalchemy as sa
>>> from app.extensions import db
>>> insp = sa.inspect(db.engine)
>>> cols = {c['name'] for c in insp.get_columns('site_settings')}
>>> assert 'theme_preset' not in cols, 'theme_preset still exists!'
>>> assert 'theme_dark_name' in cols, 'theme_dark_name missing!'
>>> print('OK: migration verified')

# Verify theme system works
flask themes list
flask themes accessibility --strict
```

### Expected Columns After Upgrade

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `theme_dark_name` | `String(128)` | `Catppuccin Mocha` | Dark theme name in Halloy registry |
| `theme_light_name` | `String(128)` | `Catppuccin Latte` | Light theme name in Halloy registry |
| `theme_default_scheme` | `String(16)` | `system` | `system`, `dark`, or `light` |

The `theme_preset` column is removed. The `syntax_theme`, `custom_css_enabled`, `custom_css`, and `logo_text` columns are unchanged.

## Rollback Procedure

### Downgrade Limitations

The downgrade path restores the `theme_preset` column but **does not** restore the original preset-to-Halloy name mapping. After downgrade:

1. `theme_preset` is restored with `server_default='github-dark'`
2. `theme_dark_name`, `theme_light_name`, `theme_default_scheme` columns remain (they are not removed by downgrade)
3. The application continues to use Halloy theme names — the restored `theme_preset` column is ignored at runtime

### Downgrade Command

```bash
# Downgrade one step (restores theme_preset column)
flask db downgrade -1

# Downgrade to before Halloy (removes all Halloy columns)
flask db downgrade 3328a74db69b
```

### What Happens on Downgrade

| Step | Effect |
|------|--------|
| Downgrade from `drop_theme_preset_column` | Restores `theme_preset` column with default `github-dark`. Halloy columns remain. |
| Downgrade from `preserve_legacy_scheme` | Reverts `theme_default_scheme` to `system` for affected rows. |
| Downgrade from `add_theme_config_to_sitesettings` | Drops `theme_dark_name`, `theme_light_name`, `theme_default_scheme`. Application falls back to legacy preset system (if `THEME_PRESETS` is present in code). |

**Important**: If downgrading past `add_theme_config_to_sitesettings`, ensure the application code still contains `THEME_PRESETS` (removed in Phase 14). A full rollback to the legacy preset system requires both the database downgrade and a code rollback to a pre-Phase-14 version.

## Recovery: Unavailable Selected Theme After Upgrade

If an external theme that was previously selected is no longer available after upgrade:

1. The application renders with `EMERGENCY_DEFAULT` (the GitHub Dark palette)
2. Check the application logs for theme resolution warnings
3. Restore the missing `.toml` file to the external themes directory
4. Run `flask themes refresh` to re-scan
5. Or select a different theme via `/admin/settings`

The emergency fallback is safe and renders a complete CSS variable set. No page will fail to render due to a missing theme.

## See Also

- [Legacy compatibility](legacy-compatibility.md) — what the preset system was and
  what replaced it
- [Theme operator guide](operator-guide.md) — the commands used above
- [Migration chain tests](../../tests/test_migration_chain.py) — the automated
  coverage for this revision chain
