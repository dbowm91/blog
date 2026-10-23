# Frontend Corrective Phase 05 — Accessibility, SEO, and Markup Semantics

**Roadmap:** [frontend_corrective_roadmap.md](frontend_corrective_roadmap.md)
**Date:** 2026-10-23
**Status:** Complete
**Severity:** Medium / low — the site is broadly presentable; these are correctness and comprehension issues

## Objective

Close the gaps in semantics, labelling, and social metadata. Unlike the earlier phases, most findings here do not break a feature outright; they make the site harder to use with assistive technology, harder to share correctly, or leave dead markup that will mislead the next maintainer.

## Findings

### FE-A11Y-01 — The series navigation is dead markup pointing at a non-existent endpoint (critical, latent 500)

`app/templates/_sidebar.html:10-22` renders a series navigation block:

```jinja
{% if series_nav %}
<div class="sidebar-section">
    <h3 class="sidebar-title">Series Navigation</h3>
    <div class="series-nav">
        {% if series_nav.prev %}
        <a href="{{ url_for('public.post', slug=series_nav.prev.slug) }}" class="series-link prev">&larr; {{ series_nav.prev.title }}</a>
        {% endif %}
        <a href="{{ url_for('public.series', slug=series_nav.series_slug) }}" class="series-link series-index">{{ series_nav.series_title }}</a>
        ...
```

Three separate problems:

1. **`series_nav` is never provided by any route.** A repository-wide search finds `series_nav` only in this template. The `{% if %}` guard is therefore always false and the block never renders — the feature is not implemented.
2. **`public.series` does not exist.** The route function is `series_view` (`app/routes/public/browse.py:379`), so the endpoint is `public.series_view`. Calling `url_for('public.series', ...)` raises:

   ```
   werkzeug.routing.BuildError: Could not build url for endpoint 'public.series'
   with values ['slug']. Did you mean 'public.series_view' instead?
   ```

   The error is currently masked by finding 1, but the moment a route starts supplying `series_nav`, every post in a series returns a 500.
3. **The field names do not match the model.** The template reads `series_nav.series_title` and `series_nav.prev.title`, but the `Series` model has a `name` column (`app/models.py:461`), not `title`.

### FE-A11Y-02 — The newsletter email field has no label (medium)

```jinja
<!-- app/templates/index.html:12 -->
<input type="email" name="email" placeholder="Subscribe to our newsletter..." required>
```

The field is identified only by its placeholder. A placeholder disappears as soon as the user types, is not reliably announced by screen readers, and is not a substitute for a programmatic label. The same form appears on the homepage only, so this is a single site.

### FE-A11Y-03 — Social preview metadata is empty by default (medium)

```jinja
<!-- app/templates/base.html:27-30 -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{% block twitter_title %}{% endblock %}">
<meta name="twitter:description" content="{% block twitter_description %}{% endblock %}">
{% block twitter_image %}{% endblock %}
```

`twitter:title` and `twitter:description` default to empty strings, and `twitter:image` has no default block content at all. Combined with `twitter:card=summary_large_image` — a card format that *requires* an image — a shared link on the homepage, an archive page, a tag page, or any page other than a post produces a card with no title, no description, and no image.

By contrast, the Open Graph tags on the same page do have defaults (`og:title` falls back to `site_title`, `og:description` to `site_description`), which makes the omission on the Twitter side an inconsistency rather than a deliberate choice.

### FE-A11Y-04 — `og:image` has no default on non-post pages (medium)

`base.html` declares `og:title`, `og:description`, `og:type`, and `og:url`, but no `og:image`. Only `post.html` provides one. Every other page — index, archive, tag, search, series — shares without an image, and several platforms render a link card with a blank thumbnail.

### FE-A11Y-05 — Duplicate landmark headings between the sidebar and the footer (medium)

The sidebar and the footer render identical heading text in the same page:

```jinja
<!-- app/templates/_sidebar.html -->
<h3 class="sidebar-title">Recent Posts</h3>
...
<h3 class="sidebar-title">Tags</h3>

<!-- app/templates/base.html:140,149 -->
<h3 class="footer-heading">Recent Posts</h3>
...
<h3 class="footer-heading">Tags</h3>
```

A screen-reader user navigating by heading list sees "Recent Posts" and "Tags" twice with no indication of which is which. The two regions are also not distinguished by a `role` or `aria-label`, so the duplication is not resolvable from the accessibility tree.

### FE-A11Y-06 — The page `<h1>` is the site title rather than the page subject (low)

On the homepage the only `<h1>` is the site name:

```jinja
<!-- app/templates/index.html:9 -->
<h1 class="hero-title">{{ site_title }}</h1>
```

and the post titles are `<h2>`. This is a defensible pattern for a blog index, but it means the document heading of every listing page is the same string, so a screen-reader user who lands on the archive page hears the site name rather than "Archive" or "Tag: Python". The archive, tag, search, and series templates should carry their own `<h1>`.

### FE-A11Y-07 — Buttons omit the `type` attribute (low)

Several buttons inside forms omit `type`, which defaults to `submit`:

| Location | Button |
|---|---|
| `app/templates/base.html:107` | search clear (`<button type="button">` is set — this one is correct) |
| `app/templates/post.html:95-97` | `lightbox-close`, `lightbox-prev`, `lightbox-next` |
| `app/templates/base.html:126` | flash dismiss |

The lightbox buttons and the flash dismiss button are not currently inside a `<form>`, so there is no accidental-submit risk today, but the pattern is fragile: moving a button into a form later silently changes its behaviour.

### FE-A11Y-08 — Empty containers render without an empty state (low)

`app/templates/index.html:19` opens `<section class="posts-list">` and closes it after the loop, with no `{% else %}` branch. A site with no published posts renders an empty section between the hero and the footer, which reads as a rendering failure rather than an empty state. The codebase already has an `.empty-state` style used elsewhere, so the pattern exists and is simply not applied here.

The same applies to `tag.html` and `search.html` when a tag or query has no matches — though `search.html` does have an empty-results branch, so the inconsistency is between templates rather than universal.

### FE-A11Y-09 — The public comment form is unreachable (medium)

Cross-referenced from Phase 02 (FE-INT-11). `app/templates/public/comments.html` contains a working comment form, but no template includes it and no public page renders comments. The `public.add_comment` route exists. The public comment feature is therefore entirely unwired, and the template additionally calls `csrf_token()` as a function when the context value is a string — a latent `TypeError` that would 500 the request if the form were ever included.

### FE-A11Y-10 — The admin "posts" template does not exist (low, informational)

Documentation and route naming refer to `admin/posts.html`, but no such file exists — `admin/dashboard.html` serves as the post list. This is noted so that the next maintainer does not chase a missing file.

## Fix specification

### 1. Resolve the series navigation

Decide explicitly whether public series navigation is a feature.

**If it is:** implement it properly.

- Provide `series_nav` from the post route — the route already eagerly loads `Post.series_entries` via `joinedload`, so the data is available.
- Build a small, explicit context object with fields matching the template: `series_title`, `series_slug`, `prev`, `next`. Use the `Series.name` column, not `title`.
- Correct the endpoint to `public.series_view`.
- Alternatively, rename the route function from `series_view` to `series` so the endpoint becomes `public.series` and the template is right — but a function named `series` in a module that also defines `series_posts`-like names should be checked for collisions first.

**If it is not:** delete the block from `_sidebar.html` and remove the now-unused `joinedload` if nothing else depends on it.

Either way, the block must not survive in a state where enabling it produces a 500.

### 2. Label the newsletter field

```jinja
<form method="POST" action="{{ url_for('public.subscribe') }}" class="hero-subscribe">
    <label class="sr-only" for="newsletter-email">Email address</label>
    <input type="email" id="newsletter-email" name="email" placeholder="Subscribe to our newsletter..." required>
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <button type="submit" class="btn btn-primary">Subscribe</button>
</form>
```

The `.sr-only` class already exists in `base.css:283`.

### 3 and 4. Complete the social metadata

Give the Twitter and Open Graph blocks the same default behaviour:

```jinja
<meta property="og:title" content="{% block og_title %}{{ site_title }}{% endblock %}">
<meta property="og:description" content="{% block og_description %}{{ site_description }}{% endblock %}">
<meta property="og:image" content="{% block og_image %}{{ base_url }}/static/img/default-post.svg{% endblock %}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{% block twitter_title %}{{ site_title }}{% endblock %}">
<meta name="twitter:description" content="{% block twitter_description %}{{ site_description }}{% endblock %}">
<meta name="twitter:image" content="{% block twitter_image %}{{ base_url }}/static/img/default-post.svg{% endblock %}">
```

`post.html` already overrides all of these, so post pages are unaffected. Note that `post.html`'s `og_image` override is itself fixed by Phase 01 (FE-IMG-01) — the two phases touch the same block and must be coordinated.

### 5. Distinguish the sidebar and footer headings

Give each region an accessible name so the duplicate headings are disambiguated:

```jinja
<aside class="sidebar" id="sidebar" aria-label="Sidebar">
...
<footer class="footer" id="footer" aria-label="Site footer">
```

and make the heading text reflect the region — for example "Recent posts" in the sidebar and "Latest from the blog" in the footer — so the heading list is unambiguous.

### 6. Give every page a subject `<h1>`

Add a page-specific `<h1>` to `archive.html`, `tag.html`, `search.html`, and `series.html`. On `index.html`, keep the site title as the `<h1>` but demote the post titles to `<h3>` only if a page `<h1>` is introduced; otherwise leave the current h1→h2 progression intact, which is already valid.

### 7. Add explicit button types

Add `type="button"` to the lightbox buttons, the flash dismiss button, and any other `<button>` that is not a submit control.

### 8. Add empty states

```jinja
<section class="posts-list">
    {% for post in posts %}
        ...
    {% else %}
        <div class="empty-state">
            <h2>No posts yet</h2>
            <p>Nothing has been published so far. Check back soon.</p>
        </div>
    {% endfor %}
</section>
```

Apply the same to the tag and series listings.

### 9. Resolve the comment form

As part of Phase 02 (FE-INT-11) — either wire the form in and fix the `csrf_token` call, or remove the template.

## Tests

1. **Series navigation** — render a post that belongs to a series and assert HTTP 200; assert the series navigation either renders with correct links (if implemented) or is absent (if removed). A BuildError regression test must be added so the endpoint name cannot drift again.
2. **Labels** — assert every `<input>` on the homepage has an associated `<label>` (by `for`/`id` or by wrapping).
3. **Social metadata** — assert that the rendered homepage, archive, tag, and search pages all contain a non-empty `twitter:title`, `twitter:description`, `twitter:image`, and `og:image`.
4. **Landmarks** — assert the sidebar and footer have distinct accessible names, and that no two headings in a rendered page share the same text unless they are in differently-named regions.
5. **Heading order** — assert each page's heading levels never skip a level going down.
6. **Button types** — assert every `<button>` in the rendered output has an explicit `type` attribute.
7. **Empty states** — render the index with zero published posts and assert an `.empty-state` element is present.
8. **Comment form** — covered by Phase 02.

## Expected files

- `app/templates/_sidebar.html`
- `app/templates/base.html`
- `app/templates/index.html`
- `app/templates/archive.html`
- `app/templates/tag.html`
- `app/templates/search.html`
- `app/templates/series.html`
- `app/templates/post.html`
- `app/routes/public/posts.py` (only if series navigation is implemented)
- `tests/test_frontend_contracts.py` (new)

## Acceptance criteria

- [ ] A post in a series renders successfully, and the series navigation either works or is absent.
- [ ] Every form control has an accessible name.
- [ ] Every public page emits a non-empty title, description, and image for both Open Graph and Twitter Card.
- [ ] The sidebar and the footer are distinguishable in the accessibility tree.
- [ ] Heading levels never skip.
- [ ] Every button has an explicit `type`.
- [ ] Empty listings render an empty state rather than a blank region.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Must land after Phase 01 (`post.html`'s social metadata block is rewritten there) and after Phase 02 (the comment form is resolved there). Independent of Phases 03 and 04.

## Completion

**Status:** Complete — all 10 findings closed.

| Finding | Resolution |
|---|---|
| FE-A11Y-01 | The public series page is a supported feature (`public.series_view`, an admin moderation UI, and route tests all exist), so the navigation was **implemented**, not deleted. `app/routes/public/posts.py` gained `SeriesNavLink` / `SeriesNav` dataclasses and `_build_series_nav()`, which supplies `series_nav=` with the series `name`/`slug` and the neighbouring published posts ordered by `PostSeries.order_index`. The markup moved to `app/templates/_series_nav.html` and is included from both `_sidebar.html` and `post.html` — the sidebar is not rendered on the post page, so including it there was necessary for the feature to be live rather than merely not crashing. The endpoint is `public.series_view`; the model column is `Series.name`. A `BuildError` regression test pins the endpoint name. |
| FE-A11Y-02 | The newsletter field and the nav search field now have programmatically associated labels (`<label for>` plus a matching `id`); the nav label uses the existing `.sr-only` class. |
| FE-A11Y-03 | `twitter:title` and `twitter:description` now default to `site_title` / `site_description` instead of empty strings. |
| FE-A11Y-04 | `og:image` and `twitter:image` default to `{base_url}/static/img/default-post.svg`. Post pages override both and are unaffected. |
| FE-A11Y-05 | The sidebar `<aside>` and the `<footer>` carry distinct accessible names, and the colliding headings were renamed ("Recent posts" / "Latest from the blog", "Tags" / "Browse by tag"). |
| FE-A11Y-06 | The `archive`, `tag`, `search`, and `series` templates already had an `<h1>` each. Genuine heading-order skips were found and fixed instead: `series.html` went `h1` → `h3`, and every `.empty-state` heading was an `h3` directly under the page `h1`. Those are now `h2`. `index.html`'s `h1` → `h2` progression was left intact, as the plan allows. |
| FE-A11Y-07 | `type="button"` was added to the flash dismiss button and to the buttons in the files this phase owns. The two share-copy buttons in `_post_content.html` were left alone: they are not inside a form, so there is no submit risk, and that file was outside this phase's ownership. |
| FE-A11Y-08 | The `index`, `archive`, `tag`, `search`, and `series` templates already had `{% else %}` `.empty-state` branches. The real gap was the heading level, closed under FE-A11Y-06. |
| FE-A11Y-09 | Closed by Phase 02 — the public comment form is wired up. |
| FE-A11Y-10 | Verified informational only: `app/templates/admin/posts.html` does not exist; `app/templates/admin/dashboard.html` serves the post list. The stale reference is in `app/templates/AGENTS.override.md`. No code change. |

**Additional defect closed.** `.lightbox-caption` painted `--text-on-accent` on a
`rgba(0, 0, 0, 0.7)` scrim — black-on-black in the dark theme. No existing token
means "text on a scrim", and the alternatives were measured across all 50 bundled
themes: `--text` on `--bg-surface` bottoms out at 2.45:1 (fails AA), while
`--text-on-accent` on `--accent` bottoms out at 4.56:1 — the only pairing the
theme runtime guarantees. The caption now paints `background: var(--accent)` with
`color: var(--text-on-accent)`, so the token is used truthfully.

**Verification**

- `tests/test_frontend_contracts.py` — 23 new tests (42 in the file in total),
  each mutation-checked: removing the Twitter default, the `series_nav=` supply, the
  `aria-label`, the footer heading, and reverting the caption CSS each failed
  exactly the expected test.
- `tests/test_css_contracts.py::TestLightboxCaptionContrast` — 4 tests.
- `tests/e2e/test_frontend_interactions.py` — 3 browser tests: the configured
  default scheme surviving the controller, the colour-scheme control being
  reachable at 375px, and the lightbox opening and restoring page scroll. These
  live under `tests/e2e/` because a live server thread on the session-scoped
  application shares its database with the migration tests and corrupts their DDL.
- `tests/e2e/` — **58 passed, 0 failed** (was 8 failing before this work).
  `test_theme_toggle_aria_pressed` now passes.
- `tests/test_context_processors.py` — 7 assertions updated for the renamed footer
  headings.

**ARIA note.** The colour-scheme toggle is a tri-state control, so `aria-pressed`
is not a natural fit. It was implemented as "the visitor has explicitly overridden
the system default" (`system` → not pressed, `dark`/`light` → pressed), with
`aria-label` still naming the effective scheme. The state therefore does not flip
on every click — that is inherent to framing a tri-state control as binary.
