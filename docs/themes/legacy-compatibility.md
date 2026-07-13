# Legacy Theme Preset Compatibility

This document maps the four existing hardcoded `THEME_PRESETS` (defined in `app/models.py:366-457`) to Halloy source files in `themes/`, records expected visual differences, and specifies migration semantics. This is a Phase 01 deliverable — no code changes.

## Section A: Legacy Preset Migration Table

| Preset key | Display name | Halloy equivalent? | File | Expected visual differences | Migration mode |
|---|---|---|---|---|---|
| `github-dark` | GitHub Dark | No exact match | — | Full palette differs; closest dark theme is `Catppuccin Mocha.toml` but uses `#11111B` bg vs `#0d1117`, `#CDD6F4` text vs `#e6edf3`, `#89B4FA` accent vs `#58a6ff` | `legacy_kept` |
| `github-light` | GitHub Light | No exact match | — | Full palette differs; closest light themes are `Catppuccin Latte.toml` (`#DCE0E8` bg) and `Noctis Lilac.toml` (`#EDECF8` bg) vs `#f6f8fa` | `legacy_kept` |
| `solarized-dark` | Solarized Dark | Near match | `"Solarized Dark.toml"` | Accent shifts from `#268BD2` (blue) to `#2AA198` (teal); surface bg `#073642` mapped from `[buffer].background_text_input` not `[buffer].background` | `near_match` |
| `monokai` | Monokai | No exact match | — | Closest is `Sonokai.toml` (Monokai variant) but bg `#2C2E34` vs `#272822`, accent `#76CCE0` vs `#66d9ef`, green `#9ED072` vs `#a6e22e` | `legacy_kept` |

### Migration mode definitions

- **`direct_alias`** — Halloy file's translated tokens are visually equivalent to the legacy preset. No visual change on migration.
- **`near_match`** — Close match with documented specific token differences. Operator should review before switching.
- **`legacy_kept`** — No Halloy equivalent exists. Legacy hex values are preserved as a special-case source in the registry.
- **`renamed`** — Halloy file is the canonical source; legacy display name is preserved as an alias.

## Section B: Cross-System Policy

### Prism syntax themes

`SiteSettings.syntax_theme` (values: `prism`, `prism-coy`, `prism-dark`, `prism-funky`, `prism-okaidia`, `prism-tomorrow`) remains a completely separate system. Prism themes are independent of the page color theme. A dark page theme may use a light Prism theme and vice versa. Halloy migration does not affect syntax highlighting.

### Custom CSS

`SiteSettings.custom_css` remains a privileged administrator feature. Generated theme CSS (from Halloy or legacy presets) is emitted *before* custom CSS in the inline style block, so intentional operator overrides via `custom_css` continue to take precedence. The custom CSS system is orthogonal to theme source.

### Visitor dark/light preference

The visitor dark/light toggle (`localStorage.theme` in `app/static/js/shared/dark-mode.js`) remains in place until Phase 08 migrates it to a new `blog-color-scheme` key with `system`/`dark`/`light` semantics. The existing `[data-theme="light"]` selector and `dark-mode.js` behavior are unchanged by this phase.

## Section C: Phase 06/14 Migration Path

### Phase 06 — Configuration and database migration

Phase 06 will expand or replace `SiteSettings.theme_preset` with:

- `dark_theme` — name of the active dark Halloy theme (or legacy preset key)
- `light_theme` — name of the active light Halloy theme (or legacy preset key)
- visitor preference: `system`, `dark`, or `light`

Existing rows with `theme_preset = "github-dark"` will be migrated to `dark_theme = "github-dark"` (using the `legacy_kept` palette). Operators may then switch to a Halloy theme of their choice through the admin UI added in Phase 10.

### Phase 14 — Legacy removal

The `THEME_PRESETS` dict in `app/models.py` will be removed in Phase 14 after all migration paths are validated and operators have had time to transition. Until Phase 14, the four legacy names (`github-dark`, `github-light`, `solarized-dark`, `monokai`) are kept as a "known-good" emergency fallback in the theme registry.

### Deprecation timeline

| Phase | Action |
|---|---|
| 06 | Legacy presets available as `legacy_kept` entries in registry alongside Halloy themes |
| 10 | Admin UI shows deprecation notice on legacy preset selection |
| 14 | `THEME_PRESETS` dict removed; legacy names no longer recognized |

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

All 22+ CSS custom properties currently emitted by `THEME_PRESETS` (via the `theme_vars` Jinja context in `app/templates/base.html:43`) have direct equivalents in the planned `BlogTheme` semantic token contract. The mapping is 1:1 for existing tokens — no CSS variable names are changed in this phase. The `BlogTheme` model (Phase 03) will extend the set with additional derived tokens (e.g., `text-on-accent`, `overlay`, `shadow`) but all current `theme_vars` keys are preserved as compatibility aliases.

Refer to the token contract defined in `plans/halloy_theme_phase_01_inventory_and_token_contract.md` (section 4, "Define `BlogTheme`") and the Phase 03 translation layer plan (`plans/halloy_theme_phase_03_blog_translation_layer.md`) for the complete token matrix and derivation rules.

## Appendix: Halloy Theme Files Referenced

| File | Role in this document |
|---|---|
| `"Solarized Dark.toml"` | Near-match for `solarized-dark` preset |
| `Catppuccin Mocha.toml` | Closest dark theme reference for `github-dark` |
| `Catppuccin Latte.toml` | Closest light theme reference for `github-light` |
| `Noctis Lilac.toml` | Alternative light theme reference for `github-light` |
| `Sonokai.toml` | Closest neighbor for `monokai` (Monokai variant) |
