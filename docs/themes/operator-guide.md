# Theme Operator Guide

Use this guide to select a theme or add a custom Halloy-compatible theme.

## Select a theme

In the admin dashboard, open **Settings > Theme**. Choose a dark theme, a light theme, and a default color scheme:

- **System** follows the visitor's operating-system preference.
- **Dark** always uses the dark theme.
- **Light** always uses the light theme.

Use **Preview** to compare a theme without saving. Save the settings to apply the selection. The selector identifies bundled themes, external themes, and external themes that override a bundled theme.

## Theme CLI

The standalone `devlog` command manages themes:

```bash
devlog themes list
devlog themes list --source external
devlog themes validate /path/to/my-theme.toml
devlog themes inspect "Catppuccin Mocha"
devlog themes paths
devlog themes refresh
devlog themes accessibility
```

`list` accepts `--source all`, `--source bundled`, or `--source external`. `paths` shows the configured external theme directory. Run `refresh` after adding, changing, or removing theme files.

## Add an external theme

### 1. Configure a theme directory

Set `external_dir` in `config.toml` or use the `THEME_EXTERNAL_DIR` environment variable. Use an absolute path for a production install:

```toml
[themes]
external_dir = "/var/lib/devlog/themes"
```

The directory must exist and be readable by the DevLog process. DevLog does not create it. Check the effective path with:

```bash
devlog themes paths
```

For Docker, mount the host directory into the app container and set `THEME_EXTERNAL_DIR` to the container path:

```yaml
services:
  blog:
    volumes:
      - ./themes/external:/themes:ro
    environment:
      - THEME_EXTERNAL_DIR=/themes
```

Create `./themes/external` on the host and place `.toml` files there.

### 2. Validate and install the file

Validate the theme before copying it into the configured directory:

```bash
devlog themes validate ./my-theme.toml
cp my-theme.toml /var/lib/devlog/themes/
devlog themes refresh
```

The validator reports parse, schema, and accessibility findings. Review warnings before selecting the theme.

### 3. Select the theme

Return to **Settings > Theme**, choose the custom theme, preview it, and save. An external theme with the same canonical name as a bundled theme takes precedence. Avoid duplicate names in the external directory.

To restore the bundled version, remove the external file with the matching name and refresh the registry.

## Accessibility checks

Check contrast findings with:

```bash
devlog themes accessibility
devlog themes accessibility --source external
devlog themes accessibility --strict
devlog themes accessibility --json
```

The report includes per-theme findings and pass/fail totals. `--strict` returns a nonzero exit status when an external theme has unexpected mandatory failures. Bundled themes are reported but are not rejected by this flag. The JSON report contains findings and counts, not the eligibility tiers described in the [accessibility policy](accessibility-policy.md).

## Troubleshooting

- **Theme does not appear:** Check the path with `devlog themes paths`. Confirm the directory exists, is readable, and contains `.toml` files. Run `devlog themes refresh`.
- **Selected theme falls back:** The file may have been removed, renamed, or become unreadable. Restore the file or choose an available theme, then refresh.
- **Preview differs from the saved site:** Preview is temporary. Save the theme selection, then check the public site in a fresh page.
- **Workers show different themes:** Each app worker has its own theme registry. Refresh each worker or restart all workers after changing an external theme.

## Further reading

- [Supported theme schema](supported-schema.md)
- [Theme token contract](blog-theme-contract.md)
- [Accessibility policy](accessibility-policy.md)
- [Theme compatibility notes](legacy-compatibility.md)
- [Theme architecture](../../architecture/core/themes.md)
