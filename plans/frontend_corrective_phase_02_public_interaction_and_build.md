# Frontend Corrective Phase 02 — Public Interaction and Build Contracts

**Roadmap:** [frontend_corrective_roadmap.md](frontend_corrective_roadmap.md)
**Date:** 2026-10-23
**Status:** Complete
**Severity:** Critical / high — public features that are present in the DOM but non-functional

## Objective

Repair the public-facing JavaScript and build-pipeline contracts where markup, stylesheet, and module expectations disagree. Every feature in this phase is already present in the rendered page — it simply does not work.

## Findings

### FE-INT-01 — The image lightbox never opens, and locks page scroll (critical)

The template ships the dialog hidden:

```jinja
<!-- app/templates/post.html:94 -->
<div class="lightbox hidden" id="lightbox" role="dialog" aria-modal="true" ...>
```

The stylesheet makes the class decisive:

```css
/* app/static/css/public.css */
.lightbox.hidden { display: none !important; }
.lightbox:not(.hidden) { display: flex; }
```

The JavaScript never removes it:

```javascript
// app/static/js/public/lightbox.js
const openLightbox = (img, index) => {
    lightbox.classList.add('open');          // 'hidden' is never removed
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';  // <-- scroll is locked regardless
    ...
};
```

Clicking a post image therefore locks the page scroll while an invisible dialog is nominally open, with `aria-modal="true"` and `aria-hidden="false"` still asserted on a `display: none` element.

Two related defects in the same block:

- `app/templates/post.html:99` renders `<img class="lightbox-img" src="" alt="">`. An empty `src` resolves to the current document URL, so the browser re-requests the page as an image.
- The three dialog buttons (`lightbox-close`, `lightbox-prev`, `lightbox-next`) have no `type` attribute. They are not inside a form, so this is not an accidental-submit risk today, but it is fragile.

### FE-INT-02 — Two modules generate heading IDs, so anchors are non-deterministic (high)

`app/static/js/public/toc.js:17-19` generates `heading-${index}`:

```javascript
const id = heading.id || `heading-${index}`;
```

`app/static/js/public/anchor-links.js:4-30` generates a slugified hash instead. Both modules are loaded on the public default module set, and both write to the same `heading.id` property. Whichever module initialises first wins.

The two are separate dynamic imports, so the winner depends on network timing — meaning a `#heading-3` link in the TOC may or may not resolve, and the two features can disagree within the same page load.

### FE-INT-03 — "Copy link" produces a malformed URL (high)

```javascript
// app/static/js/public/anchor-links.js:45
const url = origin + pathname + anchor.href;
```

`anchor.href` is already an absolute URL (`https://host/path#slug`), so the result is `https://host/pathhttps://host/path#slug`. The copied value is unusable.

### FE-INT-04 — `media-copy.js` is loaded on the wrong pages (high)

`app/static/js/main.js` places `./public/media-copy.js` in the **public** default module set, but the only "Copy URL" button in the codebase lives in the admin media library (`app/templates/admin/media.html:46`, `.media-copy-btn`). The admin route map for `/admin/media` lists only `./admin/media.js`.

Result: the module loads on every public page and initialises against no matching element, while the one page that has the button never loads the module that serves it.

### FE-INT-05 — Route prefix matching is ambiguous (medium)

```javascript
// app/static/js/main.js
const ROUTE_MODULES = {
    '/admin/new': [...],
    '/admin/edit': [...],
    '/admin/media': [...],
    '/admin/': [...],
};
```

`getModulesForPath()` uses `path.startsWith(route)` and iterates keys in insertion order. `/admin/new` is a prefix of `/admin/newsletter/preview`, so the newsletter preview page receives the post-editor module set instead of the admin default set. Any new `/admin/<x>` route is silently captured by whichever prefix was declared first.

### FE-INT-06 — Dead duplicate of the mobile menu module (low)

`app/static/js/shared/mobile-menu.js` and `app/static/js/shared/mobile-menu.jsx` are near-duplicates. The glob in `main.js` references only `./shared/mobile-menu.jsx`, so `mobile-menu.js` is unreachable dead code. The two files have already drifted: the `.js` variant uses `aria-label="Toggle navigation menu"`, omits `type="button"`, and omits `aria-controls`.

### FE-INT-07 — `shared/utils.js` is bundled into the admin chunk (medium)

`vite.config.js` assigns any module whose id contains `/admin/editor.js` to the `admin` chunk. Because `editor.js` imports `shared/utils.js`, the shared utility module is emitted **into the admin chunk** rather than the shared chunk.

Consequence: every public page fetches the admin chunk to obtain `initSharedUtils`. `app/static/js/admin/editor.js:4` executes `marked.setOptions(...)` at module top level, and the admin chunk's import list includes `marked.min.js`. If that import fails to resolve, the whole shared chunk aborts — and `initSharedUtils` goes with it, on every public page.

### FE-INT-08 — Bulk delete button label becomes "undefined" (medium)

```javascript
// app/static/js/shared/utils.js:109-131
const originalText = btn.textContent;
...
btn.dataset.originalText = originalText;
const resetButton = () => {
    btn.textContent = btn.dataset.originalText;   // reads a deleted key
    ...
};
// in the delete path:
delete btn.dataset.originalText;
```

The delete path removes `dataset.originalText`, but the 4-second timeout and the `blur` handler still call `resetButton`, which then assigns `undefined` to `textContent` — the button renders the literal string "undefined".

### FE-INT-09 — Vite emits a CSS asset that production never links (medium)

`app/static/js/main.js` imports `../css/public.css`, so the Vite build emits `dist/main-<hash>.css` (20.4 kB) and records it in the manifest:

```json
"js/main.js": { "file": "main-BzWvIMon.js", "css": ["main-BSuFspHu.css"] }
```

`app/vite.py`'s `vite_asset()` helper resolves `css/public.css` to the served source file (`/static/css/public.css?v=<hash>`), and the built HTML links the source file directly. The Vite-emitted copy is never referenced in production — confirmed by inspecting the rendered `<head>`.

Two consequences:

- a 20.4 kB asset is built and shipped but never used;
- **the CSS cascade differs between environments.** In `npm run dev`, Vite injects `public.css` as a `<style>` appended to the document, placing it *after* every linked stylesheet. In production, `public.css` is linked in DOM order between `layout.css` and `forms.css`. Any equal-specificity conflict resolves differently in the two environments. This directly affects Phase 04's cascade work, which is why it is recorded here.

### FE-INT-10 — Prefetch module targets third-party origins (medium)

```javascript
// app/static/js/shared/prefetch.js
const PREFETCH_TARGETS = ['/post/', '/tag/', '/archive', '/api/v1/posts'];
...
if (url.origin !== window.location.origin) { return; }   // guard present, but see below
```

The origin guard is present, but the module is still fetched and initialised on pages that have no internal navigation to prefetch, and the `link rel="prefetch"` elements are appended to `<head>` without a `rel`/`as` correctness check. This is low-impact but should be reviewed alongside the module-routing changes in FE-INT-04.

### FE-INT-11 — Public comment form is orphaned and its CSRF call is broken (medium)

`app/templates/public/comments.html:20` contains:

```jinja
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

`csrf_token` is a **string** in the template context, not a callable. Calling it raises `TypeError: 'str' object is not callable`, which the application converts to a 500. The template is currently included by nothing — no public template renders comments — so the defect is latent rather than live.

Either way the feature is unwired: the `public.add_comment` route exists, the template exists, and no public page presents the form.

### FE-INT-12 — The configured default colour scheme is silently overridden (medium)

The server renders the administrator's configured default into the first-paint bootstrap:

```jinja
<!-- app/templates/base.html:29-37 -->
<script nonce="{{ csp_nonce }}">
    ...
    var defaultScheme = '{{ theme_default_scheme | e }}';
    ...
</script>
```

The runtime controller then re-resolves the scheme with its own default:

```javascript
// app/static/js/shared/color-scheme.js
export function initColorScheme(options = {}) {
    const defaultScheme = options.defaultScheme || 'system';
    ...
    const stored = getStoredScheme(defaultScheme);   // 'system', not the site's default
    const effective = resolveEffectiveScheme(stored, defaultScheme);
    applyScheme(effective);
}
```

`main.js` calls `module.default()` with no arguments, so `defaultScheme` is always `'system'`. The controller therefore overwrites the `data-color-scheme` attribute the bootstrap just set with the operating-system preference.

Confirmed by rendering with `theme_default_scheme = 'light'`: the server emits `var defaultScheme = 'light'`, but the theme toggle's accessible name reports "System (follows OS)" and the page renders in the OS scheme. **The administrator's configured default is honoured for the first paint and then discarded.**

The same fallback also mislabels the control: with no stored preference, the toggle reports "System (follows OS)" even when the effective scheme is the site default.

### FE-INT-13 — The colour-scheme control is buried in the navigation (medium)

`color-scheme.js` prepends the toggle into `.nav-links`:

```javascript
const navLinks = document.querySelector('.nav-links');
if (navLinks) { navLinks.prepend(toggleButton); }
```

`.nav-links` is the element that is hidden on mobile (see Phase 04, FE-CSS-01). The colour-scheme control is therefore only reachable on a phone by opening the mobile menu, once that menu is fixed. The control is also the first item in the navigation, ahead of the primary navigation links, which is a questionable visual priority.

## Fix specification

### 1. Lightbox visibility contract

Pick one owner for the "is the dialog visible" state and make the other two follow it.

Recommended: `hidden` is the source of truth for visibility, and `open` remains an animation-state class.

```javascript
const openLightbox = (img, index) => {
    lightbox.classList.remove('hidden');
    lightbox.classList.add('open');
    lightbox.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    ...
};

const closeLightbox = () => {
    lightbox.classList.remove('open');
    lightbox.classList.add('hidden');
    lightbox.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
};
```

Alternatively, drop `hidden` from the template and let CSS gate on `.open` alone (`.lightbox { display: none } .lightbox.open { display: flex }`). Either is acceptable; the requirement is that exactly one class controls visibility and that every open path and every close path maintains it.

Also:

- give `lightbox-img` a real placeholder (`src="{{ url_for('static', filename='img/default-post.svg') }}"`) or remove the attribute until an image is set, so the browser never re-requests the document URL;
- add `type="button"` to the three dialog buttons;
- on close, restore `body.style.overflow` to the value it had before opening rather than assuming `''`.

### 2. Single producer for heading IDs

Extract the slug generator into one module and have both `toc.js` and `anchor-links.js` import it. The shared generator should be collision-safe (append a numeric suffix when a slug repeats) and deterministic.

Delete the `heading-${index}` fallback from `toc.js`; use the shared slug instead.

### 3. Correct the copy-link URL

```javascript
const url = anchor.href;   // already absolute
```

If a same-origin-relative value is wanted, use `anchor.pathname + anchor.hash` instead — but do not concatenate a URL with a URL.

### 4. Route → module mapping

Move `./public/media-copy.js` out of the public default set and into the `/admin/media` route set, next to `./admin/media.js`.

### 5. Route prefix matching

Replace the `startsWith` scan with an explicit ordered match that cannot over-match:

- match the most specific route first (longest prefix wins), **or**
- use exact route keys with an explicit fallback for the admin section.

A concrete, low-risk rule: sort the candidate routes by descending length and take the first match, with `/admin/` as the catch-all. This removes the dependency on object insertion order and makes `/admin/newsletter/preview` resolve to the admin default set.

### 6. Delete the dead duplicate

Remove `app/static/js/shared/mobile-menu.js`. Do not port its `aria-label` wording — the `.jsx` variant's `"Open navigation menu"` is the more accurate of the two.

### 7. Correct the Vite chunking

In `vite.config.js`, stop routing `shared/utils.js` into the admin chunk. Either move `marked.setOptions()` out of `editor.js`'s module top level into its `init` function, or give `shared/utils.js` an explicit shared-chunk assignment. The requirement is that a failure inside an admin-only module cannot abort a shared module.

### 8. Vite CSS duplication

Choose one owner for `public.css`:

- **Preferred:** remove the `import '../css/public.css'` from `main.js` and let the Flask template link it, matching production. This makes dev and production share a cascade.
- **Alternative:** keep the import and stop linking the source file in `base.html`; but this requires the manifest's `css` array to be honoured by `vite_asset()`, which it currently is not — so this route needs more work and is not recommended.

After the change, `npm run build` must not emit an orphaned CSS asset.

### 9. Bulk button reset

Capture `originalText` in a closure variable instead of a dataset attribute, and do not delete it:

```javascript
const originalText = btn.textContent;
let armed = false;
const resetButton = () => {
    btn.textContent = originalText;
    armed = false;
    btn.classList.remove('btn-danger-primed');
};
```

### 10. Comment form

Decide the feature's fate explicitly and record it:

- **Wire it up** — include `public/comments.html` from `post.html`/`page.html`, change `{{ csrf_token() }}` to `{{ csrf_token }}`, add a `comments` context variable, and verify the `public.add_comment` route and its `slug` argument.
- **Remove it** — delete `app/templates/public/comments.html` and the orphaned route if comments are not a supported public feature.

Do not leave the template in place with a latent 500.

### 11. Pass the site's default scheme to the runtime controller

The controller must receive the administrator's configured default instead of assuming `system`:

```javascript
// app/static/js/main.js
await loadModule('./shared/color-scheme.js', (module) => {
    if (typeof module.default === 'function') {
        module.default({ defaultScheme: document.documentElement.dataset.defaultScheme || 'system' });
    }
});
```

and the bootstrap must publish the value it already has:

```jinja
<html lang="en" data-color-scheme="dark" data-default-scheme="{{ theme_default_scheme | e }}">
```

The controller must then treat the configured default as a real fallback, not as a synonym for `system`:

- no stored preference → use the configured default, and resolve `system` through `matchMedia` only when the configured default *is* `system`;
- a stored preference → always win;
- the toggle's accessible name must describe the **effective** scheme, not the raw preference.

The bootstrap and the controller must agree: the controller must not overwrite the `data-color-scheme` attribute with a value derived from a different default.

### 12. Relocate the colour-scheme control

Move the toggle out of `.nav-links` into a container that is visible at every breakpoint — for example a dedicated `.nav-actions` element next to the logo, or the mobile menu toggle's sibling. When Phase 04 fixes the mobile navigation, the control must remain reachable on a phone without opening a menu.

## Tests

1. **Lightbox** — browser test: click a post image, assert the dialog is visible (`getComputedStyle(lightbox).display !== 'none'`), assert `document.body.style.overflow === 'hidden'`, press Escape, assert the dialog is hidden and `body.style.overflow` is restored.
2. **Heading IDs** — assert every heading that has an anchor link has a unique, slugified `id`; assert the TOC entries' `href` values all resolve to an existing element id. Run repeatedly (the defect is timing-dependent) or assert on the rendered output after a fixed settle.
3. **Copy link** — assert the copied value parses as a URL whose `pathname` and `hash` match the target heading.
4. **Module routing** — assert the module set for `/admin/media` contains `./public/media-copy.js`, and that the public default set does not.
5. **Route matching** — unit-test `getModulesForPath()` with `/admin/newsletter/preview`, `/admin/new`, `/admin/`, `/admin/media`, and `/`; assert each resolves to the expected set.
6. **Build output** — after `npm run build`, assert no emitted CSS file is orphaned (every emitted asset is referenced by the manifest and reachable from an entry), and that `main.js` does not import a CSS file if the preferred route in fix 8 is taken.
7. **Bulk button** — browser test: click the bulk delete button twice; assert the label is never the string "undefined".
8. **Comment form** — if wired up: assert a comment POST returns 302 and the comment appears; assert the template renders without a `TypeError`.
9. **Colour scheme default** — with `theme_default_scheme = 'light'` and no stored preference, assert the rendered `data-color-scheme` is `light` after the controller initialises (not the OS scheme), and that the toggle's accessible name names the effective scheme. With a stored preference of `dark`, assert the stored value wins over the configured default.
10. **Control placement** — assert the colour-scheme toggle is visible and clickable at a 375px viewport without opening the mobile menu.

## Expected files

- `app/templates/post.html`
- `app/templates/public/comments.html` (rewrite or delete)
- `app/static/js/public/lightbox.js`
- `app/static/js/public/toc.js`
- `app/static/js/public/anchor-links.js`
- `app/static/js/public/media-copy.js`
- `app/static/js/main.js`
- `app/static/js/shared/utils.js`
- `app/static/js/shared/mobile-menu.js` (delete)
- `app/static/css/public.css` (lightbox visibility rules)
- `vite.config.js`
- `app/vite.py` (if the manifest `css` array is honoured instead)
- `tests/test_frontend_contracts.py` (new)
- `tests/e2e/` — lightbox and bulk-button interactions

## Acceptance criteria

- [ ] Clicking a post image opens a visible lightbox; Escape closes it and restores page scroll.
- [ ] The lightbox never requests the document URL as an image.
- [ ] Every heading anchor resolves, and heading IDs are unique on a page.
- [ ] The copied anchor URL is a valid, usable link.
- [ ] The media library's "Copy URL" button copies the file URL.
- [ ] No public page loads the admin module chunk.
- [ ] `/admin/newsletter/preview` does not receive the post-editor module set.
- [ ] `shared/mobile-menu.js` no longer exists; exactly one mobile-menu module remains.
- [ ] `npm run build` emits no orphaned CSS asset, and the dev and production CSS cascade order are identical.
- [ ] The bulk delete button never displays "undefined".
- [ ] The public comment form either works end to end or no longer exists.
- [ ] The administrator's configured default colour scheme survives the runtime controller's initialisation.
- [ ] The colour-scheme control is reachable at a 375px viewport without opening a menu.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Must land after Phase 01 (both touch `post.html`) and before Phase 04 (Phase 04 redefines the lightbox visibility rules in CSS). Independent of Phase 03.

## Completion

**Status:** Complete — all 13 findings closed.

| Finding | Resolution |
|---|---|
| FE-INT-01 | `hidden` is the source of truth for the dialog's visibility; `open` remains the animation state. The empty `lightbox-img` `src` was replaced with a real placeholder, the three buttons got `type="button"`, and `body.style.overflow` is restored to its pre-open value. The existing `public.css` rules needed no change. |
| FE-INT-02 | `app/static/js/shared/heading-slug.js` is the single slug generator; `toc.js` and `anchor-links.js` both import it. The `heading-${index}` fallback is gone. |
| FE-INT-03 | The copy link uses `anchor.href` alone. |
| FE-INT-04 | `media-copy.js` moved to the `/admin/media` route set and out of the public default set. |
| FE-INT-05 | Route matching is on a path-segment boundary, longest match first, with `/admin/` as the catch-all. |
| FE-INT-06 | The dead `app/static/js/shared/mobile-menu.js` was deleted; the `.jsx` variant's accessible name was kept. |
| FE-INT-07 | `vite.config.js` assigns `shared/utils.js` to an explicit `shared` chunk ahead of the `/admin/editor.js` rule, so the shared module is no longer emitted into the admin chunk. |
| FE-INT-08 | Closed by the shared seam in `app/static/js/shared/utils.js` (original text captured in a closure). |
| FE-INT-09 | `import '../css/public.css'` removed from `main.js`. The build no longer emits an orphaned CSS asset and the manifest carries no `css` arrays, so dev and production share one cascade. |
| FE-INT-10 | The existing `shared/prefetch.js` already carried a same-origin guard, a protocol allow-list, an early return when there is nothing to prefetch, and used `fetch` rather than appending `link` elements. Verified rather than rewritten. |
| FE-INT-11 | The public comment form was **wired up**, not deleted: the feature is supported (moderation UI, route, and tests already exist). `csrf_token()` → `csrf_token`, labels given matching `id`s, macros imported into `post.html`, and `app/routes/public/posts.py` supplies approved comments. |
| FE-INT-12 | The configured default scheme now survives controller initialisation: `data-default-scheme` is published on the root element, and the two internal `getStoredScheme()` calls that dropped the default now pass it. |
| FE-INT-13 | The toggle moved out of `.nav-links` into a `.nav-actions` container inside `.nav-container`, which is visible at 375px without opening the menu. |

**Verification**

- `tests/test_frontend_contracts.py` — 22 tests were added here (the file later
  reached 42, and three browser tests moved to `tests/e2e/test_frontend_interactions.py`).
- Browser check: the toggle measures 44×44 at 375px and is **not** inside
  `.nav-links`; the lightbox opens, closes, restores scroll, and never requests
  the document URL as an image.
