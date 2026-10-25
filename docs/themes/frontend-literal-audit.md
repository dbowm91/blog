# Frontend Hardcoded Colour Literal Audit

An audit of hardcoded colour literals in the non-Prism stylesheets, templates and
JavaScript, and the record of which ones were converted to semantic theme tokens
and which were deliberately kept.

**Scope**: `app/static/css/` (excluding `prism*.css`), templates (excluding
email templates), and JavaScript under `app/static/js/`.

**Method**: regex search for `#RRGGBB`, `#RRGGBBAA` and `rgb()`/`rgba()` across the
target files, classified manually.

---

## Current State

Every literal that should be themeable is now a CSS custom property. The
stylesheets consume the legacy alias names (`--bg`, `--text`, `--accent`, …),
which the theme system emits from the `BlogTheme` token model.

The remaining literals fall into four groups: structural fallbacks, forced print
colours, invariant brand colours, and theme-agnostic shadows.

### Literals by File

| File | Literals | Category |
|------|----------|----------|
| `app/static/css/base.css` | 50 | 25 structural fallback variables, 3 `var()` fallbacks, 1 hero gradient, 21 print stylesheet |
| `app/static/css/public.css` | 17 | 1 hero gradient, 15 social share brand colours, 1 lightbox backdrop |
| `app/static/css/critical.css` | 7 | Structural fallback variables in `:root` |
| `app/static/css/layout.css` | 1 | Neutral box shadow |
| `app/static/css/admin.css` | 0 | — |
| `app/static/css/forms.css` | 0 | — |
| `app/static/css/utilities.css` | 0 | — |
| `app/static/js/**` | 0 | — |
| Templates (non-email) | 0 | — |
| `app/static/css/prism*.css` | not audited | Prism syntax highlighting, separate system |
| Email templates | not audited | Email clients do not support CSS custom properties |

### Retained Literals and Why

| Group | Count | Reason |
|-------|-------|--------|
| `:root` structural fallback palette in `base.css` and `critical.css` | 25 + 7 | Fallback values for the CSS custom properties, used before the inline theme style is applied and if the theme service fails. Overwritten at runtime by the injected `theme_vars`. |
| `var()` fallback values | 3 | `.btn-warning` uses `var(--amber-dim, #5c4a00)`, `var(--amber, #f59e0b)`. The fallback keeps the button readable if the variable is unset. |
| Print stylesheet | 21 | Forced print colours, including a `[data-color-scheme="light"]` variable block scoped to `@media print`. Not themeable. |
| Social share brand colours | 15 | Twitter, LinkedIn, Hacker News, Reddit and Facebook brand colours. Invariant brand identity, not themeable. |
| Hero overlay gradient | 2 | `rgba(0, 0, 0, 0.4)` in `base.css` and `public.css`. Intentionally near-black for text contrast over the hero image. |
| Lightbox backdrop | 1 | `rgba(0, 0, 0, 0.9)`. Intentionally darker than the standard overlay. |
| Neutral box shadow | 1 | `rgba(0, 0, 0, 0.15)` in `layout.css`. Theme-agnostic elevation shadow. |

---

## Classification Taxonomy

| Code | Definition |
|------|-----------|
| **REPLACE** | Literal became a semantic theme token. None remain. |
| **RETAIN** | Invariant brand or structural value that cannot or should not be themed. |
| **REMOVED** | Block or literal removed during the migration (for example the screen-level static light palette, moved to inline theme injection). |
| **SYNTAX** | Belongs to Prism syntax highlighting; a separate system, out of scope. |
| **COMPAT** | Temporary compatibility value kept during the migration. None remain. |
| **FALSE_POSITIVE** | Not actually a colour — URL fragments, `currentColor`, brightness filter values, ID selectors. |

---

## What Was Converted

The themeable literals were replaced with CSS custom properties backed by the
`ALIASES` map in `app/themes/model.py`:

- **`base.css`** — button and skip-link colours now use `var(--text-on-accent)`,
  `var(--amber)` and `var(--amber-dim)` with hex fallbacks. The noscript warning
  uses `var(--yellow)`, `var(--noscript-bg)` and `var(--noscript-text)`.
- **`critical.css`** — the navbar background uses `var(--navbar-bg)`.
- **`layout.css`** — the mobile overlay uses `var(--overlay-bg)`.
- **`admin.css`** — flash and toast borders use `var(--success-bg)`,
  `var(--error-bg)` and `var(--warning-bg)`; shadows use `var(--shadow-color)`;
  overlays use `var(--overlay-bg)`; the scheduled badge uses `var(--purple-dim)`.
- **`public.css`** — shadows use `var(--shadow-color)`; the active tag uses
  `var(--accent-dim)`; the lightbox caption uses `var(--text-on-accent)`.

All 38 legacy CSS variables are now emitted for every theme by
`to_legacy_vars()`. `tests/themes/test_phase09_css_tokens.py` verifies the
completeness of the emitted set.

Every `var(--…)` reference in the stylesheets resolves to one of the 38 aliases.
The only other custom properties in use are non-colour layout tokens
(`--space-*`, `--radius*`, `--transition`, `--font-sans`, `--font-mono`,
`--post-list-cols`) and the appearance-layer tokens `--backdrop-image` and
`--backdrop-tint`.

---

## First-Paint Behaviour

`critical.css` is loaded with `media="screen"` so the above-the-fold paint is not
delayed. `base.css`, `layout.css`, `public.css`, `forms.css` and
`utilities.css` are loaded asynchronously with `media="print"` and switched to
`media="all"` on load. `critical.css` carries its own `:root` fallback palette,
which is why it holds 7 hardcoded values rather than depending on `base.css`.

The no-flash problem is addressed by the bootstrap script in the page head: it
reads `blog-color-scheme` from `localStorage`, resolves `system` through
`matchMedia`, and sets `data-color-scheme` on `<html>` before first paint. The
screen-level static `[data-color-scheme="light"]` palette block was removed in
Phase 08; light-theme variables are provided by the inline `<style>` block that
the theme context processor fills in.

## Runtime Injection

The inline `<style>` block in `base.html` and `admin/base.html` emits two
variable scopes:

```css
:root,
[data-color-scheme="dark"] { /* theme_dark_vars */ }

[data-color-scheme="light"] { /* theme_light_vars */ }
```

Both come from `to_legacy_vars()`, so every alias in `ALIASES` is available to
the stylesheets. `custom_css` is emitted after the theme variables, so operator
overrides still win.

## See Also

- [BlogTheme token contract](blog-theme-contract.md) — the tokens and the 38
  aliases the stylesheets consume
- [Theme architecture](../../architecture/core/themes.md) — the module reference
  for `app/themes/`
- [Static assets](../../architecture/frontend/static-assets.md) — the Vite build
  and asset pipeline
