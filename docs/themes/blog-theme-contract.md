# BlogTheme Semantic Token Contract

The token model that `app/themes/model.py` defines and `app/themes/translate.py`
produces. `BlogTheme` is a frozen dataclass with **50 fields**: 41 `RGB` and 9
`RGBA`. `CSS_VARS` maps each field to a `--blog-*` CSS custom property (50
entries) and `ALIASES` maps the legacy CSS variable names to those custom
properties (38 entries).

---

## Section A: BlogTheme Token Matrix

Each row is one semantic token. Aliases (Section E) are listed separately and not
counted as tokens. "Source" is the Halloy field the translator reads, or the
formula it derives the value from.

| Token name | Semantic purpose | Source | Type | Emergency default | Alias(es) |
|---|---|---|---|---|---|
| **Backgrounds** | | | | | |
| `--blog-bg-page` | Page / root background behind all content | `[general].background` | D | `#0d1117` | `--bg` |
| `--blog-surface-default` | Content surface (cards, prose area, post body) | `[buffer].background` | D | `#161b22` | `--bg-surface` |
| `--blog-surface-elevated` | Elevated surface (modals, title bars, dropdowns) | `[buffer].background_title_bar` | D | `#1c2128` | `--bg-elevated` |
| `--blog-surface-hover` | Hovered surface (card hover, row hover) | `shift_lightness(surface-default, ±0.06)` | DER | `#21262d` | `--bg-hover` |
| `--blog-surface-active` | Active/pressed surface (button active, selected row) | `shift_lightness(surface-default, ±0.12)` | DER | `#161b22` | — |
| `--blog-navbar-bg` | Navbar / top bar background (translucent for blur) | `bg-page` at 0.85 alpha | DER | `rgba(13,17,23,0.85)` | `--navbar-bg` |
| `--blog-overlay-bg` | Modal/overlay dimming layer | fixed | DER | `rgba(0,0,0,0.5)` | `--overlay-bg` |
| **Borders** | | | | | |
| `--blog-border-primary` | Main structural border (cards, inputs, dividers) | `[general].border` | D | `#30363d` | `--border` |
| `--blog-border-subtle` | Subtle/secondary border (separators, horizontal rules) | `[general].horizontal_rule` | D | `#30363d` | — |
| `--blog-border-strong` | Strong emphasis border (active input, focus container) | `shift_lightness(border-primary, ±0.10)` | DER | `#484f58` | — |
| `--blog-border-focus` | Focus ring / outline color | `= accent` | DER | `#58a6ff` | — |
| `--blog-navbar-border` | Border below/around navbar | `= border-primary` | DER | `#30363d` | — |
| **Text** | | | | | |
| `--blog-text-primary` | Primary body text | `[text].primary` | D | `#e6edf3` | `--text` |
| `--blog-text-secondary` | Secondary/emphasized text (bylines, strong inline) | `[buffer].topic` | D | `#c9d1d9` | `--text-secondary` |
| `--blog-text-muted` | Muted/tertiary text (meta, timestamps in prose) | `[text].secondary` | D | `#8b949e` | `--text-muted` |
| `--blog-text-dim` | Dimmest text (anchors, inactive labels) | `[buffer].timestamp` | D | `#7d8590` | `--text-dim`, `--text-dim-strong` |
| `--blog-text-on-accent` | Text on accent-coloured fills (buttons, badges) | foreground selected against `accent` | DER | `#ffffff` | `--text-on-accent` |
| `--blog-text-on-success` | Text on success-coloured fills | foreground selected against `success-bg` | DER | `#ffffff` | — |
| `--blog-text-on-error` | Text on error-coloured fills | foreground selected against `error-bg` | DER | `#ffffff` | — |
| `--blog-text-on-warning` | Text on warning-coloured fills | foreground selected against `warning-bg` | DER | `#000000` | — |
| `--blog-text-on-info` | Text on info-coloured fills | foreground selected against `info-bg` | DER | `#000000` | — |
| `--blog-text-link` | Link text colour | `[buffer].url` | D | `#58a6ff` | — |
| `--blog-text-link-hover` | Link hover colour | `= accent-hover` | DER | `#79c0ff` | — |
| **Accent** | | | | | |
| `--blog-accent` | Primary accent / brand colour (links, buttons, highlights) | `[text].tertiary` | D | `#58a6ff` | `--accent` |
| `--blog-accent-hover` | Accent hover state | `shift_lightness(accent, ±0.10)` | DER | `#79c0ff` | `--accent-hover` |
| `--blog-accent-dim` | Subtle accent background (badges, active nav items) | `accent` at 0.10 alpha | DER | `rgba(88,166,255,0.1)` | `--accent-dim` |
| `--blog-accent-link` | Accent used for interactive links | `= accent` | DER | `#58a6ff` | — |
| `--blog-accent-focus-ring` | Focus ring colour | `= accent` | DER | `#58a6ff` | — |
| **States** | | | | | |
| `--blog-success-fg` | Success foreground (checkmarks, positive indicators) | `[text].success` | D | `#3fb950` | `--green` |
| `--blog-success-bg` | Success background (subtle success fill) | `success-fg` at 0.15 alpha over `bg-page` | DER | `rgba(63,185,80,0.15)` | `--green-dim`, `--success-bg` |
| `--blog-error-fg` | Error foreground (errors, destructive actions) | `[text].error` | D | `#f85149` | `--red` |
| `--blog-error-bg` | Error background (subtle error fill) | `error-fg` at 0.15 alpha over `bg-page` | DER | `rgba(248,81,73,0.15)` | `--red-dim`, `--error-bg` |
| `--blog-warning-fg` | Foreground drawn on the warning fill | foreground selected against `warning-bg` | DER | `#d29922` | `--yellow`, `--warning-fg` |
| `--blog-warning-bg` | Warning background (subtle warning fill) | `rgba(210,153,34,0.15)` over `bg-page` | DER | `rgba(210,153,34,0.15)` | `--amber-dim`, `--warning-bg` |
| `--blog-info-fg` | Foreground drawn on the info fill | foreground selected against `info-bg` | DER | `#a371f7` | `--purple`, `--amber`, `--info-fg` |
| `--blog-info-bg` | Informational background (subtle info fill) | `rgba(163,113,247,0.15)` over `bg-page` | DER | `rgba(163,113,247,0.15)` | `--purple-dim`, `--info-bg` |
| **Inputs / Code** | | | | | |
| `--blog-input-bg` | Input / text field background | `[buffer].background_text_input` | D | `#0d1117` | — |
| `--blog-input-border` | Input border | `= border-primary` | DER | `#30363d` | — |
| `--blog-input-text` | Text inside inputs | `= text-primary` | DER | `#e6edf3` | — |
| `--blog-code-bg` | Inline code and code block background | `[buffer].background_text_input` | D | `#161b22` | `--code-bg` |
| `--blog-code-border` | Code block border | `= border-subtle` | DER | `#30363d` | — |
| `--blog-code-text` | Code text colour | `= text-primary` | DER | `#e6edf3` | — |
| `--blog-selection-bg` | Text selection highlight | `[buffer].selection` | D | `#30363d` | — |
| **Navbar / Chrome** | | | | | |
| `--blog-navbar-text` | Navbar link/text colour | `= text-primary` | DER | `#e6edf3` | — |
| `--blog-navbar-text-muted` | Navbar muted/secondary text | `= text-muted` | DER | `#8b949e` | — |
| **Overlays** | | | | | |
| `--blog-shadow-color` | Box shadow / drop shadow colour | fixed per theme polarity | DER | `rgba(0,0,0,0.35)` | `--shadow-color` |
| **Miscellaneous** | | | | | |
| `--blog-noscript-bg` | Noscript warning background | fixed | DER | `#3b2e00` | `--noscript-bg` |
| `--blog-noscript-text` | Noscript warning text colour | fixed | DER | `#d4a017` | `--noscript-text` |
| `--blog-coral` | Coral accent (syntax, secondary accent) | fixed | DER | `#f78166` | `--coral` |
| `--blog-coral-dim` | Subtle coral background | fixed at 0.15 alpha | DER | `rgba(247,129,102,0.15)` | `--coral-dim` |

**Token count:** 50 unique semantic tokens (excluding aliases).

The "Emergency default" column is the value in `EMERGENCY_DEFAULT` in
`app/themes/model.py`. It is the palette the site falls back to when the theme
service fails. Note that the emergency fallback's *emitted CSS* comes from
`translate_halloy_theme()` applied to an emergency Halloy theme, not from
`EMERGENCY_DEFAULT` itself — see
[Theme architecture](../../architecture/core/themes.md#notes-and-gotchas).

---

## Section B: Halloy to BlogTheme Mapping Table

Each Halloy field the translator reads maps to one or more `BlogTheme` tokens.
Marked D (direct) when the Halloy value is used as-is, DER (derived) when the
translator computes the output from the Halloy value plus other inputs.

| Halloy field | BlogTheme token(s) | D/DER | Notes |
|---|---|---|---|
| `[general].background` | `bg-page`, `navbar-bg` | D, DER | `navbar-bg` = bg-page at 0.85 alpha |
| `[general].border` | `border-primary`, `input-border`, `navbar-border` | D, DER | `input-border` and `navbar-border` copy `border-primary` |
| `[general].horizontal_rule` | `border-subtle`, `code-border` | D, DER | `code-border` copies `border-subtle` |
| `[text].primary` | `text-primary` | D | Direct |
| `[text].secondary` | `text-muted` | D | Halloy "secondary" is blog "muted" |
| `[text].tertiary` | `accent` | D | Theme's accent/highlight colour |
| `[text].success` | `success-fg` | D | Direct |
| `[text].error` | `error-fg` | D | Direct |
| `[buffer].background` | `surface-default` | D | Buffer content area background |
| `[buffer].background_text_input` | `input-bg`, `code-bg` | D | Shared background for text inputs and code blocks |
| `[buffer].background_title_bar` | `surface-elevated` | D | Elevated/title-bar surface |
| `[buffer].selection` | `selection-bg` | D | Text selection highlight |
| `[buffer].timestamp` | `text-dim` | D | Dimmest text tier |
| `[buffer].topic` | `text-secondary` | D | Secondary emphasis text |
| `[buffer].url` | `text-link` | D | Direct |

**Halloy fields the translator does not read:** `[general].unread_indicator`,
`[buffer].action`, `[buffer].border`, `[buffer].border_selected`,
`[buffer].code`, `[buffer].highlight`, `[buffer].nickname`,
`[buffer.server_messages].*` and every `[buttons.*]` field. They are parsed and
retained on the parsed `HalloyTheme` model, but they contribute nothing to the
`BlogTheme` output.

**Mapping notes:**

- A Halloy colour with an alpha channel is composited over white before use
  (`_resolve_bg()`), so a translucent source colour becomes an opaque RGB.
- `[buffer].background` and `[general].background` are distinct: the buffer
  background is the content surface, the general background is the page
  background.
- Halloy provides no warning, info or coral colours. Those are fixed or derived
  from the page background.

---

## Section C: Derived Token Formulas

The translator computes these tokens in `app/themes/translate.py`. The dark/light
classification comes from `is_dark_background(general.background)`: a theme is
dark when the background luminance is below 0.5.

### accent-dim

```
accent-dim = RGBA(accent, alpha=0.10)
```

The accent colour at 0.10 alpha. It is *not* composited over the surface — the
alpha channel is preserved so the stylesheet can composite it at use time.

### state-bg (success-bg, error-bg)

```
state-bg = alpha_composite(RGBA(state-fg, 0.15), bg-page)
```

Uses the corresponding foreground colour (`success-fg`, `error-fg`) at 0.15
alpha composited over the page background.

### warning-bg and info-bg

```
warning-bg = alpha_composite(RGBA(210, 153, 34, 0.15), bg-page)
info-bg    = alpha_composite(RGBA(163, 113, 247, 0.15), bg-page)
```

Fixed hues at 0.15 alpha over the page background. Halloy has no warning or info
colour, so these do not vary with the source theme.

### surface-hover

```
surface-hover = shift_lightness(surface-default, +0.06)   # dark themes
surface-hover = shift_lightness(surface-default, -0.06)   # light themes
```

The 6% shift is applied in HSL lightness.

### surface-active

```
surface-active = shift_lightness(surface-default, +0.12)   # dark themes
surface-active = shift_lightness(surface-default, -0.12)   # light themes
```

Twice the hover shift. Used for button active states and selected rows.

### border-strong

```
border-strong = shift_lightness(border-primary, +0.10)   # dark themes
border-strong = shift_lightness(border-primary, -0.10)   # light themes
```

### accent-hover and text-link-hover

```
accent-hover    = shift_lightness(accent, +0.10)   # dark themes
accent-hover    = shift_lightness(accent, -0.10)   # light themes
text-link-hover = accent-hover
```

### text-on-accent and text-on-state

```
text-on-accent = foreground_selected(accent, min_ratio=4.5)
text-on-success = foreground_selected(success-bg, min_ratio=4.5)
text-on-error   = foreground_selected(error-bg, min_ratio=4.5)
text-on-warning = foreground_selected(warning-bg, min_ratio=4.5)
text-on-info    = foreground_selected(info-bg, min_ratio=4.5)
```

`foreground_selected()` picks white if it reaches 4.5:1 against the background,
otherwise black if it does; if neither reaches the threshold it picks whichever
has the higher ratio and the diagnostics report the shortfall.

`warning-fg` and `info-fg` are the same computation against `warning-bg` and
`info-bg`, so they are the *foreground drawn on* those fills — not a warning hue
in their own right.

### shadow-color

```
shadow-color = rgba(0, 0, 0, 0.35)   # dark themes
shadow-color = rgba(0, 0, 0, 0.12)   # light themes
```

Fixed values per theme polarity. Not derived from theme colours.

### overlay-bg

```
overlay-bg = rgba(0, 0, 0, 0.5)
```

Fixed for all themes. Modal backdrop / overlay dimming.

### navbar-bg

```
navbar-bg = rgba(bg-page.r, bg-page.g, bg-page.b, 0.85)
```

The page background colour at 0.85 alpha, to support backdrop-filter blur.

### Identity mappings

```
border-focus     = accent
accent-link      = accent
accent-focus-ring = accent
navbar-border    = border-primary
input-border     = border-primary
input-text       = text-primary
code-border      = border-subtle
code-text        = text-primary
navbar-text      = text-primary
navbar-text-muted = text-muted
```

### Fixed tokens with no Halloy source

```
noscript-bg   = #3b2e00
noscript-text = #d4a017
coral         = #f78166
coral-dim     = rgba(247, 129, 102, 0.15)
```

These are legacy blog-specific tokens. They are the same in every theme.

---

## Section D: Packaged Resource Layout

### Chosen layout

```text
app/themes/
    __init__.py
    model.py
    translate.py
    diagnostics.py
    halloy.py
    colors.py
    registry.py
    resources.py
    cache.py
    service.py
    ACCESSIBILITY_EXCEPTIONS.json
    bundled/
        *.toml
```

### Relationship to top-level `themes/`

- **`themes/`** (repository root): the authoring catalogue. Theme authors develop
  and review files here. `scripts/theme_inventory.py` and
  `scripts/theme_accessibility_report.py` read this directory.
- **`app/themes/bundled/`**: the packaged copy that the runtime loads through
  `importlib.resources`. The two trees hold the same 50 files.
- **External themes** (runtime): live outside the Python package at the path
  configured by `themes.external_dir` in `config.toml` or `THEME_EXTERNAL_DIR`.
  An external theme with the same canonical name overrides the bundled one.

> The root `themes/` directory is **not** the runtime external override
> directory. The external directory is configured separately.

### Resource accessor pattern

Theme loading uses `importlib.resources`. No cwd-relative lookup is used.

```python
from importlib.resources import files

def get_bundled_themes_dir():
    """Return the Traversable directory containing bundled .toml themes."""
    return files("app.themes.bundled")
```

### Packaging requirements

| Artifact | File | Notes |
|---|---|---|
| Package data declaration | `pyproject.toml` `[tool.setuptools.package-data]` | `"app.themes.bundled" = ["*.toml"]` |
| Source distribution inclusion | `MANIFEST.in` | `recursive-include app/themes/bundled *.toml` |
| Wheel inclusion | automatic via package-data | Verified by `scripts/verify_theme_package.py` |
| Editable install | automatic via package-data | — |

### Wheel-installable requirements

- No `cwd`-relative paths anywhere in theme loading code.
- `importlib.resources` is the only resource access mechanism.
- The application must work when installed as a wheel into a virtualenv outside
  the repository root.

---

## Section E: Migration Compatibility Aliases

The `ALIASES` dict in `app/themes/model.py` preserves the legacy CSS variable
names. `to_legacy_vars()` in `app/themes/translate.py` resolves each alias
through `CSS_VARS` and emits it as a `--<legacy key>` declaration.
`to_legacy_css()` serialises them for the stylesheets.

| Legacy key | Semantic token |
|---|---|
| `bg` | `--blog-bg-page` |
| `bg-surface` | `--blog-surface-default` |
| `bg-elevated` | `--blog-surface-elevated` |
| `bg-hover` | `--blog-surface-hover` |
| `border` | `--blog-border-primary` |
| `text` | `--blog-text-primary` |
| `text-secondary` | `--blog-text-secondary` |
| `text-muted` | `--blog-text-muted` |
| `text-dim` | `--blog-text-dim` |
| `text-dim-strong` | `--blog-text-dim` (same target as `text-dim`) |
| `text-on-accent` | `--blog-text-on-accent` |
| `accent` | `--blog-accent` |
| `accent-hover` | `--blog-accent-hover` |
| `accent-dim` | `--blog-accent-dim` |
| `green` | `--blog-success-fg` |
| `green-dim` | `--blog-success-bg` |
| `success-bg` | `--blog-success-bg` |
| `red` | `--blog-error-fg` |
| `red-dim` | `--blog-error-bg` |
| `error-bg` | `--blog-error-bg` |
| `yellow` | `--blog-warning-fg` |
| `yellow-dim` | `--blog-warning-bg` |
| `warning-fg` | `--blog-warning-fg` |
| `warning-bg` | `--blog-warning-bg` |
| `purple` | `--blog-info-fg` |
| `purple-dim` | `--blog-info-bg` |
| `info-fg` | `--blog-info-fg` |
| `info-bg` | `--blog-info-bg` |
| `amber` | `--blog-info-fg` |
| `amber-dim` | `--blog-warning-bg` |
| `coral` | `--blog-coral` |
| `coral-dim` | `--blog-coral-dim` |
| `code-bg` | `--blog-code-bg` |
| `navbar-bg` | `--blog-navbar-bg` |
| `overlay-bg` | `--blog-overlay-bg` |
| `shadow-color` | `--blog-shadow-color` |
| `noscript-bg` | `--blog-noscript-bg` |
| `noscript-text` | `--blog-noscript-text` |

**Alias count:** 38. Every alias resolves to a `--blog-*` custom property, so
`to_legacy_vars()` emits all 38 legacy variables for every theme.

The `THEME_PRESETS` dict and the `theme_preset` database column were removed in
phases 14 and 15 of the Halloy migration; the `name` metadata key is no longer
part of `ALIASES`.

**Ambiguity resolved:** `amber` and `purple` both map to `--blog-info-fg`, and
`amber-dim` maps to `--blog-warning-bg`, because amber is semantically closer to
warning in the legacy presets.

---

## Section F: Token Coverage Check

Every legacy CSS variable key the stylesheets consume is accounted for in the
`BlogTheme` model. The full mapping is Section E; the coverage summary is:

| Coverage | Count |
|---|---|
| `BlogTheme` fields | 50 |
| `CSS_VARS` entries | 50 |
| `ALIASES` entries | 38 |
| Legacy CSS variables emitted by `to_legacy_vars()` | 38 |

No legacy key is left without a semantic replacement, and every alias maps to
exactly one `BlogTheme` token.

---

## Tokens With No Halloy Source

These tokens have no direct Halloy equivalent:

- `--blog-warning-fg` / `--blog-warning-bg`: no `[text].warning` in Halloy. The
  fill is a fixed hue at 0.15 alpha; the foreground is selected against it.
- `--blog-info-fg` / `--blog-info-bg`: no `[text].info` in Halloy. Same pattern.
- `--blog-noscript-bg` / `--blog-noscript-text`: no Halloy equivalent. Fixed
  legacy blog-specific values.
- `--blog-coral` / `--blog-coral-dim`: no Halloy equivalent. Fixed legacy
  blog-specific values.
- `--blog-shadow-color`: no Halloy equivalent. Fixed per theme polarity.
- `--blog-overlay-bg`: no Halloy equivalent. Fixed `rgba(0,0,0,0.5)`.

---

## See Also

- [Supported Halloy theme schema](supported-schema.md) — the parser input contract
- [Cache freshness contract](cache-contract.md) — how translated themes are cached
- [Theme operator guide](operator-guide.md) — operator-facing commands
- [Theme architecture](../../architecture/core/themes.md) — the module reference
  for `app/themes/`
