# BlogTheme Semantic Token Contract

Phase 01 deliverable. This document is the authoritative source for the
`BlogTheme` token model that Phase 03 (translator) and Phase 05 (packaging)
will implement against.

---

## Section A: BlogTheme Token Matrix

Each row is one semantic token. Aliases (Section E) are listed separately and
not counted as tokens.

| Token name | Semantic purpose | Halloy source candidate | D/DER | Required contrast relationship | Fallback (github-dark) | Alias(es) |
|---|---|---|---|---|---|---|
| **Backgrounds** | | | | | | |
| `--blog-bg-page` | Page / root background behind all content | `[general].background` | D | text-primary on bg-page >= WCAG AA 4.5:1 | `#0d1117` | `--bg` |
| `--blog-surface-default` | Content surface (cards, prose area, post body) | `[buffer].background` | D | text-primary on surface >= 4.5:1 | `#161b22` | `--bg-surface` |
| `--blog-surface-elevated` | Elevated surface (modals, title bars, dropdowns) | `[buffer].background_title_bar` | D | text-primary on elevated >= 4.5:1 | `#1c2128` | `--bg-elevated` |
| `--blog-surface-hover` | Hovered surface (card hover, row hover) | derived from surface-default | DER | sufficient contrast with text-primary | `#21262d` | `--bg-hover` |
| `--blog-surface-active` | Active/pressed surface (button active, selected row) | derived from surface-default | DER | sufficient contrast with text-primary | `#161b22` (12% lighter) | -- |
| `--blog-navbar-bg` | Navbar / top bar background (translucent for blur) | `[general].background` derived | DER | navbar-text on navbar-bg >= 4.5:1 | `rgba(13,17,23,0.85)` | -- |
| `--blog-overlay-bg` | Modal/overlay dimming layer | derived | DER | -- | `rgba(0,0,0,0.5)` | -- |
| **Borders** | | | | | | |
| `--blog-border-primary` | Main structural border (cards, inputs, dividers) | `[general].border` | D | -- | `#30363d` | `--border` |
| `--blog-border-subtle` | Subtle/secondary border (separators, horizontal rules) | `[general].horizontal_rule` | D | -- | `#30363d` | -- |
| `--blog-border-strong` | Strong emphasis border (active input, focus container) | derived from border-primary | DER | -- | `#484f58` | -- |
| `--blog-border-focus` | Focus ring / outline color | = accent | DER | focus ring visible against bg-page and surface | `#58a6ff` | -- |
| `--blog-navbar-border` | Border below/around navbar | derived from border-primary | DER | -- | `#30363d` | -- |
| **Text** | | | | | | |
| `--blog-text-primary` | Primary body text | `[text].primary` | D | text-primary on bg-page >= 4.5:1; text-primary on surface >= 4.5:1 | `#e6edf3` | `--text` |
| `--blog-text-secondary` | Secondary/emphasized text (bylines, strong inline) | `[buffer].topic` | D | text-secondary on surface >= 4.5:1 | `#c9d1d9` | `--text-secondary` |
| `--blog-text-muted` | Muted/tertiary text (meta, timestamps in prose) | `[text].secondary` | D | text-muted on surface >= 3:1 (large text) | `#8b949e` | `--text-muted` |
| `--blog-text-dim` | Dimmest text (anchors, inactive labels) | `[buffer].timestamp` | D | text-dim on surface >= 3:1 (large text) | `#7d8590` | `--text-dim`, `--text-dim-strong` |
| `--blog-text-on-accent` | Text on accent-colored fills (buttons, badges) | derived (contrast check) | DER | text-on-accent on accent >= 4.5:1 | `#ffffff` | -- |
| `--blog-text-on-success` | Text on success-colored fills | derived (contrast check) | DER | text-on-success on success-bg >= 4.5:1 | `#ffffff` | -- |
| `--blog-text-on-error` | Text on error-colored fills | derived (contrast check) | DER | text-on-error on error-bg >= 4.5:1 | `#ffffff` | -- |
| `--blog-text-on-warning` | Text on warning-colored fills | derived (contrast check) | DER | text-on-warning on warning-bg >= 4.5:1 | `#000000` | -- |
| `--blog-text-on-info` | Text on info-colored fills | derived (contrast check) | DER | text-on-info on info-bg >= 4.5:1 | `#000000` | -- |
| `--blog-text-link` | Link text color | `[buffer].url` | D | link on bg-page >= 4.5:1; link on surface >= 4.5:1 | `#58a6ff` | -- |
| `--blog-text-link-hover` | Link hover color | derived from text-link | DER | link-hover on bg-page >= 4.5:1 | `#79c0ff` | `--accent-hover` |
| **Accent** | | | | | | |
| `--blog-accent` | Primary accent / brand color (links, buttons, highlights) | `[text].tertiary` or `[buffer].border_selected` | D | text-on-accent on accent >= 4.5:1 | `#58a6ff` | `--accent` |
| `--blog-accent-hover` | Accent hover state | derived from accent | DER | -- | `#79c0ff` | `--accent-hover` |
| `--blog-accent-dim` | Subtle accent background (badges, active nav items) | derived from accent | DER | -- | `rgba(88,166,255,0.1)` | `--accent-dim` |
| `--blog-accent-link` | Accent used for interactive links (= accent in most themes) | = accent | DER | link on bg-page >= 4.5:1 | `#58a6ff` | -- |
| `--blog-accent-focus-ring` | Focus ring color (= accent in most themes) | = accent | DER | visible against bg-page and surface | `#58a6ff` | -- |
| **States** | | | | | | |
| `--blog-success-fg` | Success foreground (checkmarks, positive indicators) | `[text].success` | D | success-fg on bg-page >= 4.5:1 | `#3fb950` | `--green` |
| `--blog-success-bg` | Success background (subtle success fill) | derived from success-fg | DER | -- | `rgba(63,185,80,0.15)` | `--green-dim` |
| `--blog-error-fg` | Error foreground (errors, destructive actions) | `[text].error` | D | error-fg on bg-page >= 4.5:1 | `#f85149` | `--red` |
| `--blog-error-bg` | Error background (subtle error fill) | derived from error-fg | DER | -- | `rgba(248,81,73,0.15)` | `--red-dim` |
| `--blog-warning-fg` | Warning foreground (cautions, deprecated) | derived | DER | warning-fg on bg-page >= 4.5:1 | `#d29922` | `--yellow` |
| `--blog-warning-bg` | Warning background (subtle warning fill) | derived from warning-fg | DER | -- | `rgba(210,153,34,0.15)` | `--amber-dim` |
| `--blog-info-fg` | Informational foreground (tips, highlights) | derived | DER | info-fg on bg-page >= 4.5:1 | `#a371f7` | `--purple`, `--amber` |
| `--blog-info-bg` | Informational background (subtle info fill) | derived from info-fg | DER | -- | `rgba(163,113,247,0.15)` | `--purple-dim` |
| **Inputs / Code** | | | | | | |
| `--blog-input-bg` | Input / text field background | `[buffer].background_text_input` | D | input-text on input-bg >= 4.5:1 | `#0d1117` | -- |
| `--blog-input-border` | Input border | derived from border-primary | DER | -- | `#30363d` | -- |
| `--blog-input-text` | Text inside inputs | = text-primary | DER | input-text on input-bg >= 4.5:1 | `#e6edf3` | -- |
| `--blog-code-bg` | Inline code and code block background | `[buffer].background_text_input` | D | code-text on code-bg >= 4.5:1 | `#161b22` | -- |
| `--blog-code-border` | Code block border | `[general].horizontal_rule` derived | DER | -- | `#30363d` | -- |
| `--blog-code-text` | Code text color | derived (accent or tertiary) | DER | code-text on code-bg >= 4.5:1 | `#e6edf3` | -- |
| `--blog-selection-bg` | Text selection highlight | `[buffer].selection` | D | text on selection-bg >= 3:1 | `#30363d` | -- |
| **Navbar / Chrome** | | | | | | |
| `--blog-navbar-text` | Navbar link/text color | = text-primary | DER | navbar-text on navbar-bg >= 4.5:1 | `#e6edf3` | -- |
| `--blog-navbar-text-muted` | Navbar muted/secondary text | = text-muted | DER | -- | `#8b949e` | -- |
| **Overlays** | | | | | | |
| `--blog-shadow-color` | Box shadow / drop shadow color | derived | DER | -- | `rgba(0,0,0,0.15)` | -- |
| **Miscellaneous** | | | | | | |
| `--blog-noscript-bg` | Noscript warning background | derived | DER | -- | `#3b2e00` | `--noscript-bg` |
| `--blog-noscript-text` | Noscript warning text color | derived | DER | noscript-text on noscript-bg >= 4.5:1 | `#d4a017` | `--noscript-text` |
| `--blog-coral` | Coral accent (syntax, secondary accent) | derived | DER | coral on bg-page >= 4.5:1 | `#f78166` | `--coral` |
| `--blog-coral-dim` | Subtle coral background | derived from coral | DER | -- | `rgba(247,129,102,0.15)` | `--coral-dim` |

**Token count:** 44 unique semantic tokens (excluding aliases).

---

## Section B: Halloy to BlogTheme Mapping Table

Each Halloy field maps to one or more `BlogTheme` tokens. Marked D (direct)
when the Halloy value is used as-is, DER (derived) when the translator
computes the output from the Halloy value plus other inputs.

| Halloy field | BlogTheme token(s) | D/DER | Notes |
|---|---|---|---|
| `[general].background` | `bg-page`, `navbar-bg` (with alpha) | D, DER | `navbar-bg` = bg-page with 0.85 alpha |
| `[general].border` | `border-primary`, `input-border` | D | `input-border` = border-primary (can be overridden per-theme) |
| `[general].horizontal_rule` | `border-subtle`, `code-border` | D | `code-border` = horizontal_rule |
| `[general].unread_indicator` | `accent` | D | Semantically an attention color; maps to primary accent |
| `[text].primary` | `text-primary` | D | Direct |
| `[text].secondary` | `text-muted` | D | Halloy "secondary" is blog "muted" |
| `[text].tertiary` | `accent` | D | Theme's accent/highlight color |
| `[text].success` | `success-fg` | D | Direct |
| `[text].error` | `error-fg` | D | Direct |
| `[buffer].action` | `accent` | D | Action color used as secondary accent |
| `[buffer].background` | `surface-default` | D | Buffer content area background |
| `[buffer].background_text_input` | `input-bg`, `code-bg` | D | Shared background for text inputs and code blocks |
| `[buffer].background_title_bar` | `surface-elevated` | D | Elevated/title-bar surface |
| `[buffer].border` | `border-primary` | D | Buffer-level border; may differ from `[general].border` |
| `[buffer].border_selected` | `accent` | D | Selected/bordered element highlight |
| `[buffer].code` | `accent-dim` (secondary accent) | DER | Used as a secondary accent for code syntax |
| `[buffer].highlight` | `surface-hover` | D | Hover/highlight state |
| `[buffer].nickname` | -- | -- | Informational only; not mapped in first pass |
| `[buffer].selection` | `selection-bg` | D | Text selection highlight |
| `[buffer].timestamp` | `text-dim` | D | Dimmest text tier |
| `[buffer].topic` | `text-secondary` | D | Secondary emphasis text |
| `[buffer].url` | `text-link`, `accent` | D | `text-link` = url; `accent` may also use url when distinct |
| `[buffer.server_messages].default` | -- | -- | Informational only; not mapped in first pass |
| `[buttons.primary].background` | `accent` | DER | When distinct from `[general].background`; used for primary button fills |
| `[buttons.primary].background_hover` | `surface-hover` | DER | Button hover surface |
| `[buttons.primary].background_selected` | `surface-active` | DER | Button active/selected surface |
| `[buttons.primary].background_selected_hover` | `surface-active` (brighter) | DER | Active state on hover |
| `[buttons.secondary].background` | `surface-default` | DER | Secondary button = surface |
| `[buttons.secondary].background_hover` | `surface-hover` | DER | Secondary button hover |
| `[buttons.secondary].background_selected` | `accent-dim` | DER | Selected secondary button |
| `[buttons.secondary].background_selected_hover` | `accent-dim` (brighter) | DER | Selected secondary button on hover |

**Mapping notes:**

- Some Halloy fields serve double duty (e.g., `[text].tertiary` and `[buffer].border_selected` both map to `accent`). The translator prefers `[text].tertiary` as the canonical accent source; `[buffer].border_selected` is used only when tertiary is absent.
- `[buffer].background` and `[general].background` are distinct. Buffer background is the content surface; general background is the page background.
- Halloy does not provide warning, info, or coral equivalents. Those are derived from available colors or use the emergency default.
- `[buffer].nickname` and `[buffer.server_messages].default` are informational; they are not translated in the first pass.

---

## Section C: Derived Token Formulas

All formulas assume normalized sRGB input (0-1 range). The translator uses
these in Phase 03 to compute tokens that Halloy does not provide.

### accent-dim

```
accent-dim = composite(accent, alpha=0.10, over=surface-default)
```

In CSS: `rgba(R, G, B, 0.10)` where R/G/B are the accent color channels. For
light themes, composite is performed over the surface background to ensure the
dim fill is visible. The alpha value of 0.10 matches the current `accent-dim`
behavior across all four THEME_PRESETS.

### state-bg (success-bg, error-bg, warning-bg, info-bg)

```
state-bg = composite(state-fg, alpha=0.15, over=surface-default)
```

Uses the corresponding foreground color (`success-fg`, `error-fg`, etc.) at
0.15 alpha composited over the surface background. This matches the current
`-dim` token pattern in THEME_PRESETS (e.g., `green-dim` = `rgba(63,185,80,0.15)`).

### surface-hover

```
surface-hover = lighten(surface-default, 6%)   # dark themes
surface-hover = darken(surface-default, 6%)    # light themes
```

The 6% shift is applied in HSL lightness. The dark/light classification is
determined by the Halloy `[general].background` luminance: if luminance < 0.5
the theme is dark. Current `bg-hover` value `#21262d` is ~6% lighter than
`#161b22`.

### surface-active

```
surface-active = lighten(surface-default, 12%)  # dark themes
surface-active = darken(surface-default, 12%)   # light themes
```

Twice the hover shift. Used for button active states and selected rows.

### text-on-accent

```
text-on-accent = contrast_select(accent, candidate_a=#ffffff, candidate_b=#000000, min_ratio=4.5)
```

Selects whichever of white or black provides >= 4.5:1 contrast ratio against
the accent color. Falls back to the higher-ratio candidate if neither meets
the threshold (documented in diagnostics).

### text-on-state (text-on-success, text-on-error, text-on-warning, text-on-info)

```
text-on-state = contrast_select(state-fg, candidate_a=#ffffff, candidate_b=#000000, min_ratio=4.5)
```

Same algorithm as text-on-accent but using the state foreground as the
background for contrast calculation.

### shadow-color

```
shadow-color = rgba(0, 0, 0, 0.15)   # dark themes
shadow-color = rgba(0, 0, 0, 0.08)   # light themes
```

Fixed values per theme polarity. Not derived from theme colors.

### overlay-bg

```
overlay-bg = rgba(0, 0, 0, 0.5)
```

Fixed for all themes. Modal backdrop / overlay dimming.

### navbar-bg

```
navbar-bg = rgba(bg-page.r, bg-page.g, bg-page.b, 0.85)
```

The page background color with 0.85 alpha to support backdrop-filter blur.
This matches the current light-mode navbar rule at `base.css:244-246`.

### focus-ring / accent-focus-ring

```
accent-focus-ring = accent
```

Equal to the accent color. If accent contrast against both bg-page and
surface-default is below 3:1, the translator logs a diagnostic warning.

### accent-hover

```
accent-hover = lighten(accent, 10%)   # dark themes
accent-hover = darken(accent, 10%)    # light themes
```

A perceptually brighter variant of accent for hover states. The 10% shift is
in HSL lightness.

### link-hover

```
text-link-hover = accent-hover
```

Links use the accent-hover color on hover.

### input-text, navbar-text, navbar-text-muted

These are identity mappings:

```
input-text = text-primary
navbar-text = text-primary
navbar-text-muted = text-muted
```

No computation required; the translator copies the value.

### noscript-bg, noscript-text, coral, coral-dim

These are legacy hue-based tokens with no Halloy source. The translator uses
the emergency default values for themes that do not provide equivalents. They
are candidates for removal in Phase 14 but retained for backward compatibility.

---

## Section D: Packaged Resource Layout Decision

### Chosen layout

```text
app/themes/
    __init__.py
    model.py
    translate.py
    diagnostics.py
    bundled/
        __init__.py
        *.toml
    ATTRIBUTION.md
```

### Directory structure

| Path | Purpose | Created in |
|---|---|---|
| `app/themes/__init__.py` | Package marker | Phase 03 |
| `app/themes/model.py` | `BlogTheme` dataclass / typed model | Phase 03 |
| `app/themes/translate.py` | Halloy-to-BlogTheme translator | Phase 03 |
| `app/themes/diagnostics.py` | Contrast warnings, provenance | Phase 03 |
| `app/themes/bundled/__init__.py` | Sub-package marker for resource access | Phase 05 |
| `app/themes/bundled/*.toml` | Packaged Halloy theme files | Phase 05 |
| `app/themes/ATTRIBUTION.md` | Upstream attribution and license | Phase 05 |

### Relationship to top-level `themes/`

- **`themes/`** (repository root): The canonical source catalog. Theme
  authors develop and review files here. This is the human-facing directory.
- **`app/themes/bundled/`**: The package copy. Phase 05 will add a CI check
  that verifies `themes/*.toml` (excluding `._*` macOS resource forks and any
  excluded files listed in a manifest) are byte-identical to
  `app/themes/bundled/*.toml`.
- **External themes** (runtime): Live outside the Python package at a
  configured path (default empty string; Docker convention:
  `/app/data/themes`). External themes override bundled themes of the same
  filename.

### Resource accessor pattern

Use `importlib.resources` (Python 3.9+; project requires 3.12+). Never use
`Path(__file__).parent.parent.parent` or any cwd-relative lookup.

```python
from importlib.resources import files

def get_bundled_themes_dir():
    """Return the Traversable directory containing bundled .toml themes."""
    return files("app.themes.bundled")

def list_bundled_themes():
    """List all .toml files in the bundled themes directory."""
    themes_dir = get_bundled_themes_dir()
    return [f for f in themes_dir.iterdir() if f.name.endswith(".toml")]
```

### Packaging requirements

| Artifact | File | Phase | Notes |
|---|---|---|---|
| Package data declaration | `pyproject.toml` `[tool.setuptools.package-data]` | Phase 05 | `"app.themes.bundled" = ["*.toml"]` |
| Source distribution inclusion | `MANIFEST.in` | Phase 05 | `recursive-include app/themes/bundled *.toml` |
| Wheel inclusion | automatic via package-data | Phase 05 | Verify with `wheel unpack` test |
| Editable install | automatic via package-data | Phase 05 | Verify with `pip install -e .` |

### Wheel-installable requirements

- No `cwd`-relative paths anywhere in theme loading code.
- `importlib.resources` is the only resource access mechanism.
- The application must work when installed as a wheel into a virtualenv
  outside the repository root.

---

## Section E: Migration Compatibility Aliases

Every key currently emitted by `THEME_PRESETS` in `app/models.py` lines
366-457 must have a backward-compatible alias until Phase 14 cleanup. The
`name` key is metadata and is not a CSS variable.

| Current key | Default fallback (github-dark) | New semantic token | Rename or alias | Removal target |
|---|---|---|---|---|
| `bg` | `#0d1117` | `--blog-bg-page` | Direct rename | Phase 14 |
| `bg-surface` | `#161b22` | `--blog-surface-default` | Direct rename | Phase 14 |
| `bg-elevated` | `#1c2128` | `--blog-surface-elevated` | Direct rename | Phase 14 |
| `border` | `#30363d` | `--blog-border-primary` | Direct rename | Phase 14 |
| `text` | `#e6edf3` | `--blog-text-primary` | Direct rename | Phase 14 |
| `text-muted` | `#8b949e` | `--blog-text-muted` | Direct rename | Phase 14 |
| `text-dim` | `#7d8590` | `--blog-text-dim` | Direct rename | Phase 14 |
| `text-dim-strong` | `#9ca3af` | `--blog-text-dim` | Alias (same target as text-dim) | Phase 14 |
| `text-secondary` | `#c9d1d9` | `--blog-text-secondary` | Direct rename | Phase 14 |
| `accent` | `#58a6ff` | `--blog-accent` | Direct rename | Phase 14 |
| `accent-hover` | `#79c0ff` | `--blog-accent-hover` | Direct rename | Phase 14 |
| `accent-dim` | `rgba(88,166,255,0.1)` | `--blog-accent-dim` | Direct rename | Phase 14 |
| `green` | `#3fb950` | `--blog-success-fg` | Semantic rename | Phase 14 |
| `green-dim` | `rgba(63,185,80,0.15)` | `--blog-success-bg` | Semantic rename | Phase 14 |
| `red` | `#f85149` | `--blog-error-fg` | Semantic rename | Phase 14 |
| `red-dim` | `rgba(248,81,73,0.15)` | `--blog-error-bg` | Semantic rename | Phase 14 |
| `yellow` | `#d29922` | `--blog-warning-fg` | Semantic rename | Phase 14 |
| `purple` | `#a371f7` | `--blog-info-fg` | Semantic rename | Phase 14 |
| `purple-dim` | `rgba(163,113,247,0.15)` | `--blog-info-bg` | Semantic rename | Phase 14 |
| `coral` | `#f78166` | `--blog-coral` | Alias (no semantic rename) | Phase 14 |
| `coral-dim` | `rgba(247,129,102,0.15)` | `--blog-coral-dim` | Alias (no semantic rename) | Phase 14 |
| `amber` | `#f59e0b` | `--blog-info-fg` | Alias (maps to same as purple) | Phase 14 |
| `amber-dim` | `rgba(245,158,11,0.15)` | `--blog-warning-bg` | Semantic rename | Phase 14 |
| `bg-hover` | `#21262d` | `--blog-surface-hover` | Semantic rename | Phase 14 |
| `noscript-bg` | `#3b2e00` | `--blog-noscript-bg` | Alias (no semantic rename) | Phase 14 |
| `noscript-text` | `#d4a017` | `--blog-noscript-text` | Alias (no semantic rename) | Phase 14 |
| `name` | `"GitHub Dark"` | -- | Metadata key; not a CSS variable | Phase 14 |

**Alias count:** 27 (including `name` as metadata-only; 26 CSS variable
aliases).

**Ambiguity resolved:** `amber` and `purple` both map to `--blog-info-fg`.
The current presets use them as distinct hues, but the semantic model collapses
them into a single "info" concept. If a Halloy theme provides both a purple
and an amber, the translator will prefer the one closer to the `[text].tertiary`
value; the other is discarded. The `amber-dim` alias maps to
`--blog-warning-bg` because amber is semantically closer to warning in the
existing presets.

---

## Section F: Token Coverage Check

Every token key emitted by `THEME_PRESETS` in `app/models.py` (lines 366-457)
is accounted for:

| THEME_PRESETS key | BlogTheme mapping |
|---|---|
| `bg` | `--blog-bg-page` |
| `bg-surface` | `--blog-surface-default` |
| `bg-elevated` | `--blog-surface-elevated` |
| `border` | `--blog-border-primary` |
| `text` | `--blog-text-primary` |
| `text-muted` | `--blog-text-muted` |
| `text-dim` | `--blog-text-dim` |
| `text-dim-strong` | `--blog-text-dim` (alias) |
| `accent` | `--blog-accent` |
| `accent-hover` | `--blog-accent-hover` |
| `accent-dim` | `--blog-accent-dim` |
| `green` | `--blog-success-fg` |
| `green-dim` | `--blog-success-bg` |
| `red` | `--blog-error-fg` |
| `red-dim` | `--blog-error-bg` |
| `yellow` | `--blog-warning-fg` |
| `purple` | `--blog-info-fg` |
| `purple-dim` | `--blog-info-bg` |
| `coral` | `--blog-coral` |
| `coral-dim` | `--blog-coral-dim` |
| `amber` | `--blog-info-fg` |
| `amber-dim` | `--blog-warning-bg` |
| `bg-hover` | `--blog-surface-hover` |
| `noscript-bg` | `--blog-noscript-bg` |
| `noscript-text` | `--blog-noscript-text` |
| `name` | (metadata, not a CSS variable) |

No current CSS variable is left without a semantic replacement. Every
`THEME_PRESETS` key maps to exactly one `BlogTheme` token.

---

## Ambiguities Resolved

1. **`amber` vs `purple` for info-fg:** Both map to `--blog-info-fg`. The
   translator will prefer the Halloy `[text].tertiary` value as the canonical
   accent, which typically aligns with one of these hues. The non-preferred
   hue is retained only as an alias for backward compatibility.

2. **`amber-dim` mapped to warning-bg, not info-bg:** In the existing presets,
   amber is closer to warning semantics (golden/caution) than to info
   (purple). `amber-dim` therefore maps to `--blog-warning-bg`.

3. **`text-dim-strong` maps to `text-dim`:** This key exists in `THEME_PRESETS`
   but not in `base.css` CSS variables. It is treated as an alias for
   `--blog-text-dim`. The translator uses `text-dim` as the canonical source;
   `text-dim-strong` is ignored if present in Halloy themes.

4. **`[buffer].code` as secondary accent:** Halloy's buffer code color is a
   distinct hue (e.g., `#8FBCBB` in Nord, `#FF79C6` in Dracula). It does not
   map to `--blog-code-text` because code text should match the primary text
   hierarchy. Instead, it is used as `--blog-accent-dim` or a secondary
   accent for syntax highlighting only.

5. **`[buffer].nickname` not mapped:** This field provides per-nick colors for
   IRC. The blog has no per-user color system. It is documented as
   informational only.

6. **Navbar blur alpha (0.85):** Derived from the existing light-mode navbar
   rule at `base.css:244` (`rgba(246, 248, 250, 0.85)`). This value is used
   for both light and dark themes.

7. **Missing state colors (warning, info):** Halloy provides only success and
   error in `[text]`. Warning and info are derived from available palette
   colors (yellow/amber for warning, purple for info) or fall back to the
   emergency default values.

## Tokens with Unclear Halloy Source

These tokens have no direct Halloy equivalent and are always derived:

- `--blog-warning-fg` / `--blog-warning-bg`: No `[text].warning` in Halloy.
  Derived from yellow/amber or emergency default.
- `--blog-info-fg` / `--blog-info-bg`: No `[text].info` in Halloy.
  Derived from purple or emergency default.
- `--blog-noscript-bg` / `--blog-noscript-text`: No Halloy equivalent.
  Legacy blog-specific tokens; emergency default only.
- `--blog-coral` / `--blog-coral-dim`: No Halloy equivalent. Legacy
  blog-specific tokens; emergency default only.
- `--blog-shadow-color`: No Halloy equivalent. Fixed per theme polarity.
- `--blog-overlay-bg`: No Halloy equivalent. Fixed `rgba(0,0,0,0.5)`.
