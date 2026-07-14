# Theme System Operator Guide

Guide for administrators managing Halloy themes in the DevLog admin dashboard.

## Selecting Themes

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

## Refreshing Themes

After adding, removing, or modifying external theme files, click **Refresh Theme Registry** to:

1. Re-scan the external themes directory
2. Clear the theme cache
3. Report changes via flash messages:
   - Added themes
   - Removed themes
   - External override counts
4. Warn if a selected theme disappeared (shows effective fallback name)

Refresh does not restart the process. Changes take effect on the next page load.

## External Themes

External themes are loaded from the configured `EXTERNAL_THEME_DIR` directory (if set). Place `.toml` files following the [Halloy theme schema](supported-schema.md) in this directory.

### Naming

- Theme filenames are normalized: `my-theme.toml` → `My Theme`
- Case-insensitive matching prevents duplicates
- Names must not contain path separators (`/`, `\`)

### Overrides

An external theme with the same name as a bundled theme replaces it. The selector shows `(overrides bundled)` for clarity.

### Removing Overrides

To restore a bundled theme, delete the external override file and click **Refresh Theme Registry**.

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

**Theme not appearing after upload**: Click **Refresh Theme Registry** to rescan the external directory.

**Preview looks different from saved**: Preview applies CSS directly to the page. After save, the theme loads via the normal rendering pipeline which may apply additional transforms.

**Selected theme shows as fallback**: The theme file may have been removed or renamed. Check the external directory and refresh.

**Contrast warnings**: These are advisory. The theme may still be usable, but consider choosing a theme with better contrast for accessibility.
