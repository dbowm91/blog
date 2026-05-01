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
│   ├── style.css         # Aggregates all CSS files
│   ├── base.css          # CSS variables, reset, typography
│   ├── layout.css        # Grid layout, navbar, sidebar, footer
│   ├── forms.css         # Form elements, buttons, validation
│   ├── admin.css         # Admin-specific styles
│   ├── public.css        # Public-facing page styles
│   ├── utilities.css     # Helper classes
│   ├── prism.css         # Syntax highlighting theme (base)
│   └── themes/           # Additional Prism themes (coy, dark, funky, okaidia, tomorrow)
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

Configuration: `vite.config.js` with Flask integration via `vite-plugin-flask`.

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

The mobile hamburger menu button is **created dynamically in JavaScript** (`shared/mobile-menu.js`), not in HTML templates.

## Admin Page Detection in JS

Use `document.body.classList.contains('admin-body')` to scope admin-only JS handlers.

## Lazy Image Progressive Enhancement

Images use `opacity: 0` by default and JS adds `.loaded` class. Pattern: add `document.documentElement.classList.add('js')` first, prefix CSS rules with `.js`.

## Responsive Images

Post images support responsive srcset via the `post_image_srcset` filter. Variants are generated at 400w, 800w, and 1200w widths on upload. Templates use `srcset` with `sizes` attribute.

## GPU Acceleration for Blur Effects

For `backdrop-filter: blur()`, use `will-change: backdrop-filter` in CSS:
```css
.navbar, .nav-links, .modal-overlay {
    will-change: backdrop-filter;
}
```

## CSS Architecture

- Dark mode is default; light theme toggled via `data-theme` attribute
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