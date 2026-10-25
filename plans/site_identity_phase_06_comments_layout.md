# Site Identity Phase 06 — Comment Section Layout and Readability

> **Plan status: ACTIVE — not started.** The `## Completion` section at the end of this file records `**Status:** Not started.` Nothing in this plan has shipped. See the Active Plans section of [`AGENTS.override.md`](AGENTS.override.md).

**Roadmap:** [site_identity_authoring_roadmap.md](site_identity_authoring_roadmap.md)
**Date:** 2026-10-24
**Status:** Not started
**Severity:** High — the comment column does not line up with the post column, and the comment UI has no styling at all.

## Objective

Make the comment block read as part of the post: the same measure, the same
left edge, a visible reply hierarchy, and a form that behaves on a phone.

## Findings

### SIA-23 — The comment block does not share the post measure (high)

Measured in Chromium against `/post/sample-post-1` (a post with an approved
comment):

| Viewport | `.post-body` | `.comments` | Delta |
|---|---|---|---|
| 1280px | left 260, right 1020, **760px** | left 84, right 1196, **1112px** | 176px out on each side |
| 768px | left 24, right 744, 720px | left 24, right 744, 720px | aligned |
| 390px | left 24, right 366, 342px | left 24, right 366, 342px | aligned |

Root cause: `app/static/css/public.css` sets the measure on the **article**:

```css
.post-full {
    max-width: 760px;
    margin: 0 auto;
    padding: 0 0 64px;
}
```

`.post-full` is opened by `app/templates/_post_content.html:1`
(`<article class="post-full animate-in">`) and closed at the end of that
include. The comment section is a **sibling** of the article inside
`main.container`, which is `max-width: 1160px` (`app/static/css/layout.css:4`).
So the comments are laid out against the container, not the measure.

The comment *form* inherits the same width: the textarea measures
left 84 → right 1196 at desktop — the same 1112px as the block.

The alignment is correct on tablet and mobile only because the measure exceeds
the viewport there and both collapse to the container's inner width. The defect
is a desktop defect.

### SIA-24 — The comment block has no styling whatsoever (high)

`grep -n "comment" app/static/css/*.css` matches only Prism token rules
(`.token.comment`). There is not one rule for:

`.comments`, `.comments-title`, `.comments-empty`, `.comment-list`,
`.comment`, `.comment-meta`, `.comment-body`, `.comment-replies`,
`.comment-form`, `.comment-form-wrapper`.

Measured computed styles for `.comments`: `border-top-width: 0px`,
`padding-left: 0px`, `background-color: rgba(0, 0, 0, 0)` — the block has no
rules of its own.

The result: the comment list is a wall of unstyled text. The author name, the
timestamp and the comment body all render at the same size and weight with no
separation. There is no rule, no surface, no divider between comments.

### SIA-25 — Replies have no visual hierarchy (high)

`app/templates/public/comments.html` nests replies with a `.comment-replies`
wrapper, but with no CSS the nesting is invisible. Measured with a
three-level thread (one top-level comment, one reply, one reply-to-reply):

| Viewport | top-level `left` | nested `left` |
|---|---|---|
| 1280px | 84 | 84, 84 |
| 768px | 24 | 24, 24 |
| 390px | 24 | 24, 24 |

A reply to a reply is rendered at exactly the same left edge as the original
comment. A reader cannot tell a reply from a top-level comment, and cannot
tell which comment is being replied to.

### SIA-26 — The reply form has no styling and no hierarchy (medium)

The reply form is rendered by the same `comment_form()` macro with a
`field_prefix`, so it is visually identical to the top-level form. There is no
indentation, no heading, no "replying to X", and no way back out of a reply.

### SIA-27 — The comment form does not declare a width (medium)

`app/static/css/forms.css` styles `.form-group input` and `.form-group
textarea`, but the comment form's fields are 1112px wide on desktop because
there is no max width on the form. The textarea's `overflow-wrap` is
`break-word` and the input's is `normal`, so a long unbroken URL in a name
field can overflow.

## Fix specification

### 1. One measure for the article and its comments

Introduce a single shared measure class so the post body and the comment block
cannot drift apart again.

In `app/static/css/public.css`:

```css
.content-measure {
    max-width: 760px;
    margin: 0 auto;
}
```

Apply it to `.post-full` (replacing the inline `max-width`/`margin` so there
is one producer of the measure) and to the comment block in
`app/templates/post.html`:

```jinja
<section class="comments content-measure" id="comments" aria-label="Comments">
```

`app/templates/page.html` uses `<article class="prose">` — a static page has
no comment block, so it does not need the class.

The `.related-posts` and `.series-navigation` blocks are also siblings of the
article. They are a different content type (a grid of cards and a prev/next
pair) and are not part of this phase. They are recorded in the roadmap's
out-of-scope list so the next reader knows the alignment was considered.

### 2. A comment stylesheet

Add the comment rules to `app/static/css/public.css` — the stylesheet the
public shell loads. Use **theme tokens only**, never literals:

| Rule | Tokens |
|---|---|
| `.comments` | `margin-top: var(--space-2xl)` |
| `.comments-title` | `var(--text)`, `var(--space-xl)` |
| `.comments-empty` | `var(--text-dim)` |
| `.comment` | `border-left: 1px solid var(--border)`, `padding-left: var(--space-md)` |
| `.comment + .comment` | `margin-top: var(--space-md)`, `border-top: 1px solid var(--border)` |
| `.comment-meta` | `var(--text-dim)`, `font-size: 0.875rem` |
| `.comment-body` | `var(--text)`, `line-height: 1.6`, `overflow-wrap: anywhere` |
| `.comment-replies` | `margin-left: var(--space-lg)`, `border-left: 2px solid var(--border)` |
| `.comment-form` | `max-width: 100%` |
| `.comment-form input`, `.comment-form textarea` | `width: 100%` |
| `.comment-form-wrapper` | `margin-top: var(--space-xl)`, `background: var(--bg-surface)`, `border: 1px solid var(--border)`, `border-radius: var(--radius)`, `padding: var(--space-lg)` |

No new theme tokens, no renames, no literals. The colours must work in both
the dark and the light scheme, which the token aliases already handle.

### 3. Reply hierarchy

- `.comment-replies` gets a left margin and a left rule so the thread reads as
  a tree.
- The nesting depth must be **capped** so a deep thread does not walk off the
  left edge of a phone screen. Cap the visual indent at two levels
  (e.g. `--space-lg` for level 1, `--space-lg` for level 2 and deeper), so
  level 3+ is visually flush with level 2.
- The `comment_form()` macro must render a reply heading naming the comment
  being answered, and the reply form must be visually subordinate to the
  top-level form.

The recursion in `render_comments()` is unbounded. Cap it in the macro:

```jinja
{% macro render_comments(comments, depth=0) %}
```

and stop recursing past the cap depth, or render deeper replies flat. The
cap must be a single constant used by both the template and the CSS.

### 4. The comment form

- Give the form a surface (`--bg-surface`), a border (`--border`) and padding,
  so it reads as a distinct block rather than three loose inputs.
- Set `width: 100%` on the inputs and the textarea so they fill the measure
  instead of the container.
- Add `overflow-wrap: anywhere` to `.comment-body` and to the form inputs so a
  long URL cannot overflow the column.
- The honeypot field (`website_url`, `.hidden-field`) must stay hidden — the
  new form styling must not reveal it. Assert this in a test.

### 5. Mobile

At 390px the measure collapses to the container's inner width (342px). The
reply indent must fit inside that:

- Level-1 reply indent: `var(--space-md)` (or smaller) on mobile.
- The comment form's padding must shrink on mobile so the fields keep a
  usable width.
- Long unbroken strings in a comment must wrap rather than force a
  horizontal scrollbar.
- Assert `document.documentElement.scrollWidth <= window.innerWidth` on the
  post page at 390px with a deep thread present.

### 6. Interaction with Phase 01

When `comments_enabled` is false, the whole block is not rendered (Phase 01).
This phase styles the block that exists when comments are enabled. The
"comments are closed" note must be styled by the same rules so it does not
look broken.

## Tests

1. **Measure (unit)** — assert the rendered post page contains the shared
   measure class on both the article and the comment section.
2. **Alignment (browser, `tests/e2e/`)** — at 1280px, assert
   `Math.abs(article.left - comments.left) <= 2` and
   `Math.abs(article.width - comments.width) <= 2`. This is the regression
   test for SIA-23.
3. **Alignment (browser)** — repeat at 1024px and 768px.
4. **Comment styles exist (unit)** — assert the stylesheet contains rules for
   `.comment`, `.comment-meta`, `.comment-body`, `.comment-replies` and
   `.comment-form`. A plain substring assertion over the CSS file is
   acceptable and is the cheapest guard against the block being unstyled
   again.
5. **Theme tokens only (unit)** — assert the new comment rules contain no
   hex colour literal and no `rgb(`/`hsl(` literal. Follow the existing
   pattern in `tests/test_css_contracts.py`.
6. **Reply hierarchy (browser)** — with a three-level thread, assert the level-1
   reply's left edge is greater than the top-level comment's left edge, and
   that the level-2 reply is not further left than the level-1 reply.
7. **Indent cap (browser)** — assert a level-4 reply is not further left than
   the cap.
8. **Form width (browser)** — assert the textarea's width is within 2px of the
   comment block's width, and that the Name and Email inputs match.
9. **Honeypot (browser)** — assert the `website_url` input is not visible and
   has zero rendered size.
10. **No overflow (browser)** — at 390px with a deep thread and a long
    unbroken URL in a comment, assert
    `document.documentElement.scrollWidth <= window.innerWidth`.
11. **Copy fidelity (unit)** — assert a comment body containing `<b>` renders
    as escaped text, not markup. The comment body is rendered with
    `{{ comment.content }}`, which autoescapes — assert it stays that way.
12. **Dark and light (browser)** — render the post page in both colour schemes
    and assert the comment surface's background differs between them (proving
    the tokens resolve rather than falling back to a literal).

## Expected files

- `app/static/css/public.css` (measure class, comment rules, mobile rules)
- `app/templates/post.html` (measure class on the comment section)
- `app/templates/public/comments.html` (depth cap, reply heading, reply form)
- `app/templates/_post_content.html` (use the shared measure class)
- `tests/test_comments_layout.py` (new)
- `tests/e2e/test_comments_layout.py` (new)

## Acceptance criteria

- [ ] The comment block starts at the same left edge as the post body and has the same width, at 1280px, 1024px and 768px.
- [ ] The comment form fields are the width of the comment block, not of the page container.
- [ ] Comments, replies, the author name, the timestamp and the form are visually distinct.
- [ ] A reply is visibly indented under the comment it answers.
- [ ] The reply indent is capped so a deep thread cannot walk off the screen.
- [ ] A long URL or an unbroken string in a comment wraps instead of overflowing.
- [ ] The post page has no horizontal scrollbar at 390px.
- [ ] The honeypot field stays hidden.
- [ ] The new rules use theme tokens only and work in both colour schemes.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Last in the series. Requires Phase 01 (the `comments_enabled` flag that can
hide the block) and lands after Phase 04, which also edits
`app/templates/post.html`.

## Completion

**Status:** Not started.
