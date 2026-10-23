# Frontend Corrective Phase 04 — CSS Cascade, Theme Tokens, and Contrast

**Roadmap:** [frontend_corrective_roadmap.md](frontend_corrective_roadmap.md)
**Date:** 2026-10-23
**Status:** Complete
**Severity:** High / medium — layout behaviour that is decided by load order, and theme tokens that do not exist

## Objective

Make the stylesheet layer's behaviour intentional rather than emergent. Three classes of defect are addressed: rules that lose a cascade tie they should win, tokens the stylesheet references that the theme runtime never emits, and colour choices that fail contrast in the default scheme.

## Findings

### FE-CSS-01 — The mobile navigation can never collapse (high)

The intent is expressed in `base.css`, inside a `max-width: 768px` media query:

```css
/* app/static/css/base.css:493-506 */
@media (max-width: 768px) {
    .nav-links {
        display: none;
        flex-direction: column;
        align-items: flex-start;
        ...
    }
    .nav-links.open {
        display: flex;
    }
    .mobile-menu-toggle {
        display: block;
    }
}
```

But `layout.css` sets the same property unconditionally, and `layout.css` is linked **after** `base.css`:

```css
/* app/static/css/layout.css:63 */
.nav-links {
    display: flex;
    gap: var(--space-lg);
    align-items: center;
}
```

Both selectors have specificity (0,1,0). A media query does not add specificity, and cascade order is document order, so `layout.css:63` wins at every viewport width. The measured computed value at a 375px viewport is `display: flex` — the nav is permanently expanded.

Consequences, all confirmed by rendering at 375px:

- the theme toggle, search form, and nav links occupy a ~220px-tall block at the top of every mobile page;
- the hamburger button is rendered and sized (40×48) but has no effect, because `.nav-links.open` also resolves to `display: flex`;
- `align-items` resolves to `center` (from `layout.css`) rather than `flex-start` (from `base.css`), so the expanded items are centred instead of left-aligned;
- `flex-direction: column` from `base.css` still applies, so the expanded nav is a tall centred column.

The same class of defect affects `.mobile-menu-toggle`: `base.css:444` sets `display: none` unconditionally and `base.css:527` re-enables it inside the media query, but `critical.css:104` also sets `display: block` and is linked *before* `base.css` — the later rule wins correctly here, so the button's visibility is correct. Only `.nav-links` is affected, because only it has an unconditional competing declaration.

### FE-CSS-02 — The post title is black on black in the default (dark) scheme (high)

```css
/* app/static/css/public.css:351-358 */
.post-hero-title {
    font-size: 2.2rem;
    font-weight: 700;
    ...
    color: var(--text-on-accent);
}
```

The hero title sits over the page background, not over the accent colour. The theme runtime emits `--text-on-accent` as the contrasting colour *for the accent*, and in the default Catppuccin Mocha theme that is `#000000`:

| Scheme | `--text-on-accent` | `--bg` | Contrast |
|---|---|---|---|
| dark (default) | `#000000` | `#11111b` | **1.12 : 1** |
| light | `#ffffff` | `#dce0e8` | 1.32 : 1 |

Light mode is repaired by an override that dark mode lacks:

```css
/* app/static/css/base.css:227 */
[data-color-scheme="light"] .post-hero-title {
    color: var(--text);
}
```

The dark scheme therefore renders every post's `<h1>` at 1.12:1 contrast — far below the WCAG AA 4.5:1 threshold and effectively unreadable. The rendered post page confirms it: the title is visible only as a slightly darker shape against the hero.

The same token misuse affects any other element that paints text over the background using `--text-on-accent`. The correct token for text over `--bg` is `--text`.

### FE-CSS-03 — Two referenced theme tokens are never emitted (high)

The theme runtime emits 36 CSS custom properties per scheme. Two properties referenced by the stylesheet are not among them and are not defined in any stylesheet either:

| Token | Used at | Effect |
|---|---|---|
| `--shadow-color` | `public.css:74,78,259,395,443,1290`, `admin.css:93,623` | 8 `box-shadow` declarations are invalid at computed-value time and render as `none` — no elevation anywhere |
| `--code-bg` | `base.css:232` | the light-scheme inline-code background is unset |

`--shadow-color` appears in `base.css:106` as a static definition, but that block sits under the dark-scheme static palette that the Halloy runtime is designed to replace; the runtime's own `:root` block overrides it, so the value is lost. This is a token-ownership collision between the static palette and the generated palette, not merely a missing key.

### FE-CSS-04 — There is no global anchor reset (medium)

No stylesheet defines a bare `a` rule. The only explicit `text-decoration` declaration for links is:

```css
/* app/static/css/public.css:847-848 */
.prose a {
    text-decoration: underline;
}
```

Every other link therefore inherits the browser's default `text-decoration: underline`. Post-card titles, navigation links, tag pills, footer post lists, breadcrumbs, and author links all render underlined, while the design clearly intends underlines only inside prose. Confirmed in the rendered page: sidebar "Recent Posts" entries, the nav "Posts" link, and the breadcrumb trail are all underlined.

The colour is also inconsistent: `.post-card-title a` sets `color: var(--text)`, but `.nav-links a` sets `color: var(--text-muted)`, so the same "link" role reads differently in each surface.

### FE-CSS-05 — The flash container mixes fixed positioning with the layout container (medium)

```css
/* app/static/css/public.css:424-433 */
.flash-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-width: 400px;
}
```

The markup applies both classes:

```jinja
<!-- app/templates/base.html:121 -->
<div class="flash-container container" role="status" aria-live="polite">
```

`.container` sets `max-width`, `margin: 0 auto`, and horizontal padding. The `right: 20px` is neutralised by the auto margins, so the toast stack is horizontally centred over the viewport rather than pinned to the top-right, and it inherits the container's padding. The two classes also fight over `max-width` (400px from `public.css` versus 1160px from `base.css`), resolved only by source order.

### FE-CSS-06 — The search field uses fixed pixel widths (medium)

```css
/* app/static/css/public.css:1183-1199 */
.search-input { width: 200px; }
.search-input:focus { width: 240px; }
```

The width does not respond to the viewport. At 375px the 200px field plus its button and the surrounding nav items exceed the available width, and the focus transition to 240px causes the surrounding nav to reflow at the moment the user starts typing.

### FE-CSS-07 — The print stylesheet prints the entire navigation chrome (low)

`base.css:674` opens a `@media print` block. The `a[href]::after { content: " (" attr(href) ")" }` rule at `base.css:776` is correctly scoped, but the block also prints the navbar, search form, share bar, and the "Recent Posts" / "Tags" sidebar, so a printed post includes the whole site chrome.

### FE-CSS-08 — Six emitted theme tokens are never consumed (low)

`coral-dim`, `info-bg`, `info-fg`, `text-dim-strong`, `warning-fg`, and `yellow-dim` are emitted for every scheme but referenced by no stylesheet rule. They are dead weight in every page's inline `<style>` block.

### FE-CSS-09 — The dev and production CSS cascade differ (medium)

Cross-referenced from Phase 02 (FE-INT-09). `main.js` imports `../css/public.css`, so `npm run dev` appends `public.css` to the document *after* every linked stylesheet, while production links it in DOM order between `layout.css` and `forms.css`. Equal-specificity conflicts resolve differently between the two environments.

This is the direct cause of the class of defect in FE-CSS-01 going unnoticed: a developer running `npm run dev` sees a cascade that production does not have.

## Fix specification

### 1. Make the mobile nav rule unambiguous

Two viable approaches. Choose one and apply it consistently.

**Option A — scope the conflicting rule.** Change `layout.css:63` so its `display: flex` only applies above the mobile breakpoint:

```css
@media (min-width: 769px) {
    .nav-links {
        display: flex;
        gap: var(--space-lg);
        align-items: center;
    }
}
```

and move the mobile declarations fully into `base.css`'s existing `max-width: 768px` block, which already has the correct intent.

**Option B — remove the duplicated declarations.** Keep `layout.css:63` as the single owner of `display` for `.nav-links` and delete the `display: none` / `display: flex` pair from `base.css`, replacing the mobile behaviour with a class that `mobile-menu.jsx` toggles.

Either way, the requirement is: **exactly one stylesheet owns `.nav-links` visibility at each breakpoint**, and the toggle's effect is observable.

Add a regression test that asserts the computed `display` of `.nav-links` at 375px and at 1280px.

### 2. Fix the hero title token

```css
.post-hero-title {
    color: var(--text);
}
```

and delete the now-redundant `[data-color-scheme="light"] .post-hero-title` override in `base.css:227`.

Audit every other use of `--text-on-accent` and confirm each one paints text on an `--accent` background. Where it paints on `--bg` or `--bg-surface`, switch to `--text`.

Then assert a contrast floor for the title in both schemes — the theme system's own accessibility validator (`app/themes/diagnostics.py`) should be extended to cover the "text on background" pair, not only "text on accent".

### 3. Define the missing tokens in the theme runtime

`--shadow-color` and `--code-bg` must be emitted by the theme translation layer, not patched in the stylesheet, so that every one of the 50 bundled themes provides them.

- In `app/themes/model.py`, add the two fields to the `BlogTheme` dataclass and to the `CSS_VARS` mapping.
- In `app/themes/translate.py`, derive them: `--shadow-color` from the background hue at low alpha (for example `rgba(0,0,0,0.35)` for a dark scheme and `rgba(0,0,0,0.12)` for a light one), and `--code-bg` from the surface hue.
- In `app/themes/bundled/*.toml`, the 50 theme files need the new keys, or the translator must derive them when absent (derivation is preferable — it avoids a 50-file migration and keeps new themes correct by default).
- Remove the static `--shadow-color` definition at `base.css:106` so the static palette and the generated palette no longer compete.

Add a test that asserts every custom property referenced by any stylesheet is either emitted by the theme runtime or defined in a stylesheet — the check that would have caught this.

### 4. Add an anchor baseline

In `base.css`, alongside the other element baselines:

```css
a {
    color: var(--accent);
    text-decoration: none;
}

a:hover,
a:focus-visible {
    text-decoration: underline;
}
```

Then audit the existing per-surface link rules so colour is consistent: either every link uses `--accent`, or every link inherits `--text` and only interactive emphasis changes it. Pick one and apply it across `.nav-links`, `.post-card-title`, `.tag`, `.breadcrumb`, and the footer.

The `.prose a` rule keeps its underline — that is the intended exception.

### 5. Separate the flash container from the layout container

Remove the `container` class from the flash wrapper in `base.html`, and give `.flash-container` its own centring rule that is not `margin: 0 auto`:

```css
.flash-container {
    position: fixed;
    top: 20px;
    right: 20px;
    left: auto;
    width: min(400px, calc(100vw - 40px));
    ...
}
```

### 6. Make the search field fluid

```css
.search-input {
    width: 100%;
    min-width: 0;
}

.search-input:focus {
    width: 100%;   /* no width change on focus */
}
```

and let the wrapper control the size:

```css
.search-input-wrapper {
    flex: 1 1 auto;
    min-width: 0;
    max-width: 220px;
}
```

This removes both the overflow and the focus-induced reflow.

### 7. Print stylesheet

Add to the `@media print` block in `base.css`:

```css
.navbar, .search-form, .share-bar, .sidebar, .flash-container, .footer { display: none !important; }
```

Confirm the printed output contains only the article body and the permalink.

### 8. Remove the dead tokens

Either consume the six unused tokens in appropriate rules (several of them — `warning-fg`, `info-fg` — look intended for admin status badges) or drop them from the emitted set in `app/themes/translate.py`. Prefer consuming them if the admin UI genuinely needs status colours, so the theme system can style badges per theme.

### 9. Align the dev and production cascade

Landed as part of Phase 02 (FE-INT-09), but verified here. The requirement is that the set of stylesheets, their order, and their media attributes are identical in `npm run dev` and in a production build.

## Tests

1. **Mobile nav** — browser test at 375px: assert the computed `display` of `.nav-links` is `none` before the toggle and `flex` after; assert the expanded nav's height is less than 120px; assert the toggle button is visible and has an accessible name. Repeat at 1280px to assert the nav is visible without a toggle.
2. **Hero title contrast** — a test that reads the rendered theme variables for both schemes, computes the contrast ratio of the title colour against the background, and asserts at least 4.5:1. Run across all 50 bundled themes.
3. **Token completeness** — a static test that collects every `var(--x)` reference across `app/static/css/*.css` and asserts each name is either emitted by the theme runtime or defined in a stylesheet. This is the test that would have caught `--shadow-color` and `--code-bg`.
4. **Anchor baseline** — assert that a post-card title link computes `text-decoration-line: none` and that a link inside `.prose` computes `underline`.
5. **Flash container** — assert the flash wrapper's computed `right` and `left` resolve as intended and that it is not centred by auto margins.
6. **Search field** — assert the input's width at 375px does not exceed its container, and that focusing it does not change the width.
7. **Print** — assert the print stylesheet hides the navbar, sidebar, and share bar.
8. **Cascade parity** — assert that the stylesheet list and order emitted in the production HTML matches the order the dev server uses.

## Expected files

- `app/static/css/base.css`
- `app/static/css/layout.css`
- `app/static/css/public.css`
- `app/static/css/critical.css`
- `app/templates/base.html`
- `app/themes/model.py`
- `app/themes/translate.py`
- `app/themes/diagnostics.py`
- `app/static/js/shared/mobile-menu.jsx`
- `tests/themes/` (contrast and token-completeness tests)
- `tests/test_frontend_contracts.py` (new)

## Acceptance criteria

- [ ] At 375px the navigation is collapsed and the hamburger visibly expands it.
- [ ] At 1280px the navigation is expanded and the hamburger is hidden.
- [ ] The post title's computed contrast is at least 4.5:1 in both schemes, for all 50 bundled themes.
- [ ] Every `var(--x)` reference in the stylesheets resolves to a defined or emitted value.
- [ ] Elevation shadows are visible on cards, modals, and the flash stack.
- [ ] Links outside prose are not underlined by default, and links inside prose are.
- [ ] The flash stack is pinned to the top-right and does not shift the layout.
- [ ] The search field fits a 375px viewport and does not resize on focus.
- [ ] The print stylesheet omits site chrome.
- [ ] The dev server and production produce the same stylesheet order.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Must land after Phase 02 (FE-INT-09 changes the cascade) and Phase 03 (FE-ADM-07 changes the admin preview visibility classes). Must land before Phase 05, whose contrast and focus work is defined against the corrected cascade.

## Completion

**Status:** Complete — all 9 findings closed.

| Finding | Resolution |
|---|---|
| FE-CSS-01 | `layout.css` scopes `.nav-links` to `@media (min-width: 769px)`, so exactly one stylesheet owns its visibility per breakpoint. A second, independent bug was found while verifying: `mobile-menu.jsx` replaced the button's `innerHTML` on toggle, detaching the clicked node so the document handler closed the menu again. Both icons are now rendered once and swapped via `aria-expanded` CSS. |
| FE-CSS-02 | `.post-hero-title` uses `var(--text)`; the light-mode override was removed. The post title now measures 13.1:1 in the dark theme and 6.9:1 in the light theme (was 1.12:1 / 1.32:1). |
| FE-CSS-03 | `--shadow-color` and `--code-bg` were referenced by the stylesheets and emitted by no one — eight `box-shadow` declarations silently rendered as `none`. Both are now produced by the translation layer, so every bundled theme supplies them without a 50-file migration. |
| FE-CSS-04 | A bare `a` baseline was added; `.prose a` keeps its underline as the intended exception. |
| FE-CSS-05 | `.flash-container` got its own positioning rule. |
| FE-CSS-06 | `.search-input` is fluid and no longer changes width on focus. |
| FE-CSS-07 | The print stylesheet hides the navbar, search form, share bar, sidebar, flash container, and footer. |
| FE-CSS-08 | `--warning-fg` and `--yellow-dim` were consumed by `.flash-warning`. The remaining four legacy aliases are retained because the Phase 09 alias contract pins them; they are documented in `tests/test_css_contracts.py::DEAD_TOKEN_ALLOW_LIST` with a per-token rationale. |
| FE-CSS-09 | Verified after Phase 02 landed: `main.js` imports no stylesheet, the build emits no CSS asset, and the manifest carries no `css` arrays — dev and production share one cascade. |

**Verification**

- `tests/test_css_contracts.py` — 26 tests: token completeness, title contrast
  across all 50 themes and both schemes, shadow resolution, nav ownership, anchor
  baseline, and the dead-token allow-list.
- `tests/themes/test_text_on_background_contrast.py` — 9 tests covering the
  diagnostics extension.
- Browser check: `.nav-links` computes `display: none` at 375px and `flex` after
  the hamburger click; the hovered card shadow resolves to
  `rgba(0, 0, 0, 0.12) 0px 12px 24px 0px`.

**Note:** the plan's claim that `--shadow-color` was defined at `base.css:106` was
wrong — it was defined nowhere. The real fix was the translation layer, not the
removal of a static definition.
