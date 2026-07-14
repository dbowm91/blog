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

The visitor dark/light toggle was migrated in Phase 08 to a `blog-color-scheme` localStorage key with `system`/`dark`/`light` semantics. The CSS selector was updated from `[data-theme]` to `[data-color-scheme]`. The `dark-mode.js` module now re-exports from `color-scheme.js` for backward compatibility.

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
| 06 | Legacy presets available as `legacy_kept` entries in registry alongside Halloy themes |
| 10 | Admin UI shows registry-based theme selector (legacy presets no longer in selector) |
| 14 | `THEME_PRESETS` dict removed; emergency fallback uses `EMERGENCY_DEFAULT` |
| 15 | `theme_preset` column dropped; `LEGACY_PRESET_MAP` and `migrate_legacy_preset()` removed |

## Section D: Identified Visual Differences

### `solarized-dark` → `Solarized Dark.toml` (Halloy)

This is the only legacy preset with a near-match Halloy file. Key differences:

| Token | Legacy preset | Halloy translation | Notes |
|---|---|---|---|
| `accent` | `#268BD2` (blue) | `#2AA198` (teal) | Mapped from `[buffer].url`; this is the primary visual change |
| `bg-surface` | `#073642` | `#073642` | Matches `[buffer].background_text_input` |
| `bg-elevated` | `#094857` | `#073642` | Halloy has no distinct elevated value; `[buffer].background_title_bar` = `#073642` |
| `border` | `#586e75` | `#93A1A1` | Mapped from `[general].border`; lighter in Halloy |
| `text` | `#839496` | `#839496` | Exact match — `[text].primary` |
| `text-muted` | `#586e75` | `#586E75` | Case-insensitive match — `[text].secondary` |
| `green` | `#859900` | `#859900` | Exact match — `[text].success` |
| `red` | `#dc322f` | `#DC322F` | Case-insensitive match — `[text].error` |
| `yellow` | `#b58900` | — | Not directly mapped from Halloy; would need derivation |
| `purple` | `#6c71c4` | — | Not directly mapped; would need derivation |
| `coral` | `#cb4b16` | `#CB4B16` | Case-insensitive match — `[buffer].action` |

**Summary**: The accent color shift from blue (`#268BD2`) to teal (`#2AA198`) is the most visually significant difference. After Phase 05, the legacy "solarized-dark" preset should be deleted and operators should select `Solarized Dark.toml` from the registry, accepting the accent color change.

### `github-dark` → `<future Halloy file>`

No Halloy equivalent exists. Authoring a GitHub-Dark-themed TOML file is out of scope for this phase. Phase 14 cleanup may deprecate the `legacy_kept` entry in favor of an authored file if one is added to the catalog.

Key palette reference for future authoring:

| Token | Value |
|---|---|
| `bg` | `#0d1117` |
| `bg-surface` | `#161b22` |
| `text` | `#e6edf3` |
| `accent` | `#58a6ff` |
| `green` | `#3fb950` |
| `red` | `#f85149` |

### `github-light` → `<future Halloy file>`

No Halloy equivalent exists. `Catppuccin Latte.toml` and `Noctis Lilac.toml` are the closest light themes but differ substantially in palette.

Key palette reference for future authoring:

| Token | Value |
|---|---|
| `bg` | `#f6f8fa` |
| `bg-surface` | `#ffffff` |
| `text` | `#1f2328` |
| `accent` | `#0969da` |
| `green` | `#1a7f37` |
| `red` | `#cf222e` |

### `monokai` → `<future Halloy file>`

No Halloy equivalent exists. `Sonokai.toml` is the closest neighbor (Sonokai is a Monokai variant by Eldar Tukhvatullin) but uses a distinct palette.

Key palette reference for future authoring:

| Token | Value |
|---|---|
| `bg` | `#272822` |
| `bg-surface` | `#3e3d32` |
| `text` | `#f8f8f2` |
| `accent` | `#66d9ef` |
| `green` | `#a6e22e` |
| `red` | `#f92672` |

## Section E: Compatibility Aliases Summary

All 22+ CSS custom properties previously emitted by `THEME_PRESETS` have direct equivalents in the `BlogTheme` semantic token contract. The mapping is 1:1 for existing tokens — no CSS variable names are changed. The `BlogTheme` model extends the set with additional derived tokens (e.g., `text-on-accent`, `overlay`, `shadow`) but all legacy `theme_vars` keys are preserved as compatibility aliases via the `ALIASES` dict in `app/themes/model.py`.

Refer to the token contract defined in `docs/themes/blog-theme-contract.md` for the complete token matrix and derivation rules.

## Appendix: Halloy Theme Files Referenced

| File | Role in this document |
|---|---|
| `"Solarized Dark.toml"` | Near-match for `solarized-dark` preset |
| `Catppuccin Mocha.toml` | Closest dark theme reference for `github-dark` |
| `Catppuccin Latte.toml` | Closest light theme reference for `github-light` |
| `Noctis Lilac.toml` | Alternative light theme reference for `github-light` |
| `Sonokai.toml` | Closest neighbor for `monokai` (Monokai variant) |
