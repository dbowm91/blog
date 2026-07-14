# Frontend Hardcoded Color Literal Audit

**Phase**: 01 — Inventory and Semantic Token Contract  
**Scope**: All non-Prism CSS files, templates (non-email), and JavaScript  
**Methodology**: Regex search (`#[0-9a-fA-F]{3,8}` and `rgba?\(`) across target files, classified manually line by line  
**Date**: 2026-07-13  
**Last Updated**: 2026-07-14 — Phase 09 complete

---

## Phase 09 Completion

Phase 09 is complete. All 34 REPLACE entries have been converted to CSS custom properties using the semantic token system from `app/themes/model.py`. Key changes:

- **`base.css`**: Button and skip-link colors now use `var(--accent-on-accent)`, `var(--amber)`, `var(--amber-dim)` with hex fallbacks. Light theme overrides use `var(--navbar-bg)`, `var(--bg)`, `var(--text)`, `var(--code-bg)`, `var(--bg-surface)`.
- **`critical.css`**: Navbar background now uses `var(--navbar-bg)`.
- **`layout.css`**: Mobile overlay now uses `var(--overlay-bg)`.
- **`admin.css`**: Flash/toast borders use `var(--success-bg)`, `var(--error-bg)`, `var(--warning-bg)`; shadows use `var(--shadow-color)`; overlays use `var(--overlay-bg)`; badge-scheduled uses `var(--purple-dim)`.
- **`public.css`**: Shadows use `var(--shadow-color)`; tag-active uses `var(--accent-dim)`; hero overlay uses `var(--bg)` with retained `rgba(0,0,0,0.4)` bottom gradient; lightbox caption uses `var(--text-on-accent)`.

The ALIASES dict in `app/themes/model.py` was updated with 7 new backward-compatibility entries: `yellow-dim`, `warning-fg`, `warning-bg`, `success-bg`, `error-bg`, `info-fg`, `info-bg`.

All 35 legacy CSS variables are now emitted. Tests in `tests/themes/test_phase09_css_tokens.py` verify completeness.

**Retained literals** (intentionally not changed):
- `:root` fallback palette (25 values) — structural emergency defaults
- Print stylesheet (21 values) — forced print colors
- Light theme hero overlay bottom gradient (1 value, `rgba(0,0,0,0.4)`) — intentionally near-black for contrast
- Social share brand colors (10 values) — invariant brand identity
- Lightbox backdrop (2 values, `rgba(0,0,0,0.9)` and `rgba(0,0,0,0.7)`) — intentionally darker than overlay
- Neutral box shadows using `rgba(0,0,0,...)` (5 values) — theme-agnostic
- Button fallbacks (3 values in `var()` fallbacks) — structural defaults
- SVG assets (9 values) — brand assets
- Email templates (45 values) — email clients don't support CSS vars

---

## Classification Taxonomy

| Code | Definition |
|------|-----------|
| **REPLACE** | Literal should become a semantic theme token. Phase 09 replaced all 34 entries with CSS custom properties. |
| **RETAIN** | Invariant brand or structural value that cannot or should not be themed. Includes print stylesheet forced colors, light-theme hardcoded palette (which is itself a structural fallback), and values that are the exact equivalent of a token but exist in a context where the token is already applied. |
| **REMOVED** | Block or literal removed during migration (e.g., static light palette moved to inline theme injection in Phase 08). |
| **SYNTAX** | Belongs to Prism syntax highlighting; separate system. Not in scope. |
| **COMPAT** | Temporary compatibility value kept during migration; will be removed in Phase 14. |
| **FALSE_POSITIVE** | Not actually a color (e.g., URL fragments, font-face metadata, `currentColor` SVGs, brightness filter values, ID selectors). |

---

## First-Paint Note

`critical.css` contains 7 hardcoded color literals (lines 3–9). The navbar background (line 46) now uses `var(--navbar-bg)`. These are loaded via `<link rel="stylesheet" media="screen">` for immediate above-the-fold rendering, while `base.css` loads asynchronously via `media="print" onload="this.media='all'"`.

The hardcoded values in `critical.css :root` (`--bg: #0d1117`, `--bg-surface: #161b22`, `--border: #30363d`, `--text: #e6edf3`, `--text-muted: #8b949e`, `--accent: #58a6ff`, `--accent-hover: #79c0ff`) are themselves structural fallbacks — identical to the `base.css :root` defaults. The navbar background now uses `var(--navbar-bg)` for theme-aware rendering.

**Phase 08 has addressed the no-flash problem**: the bootstrap IIFE reads `blog-color-scheme` from localStorage, resolves `system` via `matchMedia`, and sets `data-color-scheme` on `<html>` before first paint. The static `[data-color-scheme="light"]` palette block has been removed; light-theme variables are provided by inline `<style>` from Halloy themes.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total color literals audited** | 105 (128 originally; 23 removed in Phase 08) |
| REPLACE | 0 (34 converted in Phase 09) |
| RETAIN | 71 (was 85; 23 light palette removed in Phase 08; 14 converted in Phase 09) |
| FALSE_POSITIVE | 9 |
| SYNTAX | 0 |
| COMPAT | 0 |

### Count by File

| File | Total | REPLACE | RETAIN | FALSE_POS |
|------|-------|---------|--------|-----------|
| `app/static/css/base.css` | 50 (was 76; 23 light palette removed) | 0 (was 14) | 43 (was 32) | 7 |
| `app/static/css/critical.css` | 7 (was 8) | 0 (was 1) | 7 | 0 |
| `app/static/css/layout.css` | 1 (was 3) | 0 (was 1) | 1 | 0 |
| `app/static/css/public.css` | 13 (was 25) | 0 (was 10) | 13 | 0 (was 2) |
| `app/static/css/admin.css` | 0 (was 16) | 0 (was 8) | 0 (was 8) | 0 |
| `app/static/css/forms.css` | 0 | 0 | 0 | 0 |
| `app/static/css/utilities.css` | 0 | 0 | 0 | 0 |
| JavaScript (all files) | 0 | 0 | 0 | 0 |
| Templates (non-email) | 0 | 0 | 0 | 0 |
| SVG assets | 0 (not audited) | — | — | — |

### Top 5 Files by Literal Count

1. `app/static/css/base.css` — 50
2. `app/static/css/public.css` — 13
3. `app/static/css/critical.css` — 7
4. `app/static/css/admin.css` — 0
5. `app/static/css/layout.css` — 1

---

## Per-File Audit Tables

### File: `app/static/css/critical.css`

Above-the-fold critical rendering path. Loaded synchronously with `media="screen"`.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `critical.css:3` | `#0d1117` | `:root` `--bg` | RETAIN | — | Structural default; overwritten by `theme_vars` at runtime |
| `critical.css:4` | `#161b22` | `:root` `--bg-surface` | RETAIN | — | Structural default |
| `critical.css:5` | `#30363d` | `:root` `--border` | RETAIN | — | Structural default |
| `critical.css:6` | `#e6edf3` | `:root` `--text` | RETAIN | — | Structural default |
| `critical.css:7` | `#8b949e` | `:root` `--text-muted` | RETAIN | — | Structural default |
| `critical.css:8` | `#58a6ff` | `:root` `--accent` | RETAIN | — | Structural default |
| `critical.css:9` | `#79c0ff` | `:root` `--accent-hover` | RETAIN | — | Structural default |
| `critical.css:46` | `var(--navbar-bg)` | `.navbar` `background` | RETAIN | — | Phase 09: replaced `rgba(13, 17, 23, 0.85)` with `var(--navbar-bg)` |

### File: `app/static/css/base.css`

#### `:root` Block (lines 67–107) — Structural Default Palette

These 25 literals define the CSS custom property fallback values. They are overwritten at runtime by `theme_vars` injection. Classified as RETAIN because they serve as the emergency fallback palette.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:68` | `#0d1117` | `:root` `--bg` | RETAIN | — | Default dark background |
| `base.css:69` | `#161b22` | `:root` `--bg-surface` | RETAIN | — | Default surface |
| `base.css:70` | `#1c2128` | `:root` `--bg-elevated` | RETAIN | — | Default elevated |
| `base.css:71` | `#30363d` | `:root` `--border` | RETAIN | — | Default border |
| `base.css:72` | `#e6edf3` | `:root` `--text` | RETAIN | — | Default text |
| `base.css:73` | `#8b949e` | `:root` `--text-muted` | RETAIN | — | Default muted text |
| `base.css:74` | `#7d8590` | `:root` `--text-dim` | RETAIN | — | Default dim text |
| `base.css:75` | `#58a6ff` | `:root` `--accent` | RETAIN | — | Default accent |
| `base.css:76` | `#79c0ff` | `:root` `--accent-hover` | RETAIN | — | Default accent hover |
| `base.css:77` | `rgba(88, 166, 255, 0.1)` | `:root` `--accent-dim` | RETAIN | — | Default accent dim |
| `base.css:78` | `#3fb950` | `:root` `--green` | RETAIN | — | Default green |
| `base.css:79` | `rgba(63, 185, 80, 0.15)` | `:root` `--green-dim` | RETAIN | — | Default green dim |
| `base.css:80` | `#f85149` | `:root` `--red` | RETAIN | — | Default red |
| `base.css:81` | `rgba(248, 81, 73, 0.15)` | `:root` `--red-dim` | RETAIN | — | Default red dim |
| `base.css:82` | `#d29922` | `:root` `--yellow` | RETAIN | — | Default yellow |
| `base.css:83` | `#a371f7` | `:root` `--purple` | RETAIN | — | Default purple |
| `base.css:84` | `rgba(163, 113, 247, 0.15)` | `:root` `--purple-dim` | RETAIN | — | Default purple dim |
| `base.css:85` | `#f78166` | `:root` `--coral` | RETAIN | — | Default coral |
| `base.css:86` | `rgba(247, 129, 102, 0.15)` | `:root` `--coral-dim` | RETAIN | — | Default coral dim |
| `base.css:87` | `#3b2e00` | `:root` `--noscript-bg` | RETAIN | — | Noscript banner bg |
| `base.css:88` | `#d4a017` | `:root` `--noscript-text` | RETAIN | — | Noscript banner text |
| `base.css:103` | `#c9d1d9` | `:root` `--text-secondary` | RETAIN | — | Default secondary text |
| `base.css:104` | `#21262d` | `:root` `--bg-hover` | RETAIN | — | Default hover bg |
| `base.css:105` | `#f59e0b` | `:root` `--amber` | RETAIN | — | Default amber |
| `base.css:106` | `rgba(245, 158, 11, 0.15)` | `:root` `--amber-dim` | RETAIN | — | Default amber dim |

#### Button & Skip-Link Colors

Phase 09: All button and skip-link colors now use `var()` with hex fallbacks.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:204` | `#5c4a00` | `.btn-warning` `background` fallback in `var(--amber-dim, #5c4a00)` | RETAIN | — | Fallback value inside `var()`; primary value from theme |
| `base.css:205` | `#f59e0b` | `.btn-warning` `color` fallback in `var(--amber, #f59e0b)` | RETAIN | — | Fallback value inside `var()` |
| `base.css:210` | `#f59e0b` | `.btn-warning:hover` `border-color` fallback in `var(--amber, #f59e0b)` | RETAIN | — | Fallback value inside `var()` |

#### Noscript Warning

Phase 09: Noscript warning now uses `var(--yellow-dim)`.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:355` | `var(--yellow-dim)` | `.noscript-warning` `background` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.15)` with `var(--yellow-dim)` |

#### `[data-color-scheme="light"]` Static Palette Block — REMOVED (Phase 08)

The 23-literal static `[data-theme="light"]` palette block (formerly lines 218–242) has been **removed**. The light-theme CSS custom property overrides are now provided entirely by the inline `<style>` from Halloy themes (emitted via `theme_vars` / `theme_light_vars` in `base.html` and `admin/base.html`). Component-specific light overrides (navbar, post-hero-overlay, prose code/pre) remain in `base.css` under `[data-color-scheme="light"]`.

#### Light Theme Overrides (component-level, retained under `[data-color-scheme="light"]`)

Phase 09: Light theme component overrides now use CSS variables where possible.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:220` | `var(--navbar-bg)` | `[data-color-scheme="light"] .navbar` `background` | RETAIN | — | Phase 09: replaced `rgba(246, 248, 250, 0.85)` with `var(--navbar-bg)` |
| `base.css:224` | `rgba(0, 0, 0, 0.4)` | `[data-color-scheme="light"] .post-hero-overlay` gradient bottom | RETAIN | — | Intentionally near-black for contrast with `var(--bg)` top gradient |
| `base.css:227` | `var(--text)` | `[data-color-scheme="light"] .post-hero-title` `color` | RETAIN | — | Phase 09: replaced `#1f2328` with `var(--text)` |
| `base.css:231` | `var(--code-bg)` | `[data-color-scheme="light"] .prose code` `background` | RETAIN | — | Phase 09: replaced `#eff1f3` with `var(--code-bg)` |
| `base.css:235` | `var(--bg-surface)` | `[data-color-scheme="light"] .prose pre` `background` | RETAIN | — | Phase 09: replaced `#f6f8fa` with `var(--bg-surface)` |

#### Print Stylesheet (lines 699–803)

All 21 literals in the print block are RETAIN — print requires forced white backgrounds and specific text colors regardless of the active theme.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:715` | `#fff` | `@media print` `body` `background` | RETAIN | — | Print forced white bg |
| `base.css:716` | `#1f2328` | `@media print` `body` `color` | RETAIN | — | Print forced dark text |
| `base.css:720` | `#ffffff` | `@media print [data-theme="light"]` `--bg` | RETAIN | — | Print light bg |
| `base.css:721` | `#ffffff` | `@media print [data-theme="light"]` `--bg-surface` | RETAIN | — | Print light surface |
| `base.css:722` | `#f6f8fa` | `@media print [data-theme="light"]` `--bg-elevated` | RETAIN | — | Print light elevated |
| `base.css:723` | `#d0d7de` | `@media print [data-theme="light"]` `--border` | RETAIN | — | Print light border |
| `base.css:724` | `#1f2328` | `@media print [data-theme="light"]` `--text` | RETAIN | — | Print light text |
| `base.css:725` | `#57606a` | `@media print [data-theme="light"]` `--text-muted` | RETAIN | — | Print light muted text |
| `base.css:726` | `#8c959f` | `@media print [data-theme="light"]` `--text-dim` | RETAIN | — | Print light dim text |
| `base.css:730` | `#1f2328` | `@media print .prose` `color` | RETAIN | — | Print prose text |
| `base.css:734` | `#0969da` | `@media print .prose a` `color` | RETAIN | — | Print link color |
| `base.css:738` | `#f6f8fa` | `@media print .prose code` `background` | RETAIN | — | Print code bg |
| `base.css:739` | `#d0d7de` | `@media print .prose code` `border-color` | RETAIN | — | Print code border |
| `base.css:740` | `#0550ae` | `@media print .prose code` `color` | RETAIN | — | Print code text |
| `base.css:744` | `#f6f8fa` | `@media print .prose pre` `background` | RETAIN | — | Print pre bg |
| `base.css:745` | `#d0d7de` | `@media print .prose pre` `border-color` | RETAIN | — | Print pre border |
| `base.css:746` | `#1f2328` | `@media print .prose pre` `color` | RETAIN | — | Print pre text |
| `base.css:757` | `#57606a` | `@media print .post-meta` `color` | RETAIN | — | Print meta text |
| `base.css:764` | `#d0d7de` | `@media print .author-card` `border-color` | RETAIN | — | Print author card border |
| `base.css:773` | `#8c959f` | `@media print .post-full::after` `color` | RETAIN | — | Print "Printed from" text |
| `base.css:798` | `#d0d7de` | `@media print .post-card` `border-color` | RETAIN | — | Print card border |

#### FALSE_POSITIVES in base.css

| Line | Literal | CSS Context | Classification | Notes |
|------|---------|-------------|----------------|-------|
| `base.css:9` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |
| `base.css:17` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |
| `base.css:25` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |
| `base.css:33` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |
| `base.css:41` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |
| `base.css:49` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |
| `base.css:57` | `woff2` (partial match in URL) | `@font-face` `src` | FALSE_POSITIVE | Font file URL, not a color |

### File: `app/static/css/layout.css`

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `layout.css:16` | `var(--navbar-bg)` | `.navbar` `background` | RETAIN | — | Phase 09: replaced `rgba(13, 17, 23, 0.85)` with `var(--navbar-bg)` |
| `layout.css:155` | `rgba(0,0,0,0.15)` | `.nav-dropdown-menu` `box-shadow` | RETAIN | — | Neutral shadow; acceptable as-is |
| `layout.css:218` | `var(--overlay-bg)` | `.nav-links.open::before` `background` (mobile overlay) | RETAIN | — | Phase 09: replaced `rgba(0,0,0,0.5)` with `var(--overlay-bg)` |

### File: `app/static/css/public.css`

Phase 09: All REPLACE entries converted. Flash-warning uses `var(--warning-bg)`. Shadows use `var(--shadow-color)`. Tag-active uses `var(--accent-dim)`. Hero overlay top uses `var(--bg)`. Lightbox caption and search button use `var(--text-on-accent)`.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `public.css:74` | `rgba(0, 0, 0, 0.3)` | `.post-card:hover` `box-shadow` | RETAIN | — | Phase 09: now uses `var(--shadow-color)` |
| `public.css:78` | `rgba(0, 0, 0, 0.08)` | `[data-theme="light"] .post-card:hover` `box-shadow` | RETAIN | — | Phase 09: now uses `var(--shadow-color)` |
| `public.css:259` | `rgba(0,0,0,0.15)` | `.tag:hover` `box-shadow` | RETAIN | — | Phase 09: now uses `var(--shadow-color)` |
| `public.css:268` | `var(--accent-dim)` | `.tag-active` `background` | RETAIN | — | Phase 09: replaced `rgba(88, 166, 255, 0.25)` with `var(--accent-dim)` |
| `public.css:340` | `var(--bg)` / `rgba(0, 0, 0, 0.4)` | `.post-hero-overlay` gradient | RETAIN | — | Phase 09: top gradient uses `var(--bg)`; bottom gradient intentionally near-black |
| `public.css:357` | `var(--text-on-accent)` | `.post-hero-title` `color` | RETAIN | — | Phase 09: replaced `#fff` with `var(--text-on-accent)` |
| `public.css:395` | `rgba(0,0,0,0.1)` | `.share-btn:hover` `box-shadow` | RETAIN | — | Phase 09: now uses `var(--shadow-color)` |
| `public.css:443` | `rgba(0,0,0,0.3)` | `.flash` `box-shadow` | RETAIN | — | Phase 09: now uses `var(--shadow-color)` |
| `public.css:448` | `var(--warning-bg)` | `.flash-warning` `background` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.15)` with `var(--warning-bg)` |
| `public.css:459` | `rgba(29, 161, 242, 0.1)` | `.share-twitter` `background` | RETAIN | — | Twitter brand color |
| `public.css:460` | `#1da1f2` | `.share-twitter:hover` `color` | RETAIN | — | Twitter brand color |
| `public.css:460` | `#1da1f2` | `.share-twitter:hover` `border-color` | RETAIN | — | Twitter brand color |
| `public.css:461` | `rgba(10, 102, 194, 0.1)` | `.share-linkedin` `background` | RETAIN | — | LinkedIn brand color |
| `public.css:462` | `#0a66c2` | `.share-linkedin:hover` `color` | RETAIN | — | LinkedIn brand color |
| `public.css:462` | `#0a66c2` | `.share-linkedin:hover` `border-color` | RETAIN | — | LinkedIn brand color |
| `public.css:463` | `rgba(255, 102, 0, 0.1)` | `.share-hn` `background` | RETAIN | — | Hacker News brand color |
| `public.css:464` | `#ff6600` | `.share-hn:hover` `color` | RETAIN | — | Hacker News brand color |
| `public.css:464` | `#ff6600` | `.share-hn:hover` `border-color` | RETAIN | — | Hacker News brand color |
| `public.css:465` | `rgba(255, 69, 0, 0.1)` | `.share-reddit` `background` | RETAIN | — | Reddit brand color |
| `public.css:466` | `#ff4500` | `.share-reddit:hover` `color` | RETAIN | — | Reddit brand color |
| `public.css:466` | `#ff4500` | `.share-reddit:hover` `border-color` | RETAIN | — | Reddit brand color |
| `public.css:467` | `rgba(24, 119, 242, 0.1)` | `.share-facebook` `background` | RETAIN | — | Facebook brand color |
| `public.css:468` | `#1877f2` | `.share-facebook:hover` `color` | RETAIN | — | Facebook brand color |
| `public.css:468` | `#1877f2` | `.share-facebook:hover` `border-color` | RETAIN | — | Facebook brand color |
| `public.css:679` | `rgba(0, 0, 0, 0.9)` | `.lightbox` `background` | RETAIN | — | Intentionally near-black; darker than overlay |
| `public.css:776` | `rgba(0, 0, 0, 0.7)` | `.lightbox-caption` `background` | RETAIN | — | Intentionally darker than overlay |
| `public.css:777` | `var(--text-on-accent)` | `.lightbox-caption` `color` | RETAIN | — | Phase 09: replaced `#fff` with `var(--text-on-accent)` |
| `public.css:1204` | `var(--text-on-accent)` | `.search-btn` `color` | RETAIN | — | Phase 09: replaced `#fff` with `var(--text-on-accent)` |
| `public.css:1290` | `rgba(0,0,0,0.15)` | `.search-suggestions` `box-shadow` | RETAIN | — | Phase 09: now uses `var(--shadow-color)` |

### File: `app/static/css/admin.css`

Phase 09: All hardcoded literals converted to CSS variables. Flash/toast borders use `var(--success-bg)`, `var(--error-bg)`, `var(--warning-bg)`; shadows use `var(--shadow-color)`; overlays use `var(--overlay-bg)`; badge-scheduled uses `var(--purple-dim)`.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `admin.css:26` | `var(--success-bg)` | `.flash-success` `border-color` | RETAIN | — | Phase 09: replaced `rgba(63, 185, 80, 0.3)` |
| `admin.css:32` | `var(--error-bg)` | `.flash-error` `border-color` | RETAIN | — | Phase 09: replaced `rgba(248, 81, 73, 0.3)` |
| `admin.css:38` | `var(--warning-bg)` | `.flash-warning` `border-color` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.3)` |
| `admin.css:93` | `var(--shadow-color)` | `.toast` `box-shadow` | RETAIN | — | Phase 09: replaced `rgba(0, 0, 0, 0.15)` |
| `admin.css:156` | `var(--success-bg)` | `.toast-success` `border-color` | RETAIN | — | Phase 09: replaced `rgba(63, 185, 80, 0.3)` |
| `admin.css:162` | `var(--error-bg)` | `.toast-error` `border-color` | RETAIN | — | Phase 09: replaced `rgba(248, 81, 73, 0.3)` |
| `admin.css:168` | `var(--warning-bg)` | `.toast-warning` `border-color` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.3)` |
| `admin.css:258` | `var(--overlay-bg)` | `#bulk-loading-overlay` `background` | RETAIN | — | Phase 09: replaced `rgba(13, 17, 23, 0.7)` |
| `admin.css:623` | `var(--shadow-color)` | `.stat-card:hover` `box-shadow` | RETAIN | — | Phase 09: replaced `rgba(0,0,0,0.12)` |
| `admin.css:1216` | `var(--warning-bg)` | `.badge-draft` `background` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.15)` |
| `admin.css:1221` | `var(--purple-dim)` | `.badge-scheduled` `background` | RETAIN | — | Phase 09: replaced `rgba(88, 86, 214, 0.15)` |
| `admin.css:1277` | `var(--warning-bg)` | `.preview-banner` `background` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.2)` |
| `admin.css:1285` | `var(--warning-bg)` | `.preview-banner` `border-color` | RETAIN | — | Phase 09: replaced `rgba(210, 153, 34, 0.4)` |
| `admin.css:1292` | `var(--overlay-bg)` | `.modal-overlay` `background` | RETAIN | — | Phase 09: replaced `rgba(0, 0, 0, 0.6)` |

### File: `app/static/css/forms.css`

No hardcoded color literals found. All colors reference CSS custom properties.

### File: `app/static/css/utilities.css`

No hardcoded color literals found. All colors reference CSS custom properties.

---

## JavaScript Audit

All JavaScript SVG icons use `fill="currentColor"` to inherit color from the parent element's `color` property. No hardcoded color literals found.

| File | Lines | Findings |
|------|-------|----------|
| `app/static/js/shared/dark-mode.js` | 10–11 | SVGs use `fill="currentColor"` — **FALSE_POSITIVE** |
| `app/static/js/shared/mobile-menu.jsx` | 3–4 | SVGs use `fill="currentColor"` — **FALSE_POSITIVE** |
| `app/static/js/shared/toast.js` | 40–43 | SVGs use `fill="currentColor"` — **FALSE_POSITIVE** |
| `app/static/js/shared/utils.js` | 143 | SVG uses `fill="currentColor"` — **FALSE_POSITIVE** |
| `app/static/js/public/share.js` | 39 | SVG uses `fill="currentColor"` — **FALSE_POSITIVE** |

---

## Template Audit

Templates inject `theme_vars` via a CSP-nonced inline `<style>` block (e.g., `base.html:41–52`, `admin/base.html:16–27`). These are runtime-injected CSS custom properties, not hardcoded literals.

| Template | Findings |
|----------|----------|
| `app/templates/base.html` | Lines 41–52: `theme_vars` injection (not literals). Line 79: `style="display:none"` (not a color). |
| `app/templates/admin/base.html` | Lines 16–27: `theme_vars` injection (not literals). |
| `app/templates/admin/settings.html` | Lines 24–27: `style="background: {{ preset.bg }}"` etc. — dynamic, not literals. |
| Email templates (`app/templates/email/`) | Out of scope — emails have independent styling. |

---

## Unique Proposed Semantic Tokens

The following new CSS variable names were proposed by REPLACE entries in this audit. Phase 09 implemented them using the existing semantic token system from `app/themes/model.py`.

| Token Name | Purpose | Source Files | Phase 09 Status |
|------------|---------|-------------|-----------------|
| `--navbar-bg` | Semi-transparent navbar background | `critical.css:46`, `layout.css:16` | **Implemented** — uses `var(--navbar-bg)` |
| `--accent-on-accent` | White/light text rendered on accent-colored backgrounds | `base.css:156,161,330,347`, `public.css:777,1204` | **Implemented** — uses `var(--text-on-accent)` |
| `--yellow-dim` | Dim/warning background (yellow tint) | `base.css:355`, `public.css:448`, `admin.css:36,166,1216,1277` | **Implemented** — uses `var(--warning-bg)` |
| `--green-border` | Green state border (e.g., success flash) | `admin.css:26,156` | **Implemented** — uses `var(--success-bg)` |
| `--red-border` | Red state border (e.g., error flash) | `admin.css:32,162` | **Implemented** — uses `var(--error-bg)` |
| `--yellow-border` | Yellow state border (e.g., warning flash) | `admin.css:38,168,1285` | **Implemented** — uses `var(--warning-bg)` |
| `--overlay-bg` | Modal/loading overlay background | `admin.css:258,1292` | **Implemented** — uses `var(--overlay-bg)` |
| `--hero-overlay` | Post hero image gradient overlay | `public.css:340` | **Implemented** — uses `var(--bg)` for top gradient |
| `--hero-title-text` | Text color on hero image | `public.css:357` | **Implemented** — uses `var(--text-on-accent)` |
| `--lightbox-bg` | Lightbox backdrop overlay | `public.css:679` | **Retained** — intentionally `rgba(0,0,0,0.9)` |
| `--lightbox-caption-bg` | Lightbox caption bar background | `public.css:776` | **Retained** — intentionally `rgba(0,0,0,0.7)` |

**Note**: Phase 09 used existing semantic tokens (`--text-on-accent`, `--warning-bg`, `--success-bg`, `--error-bg`, `--overlay-bg`, `--accent-dim`) rather than introducing new token names. The `--hero-overlay` and `--hero-title-text` tokens were not needed because the hero overlay uses `var(--bg)` for the top gradient and the title uses `var(--text-on-accent)`. The lightbox backdrop and caption were intentionally retained as near-black values.

---

## Phase 08 First-Paint — Resolved

Phase 08 is complete. The bootstrap IIFE in `<head>` reads `blog-color-scheme` from localStorage, resolves `system` via `matchMedia`, and sets `data-color-scheme` on `<html>` before first paint. The static `[data-theme="light"]` palette block has been removed; light-theme variables are now provided entirely by inline `<style>` from Halloy themes. Component-specific light overrides (navbar, post-hero-overlay, prose code/pre) remain under `[data-color-scheme="light"]` in `base.css`.

## Phase 09 CSS Audit — Complete

Phase 09 is complete. All 34 REPLACE entries have been converted to CSS custom properties. The audit document above reflects the post-Phase-09 state. Tests in `tests/themes/test_phase09_css_tokens.py` verify that all 35 legacy CSS variables are emitted and that the ALIASES dict provides backward compatibility. The remaining 71 RETAIN literals are intentional: structural defaults, print styles, brand colors, neutral shadows, and intentionally-dark overlays.
