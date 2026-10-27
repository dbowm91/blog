# Visual Design Phase 05 — Index Layout

> **Plan status: COMPLETE — shipped 2026-10-27.** The outcome is documented in
> [`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md#the-post-list-grid).
> See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Complete — shipped 2026-10-27
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

**Status:** Complete. Shipped 2026-10-27.

### What changed

- `app/templates/_sidebar.html` — the "Recent posts" section is gone. The
  sidebar holds, in order, "Series navigation" (only when the post belongs to
  a series), "Tags" and the RSS Feed link.
- `app/context_processors.py` — the `recent_posts_sidebar` query is gone from
  `_get_footer_data()`, and the key is gone from all three branches of
  `inject_footer_data()`.
- `app/static/css/public.css` — `.posts-list` is a grid: one column by
  default, two columns from 1024px, with `minmax(0, 1fr)` tracks.
  `.post-card-body`'s padding is `20px 22px`. `.post-card-summary` is clamped
  to two lines. The tag chip's hover lift moved from `.tag:hover` to
  `a.tag:hover`, and a new `.tag-more` rule styles the count chip.
- `app/static/css/layout.css` — `.content-layout` is
  `minmax(0, 1fr) 200px`.
- `app/static/css/critical.css` — `.posts-list` paints the same grid, because
  critical.css is the first paint.
- `app/templates/macros.html` — a new `post_tag_row(post, max_tags=4)` macro
  renders a card's tag row: at most four tag links, then a
  `<span class="tag tag-more">+N</span>` label.
- `app/templates/index.html`, `search.html` and `tag.html` — the three cards
  call the macro rather than looping over the tags themselves.
- `app/templates/_post_content.html` — the post page lists its whole set of
  tags in the footer, so the count a card hides is reachable.
- `tests/test_css_contracts.py` — a `TestIndexLayout` class: the list is a
  grid, the grid holds two columns from 1024px, the tracks can shrink, no
  stylesheet paints the list as a column, the sidebar column is 200px, the
  card's padding is tightened, the summary is clamped, the lift belongs to the
  link, and the count chip is a label.
- `tests/test_frontend_contracts.py` — the sidebar does not repeat the list,
  the sidebar keeps its own sections, the three cards share one tag row, and
  the post page lists every tag.
- `tests/test_context_processors.py` — the context processor no longer queries
  for the sidebar's list, the sidebar renders no post list, and the footer
  keeps its own.
- `tests/e2e/test_index_layout.py` — 13 browser tests: the index is two
  columns at 1280px and one at 768px, two cards sit side by side, a card is
  narrower than it was, the tag row is capped, the count chip carries an
  accessible name, the summary is clamped to two lines, no width overflows,
  the sidebar is 200px, the sidebar keeps its sections, and the index shows
  more than one headline per screen.

### Deviations from the plan

1. **The density target of three headlines in the first 900px is not reachable
   with the plan's own layout.** A two-column grid shows headlines in pairs,
   so three would have to mean four: the second row's two headlines would have
   to land above 900px. At 1280px the first row's headlines sit at 598px and
   the second row's at 972px, so the count is two. For the second row to fit,
   a card would have to be shorter than 278px, and the 16:9 band that Phase 04
   established is 235px of that on its own, before the metadata and the title.
   The count is **two, up from one**, and the test asserts that the first row
   holds two headlines and that a second row of headlines starts inside the
   next 300px. Reaching three would mean giving up the 16:9 band or replacing
   the full-width band with a side column, both of which are outside this
   phase.

2. **The card is 420px wide, not the 490px the plan expected.** At 1280px the
   main column is 864px wide once the 200px sidebar and the 48px gap are
   taken out, so two cards with a 24px gap are 420px each. The plan's 490px
   does not follow from its own measurements of the container.

3. **The tag cap lives in a macro.** The plan shows the cap inline in each
   template, but three templates render the same card. `post_tag_row(post)`
   in `app/templates/macros.html` is the single owner of the cap, so the
   three cards cannot drift apart.

4. **The plan lists `search.html` for the cap "if it renders the same card"
   but not `tag.html`.** `tag.html` renders the same card, so all three use
   the macro.

5. **`critical.css` also declares `.posts-list`, and the plan does not list
   it.** It is the first paint and it declared the list as a flex column, so
   it now paints the same grid. critical.css deliberately duplicates a small
   subset of the layout; it is a documented exception, not a second owner.

6. **The post page had no tag list.** The plan says the `+N` label must say
   "that the full list is on the post page", but the post page listed only the
   primary tag in its breadcrumb. Without a list there, the tags a card hides
   would have been unreachable from the index, which the cap would have made
   worse rather than better. The post page now renders its whole set of tags
   in the footer.

7. **The hover lift is scoped to `a.tag:hover`.** The plan says the count
   chip "must also not pick up the `.tag:hover` lift". The lift is a link
   affordance and every real `.tag` is an anchor, so the rule is now
   `a.tag:hover` and the chip is excluded by construction rather than by an
   override.

### Verification

Measured in Chromium against the running instance:

| Property | Before | After |
|---|---|---|
| List at 1280px | one 804px column | two 420px columns |
| List at 768px | one 736px column | one 736px column |
| Sidebar column | 260px | 200px |
| Card body padding | `24px 28px` | `20px 22px` |
| Card image band at 1280px | 802×451 | 418×235, ratio 1.778 |
| Headlines in the first 900px at 1280px | 1 | 2 |
| Card's tags | all of them | 4 and a labelled count |
| Summary | unclamped | two lines |

- The horizontal scrollbar is gone at 390px, 768px and 1280px.
- `pytest tests/e2e/test_index_layout.py` — 13 passed.
- `pytest tests/test_css_contracts.py tests/test_frontend_contracts.py
  tests/test_context_processors.py` — passed.
- `ruff check .` and `ruff format --check .` — clean.
- Full-suite comparison against the pre-phase baseline: the failure sets are
  identical apart from `tests/test_phase8.py::TestBackupRestore::test_download_backup`,
  which is a pre-existing order-dependent failure - `tests/services/test_operations_backup.py`
  writes `blog_verify_<uuid>.db` into the shared `instance/backups` directory and the
  phase 8 test downloads the first entry of an unsorted listing, which the route
  refuses when the name is not `blog_<timestamp>.db`. It failed 10 runs out of 10 on an
  unmodified checkout when those two modules shared a session, and the backup code is
  untouched by this phase.
