# Visual Design Phase 02 — Text Roles and the Contrast Floor

> **Plan status: COMPLETE — shipped 2026-10-27.** The outcome is documented in [`architecture/core/themes.md`](../architecture/core/themes.md) and [`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md). This file is the historical record of what was planned and why.

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Complete
**Severity:** High — muted grey styles body-size text and measures below WCAG AA in most of the bundled catalogue.

## Objective

Give the theme system a **role** for small-but-readable text, and make that role
guaranteed rather than hoped for.

Today `--text-muted` does two incompatible jobs: it decorates separators and
disabled states, and it styles the table of contents, the share label, the post
metadata, the footer links and the navigation links. The second job needs 4.5:1
and does not get it. This phase adds a distinct caption role, derives it so that
it clears 4.5:1 against every surface it can land on, and stops the stylesheets
from using the decorative role for content.

## Findings

### VD-08 — Muted grey styles body-size text and fails AA (high)

Measured in Chromium on the running instance, with the foreground composited over
the surface it is actually painted on:

| Element | Dark (`berlin`) | Light (`base16-atelier-forest-light`) |
|---|---|---|
| TOC link / TOC title | **2.47:1** | 3.90:1 |
| Share label | **2.47:1** | 3.90:1 |
| Breadcrumb link | **2.91:1** | 4.35:1 |
| Footer heading / footer link | **2.91:1** | 4.35:1 |
| Navigation link | **2.91:1** | 4.35:1 |
| Post metadata (12.8px) | 3.25:1 | 4.35:1 |
| Heading anchor `#` | 3.03:1 | 5.30:1 |
| Prose inline code | 4.48:1 | **2.47:1** |
| Body paragraph / h2 / hero title | 6.89:1 | 5.30:1 |

WCAG AA requires 4.5:1 for text below 18.66px. Nine of the rows above are
content a reader has to read, and seven of them are below the floor in the
active dark theme.

The light-mode inline-code row is a different defect with the same cause: the
inline chip paints `var(--accent-hover)` on `var(--code-bg)`, and the active
light theme's `--accent-hover` is `rgb(218, 119, 0)` against `rgb(230, 226, 224)`.

### VD-09 — The theme gate and the stylesheets disagree about what muted means (high)

`app/themes/diagnostics.py` classifies the muted and dim tokens like this:

```python
(
    "text_muted",
    "surface_default",
    "text-muted on surface-default",
    3.0,
    Severity.ADVISORY,
    "muted/secondary text",
),
(
    "text_dim",
    "surface_default",
    "text-dim on surface-default",
    3.0,
    Severity.ADVISORY,
    "dim/decorative text",
),
```

Three things are wrong with that model:

1. The floor is **3.0:1**, which is the WCAG threshold for *non-text* content
   and for large text. Neither applies to a 12.8px label.
2. The pair is checked against `surface_default` only. `text_muted` also paints
   the footer and the navigation, which sit on `bg_page`.
3. The description calls the token "decorative", and the stylesheets use it for
   content. The gate and the stylesheets model the same token differently, and
   neither checks the other's model.

The result is a gate that cannot fail on this defect. The site renders muted
text at 2.47:1 and the report says every theme complies.

### VD-10 — Most of the catalogue fails the floor the stylesheets need (high)

`--text-muted` against its own `surface_default`, across all 50 bundled themes:

| Band | Count |
|---|---|
| Dark themes below 4.5:1 | **26 of 43** |
| Dark themes below 3.0:1 | **14 of 43** |
| Light themes below 4.5:1 | **6 of 7** |

Worst cases: `vik` 1.92, `Nord` 1.96, `Cyber Red` 2.13, `Oxocarbon` 2.18,
`Ferra Light` 2.27.

The active light theme's `--accent` is **2.76:1** on its own surface, which is
the colour of the search button and the focus ring.

### The eight themes cannot tell a code block from a card

Phase 01's VD-07 records that `--code-bg` and `--bg-surface` are the same
colour, or within seven units of channel distance, in these themes:

| Theme | Scheme | Max channel delta |
|---|---|---|
| Flexor Dark | dark | 0 |
| Noctis Lilac | light | 0 |
| Tokyo Night Storm | dark | 0 |
| VESPER | dark | 3 |
| Dark Green | dark | 4 |
| Rose Pine Dawn | light | 7 |
| bam | dark | 7 |
| vanimo | dark | 7 |

Phase 01 changes the code block's surface to `--code-bg`. In these eight themes
that change has no visible effect, so the repair belongs here, in the phase that
owns the theme catalogue.

### VD-11 — The accent styles tag-chip text and fails AA (high)

`.tag` in `app/static/css/public.css` paints the chip text with the accent:

```css
.tag {
    padding: 4px 12px;
    background: var(--accent-dim);
    color: var(--accent);
    font-size: 13px;
    font-family: var(--font-mono);
}
```

`--accent-dim` is the accent at ten per cent over the surface, so the chip is a
tinted surface and the text on it is 13px content. Measured on the index in
Chromium, with the chip composited over the card:

| Scheme | Accent | Chip | Ratio |
|---|---|---|---|
| dark (`berlin`) | `rgb(50, 128, 166)` | `rgb(21, 30, 36)` | **3.84:1** |
| light (`base16-atelier-forest-light`) | `rgb(195, 132, 24)` | `rgb(236, 228, 217)` | **2.52:1** |

Both are below the 4.5:1 that 13px content needs. The same token is used for
the tag chip on the index card, on the post page, in the sidebar tag cloud and
in the related-post list.

Across the catalogue the accent falls below 4.5:1 against its own surface in
**15 of 43 dark themes** and **5 of 7 light themes**, so this is the same
systemic problem as VD-08, in a second role.

## Fix specification

### 1. Two derived roles, each guaranteed to clear the floor

Add two fields to the theme model:

| File | Change |
|---|---|
| `app/themes/model.py` | `BlogTheme.text_caption: RGB` and `BlogTheme.accent_text: RGB` — two new fields. `CSS_VARS["text_caption"] = "--blog-text-caption"` and `CSS_VARS["accent_text"] = "--blog-accent-text"`. `ALIASES["text-caption"] = "--blog-text-caption"` and `ALIASES["accent-text"] = "--blog-accent-text"`. `EMERGENCY_DEFAULT` gets values that clear 4.5:1 against the emergency surfaces. |
| `app/themes/translate.py` | Derive both values in `translate_halloy_theme()`. |

#### 1a. The caption role

```python
def _derive_text_caption(
    muted: RGB, primary: RGB, surfaces: Sequence[RGB], is_dark: bool
) -> RGB:
    """Return a caption colour that clears 4.5:1 on every surface it lands on."""
```

1. If `muted` already clears 4.5:1 against every surface, return it unchanged.
2. Otherwise binary-search the smallest `w` for which `mix(muted, primary, w)`
   clears 4.5:1 against every surface. `mix(a, b, w)` is `a * (1 - w) + b * w`.
3. If `primary` does not clear the floor either — which happens when the
   theme's own primary text is below AA — mix toward the readable extreme
   instead: white for a dark theme, black for a light theme.

The surfaces are `bg_page`, `surface_default` and `surface_elevated`, because the
caption text lands on the page (footer, navigation), on a card, and on an
elevated panel (the table of contents inside the post tile).

Measured over the whole catalogue, step 2 resolves 47 of 50 themes. The median
required mix factor is **0.131**, so the caption stays visually close to the
muted colour it replaces. The three that need step 3 are `Cyber Red`,
`Rose Pine Dawn` and `Solarized Dark`, whose primary text is itself below AA;
`Rose Pine Dawn` reaches 4.5:1 at a mix factor of 0.098 toward black.

#### 1b. The accent-text role

```python
def _derive_accent_text(accent: RGB, surface: RGB, is_dark: bool) -> RGB:
    """Return an accent that clears 4.5:1 on the chip it tints."""
```

The chip is the accent at ten per cent over the surface, so moving the accent
moves the chip too. The derivation solves for the accent, not for the text:

1. Compute the chip as the accent at ten per cent over `surface_default`.
2. If the accent already clears 4.5:1 against that chip, return it unchanged.
3. Otherwise binary-search the smallest `w` for which `mix(accent, extreme, w)`
   clears 4.5:1 against the chip **that the mixed accent produces**. The chip
   is recomputed at every step.
4. The extreme is white for a dark theme and black for a light theme.

Measured over the whole catalogue, **all 50 themes resolve**. The median
required mix factor is 0.0 — most accents already clear the floor — and the
largest is 0.434. The active dark theme needs 0.091 and the active light theme
needs 0.307.

Both derivations use `mix()` and `contrast_ratio()` from `app/themes/colors.py`.
Neither may use `shift_lightness()`: `_hsl_to_rgb()` computes `q` identically in
both branches of its `lightness < 0.5` test, which is a known defect recorded in
`AGENTS.md`. That defect is not fixed by this phase and is not depended upon.

### 2. The stylesheets and the templates stop using the decorative role for content

The rule this phase establishes:

> `--text-muted` is for decoration — separators, disabled states, icon strokes.
> Any text a reader must read uses `--text-caption`.

`--text-muted` is **declared 3 times** — the emergency fallback blocks in
`app/static/css/base.css` (twice) and `app/static/css/critical.css` (once) —
and **used in 66 places**:

| Stylesheet | Uses |
|---|---|
| `admin.css` | 22 |
| `public.css` | 23 |
| `layout.css` | 9 |
| `base.css` | 7 |
| `forms.css` | 2 |
| `utilities.css` | 1 |
| `critical.css` | 1 |
| `prism-okaidia.css` | 1 |

Sixty-five of the sixty-six uses are a `color:` declaration; the one exception
is a `border-color:` in `admin.css`, which is decoration and stays.

`prism-okaidia.css` is deleted by Phase 01, so 65 uses remain when this phase
starts.

The `text-muted` utility class in `base.css` is one of those uses, and the
admin templates rely on it for **hint text** that a reader must read — "or click
to browse", "8+ chars with 3 of: lowercase, uppercase, digit, special". The
utility class takes the caption role with everything else.

Two templates also set the colour inline, and the rule covers them:

- `app/templates/admin/settings.html` sets `color: var(--text-muted)` in a
  `style` attribute, and uses `var(--text-muted, #888)` in an inline
  `<style>` block.
- `app/templates/login.html` sets `color: var(--text-muted)` inline.

Every one of those declarations is either moved to `--text-caption` or added to
a documented allowlist of decorative uses. The allowlist follows the pattern
already used by `tests/test_css_contracts.py`, which has an allowlist for
emitted tokens and a test that the allowlist is documented.

The second rule follows from VD-11:

> `--accent` is for fills, focus rings and borders.
> Accent-coloured **text** uses `--accent-text`.

The tag chip is the only accent-coloured text on the public site today, and it
is styled in `app/static/css/public.css`:

```css
.tag {
    background: var(--accent-dim);
    color: var(--accent-text);
    ...
}
```

`--accent-dim` stays as it is. The chip keeps its accent tint; only the text on
it moves to the role that is guaranteed to be readable on it.

The emergency fallback blocks — `app/static/css/base.css` (dark and light),
`app/static/css/critical.css`, and any other `:root` block that declares
`--text-muted` — must also declare `--text-caption` and `--accent-text`, so
that both roles resolve before the theme runtime has emitted them.

### 3. The gate gains two mandatory checks

In `app/themes/diagnostics.py`, add to `_CONTRAST_PAIRS`:

```python
("text_caption", "bg_page", "text-caption on bg-page", 4.5, Severity.MANDATORY, "caption text on page"),
("text_caption", "surface_default", "text-caption on surface-default", 4.5, Severity.MANDATORY, "caption text on cards"),
("text_caption", "surface_elevated", "text-caption on surface-elevated", 4.5, Severity.MANDATORY, "caption text on elevated panels"),
("accent_text", "surface_default", "accent-text on surface-default", 4.5, Severity.MANDATORY, "accent text on tinted chips"),
```

The accent check is the accent against the **surface**, not against the chip,
because the chip is the accent at ten per cent over the surface. A check
against the composited chip would be a different number, and the chip is a
composite of the accent itself, so the surface is the stable pair to gate on.

Because both roles are derived to clear the floor, these checks pass for every
theme by construction. That is the point: the check exists so that a future
change to the derivation, or to the surfaces a role can land on, fails the gate
instead of silently regressing.

The gate's current semantics must be preserved. `--strict` fails when a theme's
computed eligibility is **worse** than the class
`app/themes/ACCESSIBILITY_EXCEPTIONS.json` declares for it, so adding a check
that passes everywhere leaves the manifest untouched and the `theme-policy` CI
job green.

The advisory floor for `text_muted` and `text_dim` stays at 3.0:1. Those tokens
remain genuinely decorative in some places, and raising the advisory floor would
inflate the advisory count without changing any theme's eligibility. The caption
role is what guarantees content readability.

### 4. The eight themes get a distinguishable code surface

For each of the eight themes in VD-07, change the Halloy `buffer.background_text_input`
value — the source of `--code-bg` — so that the code surface differs from
`buffer.background` by at least **eight units** in the largest channel.

Each change is made in **both** copies of the theme: `themes/<name>.toml`, which
is the authoring source, and `app/themes/bundled/<name>.toml`, which is the
runtime copy. The two must stay byte-identical, and
`tests/themes/test_accessibility.py` already checks the bundled catalogue.

The change is a small shift of the code surface away from the card surface, in
the direction the theme's palette already implies. It must not alter the
theme's page background, its primary text, or any token that is currently
covered by the exception manifest.

### 5. The accent keeps its other jobs

`--accent` is not changed. It remains the fill of the search button, the focus
ring and the accent borders.

The search button paints `--text-on-accent` on the accent fill, which the gate
already checks (`text_on_accent` on `accent`, mandatory at 4.5:1) and which
every bundled theme passes. The focus ring and the accent borders are
non-text uses, where the 3.0:1 threshold applies and which the gate already
checks as mandatory.

Only the accent's use as a **text colour** moves, and only that use moves to
the new role.

## Tests

1. **The caption clears the floor (unit)** — for every bundled theme, assert
   `contrast_ratio(text_caption, bg_page)`, `contrast_ratio(text_caption,
   surface_default)` and `contrast_ratio(text_caption, surface_elevated)` are all
   at least 4.5.
2. **The caption is derived, not authored (unit)** — assert that changing a
   theme's `text_muted` to a failing value changes the derived caption, and that
   a theme whose `text_muted` already passes is unchanged.
3. **The fallback path is exercised (unit)** — assert the derivation clears the
   floor for `Cyber Red`, `Rose Pine Dawn` and `Solarized Dark`, whose primary
   text is below AA.
4. **The accent text clears the floor (unit)** — for every bundled theme, assert
   that the derived `accent_text` clears 4.5:1 against the chip it produces,
   where the chip is the accent at ten per cent over `surface_default`.
5. **The gate check exists (unit)** — assert the caption and accent-text pairs
   are present in `_CONTRAST_PAIRS` with `Severity.MANDATORY` and a 4.5 floor,
   and that `scripts/theme_accessibility_report.py --strict` still exits 0.
6. **The manifest is unchanged (unit)** — assert
   `app/themes/ACCESSIBILITY_EXCEPTIONS.json` is unchanged by this phase. The
   derived tokens pass every new check, so no theme's eligibility may change.
7. **The stylesheets obey the role rule (unit)** — assert that every
   `color: var(--text-muted)` in `app/static/css/` is either absent or names a
   selector on the documented decorative allowlist, and that the allowlist is
   documented in the same file, following the pattern in
   `tests/test_css_contracts.py`.
8. **The templates obey the role rule (unit)** — assert that no template in
   `app/templates/` paints text with `var(--text-muted)` outside the documented
   allowlist, covering both `style` attributes and inline `<style>` blocks.
9. **The accent-text role (unit)** — assert that no stylesheet paints
   accent-coloured **text** with `var(--accent)`; the only permitted use is the
   tag chip, which must use `var(--accent-text)`.
10. **The fallbacks declare the tokens (unit)** — assert every `:root` fallback
    block that declares `--text-muted` also declares `--text-caption` and
    `--accent-text`.
11. **Measured contrast (browser, `tests/e2e/`)** — on a post page in both
    schemes, measure the computed foreground and the composited background of the
    TOC entry, the share label, the post metadata and the footer link, and assert
    every measured ratio is at least 4.5.
12. **The caption resolves (browser)** — assert the computed colour of a caption
    element differs between the dark and the light scheme, proving the token
    resolves rather than falling back to a literal.
13. **Inline code in the light scheme (browser)** — assert the measured ratio of
    inline code against its chip background is at least 4.5 in both schemes.
14. **The tag chip (browser)** — assert the measured ratio of the tag chip's text
    against its composited chip background is at least 4.5 on the index, in both
    schemes.
15. **The eight themes (unit)** — assert that for every bundled theme, the
    maximum channel distance between `code_bg` and `surface_default` is at least
    eight.
16. **The theme copies agree (unit)** — assert `themes/<name>.toml` and
    `app/themes/bundled/<name>.toml` are identical for every bundled theme.

## Expected files

- `app/themes/model.py` (the `text_caption` and `accent_text` fields, `CSS_VARS`, `ALIASES`, `EMERGENCY_DEFAULT`)
- `app/themes/translate.py` (`_derive_text_caption`, `_derive_accent_text`)
- `app/themes/diagnostics.py` (the four mandatory pairs)
- `app/static/css/base.css`, `app/static/css/public.css`, `app/static/css/layout.css`,
  `app/static/css/admin.css`, `app/static/css/forms.css`, `app/static/css/utilities.css`,
  `app/static/css/critical.css` (the role rule and the fallbacks)
- `app/templates/admin/settings.html`, `app/templates/login.html` (the inline declarations)
- `themes/{Flexor Dark,Noctis Lilac,Tokyo Night Storm,VESPER,Dark Green,Rose Pine Dawn,bam,vanimo}.toml`
- `app/themes/bundled/{Flexor Dark,Noctis Lilac,Tokyo Night Storm,VESPER,Dark Green,Rose Pine Dawn,bam,vanimo}.toml`
- `tests/themes/test_accessibility.py` (the caption check and the code-surface distance)
- `tests/test_css_contracts.py` (the role rule and the allowlist)
- `tests/e2e/test_text_contrast.py` (new)

## Acceptance criteria

- [ ] A caption role exists, is emitted for every bundled theme and for the emergency default, and clears 4.5:1 against `bg_page`, `surface_default` and `surface_elevated` in every one of them.
- [ ] No bundled theme needed a hand-authored caption value.
- [ ] Every text-bearing use of `--text-muted` has been moved to `--text-caption` or is on the documented decorative allowlist.
- [ ] The table of contents, the share label, the post metadata, the footer and the navigation all measure at least 4.5:1 in both schemes.
- [ ] Inline code measures at least 4.5:1 in the light scheme.
- [ ] The tag chip's text measures at least 4.5:1 against its composited chip background, in both schemes, in every bundled theme.
- [ ] The theme gate has mandatory 4.5:1 checks for the caption role and the accent-text role, and `scripts/theme_accessibility_report.py --strict` still exits 0.
- [ ] `app/themes/ACCESSIBILITY_EXCEPTIONS.json` is unchanged.
- [ ] Every bundled theme distinguishes its code surface from its card surface by at least eight units in the largest channel.
- [ ] The authoring and runtime copies of every theme remain byte-identical.
- [ ] The documented token counts are updated: `BlogTheme` has 52 fields (43 `RGB` + 9 `RGBA`), `CSS_VARS` has 52 entries and `ALIASES` has 40.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

Requires Phase 01, which changes the code block's surface to `--code-bg` and
therefore depends on the eight themes having a distinguishable code surface.

Must land before Phases 03 to 06. Every later phase introduces or re-styles text
at content size, and they must all use the caption role this phase establishes.

Phase 05 changes the tag chip's container — it caps the row — so the tag chip's
measurement must be taken after Phase 05 as well.

## Completion

**Status:** Complete — shipped 2026-10-27.

### What changed

**Two derived roles, no authored values.** `app/themes/model.py` gained two fields,
`text_caption` and `accent_text`, taking `BlogTheme` to **52 fields — 43 `RGB` and
9 `RGBA`** — with `CSS_VARS` at 52 entries and `ALIASES` at 40. Both are derived in
`app/themes/translate.py` by `_derive_text_caption()` and `_derive_accent_text()`.
No theme file declares either one, so a theme cannot opt out of the floor and a
theme cannot hand-author a caption the gate would then have to trust.

The caption is the muted colour moved toward the primary colour until it clears
4.5:1 against `bg_page`, `surface_default` and `surface_elevated`; where the primary
itself is below the floor it mixes toward white in a dark theme and black in a
light one instead. The accent text is the accent moved until it clears 4.5:1
against the chip it tints — the accent at ten per cent over the surface — with the
chip recomputed at every step and held against all three surfaces.

**The derivation was measured, not assumed.** Over the whole catalogue: 18 themes
need no change at all, 29 resolve by mixing toward the primary with a median factor
of **0.131**, and exactly **three** — Cyber Red, Rose Pine Dawn and Solarized Dark
— need the extreme fallback, Rose Pine Dawn at a factor of 0.098 toward black. That
is the plan's own reference measurement, reproduced exactly.

**The role rule was applied.** Sixty `color: var(--text-muted)` uses across
`app/static/css/` became `color: var(--text-caption)`: the table of contents, the
share label, the post metadata, the footer, the navigation, the breadcrumb, the
sidebar titles, the form labels and help text, the inline declarations in
`login.html`, `account.html` and `admin/settings.html`, and the `text-muted`
utility class. Seven uses remain on the decorative role and are documented as an
allowlist: the two admin icon-button rules, the disabled-tool hover, the preset
card's border, the theme toggle, the back-to-top button, the mobile menu toggle
and the search clear button. All of them are icon strokes or borders.

**The accent lost its job as a text colour.** Every `color: var(--accent)` and
`color: var(--accent-hover)` became `color: var(--accent-text)`, so no stylesheet
paints accent-coloured text with the accent any more. The accent keeps its 43
non-text uses: the search button's fill, the focus ring, the accent borders. The
inline-code chip is the one exception and it moved to `--text-caption` rather than
`--accent-text`, because the chip is the code surface and the accent text is
derived against the tinted chip, not against the code surface.

**The gate now holds the floor.** `app/themes/diagnostics.py` gained four mandatory
4.5:1 pairs: `text_caption` against `bg_page`, `surface_default` and
`surface_elevated`, and `accent_text` against `surface_default`. Every bundled
theme passes all four, so `scripts/theme_accessibility_report.py --strict` still
exits 0 and `app/themes/ACCESSIBILITY_EXCEPTIONS.json` is unchanged — 45 entries,
schema version 2. The manifest was not edited, because the new checks pass
everywhere.

**Eight themes were repaired.** Flexor Dark, Noctis Lilac, Tokyo Night Storm,
VESPER, Dark Green, Rose Pine Dawn, bam and vanimo had a code surface
indistinguishable from the card surface. Each was given a code surface at least
eight units away from its card in the largest channel, in both the authoring copy
and the runtime copy, which remain byte-identical.

### Deviations from the plan

Three, all recorded here.

**The accent text is held against three surfaces, not one.** The plan derived it
against the chip over `surface_default` alone. Measured in Chromium, the tag chip
on the post page sits on the page background rather than on a card, and the page
carries a gradient, so the chip was 3.98:1 against the text where the
single-surface model predicted 4.71:1. The derivation now holds against the chip
on all three surfaces; the dark tag chip measures 5.79:1 and the light one 5.24:1.

**The inline code chip took the caption role, not the accent-text role.** The plan
did not say which. The accent text is derived against the tinted chip and the
inline chip is the code surface, so moving the inline code to the accent text
would have *lowered* the dark scheme's contrast from 4.48:1 to 3.69:1. The
caption role gives 6.52:1 in the dark scheme and 4.72:1 in the light one.

**The code surface moved the code text below the floor in three themes.** Those
three — Cyber Red, Rose Pine Dawn and Solarized Dark — already declare
`code-text on code-bg` as a mandatory defect in the exception manifest, so the
shortfall was known and recorded before this series. Phase 01 made it visible by
pointing the code block at the code surface. The manifest was not edited; a test
now asserts that any theme whose code text falls below the floor declares it, and
that no theme declares a failure it no longer has.

### Verification

- `tests/themes/test_text_roles.py` — 19 tests: the caption clears the floor
  against all three surfaces in every bundled theme, the accent text clears the
  floor on the chip in every bundled theme, neither derived role is ever worse
  than the token it replaces, a theme that already cleared the floor keeps its
  muted colour, no theme file declares either role, the token counts are 52/52/40,
  every bundled theme distinguishes its code surface by at least eight units, the
  authoring and runtime theme copies are byte-identical, the gate carries the
  mandatory pairs, and the exception manifest is unchanged.
- `tests/test_css_contracts.py` — the role-rule contracts: no muted text outside the
  documented allowlist, every allowlisted use still present, the accent paints no
  text, the tag chip uses the accent-text role, the accent keeps its fills and
  borders, and every emergency fallback block declares both roles with values
  that clear the floor.
- `tests/e2e/test_text_roles.py` — 8 browser tests measuring the painted result in
  both schemes: the caption role on the post metadata, the footer, the navigation
  and the share label; the inline code; and the derived tokens being emitted.
- Chromium on the running instance, both schemes, with the foreground composited
  over every layer it is actually painted on — the translucent tile, the page
  gradient and the theme's page colour: the post metadata, the footer link, the
  navigation link, the share label and the breadcrumb measure **4.61:1** to
  **6.07:1** in the dark theme and **4.55:1** to **5.06:1** in the light one; the
  inline code measures **6.52:1** and **4.72:1**; the tag chip measures
  **5.79:1** and **5.24:1**. Every one of them clears 4.5:1.
