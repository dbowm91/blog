# Frontend Agent Override

Specialized handling for JavaScript, CSS, and Vite build system.

## Directory Structure

```
app/static/
├── js/
│   ├── main.js           # Route-based dynamic imports loader
│   ├── lib/              # Third-party JS libraries (marked.js for markdown preview)
│   ├── shared/           # Shared JS modules (utils, dark-mode, modal, mobile-menu, toast, etc.)
│   ├── public/           # Public-facing JS modules (share, lightbox, toc, search, etc.)
│   └── admin/            # Admin JS modules (editor, bulk, shortcuts)
├── css/
│   ├── critical.css       # Above-the-fold CSS for fast initial paint
│   ├── base.css          # CSS variables, reset, typography
│   ├── layout.css        # Grid layout, navbar, sidebar, footer
│   ├── forms.css         # Form elements, buttons, validation
│   ├── admin.css         # Admin-specific styles
│   ├── public.css        # Public-facing page styles
│   ├── utilities.css     # Helper classes
│   ├── prism.css         # Syntax highlighting theme (base)
│   └── prism-*.css       # Additional Prism themes (coy, dark, funky, okaidia, tomorrow)
├── fonts/                # Self-hosted fonts (Inter, JetBrains Mono)
├── img/                  # Static images
└── dist/                 # Vite build output
```

## Vite Build System

```bash
# Install dependencies
npm install --registry https://registry.npmjs.org/

# Development with HMR
npm run dev

# Build for production (with content hashing)
npm run build
```

Configuration: `vite.config.js`.

## Content Hashing

- Vite generates content-hashed filenames (e.g., `main-BVtPp-ke.js`)
- Manifest file generated at `app/static/dist/.vite/manifest.json`
- Flask helper `vite_asset()` in `app/vite.py`:
  - JS files: Looks up hashed filename from manifest
  - CSS/other: Appends MD5 content hash as query string (e.g., `base.css?v=3544ab62`)
- Templates use `{{ vite_asset('path/to/file') }}` instead of `{{ url_for('static', ...) }}`
- Enables aggressive caching with `Cache-Control: max-age=31536000, immutable`

## JS Module Initialization (CRITICAL)

All JavaScript modules must export a default function for initialization. When adding new modules to `shared/` or `public/`, you **must** add `export default initXxx;` where `initXxx` is the initialization function. The main.js loader calls `module.default()` to invoke the exported function. Modules without this export will not be called on page load.

**Dynamic Imports**: Vite requires static analysis for bundling. ALWAYS use `import.meta.glob(['./path/*.js'])` for dynamic route-based module loading in `main.js`. Never use variable-based `import(path)`.

## Route-Based Code Splitting

`app/static/js/main.js` uses route-based dynamic imports. Admin pages get utils, modal, shortcuts, bulk. Public pages get utils, dark-mode, mobile-menu, lazy-load, share, lightbox, toc.

## Mobile Menu Toggle

The mobile hamburger menu button is **created dynamically in JavaScript** (`shared/mobile-menu.jsx`), not in HTML templates.

## Admin Page Detection in JS

Use `document.body.classList.contains('admin-body')` to scope admin-only JS handlers.

## Lazy Image Progressive Enhancement

Images use `opacity: 0` by default and JS adds `.loaded` class. Pattern: add `document.documentElement.classList.add('js')` first, prefix CSS rules with `.js`.

See [Lazy Image Loading](#lazy-image-loading) under Cross-Layer Contracts for the
restoration-path rule that makes this safe.

## Responsive Images

Post images support responsive srcset via the `post_image_srcset` filter. Variants are generated at 400w, 800w, and 1200w widths on upload. Templates use `srcset` with `sizes` attribute.

The filter returns `None` when no variants exist, so the `srcset` attribute must be
guarded — see [Image URLs](#image-urls).

## GPU Acceleration for Blur Effects

For `backdrop-filter: blur()`, use `will-change: backdrop-filter` in CSS:
```css
.navbar, .nav-links, .modal-overlay {
    will-change: backdrop-filter;
}
```

## CSS Architecture

- Dark mode is default; light theme toggled via `data-color-scheme` attribute (migrated from `data-theme` in Phase 08)
- Self-hosted fonts (Inter, JetBrains Mono) via `@font-face`
- No external font CDNs

## Syntax Highlighting Themes

Configurable via `SiteSettings.syntax_theme`:
- Admin: `/admin/settings` has theme selector with 6 Prism themes
- Themes: prism (default), prism-coy, prism-dark, prism-funky, prism-okaidia, prism-tomorrow

## Assets Policy

- **No external assets**—all fonts are self-hosted in `app/static/fonts/`
- **Prism.js** is self-hosted with extended language definitions
- Do not add external CDN links (Google Fonts, CDNs, etc.)

## Cross-Layer Contracts

These are the seams where a template, a stylesheet, a module, and the server each make
an assumption about the other. Every one of them has caused a defect before, so each
now has a single owner and a named rule. Do not reintroduce a second producer for any
of these values.

### Image URLs

`post_image_url` returns a **URL**, not a filename: `/static/uploads/<file>` for the
local backend and an absolute `https://…` URL for S3. Templates must use the filter
output directly.

```jinja
{# correct #}
<img src="{{ img }}"{% if srcset %} srcset="{{ srcset }}" sizes="…"{% endif %}>

{# wrong — produces /static/uploads//static/uploads/<file> #}
<img src="{{ url_for('static', filename='uploads/' + img) }}">
```

`app/templates/admin/media.html` is the one exception: it renders `f.name` from
`storage.list_files()`, which **is** a bare filename.

`post_image_srcset` returns `None` when no responsive variants exist. Jinja renders
`None` as the literal string `"None"`, and a `srcset` candidate list overrides `src`
entirely — so the attribute must be guarded, never emitted unguarded.

### Lazy Image Loading

`.js img[loading="lazy"] { opacity: 0 }` is only safe because a restoration path is
guaranteed. `shared/lazy-load.js` attaches the `load` **and** `error` handlers
*before* the native-support early return, so the `.loaded` class is applied on every
browser. The `error` listener is required: a broken image must not stay invisible.
Any new rule that hides an element must have a matching restoration selector.

### Lightbox Visibility

`hidden` is the source of truth for the dialog's visibility; `open` is the animation
state. `.lightbox.hidden { display: none !important }` and `.lightbox:not(.hidden)
{ display: flex }` therefore need no JavaScript to open the dialog — the JS only
removes and re-adds `hidden`. Restore `document.body.style.overflow` to the value it
had before opening, not to `''`.

### CSRF Header Name

The header name is defined **once**, in `app/csrf.py` as `CSRF_HEADER_NAME`
(`X-CSRF-Token`). It is published to the browser as `data-csrf-header` on the root
element and read by `csrfHeaders()` in `shared/utils.js`. No template or module may
hard-code the name — HTTP header names are case-insensitive but not hyphen-
insensitive, so `X-CSRFToken` does not match `X-CSRF-Token`.

### Route → Module Mapping

`getModulesForPath()` in `main.js` matches on a **path-segment boundary**
(`path === route || path.startsWith(route + '/')`), preferring the longest match,
with `/admin/` as the catch-all. Plain `startsWith` is not sufficient: `/admin/new`
is a literal prefix of `/admin/newsletter/preview`.

### Heading IDs

Exactly one module produces heading IDs: `shared/heading-slug.js`. `public/toc.js`
and `public/anchor-links.js` both import it. Do not add a second slugger.

### Flash Messages

The server renders flashes as `.flash-container > .flash > .flash-message`.
`shared/toast.js` converts them into toasts and removes the container on load, so
the final DOM may contain either representation. Tests must assert the
user-visible message, not one specific node.

### Theme Tokens

The theme runtime owns colour. Static CSS consumes theme tokens and must not use
literals for themed surfaces. Every `var(--x)` referenced by a stylesheet must be
either emitted by the theme runtime or defined in a stylesheet — this is enforced by
`tests/test_css_contracts.py`. Tokens that the runtime emits but no stylesheet
consumes are dead weight.

### Stylesheet Ownership

Exactly one stylesheet owns a given element's visibility at each breakpoint.
`layout.css` and `base.css` both setting `.nav-links { display }` is a cascade tie
resolved by document order, not by intent — scope the rule instead.

### Vite Build

`main.js` must **not** import a stylesheet. Flask links the stylesheets in
`app/templates/base.html` so that the dev server and production share one cascade
order. `shared/utils.js` is assigned to the `shared` chunk explicitly so a failure
inside an admin-only module cannot abort a shared module on a public page.