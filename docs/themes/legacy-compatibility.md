# Legacy Theme Preset Compatibility

This document records the historical migration of four hardcoded `THEME_PRESETS` (formerly in `app/models.py`) to Halloy source files in `themes/`, documents expected visual differences, and specifies migration semantics. The `THEME_PRESETS` dict was removed in Phase 14, and the `theme_preset` column was dropped in Phase 15.

## Section A: Legacy Preset Migration Table

| Preset key | Display name | Halloy equivalent | Expected visual differences |
|---|---|---|---|
| `github-dark` | GitHub Dark | `Catppuccin Mocha` (mapped) | Full palette differs; closest dark theme uses `#11111B` bg vs `#0d1117`, `#CDD6F4` text vs `#e6edf3`, `#89B4FA` accent vs `#58a6ff` |
| `github-light` | GitHub Light | `Catppuccin Latte` (mapped) | Full palette differs; closest light themes use `#DCE0E8` bg vs `#f6f8fa` |
| `solarized-dark` | Solarized Dark | `Solarized Dark` (near match) | Accent shifts from `#268BD2` (blue) to `#2AA198` (teal); surface bg matches |
| `monokai` | Monokai | `Sonokai` (mapped) | Closest is Sonokai (Monokai variant) but bg `#2C2E34` vs `#272822`, accent `#76CCE0` vs `#66d9ef` |

### Legacy preset mapping

The `LEGACY_PRESET_MAP` was previously in `app/services/theme_settings.py` and mapped old preset keys to Halloy theme names:

```python
LEGACY_PRESET_MAP = {
    "github-dark": "Catppuccin Mocha",
    "github-light": "Catppuccin Latte",
    "solarized-dark": "Solarized Dark",
    "monokai": "Sonokai",
}
```

This mapping was used by `migrate_legacy_preset()` when upgrading from the old system. Both `LEGACY_PRESET_MAP` and `migrate_legacy_preset()` have been removed entirely as of Phase 15.

## Section B: Cross-System Policy

### Prism syntax themes

`SiteSettings.syntax_theme` (values: `prism`, `prism-coy`, `prism-dark`, `prism-funky`, `prism-okaidia`, `prism-tomorrow`) remains a completely separate system. Prism themes are independent of the page color theme. A dark page theme may use a light Prism theme and vice versa. Halloy migration does not affect syntax highlighting.

### Custom CSS

`SiteSettings.custom_css` remains a privileged administrator feature. Generated theme CSS (from Halloy or legacy presets) is emitted *before* custom CSS in the inline style block, so intentional operator overrides via `custom_css` continue to take precedence. The custom CSS system is orthogonal to theme source.

### Visitor dark/light preference

The visitor dark/light toggle was migrated in Phase 08 to a `blog-color-scheme` localStorage key with `system`/`dark`/`light` semantics. The CSS selector was updated from `[data-theme]` to `[data-color-scheme]`. The implementation lives in `app/static/js/shared/color-scheme.js`; there is no separate `dark-mode.js` module.

## Section C: Migration Path (Completed)

### Phase 06 — Configuration and database migration

Phase 06 expanded `SiteSettings` with `theme_dark_name`, `theme_light_name`, and `theme_default_scheme` columns. Operators may then switch to a Halloy theme of their choice through the admin UI added in Phase 10.

### Phase 14 — Legacy removal (complete)

The `THEME_PRESETS` dict was removed from `app/models.py` in Phase 14. The emergency fallback in `app/context_processors.py` now uses `EMERGENCY_DEFAULT` from `app/themes/model.py` which provides the same palette as the former `github-dark` preset.

### Phase 15 — Release closure (complete)

The `theme_preset` column was dropped from `SiteSettings` via Alembic migration. The `LEGACY_PRESET_MAP` and `migrate_legacy_preset()` were removed from `app/services/theme_settings.py`. All legacy preset references have been fully excised from the codebase.

### Deprecation timeline (complete)

| Phase | Action |
|---|---|
| 06 | Legacy presets kept in the registry alongside Halloy themes |
| 10 | Admin UI shows registry-based theme selector (legacy presets no longer in selector) |
| 14 | `THEME_PRESETS` dict removed; emergency fallback uses `EMERGENCY_DEFAULT` |
| 15 | `theme_preset` column dropped; `LEGACY_PRESET_MAP` and `migrate_legacy_preset()` removed |

The registry still resolves lower-case *name* aliases — for example
`solarized-dark` resolves to the `Solarized Dark` theme — through `_THEME_ALIASES`
in `app/themes/registry.py`. These are theme-name spellings, not the removed
preset system.

## Section D: Identified Visual Differences

The differences below were recorded when the presets were still live. The
translator now derives `BlogTheme` from the Halloy source files directly, so the
"Halloy translation" column is what the current translator actually produces.

### `solarized-dark` → `Solarized Dark.toml`

`themes/Solarized Dark.toml` is the only catalog file built from a legacy preset.
Key differences:

| Token | Legacy preset | Halloy translation | Notes |
|---|---|---|---|
| `accent` | `#268BD2` (blue) | `#93A1A1` | Mapped from `[text].tertiary` |
| `text-link` | — | `#2AA198` (teal) | Mapped from `[buffer].url` |
| `bg-page` | `#002B36` | `#002B36` | Matches `[general].background` |
| `bg-surface` | `#073642` | `#002B36` | Mapped from `[buffer].background` |
| `bg-elevated` | `#094857` | `#073642` | Mapped from `[buffer].background_title_bar` |
| `border` | `#586e75` | `#93A1A1` | Mapped from `[general].border`; lighter in the Halloy file |
| `text` | `#839496` | `#839496` | Exact match — `[text].primary` |
| `text-muted` | `#586e75` | `#586E75` | Case-insensitive match — `[text].secondary` |
| `green` | `#859900` | `#859900` | Exact match — `[text].success` |
| `red` | `#dc322f` | `#DC322F` | Case-insensitive match — `[text].error` |
| `yellow` | `#b58900` | — | Not mapped from Halloy; the warning fill uses a fixed hue |
| `purple` | `#6c71c4` | — | Not mapped from Halloy; the info fill uses a fixed hue |
| `coral` | `#cb4b16` | `#F78166` | Fixed constant in the translator; not read from Halloy |

**Summary**: the accent shift from blue (`#268BD2`) to the muted slate
(`#93A1A1`) is the most visually significant difference. Operators who want the
old blue accent should select a theme whose `[text].tertiary` is blue.

### `github-dark` → no catalog file

No Halloy equivalent exists. The closest reference is `Catppuccin Mocha.toml`,
which uses a different palette. The GitHub Dark palette survives as the
`EMERGENCY_DEFAULT` emergency fallback in `app/themes/model.py`:

| Token | Value |
|---|---|
| `bg-page` | `#0d1117` |
| `surface-default` | `#161b22` |
| `text-primary` | `#e6edf3` |
| `accent` | `#58a6ff` |
| `success-fg` | `#3fb950` |
| `error-fg` | `#f85149` |

### `github-light` → no catalog file

No Halloy equivalent exists. `Catppuccin Latte.toml` and `Noctis Lilac.toml` are
the closest light themes but differ substantially in palette. The GitHub Light
palette reference:

| Token | Value |
|---|---|
| `bg-page` | `#f6f8fa` |
| `surface-default` | `#ffffff` |
| `text-primary` | `#1f2328` |
| `accent` | `#0969da` |
| `success-fg` | `#1a7f37` |
| `error-fg` | `#cf222e` |

### `monokai` → no catalog file

No Halloy equivalent exists. `Sonokai.toml` is the closest neighbour (Sonokai is
a Monokai variant by Eldar Tukhvatullin) but uses a distinct palette. The Monokai
palette reference:

| Token | Value |
|---|---|
| `bg-page` | `#272822` |
| `surface-default` | `#3e3d32` |
| `text-primary` | `#f8f8f2` |
| `accent` | `#66d9ef` |
| `success-fg` | `#a6e22e` |
| `error-fg` | `#f92672` |

## Section E: Compatibility Aliases Summary

Every CSS custom property previously emitted by `THEME_PRESETS` has a direct
equivalent in the `BlogTheme` semantic token contract. The `ALIASES` dict in
`app/themes/model.py` preserves all **38** legacy variable names, so no CSS
variable name the stylesheets consume was changed. The `BlogTheme` model extends
the set with additional derived tokens (`text-on-accent`, `overlay-bg`,
`shadow-color`) that the aliases also expose.

Refer to the token contract defined in [the BlogTheme token contract](blog-theme-contract.md)
for the complete token matrix, derivation rules and the full alias table.

## Appendix: Halloy Theme Files Referenced

| File | Role in this document |
|---|---|
| `"Solarized Dark.toml"` | Built from the legacy `solarized-dark` preset |
| `Catppuccin Mocha.toml` | Closest dark theme reference for `github-dark` |
| `Catppuccin Latte.toml` | Closest light theme reference for `github-light` |
| `Noctis Lilac.toml` | Alternative light theme reference for `github-light` |
| `Sonokai.toml` | Closest neighbour for `monokai` (Monokai variant) |

## See Also

- [BlogTheme token contract](blog-theme-contract.md) — the token matrix and the
  full alias table
- [Migration boundary](migration-boundary.md) — the Alembic migrations that removed
  the legacy preset column
- [Theme architecture](../../architecture/core/themes.md) — the module reference
  for `app/themes/`
