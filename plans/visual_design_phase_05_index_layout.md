# Visual Design Phase 05 — Index Layout

> **Plan status: ACTIVE — not started.** Nothing in this plan has shipped. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Not started
**Severity:** Medium — the index shows one headline per screen, and the sidebar repeats the list it sits beside.

## Objective

Get more posts in front of a reader per screen, and stop the sidebar spending
its space on a copy of the list next to it.

## Findings

### VD-15 — The sidebar repeats the main list (medium)

`app/templates/_sidebar.html` opens with:

```jinja
<div class="sidebar-section">
    <h3 class="sidebar-title">Recent posts</h3>
    <ul class="sidebar-links">
        {% for post in recent_posts_sidebar %}
        <li><a href="{{ url_for('public.post', slug=post.slug) }}">{{ post.title }}</a></li>
        {% endfor %}
    </ul>
</div>
```

`recent_posts_sidebar` is supplied by `app/context_processors.py` and holds the
five most recent published posts. The index page lists the same posts, in the
same order, immediately to the left of it. Measured at 1280px, the sidebar's
first five entries are "Code Lines Demo", "Sample Post 12", "Sample Post 11",
"Sample Post 10" and "Sample Post 9" — the top of the main list, in order.

The block costs 260px of column width, because the post titles wrap to two lines
in a narrow column, and it gives the reader nothing they cannot get from the
column beside it.

This is the operator decision of 2026-10-27: the "Recent posts" block is
dropped. "Tags", "Series navigation" and the RSS link stay.

### VD-16 — One headline per screen (low)

Measured at 1280×900 on the index:

| Element | Value |
|---|---|
| Hero | 208px tall, top 79px |
| First card | top 312px, 404px tall |
| Card image band | 200px |
| Card title | top 567px |
| Second card | top ~740px |

The reader sees one headline and one image before scrolling. The card spends
200px on an image, 24px of top padding, a metadata line, the title, a summary
and a row of five tag chips — 404px for one entry.

The tag row is the least earned part: `#python #flask #web-dev #database #api`
are five pills with borders and backgrounds, wrapping into the card's full
width and adding roughly 60px.

## Fix specification

### 1. A two-column card grid on wide viewports

The index's post list becomes a two-column grid at 1024px and above, and stays
one column below it. At 1280px each card is about 490px wide instead of 804px.

`app/templates/index.html` renders the list as `<section class="posts-list">`,
and `app/static/css/public.css` currently lays it out as a flex column:

```css
.posts-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
}
```

It becomes a grid:

```css
.posts-list {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-lg);
}

@media (min-width: 1024px) {
    .posts-list {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
```

The grid needs `minmax(0, 1fr)` rather than `1fr`, so that a long unbroken
title can shrink its column instead of forcing the grid wider.

The same treatment applies to the search results page, which renders the same
`.posts-list` markup, and to the archive and tag pages if they use the same
class.

### 2. The card loses its padding

With a 16:9 band from Phase 04, a 490px card has a 276px image. The card's own
padding must come down so the card is not mostly padding:

| Property | Before | After |
|---|---|---|
| `.post-card-body` padding | `24px 28px` | `20px 22px` |
| `.post-card-summary` | unclamped | clamped to two lines |

The summary is clamped with `-webkit-line-clamp: 2` and the standard
`line-clamp: 2`, with the existing overflow rules retained.

### 3. The tag row is capped

The card shows at most **four** tags plus a count of the rest. The container is
`.post-tags`, and it is a flex row with an 8px gap:

```jinja
<div class="post-tags">
    {% for tag in post.tags[:4] %}
    <a class="tag" href="{{ url_for('public.tag', slug=tag.slug) }}">#{{ tag.name | escape }}</a>
    {% endfor %}
    {% if post.tags|length > 4 %}
    <span class="tag tag-more">+{{ post.tags|length - 4 }}</span>
    {% endif %}
</div>
```

The `+N` chip is a label, not a link, and must carry an accessible name that
says how many tags the post has and that the full list is on the post page —
otherwise a screen reader announces a bare "+3". It must also not pick up the
`.tag:hover` lift, which is a link affordance; `.tag-more` gets its own rule.

The tag pill styling itself does not change in this phase, apart from
`.tag-more`. Phase 02 gives the pill's text the accent-text role, and Phase 06
gives the metadata and the tag treatments a distinct voice.

### 4. The sidebar loses the duplicate and narrows

`app/templates/_sidebar.html` drops the "Recent posts" section. The remaining
sections — "Series navigation" (when the post has one), "Tags" and the RSS
link — stay, in that order.

`app/context_processors.py` drops the `recent_posts_sidebar` query and the
context key from all three branches, so the sidebar's context does not carry a
list nobody renders.

The sidebar narrows, because the block that needed the width is gone.
`app/static/css/layout.css` currently declares:

```css
.content-layout {
    display: grid;
    grid-template-columns: 1fr 260px;
    gap: var(--space-2xl);
}
```

It becomes:

```css
.content-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 200px;
    gap: var(--space-2xl);
}
```

`minmax(0, 1fr)` rather than `1fr`, so that a long unbroken title in the main
column cannot push the grid wider than its container. The tag cloud is the
widest thing that remains in the sidebar, and a 200px column holds it.

### 5. What this phase does not change

- **The hero.** The 208px hero with the site title and the description is
  identity, not content. It stays.
- **The archive, search and tag pages.** They include the same sidebar, so they
  inherit the removal of the duplicate block. Their own list layouts are not
  changed by this phase.
- **The pagination.** The index's pagination control keeps its current
  position and behaviour.

## Tests

1. **No duplicate list (unit)** — assert `app/templates/_sidebar.html` contains
  no "Recent posts" heading, and that `app/context_processors.py` contains no
   `recent_posts_sidebar`.
2. **The sidebar keeps its other sections (unit)** — assert the sidebar still
   renders "Tags" and the RSS link.
3. **Two columns at 1280px (browser, `tests/e2e/`)** — assert the index's post
   list computes `grid-template-columns` with two tracks at 1280px and one track
   at 768px.
4. **The cards are narrower (browser)** — assert the first card's width is
   between 420px and 560px at 1280px.
5. **The tag row is capped (browser)** — assert that a post with five or more
   tags renders at most four `.tag` elements plus one `.tag-more`, and that the
   `.tag-more` element has a non-empty accessible name.
6. **No overflow (browser)** — assert `document.documentElement.scrollWidth <=
   window.innerWidth` on the index at 390px, 768px and 1280px.
7. **The sidebar narrows (browser)** — assert the sidebar's width is 200px at
   1280px.
8. **Density (browser)** — assert that at least **three** post titles are
   visible within the first 900px of the index at 1280px, measured against each
   title's bounding box. Before this phase the count is one.

## Expected files

- `app/templates/index.html` (the tag cap)
- `app/templates/_sidebar.html` (the "Recent posts" section removed)
- `app/templates/search.html` (the tag cap, if it renders the same card)
- `app/context_processors.py` (the `recent_posts_sidebar` query and key removed)
- `app/static/css/public.css` (the grid, the card padding, the summary clamp, the tag cap)
- `app/static/css/layout.css` (the sidebar width)
- `tests/e2e/test_index_layout.py` (new)

## Acceptance criteria

- [ ] The sidebar no longer lists recent posts, on any page that includes it.
- [ ] The context processor no longer queries for the sidebar's post list.
- [ ] The sidebar still renders "Tags" and the RSS link.
- [ ] The index shows two cards per row at 1280px and one at 768px.
- [ ] A card renders at most four tags plus a labelled count.
- [ ] The summary is clamped to two lines.
- [ ] At least three post titles are visible in the first 900px at 1280px.
- [ ] The index has no horizontal scrollbar at 390px, 768px or 1280px.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 04, which sets the card's image band to 16:9. The band's height
depends on the card's width, so the two must be measured together.

Runs before Phase 06.

## Completion

**Status:** Not started.
