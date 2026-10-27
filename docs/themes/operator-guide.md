# Theme System Operator Guide

Guide for administrators managing Halloy themes in the DevLog admin dashboard and CLI.

## CLI Commands

Theme management is available through two CLIs with the same command names: the
Flask CLI (`flask themes ...`) and the standalone operator CLI (`devlog themes
...`).

```bash
flask themes list [--source all|bundled|external] [--json] [--warnings] [--verbose]
flask themes validate PATH [--json]
flask themes inspect NAME [--json] [--css]
flask themes refresh
flask themes paths
flask themes accessibility [--source all|bundled|external] [--strict] [--json]

devlog themes list
devlog themes validate PATH [--json]
devlog themes inspect NAME [--json] [--css]
devlog themes refresh
devlog themes paths
devlog themes accessibility [--source all|bundled|external] [--strict] [--json]
```

### Listing Themes

```bash
flask themes list                    # Table output of all themes
flask themes list --source bundled   # Bundled themes only
flask themes list --json             # JSON output for automation
flask themes list --warnings         # Include warning summaries
```

### Validating Themes

Validate a file before installation:

```bash
flask themes validate ./my-theme.toml           # Human-readable output
flask themes validate ./my-theme.toml --json    # JSON for CI/scripts
```

Validate a registered theme name:

```bash
flask themes validate "Catppuccin Mocha"
```

Exit codes: `0` = valid, nonzero = invalid (unreadable, oversized, parse error, translation failure).

### Inspecting Themes

```bash
flask themes inspect "Catppuccin Mocha"          # Full details
flask themes inspect "Catppuccin Mocha" --json   # JSON output
flask themes inspect "Catppuccin Mocha" --css    # Generated CSS variables
flask themes inspect catppuccin-mocha            # Also works via alias
```

### Refreshing the Registry

After adding, removing, or modifying external theme files:

```bash
flask themes refresh
```

Reports catalog count changes, added/removed themes, and active external overrides.

### Checking Theme Paths

```bash
flask themes paths
```

Shows bundled package identity, external directory configuration, file counts, and precedence rules.

### Path Reference

#### Development (local venv)

- **Bundled themes**: `app/themes/bundled/` relative to the project root. Read-only, shipped with DevLog.
- **External themes**: Set `external_dir` in `config.toml` under `[themes]`, or via the `THEME_EXTERNAL_DIR` environment variable. When unset (empty string), external themes are disabled.

Example `config.toml`:

```toml
[themes]
external_dir = "themes/external"
allow_external = true
```

A relative path like `"themes/external"` resolves from the project root. Use an absolute path for a location outside the project tree.

#### Docker / Container

The container WORKDIR is `/home/blog`. Bundled themes are baked into the image at `/home/blog/app/themes/bundled/` and are read-only.

To use external themes in Docker, mount a host directory into the container and set `THEME_EXTERNAL_DIR` to the container path:

```yaml
services:
  blog:
    volumes:
      - ./themes/external:/home/blog/themes/external
    environment:
      - THEME_EXTERNAL_DIR=/home/blog/themes/external
```

Or set it in `config.toml` mounted into the container:

```yaml
services:
  blog:
    volumes:
      - ./config.toml:/home/blog/config.toml:ro
      - ./themes/external:/home/blog/themes/external
```

Ensure the mounted directory exists on the host and contains `.toml` theme files before starting the container.

#### XDG-Style Paths

Operators who follow XDG conventions can store external themes under the data directory:

```toml
[themes]
external_dir = "/home/user/.local/share/devlog/themes"
```

Or via environment variable:

```bash
export THEME_EXTERNAL_DIR="$XDG_DATA_HOME/devlog/themes"
```

The path must be absolute or relative to the project root. The directory is created automatically only if managed externally; DevLog does not create it.

#### Precedence

- External themes override bundled themes with the same canonical name.
- If multiple external files share a canonical name, the last one discovered wins (filesystem order).
- The admin selector labels overrides with `(overrides bundled)` for clarity.

Run `flask themes paths` at any time to confirm the effective configuration.

### Accessibility Checks

```bash
flask themes accessibility                   # Check all themes
flask themes accessibility --source bundled  # Bundled only
```

Reports WCAG contrast ratio failures across all themes.

## Selecting Themes (Admin UI)

Navigate to **Settings > Theme** to configure:

- **Dark Theme**: Applied when visitor's color scheme is `dark` or `system` (in dark mode)
- **Light Theme**: Applied when visitor's color scheme is `light` or `system` (in light mode)
- **Default Color Scheme**: `system` (respects OS preference), `dark`, or `light`

### Theme Metadata

Each theme selector displays:

- **Source**: `bundled` (shipped with DevLog) or `external` (custom themes directory)
- **Classification**: `dark` or `light` (when known)
- **Override status**: External themes that replace a bundled theme are labeled `(overrides bundled)`

### Previewing Themes

Click **Preview** next to any theme selector to see a live preview without saving:

- CSS variables are applied to a bounded preview container
- Representative UI elements (headings, links, buttons, inputs, badges, code blocks, cards) are shown
- WCAG contrast warnings are displayed if detected
- Classification mismatch warnings appear when both themes are the same type

Preview is non-persistent. Click **Clear Preview** or navigate away to restore the current theme.

## External Theme Workflow

### Step 1: Obtain a Theme

Create or download a Halloy-compatible TOML theme file. See [supported-schema.md](supported-schema.md) for the schema reference.

### Step 2: Validate

```bash
flask themes validate /path/to/my-theme.toml
```

Fix any parse errors, schema issues, or contrast warnings before proceeding.

### Step 3: Install

Copy the validated `.toml` file into the configured external themes directory:

```bash
cp my-theme.toml /path/to/external-themes/
```

The external directory is configured as `external_dir` under `[themes]` in
`config.toml`, or via the `THEME_EXTERNAL_DIR` environment variable. Check the
effective value with:

```bash
flask themes paths
```

### Step 4: Refresh

```bash
flask themes refresh
```

Or use the **Refresh Theme Registry** button in the admin Settings page.

### Step 5: Select

Navigate to **Settings > Theme** in the admin dashboard and select the new theme for dark or light mode.

### Step 6: Remove (Optional)

To restore a bundled theme, delete the external override file and refresh:

```bash
rm /path/to/external-themes/my-theme.toml
flask themes refresh
```

## Overrides

An external theme with the same name as a bundled theme replaces it. The selector shows `(overrides bundled)` for clarity.

## Naming

- Theme filenames are normalized: `my-theme.toml` → `My Theme`
- Case-insensitive matching prevents duplicates
- Names must not contain path separators (`/`, `\`)

## Warnings

The system displays warnings for:

- **Missing themes**: Selected theme no longer exists (shows fallback)
- **Malformed themes**: External theme file has parse errors
- **Classification mismatch**: Both dark and light slots use themes of the same type
- **Low contrast**: WCAG contrast ratio below threshold
- **External overrides**: Bundled theme is being replaced

## Persistence

Theme settings are saved atomically with other site settings. Saving preserves:

- Custom CSS (if enabled)
- Logo text

Theme names are validated against the registry before save. Invalid names are rejected.

## Cache Behavior

- Theme CSS is cached in-process for performance
- Settings changes automatically invalidate the cache
- Refresh explicitly rebuilds the registry and clears caches
- No process restart is required for changes to take effect

## Multi-Worker Deployment

When running multiple worker processes (e.g., with Gunicorn or Granian):

- Each worker maintains its own in-process theme registry and cache
- Theme changes require explicit refresh on each worker, or a restart/reload
- Use `flask themes refresh` or the admin "Refresh Theme Registry" button on each worker
- The `ENABLE_SCHEDULER` env var should be set on exactly one container to prevent duplicate jobs

### Cache Freshness

The theme cache follows an explicit-invalidation model:
- Bundled themes are immutable for the process lifetime
- External theme changes require explicit `invalidate()` or `invalidate(name)`
- Admin and CLI refresh are authoritative
- Warm requests perform no filesystem reads or TOML parsing

See the [cache freshness contract](cache-contract.md) for the full cache model.

## Troubleshooting

**Theme not appearing after upload**: Run `flask themes refresh` or click **Refresh Theme Registry** in the admin.

**Preview looks different from saved**: Preview applies CSS directly to the page. After save, the theme loads via the normal rendering pipeline which may apply additional transforms.

**Selected theme shows as fallback**: The theme file may have been removed or renamed. Check the external directory and refresh.

**Contrast warnings**: These are advisory. The theme may still be usable, but consider choosing a theme with better accessibility. Run `flask themes accessibility` to check all themes.

**Emergency fallback activated**: If the theme service encounters an error, the site falls back to `EMERGENCY_DEFAULT` (same palette as the former `github-dark` preset). Check logs for the specific error and run `flask themes refresh` to reinitialize.

**Legacy preset names no longer work**: The `THEME_PRESETS` dict was removed in Phase 14, and the `theme_preset` database column was dropped in Phase 15. The preset names `github-dark`, `github-light` and `monokai` no longer resolve to anything. `solarized-dark` does still resolve, as a theme *name alias* to the `Solarized Dark` theme. Select a Halloy theme name from the admin settings page instead.

## Accessibility Policy

Every bundled and external theme is classified into one of three eligibility tiers based on WCAG contrast ratio checks:

### Tiers

| Tier | Meaning | Operator guidance |
|------|---------|-------------------|
| **recommended** | Zero mandatory failures, zero expected exceptions. All 29 contrast pairs (18 mandatory, 11 advisory) pass WCAG thresholds. | Safe for production use with no caveats. |
| **compatible-with-exceptions** | Mandatory failures exist but every one is covered by a documented exception in the exception manifest. The theme is usable but has known contrast deviations. | Safe for production. Review the exception reasons to understand the trade-offs (e.g., decorative input borders, composited-pair edge cases). |
| **experimental** | One or more mandatory failures with no matching exception. The theme has contrast issues that have not been reviewed or accepted. | Not recommended for production. Use at your own risk; run `flask themes accessibility --strict` to identify the specific failures. |

### How themes are classified

Classification is determined by `classify_theme_eligibility()` in `app/themes/diagnostics.py`. The logic is:

1. If a theme has **zero mandatory failures** and **zero expected exceptions**, it is `recommended`.
2. If a theme has mandatory failures but **every failure matches a documented exception** (unexpected failures = 0), it is `compatible-with-exceptions`.
3. Otherwise it is `experimental`.

Advisory-only warnings (below recommended thresholds but above mandatory minimums) do not affect classification. A theme with only advisory findings is still `recommended`.

### Exception manifest

Documented exceptions are maintained in `app/themes/ACCESSIBILITY_EXCEPTIONS.json`. The manifest structure:

```json
{
  "schema_version": 2,
  "policy_version": "1.0",
  "reviewed_date": "2026-07-14",
  "exceptions": {
    "Theme Name": {
      "total_failures": 2,
      "policy_class": "compatible-with-exceptions",
      "pairs": [
        {
          "token": "--blog-input-border",
          "description": "input-border on bg-page",
          "ratio": 1.71,
          "required": 3.0,
          "policy_class": "advisory_deviation",
          "rationale": "Explanation of why this deviation is acceptable",
          "wcag_criteria": ["1.4.11"],
          "rendered_context": "Where this element appears in the UI"
        }
      ]
    }
  }
}
```

Top-level fields: `schema_version` (integer, bumps on structural changes), `validator_version`, `policy_version` (semantic version of the accessibility policy), `reviewed_date` (ISO date of last review), `owner`, `version`, `description` and a `summary` block with aggregate counts. Each theme entry lists its failing contrast pairs with a `policy_class`, `rationale`, applicable WCAG criteria, and rendered context.

### Running accessibility checks

```bash
flask themes accessibility                   # Check all themes, report results
flask themes accessibility --strict          # Exit nonzero if any theme has unexpected mandatory failures
flask themes accessibility --source bundled  # Bundled themes only
flask themes accessibility --json            # Structured JSON output
```

The `--strict` flag rejects **external** themes that have unexpected mandatory
failures: it makes the command exit non-zero and list each rejected theme.
Bundled themes are never rejected by `--strict`, and themes whose failures are
all covered by the exception manifest pass under `--strict`. This is useful as a
CI gate against shipping a broken operator-supplied theme.

Use `python scripts/theme_accessibility_report.py` when you want a gate over the
whole bundled catalogue — that script exits non-zero when any theme has a
mandatory accessibility failure.

### Catalog summary

The `CatalogEligibility` dataclass returned by `classify_catalog_eligibility()` provides aggregate counts:

- `recommended_count` — themes with zero mandatory failures
- `compatible_count` — themes with only documented exceptions
- `experimental_count` — themes with unexpected mandatory failures

Run `flask themes accessibility --json` to see per-theme eligibility and catalog-level totals.

## Migration from Legacy Presets

If upgrading from a version that used `THEME_PRESETS`, the database migrations
handled the schema change:

1. The `preserve_legacy_scheme` migration preserves your visual mode setting
2. The `theme_preset` column is dropped by the `drop_theme_preset_column`
   migration
3. The `add_theme_config_to_sitesettings` migration added `theme_dark_name`,
   `theme_light_name` and `theme_default_scheme`

The preset-to-Halloy name mapping was applied by `migrate_legacy_preset()`, which
was removed in Phase 15. It mapped:

| Legacy preset | Halloy equivalent |
|---|---|
| `github-dark` | `Catppuccin Mocha` |
| `github-light` | `Catppuccin Latte` |
| `solarized-dark` | `Solarized Dark` |
| `monokai` | `Sonokai` |

After upgrading, navigate to **Settings > Theme** to choose different themes.
Custom CSS is preserved unchanged.

## Database Support

- **SQLite** (recommended): Fully supported. All migrations use `batch_alter_table` for SQLite-safe DDL. FTS5 search and WAL mode are production-ready.
- **PostgreSQL**: Not currently supported. The `PostgreSQLSearchProvider` is a stub for future use. While Alembic migrations are dialect-neutral, the application has not been tested or documented for PostgreSQL. Do not use PostgreSQL in production without first validating FTS5 search compatibility and deployment configuration.

For full migration details, rollback procedures, and recovery steps, see [the migration boundary guide](migration-boundary.md).

## See Also

- [Supported theme schema](supported-schema.md) — the input contract for theme files
- [BlogTheme token contract](blog-theme-contract.md) — the tokens and aliases themes emit
- [Accessibility policy](accessibility-policy.md) — the policy behind the eligibility tiers
- [Theme architecture](../../architecture/core/themes.md) — the module reference for `app/themes/`
