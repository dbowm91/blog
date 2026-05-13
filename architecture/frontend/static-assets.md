# Static Assets (`app/static/`)

Frontend JavaScript and CSS assets.

## Directory Structure

```
app/static/
├── js/
│   ├── admin/          # Admin dashboard JS
│   │   ├── bulk.js
│   │   ├── editor.js
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
│   │   ├── marked.min.js
│   │   └── prism.min.js
│   ├── image-preview.js
│   ├── main.js         # Entry point with route-based code splitting
│   ├── prism-languages.js
│   └── upload.js
├── css/                # SCSS/CSS files
├── fonts/              # Web fonts (woff2)
├── img/                # Static images (favicon, default-post)
├── uploads/            # User-uploaded media (local fallback; production may use S3)
└── dist/               # Vite build output
```

## JavaScript

### Module Initialization Pattern

JavaScript modules must export a default initialization function named `initXxx` (e.g., `export default initDarkMode`). The module loader in `main.js:85-96` calls `module.default()` if it exists:

```javascript
// Correct - default export named initXxx
export default function initMyModule() { ... }

// Incorrect - named export without default
export function setup() { ... }
```

### Route-Based Code Splitting

Code splitting is implemented in `main.js:30-83` using `import.meta.glob()`. Modules are loaded dynamically based on the current route:

```javascript
const ROUTE_MODULES = {
    '/admin/posts': ['./shared/utils.js', './shared/modal.js', ...],
    '/admin/media': ['./shared/utils.js', './shared/modal.js', ...],
    '/admin/': ['./shared/utils.js', './shared/modal.js', ...],
};

function getModulesForPath(path) {
    // Returns route-specific modules or default public modules
}
```

This allows Vite to create optimized chunks that are only loaded when needed.

### Lazy Image Loading

CSS pattern for progressive image loading:
- Default: `opacity: 0`
- `.loaded` class: `opacity: 1` with transition
- JavaScript adds `document.documentElement.classList.add('js')` first to enable progressive enhancement

### Admin Body Class Detection

Admin pages can be detected via `document.body.classList.contains('admin-body')`.

### JSX Support

JSX files (like `mobile-menu.jsx`) are handled via Vite's esbuild options in `vite.config.js:31-39`:

```javascript
optimizeDeps: {
    esbuildOptions: {
        loader: {
            '.js': 'js',
            '.jsx': 'jsx',  // JSX support for .jsx files
        },
    },
}
```

### Admin JS
- Dashboard functionality
- Post editor enhancements
- Media management
- Settings forms

### Public JS
- Comments submission
- Newsletter subscription
- Search functionality

## CSS

Stylesheets in `app/static/css/`:
- Base styles
- Component styles
- Theme-specific styles

## Vite Configuration

Located at `vite.config.js`:
- Entry point: `app/static/js/main.js`
- Output: `app/static/dist/`
- Code splitting via `manualChunks` (vendor, admin, public)
- JSX support via esbuildOptions for `.jsx` files
- Dev server on port 3000 with proxy to Flask on port 5000

## See Also
- [Templates](frontend/templates.md) - Jinja2 templates
- [App Factory](core/app-factory.md) - Vite initialization
