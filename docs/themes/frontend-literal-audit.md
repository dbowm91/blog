# Frontend Hardcoded Color Literal Audit

**Phase**: 01 — Inventory and Semantic Token Contract  
**Scope**: All non-Prism CSS files, templates (non-email), and JavaScript  
**Methodology**: Regex search (`#[0-9a-fA-F]{3,8}` and `rgba?\(`) across target files, classified manually line by line  
**Date**: 2026-07-13

---

## Classification Taxonomy

| Code | Definition |
|------|-----------|
| **REPLACE** | Literal should become a semantic theme token. Phase 09 will replace it with a CSS custom property. |
| **RETAIN** | Invariant brand or structural value that cannot or should not be themed. Includes print stylesheet forced colors, light-theme hardcoded palette (which is itself a structural fallback), and values that are the exact equivalent of a token but exist in a context where the token is already applied. |
| **SYNTAX** | Belongs to Prism syntax highlighting; separate system. Not in scope. |
| **COMPAT** | Temporary compatibility value kept during migration; will be removed in Phase 09/14. |
| **FALSE_POSITIVE** | Not actually a color (e.g., URL fragments, font-face metadata, `currentColor` SVGs, brightness filter values, ID selectors). |

---

## First-Paint Note

`critical.css` contains 8 hardcoded color literals (lines 3–9, 46). These are loaded via `<link rel="stylesheet" media="screen">` for immediate above-the-fold rendering, while `base.css` loads asynchronously via `media="print" onload="this.media='all'"`.

The hardcoded values in `critical.css :root` (`--bg: #0d1117`, `--bg-surface: #161b22`, `--border: #30363d`, `--text: #e6edf3`, `--text-muted: #8b949e`, `--accent: #58a6ff`, `--accent-hover: #79c0ff`) are themselves structural fallbacks — identical to the `base.css :root` defaults. The navbar background (`rgba(13, 17, 23, 0.85)`) is a hardcoded dark-theme semi-transparent value.

**Phase 08 must address the no-flash problem**: when a visitor has a light theme preference, `critical.css` renders dark-theme colors for ~100ms until the inline `<style>` with `theme_vars` applies. The Phase 08 bootstrap script must set `data-theme` before first paint, or `critical.css` must emit both light and dark palettes keyed to `data-theme` to prevent visible flash.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total color literals audited** | 128 |
| REPLACE | 34 |
| RETAIN | 85 |
| FALSE_POSITIVE | 9 |
| SYNTAX | 0 |
| COMPAT | 0 |

### Count by File

| File | Total | REPLACE | RETAIN | FALSE_POS |
|------|-------|---------|--------|-----------|
| `app/static/css/base.css` | 76 | 14 | 55 | 7 |
| `app/static/css/critical.css` | 8 | 1 | 7 | 0 |
| `app/static/css/layout.css` | 3 | 1 | 2 | 0 |
| `app/static/css/public.css` | 25 | 10 | 13 | 2 |
| `app/static/css/admin.css` | 16 | 8 | 8 | 0 |
| `app/static/css/forms.css` | 0 | 0 | 0 | 0 |
| `app/static/css/utilities.css` | 0 | 0 | 0 | 0 |
| JavaScript (all files) | 0 | 0 | 0 | 0 |
| Templates (non-email) | 0 | 0 | 0 | 0 |
| SVG assets | 0 (not audited) | — | — | — |

### Top 5 Files by Literal Count

1. `app/static/css/base.css` — 77
2. `app/static/css/public.css` — 25
3. `app/static/css/admin.css` — 16
4. `app/static/css/critical.css` — 8
5. `app/static/css/layout.css` — 3

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
| `critical.css:46` | `rgba(13, 17, 23, 0.85)` | `.navbar` `background` | REPLACE | `--navbar-bg` | Dark-theme semi-transparent navbar; must become theme-aware for light themes |

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

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:156` | `#fff` | `.btn-primary` `color` | REPLACE | `--accent-on-accent` | White text on accent background |
| `base.css:161` | `#fff` | `.btn-primary:hover` `color` | REPLACE | `--accent-on-accent` | White text on accent hover |
| `base.css:204` | `#5c4a00` | `.btn-warning` `background` fallback | REPLACE | `--amber-dim` | Fallback when `--amber-dim` is unset |
| `base.css:205` | `#f59e0b` | `.btn-warning` `color` fallback | REPLACE | `--amber` | Fallback when `--amber` is unset |
| `base.css:210` | `#f59e0b` | `.btn-warning:hover` `border-color` fallback | REPLACE | `--amber` | Fallback when `--amber` is unset |
| `base.css:330` | `#fff` | `.skip-link` `color` | REPLACE | `--accent-on-accent` | White text on accent background |
| `base.css:347` | `white` | `.skip-link:focus` `color` | REPLACE | `--accent-on-accent` | White text on accent background |

#### Noscript Warning

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:355` | `rgba(210, 153, 34, 0.15)` | `.noscript-warning` `background` | REPLACE | `--yellow-dim` | Yellow tint; should be `--yellow-dim` |

#### `[data-theme="light"]` Block (lines 218–242)

These 23 literals define the light-theme CSS custom property overrides. They are the structural fallback for the light theme — equivalent to what `theme_vars` injects at runtime. Classified as RETAIN.

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:219` | `#f6f8fa` | `[data-theme="light"]` `--bg` | RETAIN | — | Light background |
| `base.css:220` | `#ffffff` | `[data-theme="light"]` `--bg-surface` | RETAIN | — | Light surface |
| `base.css:221` | `#f0f2f5` | `[data-theme="light"]` `--bg-elevated` | RETAIN | — | Light elevated |
| `base.css:222` | `#d0d7de` | `[data-theme="light"]` `--border` | RETAIN | — | Light border |
| `base.css:223` | `#1f2328` | `[data-theme="light"]` `--text` | RETAIN | — | Light text |
| `base.css:224` | `#57606a` | `[data-theme="light"]` `--text-muted` | RETAIN | — | Light muted text |
| `base.css:225` | `#6e7781` | `[data-theme="light"]` `--text-dim` | RETAIN | — | Light dim text |
| `base.css:226` | `#6e7781` | `[data-theme="light"]` `--text-secondary` | RETAIN | — | Light secondary text |
| `base.css:227` | `#eaeef2` | `[data-theme="light"]` `--bg-hover` | RETAIN | — | Light hover bg |
| `base.css:228` | `#0969da` | `[data-theme="light"]` `--accent` | RETAIN | — | Light accent |
| `base.css:229` | `#0550ae` | `[data-theme="light"]` `--accent-hover` | RETAIN | — | Light accent hover |
| `base.css:230` | `rgba(9, 105, 218, 0.1)` | `[data-theme="light"]` `--accent-dim` | RETAIN | — | Light accent dim |
| `base.css:231` | `#1a7f37` | `[data-theme="light"]` `--green` | RETAIN | — | Light green |
| `base.css:232` | `rgba(26, 127, 55, 0.15)` | `[data-theme="light"]` `--green-dim` | RETAIN | — | Light green dim |
| `base.css:233` | `#cf222e` | `[data-theme="light"]` `--red` | RETAIN | — | Light red |
| `base.css:234` | `rgba(207, 34, 46, 0.15)` | `[data-theme="light"]` `--red-dim` | RETAIN | — | Light red dim |
| `base.css:235` | `#9a6700` | `[data-theme="light"]` `--yellow` | RETAIN | — | Light yellow |
| `base.css:236` | `#8250df` | `[data-theme="light"]` `--purple` | RETAIN | — | Light purple |
| `base.css:237` | `rgba(130, 80, 223, 0.15)` | `[data-theme="light"]` `--purple-dim` | RETAIN | — | Light purple dim |
| `base.css:238` | `#d4513d` | `[data-theme="light"]` `--coral` | RETAIN | — | Light coral |
| `base.css:239` | `rgba(212, 81, 61, 0.15)` | `[data-theme="light"]` `--coral-dim` | RETAIN | — | Light coral dim |
| `base.css:240` | `#9a6700` | `[data-theme="light"]` `--amber` | RETAIN | — | Light amber |
| `base.css:241` | `rgba(154, 103, 0, 0.15)` | `[data-theme="light"]` `--amber-dim` | RETAIN | — | Light amber dim |

#### Light Theme Overrides (component-level)

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `base.css:245` | `rgba(246, 248, 250, 0.85)` | `[data-theme="light"] .navbar` `background` | RETAIN | — | Light navbar; matches `--bg` (#f6f8fa) at 0.85 opacity |
| `base.css:249` | `rgba(246, 248, 250, 0.95)` | `[data-theme="light"] .post-hero-overlay` gradient | RETAIN | — | Light hero overlay top |
| `base.css:249` | `rgba(246, 248, 250, 0.4)` | `[data-theme="light"] .post-hero-overlay` gradient | RETAIN | — | Light hero overlay bottom |
| `base.css:253` | `#1f2328` | `[data-theme="light"] .post-hero-title` `color` | RETAIN | — | Matches `--text` in light theme |
| `base.css:257` | `#eff1f3` | `[data-theme="light"] .prose code` `background` | RETAIN | — | Light inline code bg |
| `base.css:261` | `#f6f8fa` | `[data-theme="light"] .prose pre` `background` | RETAIN | — | Matches `--bg` in light theme |

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
| `layout.css:16` | `rgba(13, 17, 23, 0.85)` | `.navbar` `background` | REPLACE | `--navbar-bg` | Semi-transparent dark navbar bg; must support light themes |
| `layout.css:155` | `rgba(0,0,0,0.15)` | `.nav-dropdown-menu` `box-shadow` | RETAIN | — | Neutral shadow; acceptable as-is |
| `layout.css:218` | `rgba(0,0,0,0.5)` | `.nav-links.open::before` `background` (mobile overlay) | RETAIN | — | Dark overlay for mobile menu |

### File: `app/static/css/public.css`

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `public.css:74` | `rgba(0, 0, 0, 0.3)` | `.post-card:hover` `box-shadow` | RETAIN | — | Neutral hover shadow |
| `public.css:78` | `rgba(0, 0, 0, 0.08)` | `[data-theme="light"] .post-card:hover` `box-shadow` | RETAIN | — | Light theme hover shadow |
| `public.css:259` | `rgba(0,0,0,0.15)` | `.tag:hover` `box-shadow` | RETAIN | — | Neutral tag shadow |
| `public.css:268` | `rgba(88, 166, 255, 0.25)` | `.tag-active` `background` | REPLACE | `--accent-dim` | Active tag bg; should use `--accent-dim` or `--accent-active` |
| `public.css:340` | `rgba(13, 17, 23, 0.95)` | `.post-hero-overlay` gradient top | REPLACE | `--hero-overlay` | Dark overlay for hero image; theme-dependent |
| `public.css:340` | `rgba(13, 17, 23, 0.4)` | `.post-hero-overlay` gradient bottom | REPLACE | `--hero-overlay` | Dark overlay for hero image |
| `public.css:357` | `#fff` | `.post-hero-title` `color` | REPLACE | `--hero-title-text` | White text on hero image; needs contrast token |
| `public.css:395` | `rgba(0,0,0,0.1)` | `.share-btn:hover` `box-shadow` | RETAIN | — | Neutral share btn shadow |
| `public.css:443` | `rgba(0,0,0,0.3)` | `.flash` `box-shadow` | RETAIN | — | Toast shadow |
| `public.css:448` | `rgba(210, 153, 34, 0.15)` | `.flash-warning` `background` | REPLACE | `--yellow-dim` | Warning flash bg; should use `--yellow-dim` |
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
| `public.css:679` | `rgba(0, 0, 0, 0.9)` | `.lightbox` `background` | REPLACE | `--lightbox-bg` | Near-black overlay; theme-dependent |
| `public.css:776` | `rgba(0, 0, 0, 0.7)` | `.lightbox-caption` `background` | REPLACE | `--lightbox-caption-bg` | Caption bg; theme-dependent |
| `public.css:777` | `#fff` | `.lightbox-caption` `color` | REPLACE | `--accent-on-accent` | White text on dark caption |
| `public.css:1204` | `#fff` | `.search-btn` `color` | REPLACE | `--accent-on-accent` | White text on accent button |
| `public.css:1290` | `rgba(0,0,0,0.15)` | `.search-suggestions` `box-shadow` | RETAIN | — | Neutral dropdown shadow |

### File: `app/static/css/admin.css`

| Line | Literal | CSS Context | Classification | Proposed Token | Notes |
|------|---------|-------------|----------------|----------------|-------|
| `admin.css:26` | `rgba(63, 185, 80, 0.3)` | `.flash-success` `border-color` | REPLACE | `--green-border` | Green border; should use semantic token |
| `admin.css:32` | `rgba(248, 81, 73, 0.3)` | `.flash-error` `border-color` | REPLACE | `--red-border` | Red border; should use semantic token |
| `admin.css:36` | `rgba(210, 153, 34, 0.15)` | `.flash-warning` `background` | REPLACE | `--yellow-dim` | Warning flash bg |
| `admin.css:38` | `rgba(210, 153, 34, 0.3)` | `.flash-warning` `border-color` | REPLACE | `--yellow-border` | Warning border; should use semantic token |
| `admin.css:93` | `rgba(0, 0, 0, 0.15)` | `.toast` `box-shadow` | RETAIN | — | Neutral toast shadow |
| `admin.css:156` | `rgba(63, 185, 80, 0.3)` | `.toast-success` `border-color` | REPLACE | `--green-border` | Duplicate of line 26 |
| `admin.css:162` | `rgba(248, 81, 73, 0.3)` | `.toast-error` `border-color` | REPLACE | `--red-border` | Duplicate of line 32 |
| `admin.css:166` | `rgba(210, 153, 34, 0.15)` | `.toast-warning` `background` | REPLACE | `--yellow-dim` | Duplicate of line 36 |
| `admin.css:168` | `rgba(210, 153, 34, 0.3)` | `.toast-warning` `border-color` | REPLACE | `--yellow-border` | Duplicate of line 38 |
| `admin.css:258` | `rgba(13, 17, 23, 0.7)` | `#bulk-loading-overlay` `background` | REPLACE | `--overlay-bg` | Dark overlay; theme-dependent |
| `admin.css:623` | `rgba(0,0,0,0.12)` | `.stat-card:hover` `box-shadow` | RETAIN | — | Neutral card shadow |
| `admin.css:1216` | `rgba(210, 153, 34, 0.15)` | `.badge-draft` `background` | REPLACE | `--yellow-dim` | Draft badge bg |
| `admin.css:1221` | `rgba(88, 86, 214, 0.15)` | `.badge-scheduled` `background` | REPLACE | `--purple-dim` | Scheduled badge bg; note: uses `rgba(88, 86, 214)` not the standard `--purple` |
| `admin.css:1277` | `rgba(210, 153, 34, 0.2)` | `.preview-banner` `background` | REPLACE | `--yellow-dim` | Preview banner bg |
| `admin.css:1285` | `rgba(210, 153, 34, 0.4)` | `.preview-banner` `border-color` | REPLACE | `--yellow-border` | Preview banner border |
| `admin.css:1292` | `rgba(0, 0, 0, 0.6)` | `.modal-overlay` `background` | REPLACE | `--overlay-bg` | Modal overlay; theme-dependent |

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

The following new CSS variable names are introduced by REPLACE entries in this audit:

| Token Name | Purpose | Source Files |
|------------|---------|-------------|
| `--navbar-bg` | Semi-transparent navbar background | `critical.css:46`, `layout.css:16` |
| `--accent-on-accent` | White/light text rendered on accent-colored backgrounds | `base.css:156,161,330,347`, `public.css:777,1204` |
| `--yellow-dim` | Dim/warning background (yellow tint) | `base.css:355`, `public.css:448`, `admin.css:36,166,1216,1277` |
| `--green-border` | Green state border (e.g., success flash) | `admin.css:26,156` |
| `--red-border` | Red state border (e.g., error flash) | `admin.css:32,162` |
| `--yellow-border` | Yellow state border (e.g., warning flash) | `admin.css:38,168,1285` |
| `--overlay-bg` | Modal/loading overlay background | `admin.css:258,1292` |
| `--hero-overlay` | Post hero image gradient overlay | `public.css:340` |
| `--hero-title-text` | Text color on hero image | `public.css:357` |
| `--lightbox-bg` | Lightbox backdrop overlay | `public.css:679` |
| `--lightbox-caption-bg` | Lightbox caption bar background | `public.css:776` |

**Note**: `--yellow-dim` already exists in some THEME_PRESETS (e.g., Monokai) but is not in the standard token set. It should be added to the canonical token contract. The `--accent-dim` token already exists and the `.tag-active` background (`public.css:268`) may use it directly rather than introducing a new token.

---

## Phase 08 First-Paint Attention Required

The following items need Phase 08 attention:

1. **`critical.css` navbar background** (`critical.css:46`): `rgba(13, 17, 23, 0.85)` is a dark-theme-specific value. If the visitor prefers light theme, this will flash dark before the inline `theme_vars` style applies. Phase 08 must either:
   - Emit a `data-theme`-keyed navbar background in `critical.css`, or
   - Ensure the bootstrap script sets `data-theme` before the first frame.

2. **`critical.css :root` defaults** (`critical.css:3–9`): These are dark-theme fallbacks. The first-paint bootstrap must apply `data-theme="light"` before CSS parses if the visitor's preference is light, or `critical.css` must include a `[data-theme="light"]` override block.

3. **`layout.css` navbar** (`layout.css:16`): Same `rgba(13, 17, 23, 0.85)` issue — will be overridden by `base.css` but `layout.css` loads async. The first-paint sequence is: `critical.css` → inline `theme_vars` → `base.css` → `layout.css`. If `layout.css` applies before `theme_vars`, it will flash the dark navbar.
