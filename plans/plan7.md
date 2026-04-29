# Frontend Improvement Plan — Plan 7

**Date:** 2026-04-28  
**Scope:** Stylistic & usability improvements for Blog CMS frontend  
**Investigation:** Deep-dive via subagents across all 17 identified items

---

## Executive Summary

A comprehensive review of the Blog CMS frontend identified **5 critical bugs**, **7 medium-priority improvements**, and **3 low-priority architectural suggestions**. The most severe issue is that **all JavaScript modules are non-functional** due to a bug in `main.js:68` — the module initialization code calls the module object as a function instead of calling the correct named exports.

**Root cause:** `modules.forEach(m => loadModule(m, fn => fn()));` passes the entire module object (e.g., `{ initDarkMode: Function }`) to the callback as `fn`, then tries to call `fn()` — which throws `TypeError` since the module object is not callable.

**Fix approach:** Add `export default` to each module's init function, then call `module.default()` in `main.js`.

**Estimated total effort:** ~3-4 hours

---

## Critical Bugs (Fix First — ~90 min)

### BUG 1: JS Modules Not Initializing
**Files:** `app/static/js/main.js:68`, all JS modules in `shared/`, `admin/`, `public/`

**Problem:** `modules.forEach(m => loadModule(m, fn => fn()));` receives the entire module object (e.g., `{ initDarkMode: Function }`) and tries to call it as a function. This throws `TypeError` — **all JS is broken**.

**Module init function names (verified):**
| Module Path | Init Function | Has Default Export? |
|-------------|---------------|----------------------|
| `shared/dark-mode.js` | `initDarkMode()` | ❌ Needs `export default initDarkMode;` |
| `shared/mobile-menu.js` | `initMobileMenu()` | ❌ Needs `export default initMobileMenu;` |
| `shared/lazy-load.js` | `initLazyLoad()` | ❌ Needs `export default initLazyLoad;` |
| `shared/utils.js` | `initSharedUtils()` | ❌ Needs `export default initSharedUtils;` |
| `shared/modal.js` | `initModal()` | ❌ Needs `export default initModal;` |
| `shared/toast.js` | `initToast()` | ✅ Has `export { initToast as default };` |
| `shared/nav-dropdown.js` | `initNavDropdown()` | ❌ Needs `export default initNavDropdown;` |
| `shared/filter-select.js` | `initFilterSelect()` | ❌ Needs `export default initFilterSelect;` |
| `shared/prefetch.js` | `initPrefetch()` | ❌ Needs `export default initPrefetch;` |
| `public/search.js` | `initSearch()` | ❌ Needs `export default initSearch;` |
| `public/lightbox.js` | `initLightbox()` | ❌ Needs `export default initLightbox;` |
| `public/toc.js` | `initToc()` | ❌ Needs `export default initToc;` |
| `public/share.js` | `initShare()` | ❌ Needs `export default initShare;` |
| `public/code-copy.js` | `initCodeCopy()` | ❌ Needs `export default initCodeCopy;` |
| `public/anchor-links.js` | `initAnchorLinks()` | ❌ Needs `export default initAnchorLinks;` |
| `public/media-copy.js` | `initMediaCopy()` | ❌ Needs `export default initMediaCopy;` |
| `admin/editor.js` | `initEditor()` | ❌ Needs `export default initEditor;` |
| `admin/bulk.js` | `initBulk()` | ❌ Needs `export default initBulk;` |
| `admin/shortcuts.js` | `initShortcuts()` | ❌ Needs `export default initShortcuts;` |
| `image-preview.js` | `initImagePreview()` | ❌ Needs `export default initImagePreview;` |
| `upload.js` | `initUpload()` | ❌ Needs `export default initUpload;` |

**Fix:**
1. Add `export default initXxx;` to each module that doesn't have it (all except `shared/toast.js`):
   - Add one line at end of each file (except `shared/toast.js` which already has it)

2. Fix `main.js:68`:
```javascript
modules.forEach(m => loadModule(m, module => {
    if (typeof module.default === 'function') {
        module.default();
    }
}));
```

**Verification:** After fix, verify dark mode toggle, mobile menu, search suggestions, and editor preview all work.

---

### BUG 2: Share Button Class Mismatch in Mobile CSS
**File:** `app/static/css/style.css:3482`

**Problem:** Mobile CSS hides non-existent classes:
```css
/* WRONG - these classes don't exist */
.share-btn-linkedin, .share-btn-hn, .share-btn-reddit, .share-btn-pinterest {
    display: none;
}
```

Correct classes (from lines 792-803): `.share-linkedin`, `.share-hn`, `.share-reddit`, `.share-pinterest` (doesn't exist)

**Fix:** Change line 3482 to:
```css
.share-linkedin, .share-hn, .share-reddit {
    display: none;
}
```

**Verification:** Resize browser to mobile width, verify share buttons are hidden.

---

### BUG 3: Toast Stacking Logic Broken
**File:** `app/static/js/shared/toast.js:51-53`

**Problem:** `translateY(-100%)` is relative to each element's own height. With 3+ toasts, they overlap because the offset isn't cumulative.

**Fix:** Replace the stacking loop with cumulative pixel-based offsets:
```javascript
const GAP = 12; // matches CSS gap
let cumulativeOffset = 0;

for (let i = toastStack.length - 1; i >= 0; i--) {
    const t = toastStack[i];
    t.style.transform = `translateY(-${cumulativeOffset}px)`;
    cumulativeOffset += t.offsetHeight + GAP;
}
```

**Verification:** Trigger 3+ toasts in quick succession, verify they stack without overlapping.

---

### BUG 4: Lazy Load Fallback Broken
**File:** `app/static/js/shared/lazy-load.js`

**Problem:** For browsers without native `loading="lazy"`, the code sets `loading="lazy"` attribute — which has no effect on those browsers. No actual polyfill exists.

**Fix:** Implement `IntersectionObserver` fallback:
```javascript
export function initLazyLoad() {
    const supportsNativeLazy = 'loading' in HTMLImageElement.prototype;
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');

    const addLoadedClass = (img) => {
        if (img.complete) {
            img.classList.add('loaded');
        } else {
            img.addEventListener('load', () => img.classList.add('loaded'), { once: true });
            img.addEventListener('error', () => img.classList.add('loaded'), { once: true });
        }
    };
    lazyImages.forEach(addLoadedClass);

    if (supportsNativeLazy) return;

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        }, { rootMargin: '200px 0px' });

        lazyImages.forEach((img) => {
            if (!img.dataset.src && img.src) {
                img.dataset.src = img.src;
                img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
            }
            if (img.dataset.src) observer.observe(img);
        });
    }
}
```

Also update image templates to use `data-src` pattern:
```html
<img data-src="image.jpg" loading="lazy" alt="...">
```

**Verification:** Test in browser without native lazy loading support, or disable flag in Chrome.

---

### BUG 5: Modal `transitionend` Fires Multiple Times
**File:** `app/static/js/shared/modal.js:24-33`

**Problem:** Modal has both `opacity` and `transform` CSS transitions, so `transitionend` fires twice per open/close cycle.

**Fix:** Check `event.propertyName`:
```javascript
modal.addEventListener('transitionend', (e) => {
    if (e.propertyName !== 'opacity') return;

    if (!modal.classList.contains('hidden')) {
        previousActiveElement = document.activeElement;
        const focusable = modal.querySelector(focusableSelectors);
        if (focusable) focusable.focus();
    } else if (previousActiveElement) {
        previousActiveElement.focus();
        previousActiveElement = null;
    }
});
```

**Verification:** Open/close modal multiple times, verify focus management works correctly.

---

## Medium Priority Improvements (~90 min)

### IMPROVEMENT 6: Add `:focus-visible` to Interactive Cards

**Files:** `app/static/css/style.css`
- Line 4023: `.preset-card` (is a `<label>`, focusable)
- Line 1856: `.media-card` (is a `<div>`, add `tabindex="0"` if interactive)
- Line 891: `.related-card` (is an `<a>`, focusable)
- Line 2239: `.stat-card` (is a `<div>`, add `tabindex="0"` if interactive)

**Fix Pattern:**
```css
.related-card:focus-visible {
    border-color: var(--text-dim);
    transform: translateY(-2px);
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}
```

Apply similar pattern to `preset-card`. Only add to `media-card` and `stat-card` if they are interactive.

**Verification:** Tab through page, verify focus rings appear on all interactive cards.

---

### IMPROVEMENT 7: Guard Against Duplicate Dark Mode Toggle
**File:** `app/static/js/shared/dark-mode.js:34-40`

**Problem:** No check for existing `.theme-toggle` button — multiple `initDarkMode()` calls create duplicates.

**Fix:**
```javascript
const navLinksEl = document.querySelector('.nav-links');
if (navLinksEl && !navLinksEl.querySelector('.theme-toggle')) {
    const wrapper = document.createElement('span');
    wrapper.appendChild(themeToggle);
    navLinksEl.prepend(wrapper);
}
```

**Verification:** Call `initDarkMode()` twice, verify only one toggle button exists.

---

### IMPROVEMENT 8: Add `aria-selected` to Search Suggestions
**File:** `app/static/js/public/search.js`

**Problem:** Keyboard navigation (ArrowUp/Down) toggles `active` class but never sets `aria-selected="true"`.

**Fix:** In ArrowDown/ArrowUp handlers (around lines 71-86):
```javascript
if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (!active) {
        items[0]?.classList.add('active');
        items[0]?.setAttribute('aria-selected', 'true');
    } else {
        const idx = Array.from(items).indexOf(active);
        items[idx]?.classList.remove('active');
        items[idx]?.removeAttribute('aria-selected');
        items[idx + 1]?.classList.add('active');
        items[idx + 1]?.setAttribute('aria-selected', 'true');
    }
} else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (active) {
        const idx = Array.from(items).indexOf(active);
        items[idx]?.classList.remove('active');
        items[idx]?.removeAttribute('aria-selected');
        items[idx - 1]?.classList.add('active');
        items[idx - 1]?.setAttribute('aria-selected', 'true');
    }
}
```

**Verification:** Tab to search, use arrow keys, inspect DOM for `aria-selected="true"`.

---

### IMPROVEMENT 9: Add `theme-color` Meta Tag
**File:** `app/templates/base.html` (after line 16)

**Problem:** Mobile browser chrome color doesn't match site theme.

**Fix:**
```html
<meta name="theme-color" content="{{ theme_vars.bg }}">
```

Note: `theme_vars` is available from `app/context_processors.py:140`.

**Verification:** Open site on mobile, verify browser chrome color matches background.

---

### IMPROVEMENT 10: Add Sidebar Skip Link
**Files:** `app/templates/base.html` (after line 55)

**Problem:** Only main content has skip link — sidebar (`id="sidebar"`) has no skip target.

**Fix:**
```html
<a href="#sidebar" class="skip-link">Skip to sidebar</a>
```

**Verification:** Tab from page load, verify both skip links appear in order.

---

### IMPROVEMENT 11: Preload Inter 700 Font Weight
**File:** `app/templates/base.html` (after line 25)

**Problem:** Only Inter 400 and JetBrains Mono 400 are preloaded. Inter 700 (headings) causes FOUT.

**Fix:**
```html
<link rel="preload" href="{{ url_for('static', filename='fonts/inter-700-latin.woff2') }}" as="font" type="font/woff2" crossorigin>
```

**Verification:** Check Network tab, verify Inter 700 is preloaded.

---

### IMPROVEMENT 12: Fix Duplicate CSS Definitions

**File:** `app/static/css/style.css`

**Issues:**
1. `--space-sm-md: 12px` defined twice (lines 102 and 1613) — remove line 1613
2. `.toast` defined twice (lines 1495 and 3831) — rename second to `.toast-copied`:
   - Lines 3831-3848: change `.toast {` → `.toast-copied {`
   - Line 3850: change `.toast.visible {` → `.toast-copied.visible {`
   - `app/static/js/public/anchor-links.js:49`: change `toast.className = 'toast';` → `toast.className = 'toast-copied';`

**Verification:** Check toast notifications and "link copied" toasts work independently.

---

## Low Priority Suggestions (~30 min research/setup)

### IMPROVEMENT 13: Split `style.css` into Partials

**Current:** Single 4082-line CSS file

**Suggested structure:**
```
app/static/css/
├── style.css      # Manifest file with @imports
├── base.css       # Fonts, :root vars, reset, html/body
├── layout.css     # Navbar, container, footer
├── components.css # Buttons, forms, cards, tags
├── admin.css      # Dashboard, analytics, admin panels
├── prose.css      # Typography, post content, TOC
├── features.css   # Progress bar, back-to-top, share
└── responsive.css # All @media queries
```

**Implementation:** Create partials, then `style.css` becomes:
```css
@import url('base.css');
@import url('layout.css');
@import url('components.css');
@import url('admin.css');
@import url('prose.css');
@import url('features.css');
@import url('responsive.css');
```

---

### IMPROVEMENT 14: Light Mode Accent Color

**Status:** No fix needed — both `#0969da` (4.88:1) and `#0550ae` (7.18:1) pass WCAG AA. The initial assumption was incorrect.

**Optional enhancement:** Swap `--accent: #0969da` to `#0550ae` for higher contrast (7.18:1), then set `--accent-hover: #033d7a`.

---

### IMPROVEMENT 15: `prefers-reduced-motion` / `scroll-behavior` Spelling

**Status:** No bug found — all 5 instances are correctly spelled. The initial assumption was incorrect.

---

### IMPROVEMENT 16: Frontend Build Step

**Recommendation:** NOT YET NEEDED

Current setup (native ES modules, no transpilation) is fine for ~10 JS files and 4k CSS. If needed later, use a `Makefile` with:
- `esbuild` for JS bundling/minification
- `lightningcss` for CSS minification

Skip Flask-Assets (unmaintained).

---

### IMPROVEMENT 17: Email Template Inline Styles

**Files:** `app/templates/email/*.html`

**Problem:** Each template has 10+ inline styles.

**Options:**
1. **Keep as-is** — fine for small templates, email clients handle inline styles reliably
2. **Add premailer** — `pip install premailer`, add to `requirements.txt`, use in `app/email.py`:
```python
from premailer import transform
html_body = transform(html_body, keep_style_tags=True)
```

---

## Implementation Order

Recommended sequence to minimize breakage:

1. **BUG 1: JS module init** (everything else depends on this)
2. **BUG 5: Modal transitionend** (quick fix)
3. **BUG 2: Share button classes** (quick fix)
4. **BUG 3: Toast stacking** (test after JS init works)
5. **BUG 4: Lazy load polyfill** (test after JS init works)
6. **IMPROVEMENT 7: Dark mode guard** (quick fix)
7. **IMPROVEMENT 8: aria-selected** (quick fix)
8. **IMPROVEMENT 9: theme-color meta** (quick fix)
9. **IMPROVEMENT 10: Sidebar skip link** (quick fix)
10. **IMPROVEMENT 11: Font preload** (quick fix)
11. **IMPROVEMENT 12: Duplicate CSS** (quick fix)
12. **IMPROVEMENT 6: focus-visible cards** (styling task)
13. **IMPROVEMENT 13: CSS split** (architectural, can be separate PR)
14. **IMPROVEMENT 17: Email styles** (cosmetic, optional)

---

## Testing Strategy

### Critical Bug Verification
```bash
# Start dev server
ADMIN_PASSWORD=test SECRET_KEY=test python3 run.py &

# Run existing tests
ADMIN_PASSWORD=test SECRET_KEY=test python3 -m pytest tests/ --ignore=tests/e2e -v
```

### Manual Testing Checklist
- [ ] Dark mode toggle works (click, verify state persists)
- [ ] Mobile menu opens/closes (hamburger button)
- [ ] Search suggestions appear and keyboard navigation works
- [ ] Editor preview updates as you type
- [ ] Toast notifications stack correctly (3+ toasts)
- [ ] Modal open/close focuses correctly
- [ ] Share buttons hidden on mobile view
- [ ] `aria-selected` appears on active search suggestion
- [ ] Sidebar skip link appears and works
- [ ] Font preloading visible in Network tab

### CSS Validation
```bash
# Check for CSS syntax errors
curl -s https://jigsaw.w3.org/css-validator/validator?text=$(cat app/static/css/style.css)
```

---

## Summary Table

| # | Item | Priority | Effort | Files |
|---|------|----------|--------|-------|
| 1 | JS module init | 🔴 Critical | 20 min | main.js + 19 JS modules |
| 2 | Share button classes | 🔴 Critical | 2 min | style.css:3482 |
| 3 | Toast stacking | 🔴 Critical | 10 min | shared/toast.js |
| 4 | Lazy load polyfill | 🔴 Critical | 20 min | shared/lazy-load.js + templates |
| 5 | Modal transitionend | 🔴 Critical | 5 min | shared/modal.js |
| 6 | focus-visible cards | 🟡 Medium | 10 min | style.css |
| 7 | Dark mode guard | 🟡 Medium | 5 min | shared/dark-mode.js |
| 8 | aria-selected | 🟡 Medium | 5 min | public/search.js |
| 9 | theme-color meta | 🟡 Medium | 2 min | base.html |
| 10 | Sidebar skip link | 🟡 Medium | 2 min | base.html |
| 11 | Font preload | 🟡 Medium | 2 min | base.html |
| 12 | Duplicate CSS | 🟡 Medium | 10 min | style.css, anchor-links.js |
| 13 | CSS split | 🟢 Low | 60 min | style.css → 7 partials |
| 14 | Accent color | ✅ No fix | 0 min | — |
| 15 | Spelling check | ✅ No bug | 0 min | — |
| 16 | Build step | 🟢 Low | 30 min | Makefile (optional) |
| 17 | Email styles | 🟢 Low | 15 min | email templates + premailer |

---

**Total estimated time:** 3-4 hours (excluding low-priority architectural items)
