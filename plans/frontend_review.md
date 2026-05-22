# Frontend Architecture Review

## static-assets.md

### Verified Claims

**Directory Structure**: All files exist as documented:
- JS files in `js/admin/`, `js/public/`, `js/shared/`, `js/lib/` match exactly
- CSS files in `css/` match (base.css, admin.css, public.css, forms.css, layout.css, utilities.css, prism*.css)
- Fonts (woff2 files for Inter and JetBrains Mono) present in `fonts/`
- Images (favicon.svg, default-post.svg) present in `img/`
- `uploads/` and `dist/` directories exist

**Module Initialization Pattern**: Verified in main.js:85-96 - modules export `initXxx` functions called via `module.default()`.

**Route-Based Code Splitting**: Verified in main.js:30-83 using `import.meta.glob()` with `ROUTE_MODULES` object.

**JSX Support via esbuildOptions**: Verified in vite.config.js:30-39 with `.jsx` loader configuration.

**Vite Configuration**: Entry point `app/static/js/main.js`, output `dist/`, manualChunks, dev server on port 3000 all match.

### Discrepancies

1. **mobile-menu.jsx Import Bug**: main.js:72 imports `./shared/mobile-menu.js` but the actual file is `mobile-menu.jsx`. Vite's glob pattern on line 6-28 uses `./shared/mobile-menu.js` (matching the .js extension), but the actual file is JSX. This works by coincidence because Vite's glob uses glob patterns not exact file matching, but it's incorrect and confusing.

2. **vite.config.js missing vite-plugin-flask**: The AGENTS.override.md mentions `vite-plugin-flask` for Flask integration, but package.json and vite.config.js show no such plugin. This is a documentation error in AGENTS.override.md.

3. **CSS Directory Structure**: static-assets.md claims CSS files exist at root level but AGENTS.override.md shows a more detailed structure with `style.css` as aggregator and `themes/` subdirectory. The actual `css/` contains individual files (base.css, admin.css, etc.) without style.css or themes/ subdirectory.

### Bugs Found

1. **Critical - mobile-menu.jsx Extension Mismatch**: main.js:72 imports `./shared/mobile-menu.js` but the file is `mobile-menu.jsx`. While it happens to work (glob matches on `.js` finds `mobile-menu.jsx` too), this is incorrect and could break if the import pattern changes.

### Improvement Opportunities

1. **vite-plugin-flask Reference**: AGENTS.override.md mentions `vite-plugin-flask` integration that's not in package.json or vite.config.js. Either add the plugin or remove the reference.

2. **mobile-menu.jsx**: Consider renaming to `.js` if no JSX features are used, or ensure the import correctly references `.jsx`.

3. **CSS Aggregator**: AGENTS.override.md mentions `style.css` as an aggregator but it doesn't exist. Either create it or update documentation.

---

## templates.md

### Verified Claims

**Directory Structure**: All listed templates exist:
- Error pages (_error.html, 404.html, 429.html, 500.html)
- Base templates (base.html, index.html, post.html, page.html, archive.html, search.html, series.html, tag.html)
- Partials (_post_content.html, _sidebar.html, macros.html)
- Admin templates (all 25+ files present)
- Email templates (base_email.html, confirm.html, newsletter.html, password_reset.html)
- Public partials (comments.html)

**Template Inheritance**: Verified - both admin/ and public templates extend base.html.

**Filters**: Verified in filters.py:
- `markdown_safe` (line 12-17)
- `reading_time` (line 19-25)
- `sanitize_css` (line 27-31)
- `post_image_url` (line 33-50)
- `post_image_srcset` (line 52-73)
- `post_image_avif_url_stub` (line 75-84) - returns None (stub)

**Context Processors**: Verified in context_processors.py:
- `inject_csrf()` lines 138-148
- `inject_config()` lines 150-161
- `inject_theme()` lines 163-165
- `inject_footer_data()` lines 167-191
- `inject_show_footer_posts()` lines 193-200

**Cache Invalidation Functions**: Verified - `invalidate_settings_cache()` line 30-32, `invalidate_footer_cache()` line 35-37.

### Discrepancies

1. **inject_config() Variable Names**: templates.md line 89-90 says:
   - `site_title` (not site_name) - CORRECT
   - `site_description` (not site_tagline) - CORRECT
   
   But AGENTS.override.md line 92 incorrectly says "site_name, site_tagline" which is wrong. The actual variable names in context processors match templates.md.

2. **public_preview.html**: templates.md line 21 lists `public_preview.html` but this file doesn't exist in app/templates/. It's possible this is a planned template or the file is missing.

3. **Missing Template - forgot-password.html**: templates.md line 36 lists `forgot-password.html` but this file exists in `app/templates/admin/`. ✓ (exists)

4. **Missing Template - disable_2fa.html**: templates.md line 34 lists `disable_2fa.html` but this file exists in `app/templates/admin/`. ✓ (exists)

### Bugs Found

1. **Minor - public_preview.html Missing**: Listed in templates.md but the file doesn't exist in app/templates/.

### Improvement Opportunities

1. **AGENTS.override.md Contradicts templates.md**: Line 92 says `inject_config()` provides `site_name, site_tagline` but actual code provides `site_title, site_description`. AGENTS.override.md should be corrected.

2. **Create public_preview.html**: If preview functionality for public pages exists, the template may need to be created.

---

## Overview.md

### Verified Claims

All component locations and purposes are accurate:
- JavaScript in `app/static/js/` ✓
- CSS in `app/static/css/` ✓
- Uploads in `app/static/uploads/` ✓
- Built assets in `app/static/dist/` ✓
- Templates in `app/templates/` ✓

---

## Summary

### Priority: High

1. **mobile-menu.jsx Import Bug** (main.js:72): Import references `.js` but file is `.jsx`. Should be `./shared/mobile-menu.jsx` or file renamed to `.js`.

### Priority: Medium

2. **AGENTS.override.md vite-plugin-flask**: References plugin not present in package.json or vite.config.js. Remove reference or add plugin.

3. **AGENTS.override.md inject_config()**: Says `site_name, site_tagline` but actual code uses `site_title, site_description`.

4. **public_preview.html Missing**: Listed in templates.md but doesn't exist.

### Priority: Low

5. **CSS Aggregator style.css**: Referenced in AGENTS.override.md but doesn't exist.

6. **CSS themes/ Directory**: AGENTS.override.md mentions `themes/` subdirectory but CSS files are flat in `css/`.