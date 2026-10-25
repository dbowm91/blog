# Frontend Corrective Phase 01 — Image Rendering Pipeline

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/frontend/overview.md](../architecture/frontend/overview.md); this file is the historical record.

**Roadmap:** [frontend_corrective_roadmap.md](frontend_corrective_roadmap.md)
**Date:** 2026-10-23
**Status:** Complete
**Severity:** Critical — affects every public page and the admin editor

## Objective

Make every post image render: on listing cards, on the post hero, on related-post thumbnails, on the author avatar, in the admin editor's cover-image preview, and in social preview metadata. No image may be broken (404) or invisible (`opacity: 0`).

## Findings

### FE-IMG-01 — Post image URLs are double-prefixed and 404 (critical)

`post_image_url` returns a **URL**, not a filename:

```python
# app/filters.py — post_image_url filter
result = storage.url(post.image) if storage.exists(post.image) else None

# app/storage.py — LocalStorageBackend.url
def url(self, filename: str) -> str:
    return f"/static/uploads/{filename}"
```

Every template that consumes the filter then re-wraps it as though it were a bare filename:

```jinja
{% set img = post|post_image_url %}
<img src="{{ url_for('static', filename='uploads/' + img) }}" ...>
```

Verified rendered output (post with a real upload):

```html
<img src="/static/uploads//static/uploads/demo.png" srcset="None" sizes="(max-width: 600px) 400px, 800px" ...>
```

The filter contract is covered by `tests/test_filters.py::test_post_image_url_filter_with_image`, which asserts the result equals `storage.url("test.jpg")`. **The filter is correct; the templates are wrong.** Do not change the filter — `S3StorageBackend.url` returns an absolute `https://...` URL, so the filter output is the only value that is correct for both backends.

Affected sites (the `{% set %}` line and the consuming `{% if img %}` branch):

| Template | Set | Consuming lines |
|---|---|---|
| `app/templates/index.html` | 21 | 27, 31 |
| `app/templates/tag.html` | 26 | 32, 36 |
| `app/templates/search.html` | 26 | 32, 36 |
| `app/templates/post.html` (related) | 78 | 80, 82 |
| `app/templates/_post_content.html` (hero) | 3 | 7, 9 |
| `app/templates/admin/editor.html` | 33 | 33–34 |
| `app/templates/post.html` (social) | 4 (`og_img`) | 11, 14, 22 |

`app/templates/_post_content.html` is included by `post.html` and `page.html`, so static pages are affected as well.

**Note on `admin/media.html:38,46` and `admin/editor.html`:** `media.html` uses `f.name` from `storage.list_files()`, which is a bare filename — that site is correct and must not be changed.

### FE-IMG-02 — `srcset="None"` is emitted into the markup (high)

`post_image_srcset` returns `None` when no `400_`/`800_`/`1200_` variants exist on disk (the normal case for an image uploaded before variants were generated, or for a default placeholder). Jinja renders `None` as the four-character string `None`:

```html
<img src="..." srcset="None" sizes="(max-width: 600px) 400px, 800px" ...>
```

The browser parses `"None"` as a valid 1× candidate and requests it. A `srcset` candidate list overrides `src` entirely, so this both requests a bogus URL and suppresses the real image.

Affected: `index.html:27`, `tag.html:32`, `search.html:32`, `_post_content.html:7`.

### FE-IMG-03 — Every lazily-loaded image is permanently invisible (critical)

```css
/* app/static/css/public.css */
.js img[loading="lazy"] {
    opacity: 0;
    transition: opacity 0.4s ease;
}

.js img[loading="lazy"].loaded,
.js img:not([loading="lazy"]) {
    opacity: 1;
}
```

The `.loaded` class is added in exactly one place:

```javascript
// app/static/js/shared/lazy-load.js
export function initLazyLoad() {
    if ('loading' in HTMLImageElement.prototype) {
        return;                       // <-- early return in every modern browser
    }
    ...
    img.addEventListener('load', () => img.classList.add('loaded'), { once: true });
}
```

`'loading' in HTMLImageElement.prototype` is `true` in Chrome 77+, Firefox 75+, and Safari 15.4+. The early return therefore executes in every browser that can run this codebase, and the `.loaded` class is never added. `app/static/js/main.js:3` adds the `js` class to `<html>`, so the `opacity: 0` rule applies and the image is never restored.

Verified by pixel-sampling a rendered homepage: the card image region measures `#181825` (the card's `--bg-surface`) rather than `#0d1117` (the `default-post.svg` fill) — the image is not painted at all.

The `.img-skeleton` shimmer is equally invisible, because `opacity` applies to the element's background as well as its content. The result is a permanently empty, silently shimmering placeholder.

### FE-IMG-04 — Admin editor cover-image preview is broken (high, follows FE-IMG-01)

`app/templates/admin/editor.html:33-34` renders the existing cover image through the same double-prefixed expression, so an admin editing a post with a cover image sees a broken image in the editor.

## Fix specification

### 1. Use the filter output directly

Replace every `url_for('static', filename='uploads/' + img)` with the filter output:

```jinja
<img src="{{ img }}" ...>
```

For the `srcset` attribute, guard on the value so `None` is never rendered:

```jinja
{% if srcset %}srcset="{{ srcset }}" sizes="(max-width: 600px) 400px, 800px"{% endif %}
```

### 2. Correct the social-preview image URL

`post.html:11,14,22` prepends `{{ base_url }}/static/uploads/` to `og_img`, which is already a URL. The value is root-relative for local storage and absolute for S3, so it must be composed conditionally:

```jinja
{% set og_abs = og_img if og_img and og_img.startswith('http') else (base_url ~ og_img if og_img else base_url ~ '/static/img/default-post.svg') %}
```

Use `og_abs` for `og:image`, `twitter:image`, and the JSON-LD `image` field.

### 3. Make the lazy-image contract explicit

Preferred approach — attach the load handler before the native early return, so the class contract holds on every browser:

```javascript
export function initLazyLoad() {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');

    lazyImages.forEach((img) => {
        const markLoaded = () => img.classList.add('loaded');
        if (img.complete && img.naturalWidth > 0) {
            markLoaded();
        } else {
            img.addEventListener('load', markLoaded, { once: true });
            img.addEventListener('error', markLoaded, { once: true });
        }
    });

    if ('loading' in HTMLImageElement.prototype) {
        return;   // native lazy loading handles the fetching; the class contract is satisfied above
    }
    // ...existing IntersectionObserver path...
}
```

The `error` listener is required so a broken image does not stay at `opacity: 0` forever.

Alternative (also acceptable, and arguably cleaner): drop the `opacity: 0` rule entirely and let the `.img-skeleton` shimmer be the only loading affordance. If this route is taken, the `.loaded` rule and the `transition` become dead and should be removed rather than left in place.

**Constraint:** whichever approach is chosen, the CSS and the JavaScript must agree on one contract. A rule that hides images must have a guaranteed restoration path.

### 4. Do not change the filter

`post_image_url` and `post_image_srcset` must keep returning URLs. `tests/test_filters.py` asserts this, and the S3 backend's absolute URLs would break if the filter returned bare filenames.

## Tests

Add to `tests/test_templates.py` (or a new `tests/test_image_rendering.py`):

1. **No double prefix** — render `/`, `/tag/<slug>`, `/search?q=…`, and a post page for a post that has a real uploaded image; assert no `src` attribute contains `/static/uploads//static/uploads/`.
2. **No `srcset="None"`** — render the same pages for a post without responsive variants; assert `srcset="None"` does not appear and that the attribute is either absent or a valid candidate list.
3. **srcset present when variants exist** — create `400_<file>`, `800_<file>`, `1200_<file>` in the storage backend; assert a valid `srcset` is rendered with the expected widths.
4. **Lazy image class contract** — assert `public.css` and `lazy-load.js` agree: the CSS selector that hides an image must have a matching restoration selector that the JavaScript actually applies. A regex assertion over the two files is acceptable as a regression guard if no browser harness is available.
5. **Editor preview** — render `admin/editor.html` for a post with a cover image; assert the `#image-preview-img` `src` resolves to an existing file (no double prefix).
6. **Social metadata** — render a post page; assert `og:image` and `twitter:image` are absolute URLs that do not contain a doubled path segment, and that the JSON-LD `image` matches `og:image`.

Extend the E2E suite (`tests/e2e/`) with a browser assertion that a post card image has a non-zero bounding box **and** a computed `opacity` of `1` after load. The opacity assertion is the one that catches FE-IMG-03, which a DOM-only test cannot detect.

## Expected files

- `app/templates/index.html`
- `app/templates/tag.html`
- `app/templates/search.html`
- `app/templates/post.html`
- `app/templates/_post_content.html`
- `app/templates/admin/editor.html`
- `app/static/js/shared/lazy-load.js`
- `app/static/css/public.css` (only if the alternative route in fix 3 is taken)
- `tests/test_image_rendering.py` (new) or `tests/test_templates.py`
- `tests/e2e/` — post image visibility assertion

## Acceptance criteria

- [ ] No rendered page contains `/static/uploads//static/uploads/`.
- [ ] No rendered page contains the literal `srcset="None"`.
- [ ] A post with a real uploaded image renders an `<img>` whose `src` returns HTTP 200.
- [ ] A post card image is painted: computed `opacity` is `1` and the element has non-zero size, in Chrome, Firefox, and Safari.
- [ ] A failed image load does not leave a permanently invisible element.
- [ ] `post_image_url` and `post_image_srcset` still return URLs (existing filter tests unchanged and passing).
- [ ] Social preview metadata resolves to a reachable absolute URL.
- [ ] `npm run build` succeeds; `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

None. This phase is independent of all others and can be implemented in parallel with Phases 02 and 03.

## Completion

**Status:** Complete — all 4 findings closed.

| Finding | Resolution |
|---|---|
| FE-IMG-01 | Templates consume `post_image_url` output directly. The double-prefix pattern was removed from `index.html`, `tag.html`, `search.html`, `post.html`, `_post_content.html`, `admin/editor.html`, and `app/templates/email/newsletter.html` (the last was found during implementation — same root cause, outside the original scope). |
| FE-IMG-02 | `srcset` is guarded on the filter's `None` result in every template. |
| FE-IMG-03 | `shared/lazy-load.js` attaches the `load` **and** `error` handlers before the native-support early return; an already-complete image is marked immediately. The CSS restoration path is unchanged. |
| FE-IMG-04 | The admin editor's cover-image preview uses the filter output directly. |

**Verification**

- `tests/test_image_rendering.py` — 7 tests. Each was confirmed non-vacuous by
  inverting the fix and observing the test fail.
- `tests/e2e/test_image_visibility.py` — 2 Chromium tests asserting the computed
  opacity is `1` and the element has a non-zero box, plus that a broken image does
  not stay invisible.
- Browser check: the post image measures 760×400 at `opacity: 1`.

**Note:** `app/static/dist/` is a gitignored build artifact and is not part of the
change.
