# Visual Design Phase 06 — Article Furniture

> **Plan status: ACTIVE — not started.** Nothing in this plan has shipped. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Not started
**Severity:** Medium — the share panel occupies the top of the article, and the page has no visual hierarchy between its structure and its content.

## Objective

Let the article start where the reader expects it, and give the page a voice for
its structure so that the structure is distinguishable from the content.

## Findings

### VD-17 — The share panel occupies the top of the article (medium)

`app/templates/_post_content.html` renders the share bar inside `.post-content`,
before the TL;DR and before the article body:

```jinja
<div class="post-content">
{% if show_full_share %}
<div class="share-bar" data-post-id="{{ post.id }}" data-share-url="{{ share_url }}">
    <span class="share-label">Share</span>
    ... six network links and a copy button ...
</div>
{% else %}
<div class="share-bar" ...>
    <span class="share-label">Share</span>
    <button class="share-btn share-copy" ...>...</button>
</div>
{% endif %}

{% if post.summary %}
<div class="tldr">...</div>
{% endif %}

<div class="post-body prose">
    {{ post.body | markdown_safe | safe }}
</div>
```

Seven controls in a bordered panel sit between the hero image and the first
paragraph. Measured at 1280px the panel is 966px wide and 76px tall.

This is the operator decision of 2026-10-27: the share bar moves below the
article. It keeps every network and its current behaviour; only its position
changes.

### VD-18 — Structure and content are the same voice (low)

Five kinds of text on the public site share one size and one colour:

| Kind | Size | Colour | Role |
|---|---|---|---|
| Table-of-contents title ("On This Page") | 12.8px | `--text-muted` | structure |
| Table-of-contents entry | 14px | `--text-muted` | structure |
| Share label ("Share") | 12.8px | `--text-muted` | structure |
| Sidebar heading ("Tags") | 12.8px | `--text-muted` | structure |
| Post metadata (date, reading time) | 12.8px | `--text-muted` | structure |

The body prose is 16.8px in `--text`, so the difference is a size and a colour
difference — which is enough to read the prose, but not enough to read the
*structure* as structure. A reader cannot tell at a glance which parts of the
page are navigation.

The metadata is already set in the mono face (`Fira Code`), which is the right
instinct: mono marks the machine-facing parts of a page. The instinct stops
there.

## Fix specification

### 1. The share bar moves below the article

In `app/templates/_post_content.html`, the share bar moves to **after** the
`.post-body` and **before** the `.author-card`:

```jinja
<div class="post-body prose">
    {{ post.body | markdown_safe | safe }}
</div>

{% if show_full_share %}
<div class="share-bar" data-post-id="{{ post.id }}" data-share-url="{{ share_url }}">
    ...
</div>
{% else %}
<div class="share-bar" data-post-id="{{ post.id }}" data-share-url="{{ share_url }}">
    ...
</div>
{% endif %}

{% set post_author = resolve_author(post) %}
...
<div class="author-card">...</div>
```

The reader finishes the article and is offered sharing before the byline. The
alternative placement — after the author card — is acceptable and must be
recorded in the phase's `## Completion` section if it is chosen.

Nothing about the markup changes except its position. The `data-post-id` and
`data-share-url` attributes travel with it, so `app/static/js/public/share.js`
is unaffected.

The panel's spacing changes with its position: `margin-bottom: 24px` becomes
`margin-top: 24px`, because the bar is no longer the first child of
`.post-content`.

### 2. A structural voice

The structural elements — the table-of-contents title, the table-of-contents
entries, the share label, the sidebar headings — get one shared treatment that
separates them from the content without competing with it:

- The **mono face**, which the metadata already uses. Structure on a technical
  page reads as machine-facing.
- A **smaller size** than the body, which they already have.
- **Uppercase with letter-spacing** for the *titles* — the "On This Page"
  label, the "Share" label, the sidebar headings — so they read as labels
  rather than as headings.
- The **caption role** from Phase 02 for their colour, so they clear 4.5:1.

```css
/* app/static/css/public.css */
.post-toc-title,
.share-label,
.sidebar-title {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-caption);
}
```

The table-of-contents **entries** keep their current size and weight — they are
links, and links should look like links — but take the caption role for colour,
and they keep their hover and focus treatment.

The metadata keeps the mono face it already has. Phase 02 gives it the caption
role for colour, and this phase leaves its size alone.

The stylesheet that owns each element keeps it. `.post-toc-title` and
`.share-label` are owned by `app/static/css/public.css`; `.sidebar-title` is
owned by `app/static/css/layout.css`, which is where it is declared today. The
`.sidebar-title` rule moves with the change, and no rule is declared in two
sheets.

### 3. What this phase does not change

- **The share bar's contents.** Six networks and a copy button, in the same
  order, with the same labels and the same `title` attributes.
- **The share JavaScript.** `app/static/js/public/share.js` finds the bar by
  class and reads its data attributes; moving the bar does not affect it.
- **The keyword shortcut.** The "Press C to copy" hint still applies.
- **The tag pill styling on the index.** Phase 05 caps the row; this phase
  does not restyle the pills.

## Tests

1. **The bar is below the article (unit)** — assert that in
   `app/templates/_post_content.html` the `.share-bar` element appears after the
   `.post-body` element in the source.
2. **The bar is unchanged (unit)** — assert the bar still contains six network
   links and one copy button in the full variant, and one copy button in the
   compact variant.
3. **The bar is rendered after the prose (browser, `tests/e2e/`)** — assert the
   share bar's bounding box `top` is greater than the article body's bounding
   box `top` plus the article body's height, and that the article body's `top`
   is less than the share bar's `top`.
4. **The article starts higher (browser)** — assert that the first paragraph's
   `top` on the post page is **at least 100px higher** than it is before this
   phase, measured against the TL;DR's presence.
5. **The structural voice (unit)** — assert that `.post-toc-title`,
   `.share-label` and `.sidebar-title` are declared with the mono face and the
   uppercase treatment, and that they use the caption role rather than the
   muted role.
6. **The links still look like links (browser)** — assert a table-of-contents
   entry keeps its underline or its distinct link treatment, and that its
   computed colour is at least 4.5:1 against its background.
7. **The focus ring still shows (browser)** — assert a table-of-contents entry
   has a visible `:focus-visible` outline.
8. **The layout holds (browser)** — assert the post page has no horizontal
   scrollbar at 390px, and that the share bar wraps rather than overflowing at
   390px.

## Expected files

- `app/templates/_post_content.html` (the share bar's position)
- `app/static/css/public.css` (`.post-toc-title`, `.share-label`, the share bar's spacing)
- `app/static/css/layout.css` (`.sidebar-title`, if it is declared there)
- `tests/e2e/test_article_furniture.py` (new)
- `tests/test_css_contracts.py` (the structural voice)

## Acceptance criteria

- [ ] The share bar renders after the article body and before the author card.
- [ ] The share bar still contains every network and the copy button, and the copy button still works.
- [ ] The first paragraph of the article starts at least 100px higher on the page than before this phase.
- [ ] The table-of-contents title, the share label and the sidebar headings use the mono face, an uppercase treatment and the caption role.
- [ ] The table-of-contents entries keep their link treatment and clear 4.5:1.
- [ ] The share bar wraps rather than overflowing at 390px.
- [ ] The post page has no horizontal scrollbar at 390px.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Last in the series. Requires Phase 02, whose caption role this phase applies to
the structural elements, and Phase 03, which changes the measure the elements
sit around.

## Completion

**Status:** Not started.
