# Theme System Operator Guide

Guide for administrators managing Halloy themes in the DevLog admin dashboard and CLI.

## CLI Commands

All theme management can be done via the Flask CLI:

```bash
flask themes list [--source all|bundled|external] [--json] [--warnings] [--verbose]
flask themes validate PATH [--json]
flask themes inspect NAME [--json] [--css]
flask themes refresh
flask themes paths
flask themes accessibility [--source all|bundled|external]
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

The external directory path is configured via `THEME_EXTERNAL_DIR` in `config.toml` under `[themes]`. Check with:

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

- Syntax highlighting theme
- Custom CSS (if enabled)
- Logo text

Theme names are validated against the registry before save. Invalid names are rejected.

## Cache Behavior

- Theme CSS is cached in-process for performance
- Settings changes automatically invalidate the cache
- Refresh explicitly rebuilds the registry and clears caches
- No process restart is required for changes to take effect

## Troubleshooting

**Theme not appearing after upload**: Run `flask themes refresh` or click **Refresh Theme Registry** in the admin.

**Preview looks different from saved**: Preview applies CSS directly to the page. After save, the theme loads via the normal rendering pipeline which may apply additional transforms.

**Selected theme shows as fallback**: The theme file may have been removed or renamed. Check the external directory and refresh.

**Contrast warnings**: These are advisory. The theme may still be usable, but consider choosing a theme with better accessibility. Run `flask themes accessibility` to check all themes.
