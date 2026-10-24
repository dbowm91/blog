# Static Assets (`app/static/`)

Frontend JavaScript and CSS assets.

## Directory Structure

```
app/static/
├── js/
│   ├── admin/          # Admin dashboard JS
│   │   ├── bulk.js
│   │   ├── editor.js
│   │   ├── markdown-toolbar.js
│   │   └── shortcuts.js
│   ├── public/         # Public site JS
│   │   ├── anchor-links.js
│   │   ├── code-copy.js
│   │   ├── lightbox.js
│   │   ├── media-copy.js
│   │   ├── search.js
│   │   ├── share.js
│   │   └── toc.js
│   ├── shared/         # Shared components
│   │   ├── dark-mode.js
│   │   ├── filter-select.js
│   │   ├── lazy-load.js
│   │   ├── mobile-menu.jsx  # JSX file (Vite handles via esbuildOptions)
│   │   ├── modal.js
│   │   ├── nav-dropdown.js
│   │   ├── prefetch.js
│   │   ├── toast.js
│   │   └── utils.js
│   ├── lib/            # Third-party libraries
│   │   ├── marked-wrapper.js
│   │   └── marked.min.js
│   ├── prism.min.js
│   ├── prism-languages.js
│   ├── image-preview.js
│   ├── main.js         # Entry point with route-based code splitting
│   └── upload.js
├── css/                # CSS files
├── fonts/              # Web fonts (woff2)
├── img/                # Static images (favicon, default-post)
├── uploads/            # User-uploaded media (local fallback; production may use S3)
└── dist/               # Vite build output
```

## JavaScript

### Module Initialization Pattern

JavaScript modules must export a default initialization function named `initXxx` (e.g., `export default initDarkMode`). The module loader in `main.js` calls `module.default()` if it exists:

```javascript
// Correct - default export named initXxx
export default function initMyModule() { ... }

// Incorrect - named export without default
export function setup() { ... }
```

### Route-Based Code Splitting

Code splitting is implemented in `main.js` using `import.meta.glob()`. Modules are loaded dynamically based on the current route:

```javascript
const ROUTE_MODULES = {
    '/admin/new': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/edit': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/pages/new': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
    ],
    '/admin/pages/edit': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
    ],
    '/admin/media': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './upload.js',
        './image-preview.js',
    ],
    '/admin/': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
    ],
};

function getModulesForPath(path) {
    // Returns route-specific modules or default public modules.
    // Matching is on a path-segment boundary, preferring the longest route:
    //   path === route || path.startsWith(route + '/')
    // Plain startsWith is not sufficient — '/admin/new' is a literal prefix
    // of '/admin/newsletter/preview'.
}
```

This allows Vite to create optimized chunks that are only loaded when needed.

### Lazy Image Loading

The progressive image loading pattern in `app/static/css/public.css` is:
- Default: `opacity: 0` on `img[loading="lazy"]` (requires `.js` class on `<html>`)
- `.loaded` class: `opacity: 1` with 0.4s ease transition
- JavaScript adds `document.documentElement.classList.add('js')` first to enable progressive enhancement

#### Image Skeleton Shimmer

`.img-skeleton` class provides a loading placeholder animation:
- Background: `linear-gradient(90deg, var(--bg-surface) 25%, var(--bg-elevated) 50%, var(--bg-surface) 75%)` with `background-size: 200% 100%`
- Animation: `shimmer` keyframe moves background position from `200%` to `-200%` over 1.5s (infinite loop)
- When `.loaded` is added: animation stops, background clears

#### JavaScript Fallback Behavior

The `lazy-load.js` module attaches the `load` and `error` listeners **before** the
native-support early return, so the `.loaded` class is applied on every browser:

1. **Class contract (always)**: every `img[loading="lazy"]` gets a `load` listener
   that adds `.loaded`, and an `error` listener that also adds it — a broken image
   must not be left at `opacity: 0` forever. An image that is already complete is
   marked immediately.
2. **Native lazy loading**: If `'loading' in HTMLImageElement.prototype`, the
   browser handles the deferred fetching and the module stops there.
3. **IntersectionObserver polyfill**: If native is not supported but
   IntersectionObserver exists, observe images with `rootMargin: '200px 0px'` and
   swap `dataset.src` into `src` when intersecting.
4. **Immediate load fallback**: If no IntersectionObserver support, load all
   `loading="lazy"]` images immediately by copying `dataset.src` to `src`.

Step 1 is what makes the `opacity: 0` rule safe. Any new rule that hides an element
must have an equivalent guaranteed restoration path.

### Admin Body Class Detection

Admin pages can be detected via `document.body.classList.contains('admin-body')`.

### marked.min.js Loading Pattern

`marked.min.js` is loaded through Vite's asset pipeline via `vite_asset()` in both `base.html` and `admin/base.html`, receiving content hashing and CDN support like other JS assets:

```html
<script src="{{ vite_asset('js/lib/marked.min.js') }}"></script>
```

The adapter layer `marked-wrapper.js` is also loaded via `vite_asset()`.

### JSX Support

JSX files (like `mobile-menu.jsx`) are handled via Vite's esbuild options in `vite.config.js`:

```javascript
optimizeDeps: {
    esbuildOptions: {
        loader: {
            '.js': 'js',
            '.jsx': 'jsx',
            '.svg': 'text',
        },
        target: ['chrome100', 'edge100', 'firefox100', 'safari15'],
    },
}
```

### Admin JS
- Dashboard analytics and charts
- Post editor enhancements
- Markdown formatting toolbar (`markdown-toolbar.js`) — inserts markdown at the caret; loaded through `editor.js`
- Media upload management
- Settings and theme forms
- Bulk operations

### Public JS
- Anchor link handling (`anchor-links.js`)
- Code block copy buttons (`code-copy.js`)
- Image lightbox (`lightbox.js`)
- Search functionality (`search.js`)
- Social share buttons (`share.js`)
- Table of contents generation (`toc.js`)

`media-copy.js` lives under `public/` but belongs to the admin media library — it is
loaded only for the `/admin/media` route.

## CSS

Stylesheets in `app/static/css/`:
- `base.css` — Base styles
- `layout.css` — Page layout
- `public.css` — Public site styles
- `forms.css` — Form styles
- `utilities.css` — Utility classes
- `critical.css` — Above-the-fold CSS for fast initial paint

### Cascade Ownership

The stylesheets are linked in DOM order: `critical.css` → `base.css` →
`layout.css` → `public.css` → `forms.css` → `utilities.css`. At equal specificity
the later stylesheet wins, so **exactly one stylesheet may own an element's
visibility at a given breakpoint**.

`.nav-links` is the worked example: `base.css` hid it below 769px while
`layout.css` set `display: flex` unconditionally. Both declarations had equal
specificity, so document order decided the outcome and the mobile navigation could
never collapse. `layout.css` now scopes its rule to `@media (min-width: 769px)`.

### Code Block Line Numbers

Code blocks are numbered on the left by a CSS counter. `app/markdown_renderer.py`
wraps every code line in `<span class="code-line">` — CSS cannot enumerate the
lines of a text node, so the markup has to carry the structure the counter
counts — and `base.css` owns the counter rules:

- `counter-reset: code-line` on `.prose pre`
- `counter-increment: code-line` on `.code-line`
- `content: counter(code-line)` on `.code-line::before`, in a fixed-width gutter

The newlines stay between the spans rather than inside them, so the code text
(`textContent`) is unchanged and copy and paste still yields what the author
wrote. `base.css` owns the rules because the admin shell does not load
`public.css` and the admin live preview renders `.prose` code blocks too. No
JavaScript takes part in the numbering.
- `admin.css` — Admin dashboard styles
- Prism.js themes: `prism.css`, `prism-dark.css`, `prism-coy.css`, `prism-funky.css`, `prism-okaidia.css`, `prism-tomorrow.css`

### Dark Mode

Dark mode follows OS preference by default via `prefers-color-scheme: dark`. The visitor color-scheme system uses a 3-state model (system/dark/light) with the `data-color-scheme` attribute (migrated from `data-theme` in Phase 08). The `color-scheme.js` module:
- Checks `localStorage.getItem('blog-color-scheme')` for persisted preference
- Falls back to `prefers-color-scheme: dark` media query
- Toggles by setting `data-color-scheme` attribute to `light` or `dark`
- Persists choice to `localStorage` under the `blog-color-scheme` key
- Listens for OS theme changes when preference is `system`
- `dark-mode.js` re-exports from `color-scheme.js` for backward compatibility

### Critical CSS

`critical.css` provides above-the-fold styles for fast initial paint. It mirrors the actual navbar, hero, container, and post-card classes so the first paint uses the same dark theme as the full stylesheets. It is loaded immediately; the remaining stylesheets use `media="print" onload="this.media='all'"` for deferred loading.

### Design Tokens

`base.css` owns the fallback design tokens used by every theme, including spacing, typography, surfaces, borders, focus colors, and semantic colors. The inline `theme_vars` block in the base templates overrides the color tokens for the selected Halloy theme (default: "Catppuccin Mocha"). The theme system translates Halloy TOML palettes into the blog's semantic CSS variables via `BlogTheme` and `translate.py`. Keep new component rules on these variables so all bundled Halloy themes remain coherent.

Phase 09 is complete — all CSS files now use semantic variables (`var(--navbar-bg)`, `var(--overlay-bg)`, `var(--shadow-color)`, `var(--success-bg)`, `var(--error-bg)`, `var(--warning-bg)`, `var(--accent-dim)`, `var(--text-on-accent)`, etc.) instead of hardcoded color literals. The only remaining hardcoded values are: `:root` emergency fallbacks, print stylesheet, social share brand colors, lightbox backdrop, neutral shadows, and SVG/email assets. See `docs/themes/frontend-literal-audit.md` for the full audit.

**Token completeness is enforced.** `tests/test_css_contracts.py` collects every
`var(--x)` referenced by a stylesheet and asserts that each name is either emitted
by the theme runtime or defined in a stylesheet. This is what catches a token that
is referenced but never emitted — such tokens resolve to the guaranteed-invalid
value, so the declaration using them is dropped at computed-value time.

`--shadow-color` and `--code-bg` were both referenced by the stylesheets while
being emitted by no one: eight `box-shadow` declarations silently rendered as
`none`, and light-mode inline code had no background. They are now produced by the
translation layer (`app/themes/translate.py` via the `ALIASES` map in
`app/themes/model.py`), so every bundled theme supplies them without a 50-file
migration.

The runtime also emits a small number of legacy aliases that no stylesheet
consumes. They are kept because `tests/themes/test_phase09_css_tokens.py` and
`tests/themes/test_translation.py` pin the legacy alias set; the allow-list and the
per-token rationale live in `tests/test_css_contracts.py::DEAD_TOKEN_ALLOW_LIST`.

### Font Self-Hosting

Fonts are self-hosted in `app/static/fonts/` as woff2 files:
- Inter (weights 300–700) for body text (`--font-sans`)
- JetBrains Mono (weights 400, 500) for code blocks (`--font-mono`)
- Preloaded in `base.html` with the `crossorigin` attribute

### Admin Prism CSS Theme

`admin/base.html` uses `syntax_theme` variable for dynamic Prism CSS theme selection via `vite_asset('css/' + syntax_theme + '.css')`.

### Syntax Highlighting Themes

Six Prism.js themes available via `SiteSettings.syntax_theme`. Theme CSS is loaded dynamically using the `syntax_theme` context variable. Prism.js itself is lazy-loaded by `main.js` only when code blocks are present.

## Vite Configuration

Located at `vite.config.js`:
- Entry point: `app/static/js/main.js`
- Output: `app/static/dist/`
- Code splitting via `manualChunks` (vendor, admin, public)
- JSX support via esbuildOptions for `.jsx` files
- Dev server on port 3000 with proxy to Flask on port 5000

> **⚠️ Production Build Requirement:** The `npm run build` command (or `vite build`) must be executed before production deployment. This generates the `manifest.json` at `app/static/dist/.vite/manifest.json`. Without this build, templates fall back to unbundled source paths, so the production code-splitting entry point will not work correctly.
>
> **Docker builds handle this automatically.** The Dockerfile uses a multi-stage build where the first stage (`node:20-alpine`) runs `npm ci && npm run build`, and the runtime stage copies the resulting `app/static/dist/` into the final image. No manual build step is needed for Docker deployments.
>
> **Non-Docker deployments** require running `npm ci && npm run build` manually before starting the server.

> **⚠️ Restart a running server after every frontend build.** `app/vite.py` caches the Vite manifest in a module-level global for the life of the process. A rebuild renames the hashed bundles and deletes the old ones, but a server that is already running keeps serving the stale manifest — so it points at bundle files that no longer exist, the JavaScript never loads, and every interactive control silently does nothing. Restart the Flask server before you trust a browser check of a frontend change.

### Vite Asset Helper

`vite_asset()` in `app/vite.py` resolves content-hashed asset URLs and is registered as a Jinja2 global by `init_vite()`. It is used in the base templates for CSS, JS, fonts, and images.

In production:
- JS files: looks up hashed filename from `.vite/manifest.json`
- CSS/other: appends MD5 content hash as query string
- If `CDN_URL` is configured, prepends it to the asset path

### Chunk Split

Actual chunks via `manualChunks` in `vite.config.js`:
- `vendor` — Prism.js libraries (`prism.min.js`, `prism-languages.js`)
- `shared` — `shared/utils.js`, assigned explicitly so a failure inside an
  admin-only module cannot abort a shared module on a public page
- `admin` — Admin editor (`admin/editor.js`)
- `public` — Public search (`public/search.js`)

`shared/utils.js` must be assigned to the `shared` chunk **before** the
`/admin/editor.js` rule. `admin/editor.js` imports it, and without the explicit
assignment Rollup emits the shared module into the admin chunk — every public page
then fetches the admin chunk to obtain `initSharedUtils`.

`main.js` must not import a stylesheet. Flask links the stylesheets in the base
templates so the dev server and production share one cascade order; an import in
`main.js` would emit an orphaned CSS asset and append the stylesheet after every
linked one in dev.

## See Also
- [Templates](frontend/templates.md) - Jinja2 templates
- [App Factory](core/app-factory.md) - Vite initialization
