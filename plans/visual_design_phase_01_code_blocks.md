# Visual Design Phase 01 — Code Blocks

> **Plan status: COMPLETE — shipped 2026-10-27.** The outcome is documented in [`architecture/frontend/static-assets.md`](../architecture/frontend/static-assets.md) and [`architecture/core/themes.md`](../architecture/core/themes.md). This file is the historical record of what was planned and why.

**Roadmap:** [visual_design_roadmap.md](visual_design_roadmap.md)
**Date:** 2026-10-27
**Status:** Complete
**Severity:** Critical — no code block on the site has ever been syntax-highlighted, and none has ever had a copy button.

## Objective

Make fenced code blocks render the way the source tree says they should: highlighted,
copyable, and coloured by the active theme rather than by a vendored third-party
palette.

This phase also retires the `syntax_theme` setting. It is the operator decision of
2026-10-27 recorded in the roadmap: Prism's token classes are remapped onto the
active theme's own palette, and the six vendored Prism stylesheets and the setting
that selects between them are deleted.

## Findings

### VD-01 — The sanitiser strips the only attribute the highlighter depends on (critical)

`app/markdown_config.py` permits the `class` attribute on `span` and `div` only:

```python
MARKDOWN_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "span": {"class"},
    "div": {"class"},
}
```

Python-Markdown's `fenced_code` extension writes the fence's info string into a
`class` attribute on the `<code>` element. Rendered, before sanitisation:

```html
<pre><code class="language-python">x = 1
</code></pre>
```

`app/markdown_renderer.py` runs `nh3.clean()` last, so the class is stripped and
the emitted markup is `<pre><code>`.

`app/static/js/main.js` `loadPrismIfNeeded()` gates the entire highlighter on
that class:

```javascript
const codeBlocks = document.querySelectorAll('pre[class*="language-"]');
if (codeBlocks.length === 0) return;
```

The gate can never open. Measured on `/post/sample-post-12` in Chromium:
`window.Prism` is `undefined`, the document contains **zero** `.token` elements,
and both `<pre>` and `<code>` carry an empty `class` attribute.

### VD-02 — The grammar bundle is not valid JavaScript and never executes (critical)

`app/static/js/prism-languages.js` is a hand-assembled bundle of twenty Prism
grammars. It has at least two independent defects and **does not parse**:

```
$ node --check app/static/js/prism-languages.js
app/static/js/prism-languages.js:16
Prism.languages.markdown=Prism.languages.extend("markup",{},{...punctuation:/^---$/};
                                                                               ^
SyntaxError: missing ) after argument list
```

The `Prism.languages.extend(...)` call is closed with `;` instead of `);`. Repairing
that parenthesis exposes a second fault in the `yaml` grammar on line 23:

```
SyntaxError: Invalid regular expression: /(^|[\s,]|^---)(?:[\w\-\cK-ÖÜ-öü-ÿ].../m: Nothing to repeat
```

The character class `[\w\-\cK-ÖÜ-öü-ÿ]` contains an invalid `\c` escape and a
malformed range. Confirmed in the browser: loading the bundle raises
`pageerror: missing ) after argument list`, and `Prism.languages` afterwards
contains only `plain`, `plaintext`, `text`, `txt`, `extend`, `insertBefore` and
`DFS` — none of the twenty usable grammars.

`app/static/js/prism.min.js` is the Prism **core**, and a core carries no
grammars. The two files together are the whole highlighter, and the second one
does not run.

Nothing in the build catches this. `npm run build` does not parse these files
(Vite's `manualChunks` mentions them, but they are not in the module graph), and
the failure is a runtime `pageerror` on a page no test loads.

### VD-03 — The copy button module selects on the same stripped class (high)

`app/static/js/public/code-copy.js` `initCodeCopy()` opens with:

```javascript
document.querySelectorAll('pre[class*="language-"]').forEach((pre) => {
```

and reads the language with `pre.className.match(/language-(\S+)/)`. The selector
matches nothing, so the module is complete, correct, and unreachable. It reads as
a working feature in the source tree.

### VD-04 — The copy button is styled by one of the six vendored palettes (high)

`grep -c 'copy-code-btn' app/static/css/prism*.css`:

| Stylesheet | Occurrences |
|---|---|
| `prism-okaidia.css` | 4 |
| `prism.css`, `prism-coy.css`, `prism-dark.css`, `prism-funky.css`, `prism-tomorrow.css` | 0 |

Code-block chrome — a button that is part of the application, not of a third-party
palette — is owned by a vendored stylesheet. With the active setting at `prism`,
that stylesheet is `prism.css`, which does not style the button at all. Even with
VD-01 and VD-03 repaired, the button would appear unstyled.

### VD-05 — The inline-code chip leaks onto every line inside a `<pre>` (high)

`app/static/css/base.css` contains both of these rules:

```css
.prose pre code {          /* specificity 0,1,2 */
    padding: 0;
    background: none;
    ...
}

[data-color-scheme="light"] .prose code {   /* specificity 0,2,1 */
    background: var(--code-bg);
}
```

The scheme-scoped rule wins, so in the light scheme every line of every code
block inherits the inline chip's background. Measured in Chromium:

| Scheme | `pre` background | `code` background |
|---|---|---|
| dark | `rgb(18, 18, 20)` | `rgba(0, 0, 0, 0)` |
| light | `rgb(241, 239, 238)` | `rgb(230, 226, 224)` |

The light-mode result is a ragged stripe of grey chips behind each line, which is
visible in the review screenshots.

### VD-06 — The code block has no surface of its own (high)

`.prose pre` paints `var(--bg-surface)`. In the active light theme
`--bg-surface` is `#F1EFEE`, which is **the page background exactly**, so the block
is held together by a one-pixel border and nothing else. In the active dark theme
the block is `rgb(18, 18, 20)` and the post tile composites to `rgb(18, 19, 21)` —
a difference of one unit in the blue channel.

A code block that looks the same as the paragraph around it is not a code block.
It is a paragraph in a font.

### VD-07 — Eight bundled themes cannot distinguish the code surface from the card surface (medium)

`--code-bg` is derived from the Halloy `buffer.background_text_input` value and
`--bg-surface` from `buffer.background`. In **8 of the 50 bundled themes** the two
are the same colour or within seven units of channel distance:

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

No theme is repaired by this phase except where the gate in Phase 02 demands it.
This finding is the reason Phase 02 adds a gate check for the code surface; the
theme repair itself belongs to Phase 02, which owns the theme catalogue.

## Fix specification

### 1. Re-attach the fence language after sanitisation

The sanitiser stays exactly as it is. `MARKDOWN_ALLOWED_ATTRIBUTES` must not gain
a `code` entry — the allowlist is the boundary that keeps authored HTML inert, and
the renderer is the layer that owns the markup.

`app/markdown_renderer.py` becomes:

```python
html = markdown.markdown(text, extensions=[*extensions, StrikethroughExtension()])
languages = extract_fence_languages(html)
cleaned = nh3.clean(
    wrap_code_lines(html),
    tags=MARKDOWN_ALLOWED_TAGS,
    attributes=MARKDOWN_ALLOWED_ATTRIBUTES,
)
return apply_fence_languages(cleaned, languages)
```

- `extract_fence_languages(html)` returns the ordered list of fence languages, one
  entry per `<pre>` block, with `None` for a block that has no language. It reads
  the `class="language-..."` on the `<code>` element of the **pre-sanitisation**
  markup.
- `apply_fence_languages(cleaned, languages)` walks the `<pre>` blocks of the
  sanitised markup in order and writes `class="language-<slug>"` onto the matching
  `<pre>` and `<code>` pair.

Two invariants, both asserted by tests:

1. **The block count must match.** If the sanitised markup contains a different
   number of `<pre>` blocks than the pre-sanitisation markup, the function returns
   the markup unchanged. The feature fails closed — an unhighlighted block is
   correct; a block labelled with the wrong language is not.
2. **The slug must be validated.** Only `^[a-z0-9_+-]{1,32}$` is accepted. A
   value that does not match is dropped, not escaped.

The class is written to **both** the `<pre>` and the `<code>`. The loader and the
copy module both select on `pre[class*="language-"]`, and Prism's own default
selector is `code[class*="language-"]`.

Python-Markdown only emits a language for a lowercase fence tag, and it treats a
malformed info string as prose rather than a fence. Measured:

| Source | Rendered |
|---|---|
| ` ```python ` | `<pre><code class="language-python">` |
| ` ```js ` | `<pre><code class="language-js">` |
| ` ```PYTHON ` | `<pre><code>` — the tag is not recognised |
| ` ```python"onmouseover="alert(1) ` | a `<p>` with the text escaped |

The sanitiser therefore never has to defend against a hostile fence tag, but the
slug validation is still required as defence in depth.

### 2. Replace the hand-assembled grammar bundle with a built one

`app/static/js/prism-languages.js` is deleted. The grammars become a Vite entry
point built from the official Prism distribution:

- Add `prismjs` to `devDependencies` in `package.json`.
- Add `app/static/js/prism.js` as a second Rollup input in `vite.config.js`,
  importing the Prism core and the component set the site needs:

  `markup`, `html`, `css`, `clike`, `javascript`, `js`, `typescript`, `ts`,
  `python`, `py`, `go`, `rust`, `sql`, `yaml`, `json`, `toml`, `markdown`,
  `docker`, `c`, `cpp`, `csharp`, `swift`.

  Prism's component files pull in their own dependencies, so `markup`, `clike`
  and `javascript` arrive with the components that need them. The set above
  covers the twenty grammars the current hand-assembled bundle declares, plus
  `css`, and it keeps the aliases the current bundle uses (`py`, `ts`, `js`,
  `markup`) so a fence tagged with either spelling resolves.

  The bundle must not be hand-written. A hand-assembled bundle is what
  produced VD-02, and nothing in the build caught it.
- `npm run build` emits the bundle into `app/static/dist/`, and `vite_asset()`
  resolves it.

The point of the change is not the bundle but the **build**: a syntax error in a
grammar is now a build failure, caught by the `frontend-build` CI job, instead of
a runtime `pageerror` on a page no test loads.

If the dependency cannot be added, the fallback is to repair the two faults in the
existing file by hand and add a parse check to the build. That fallback restores
the feature but leaves it hand-assembled, and it must be recorded in the phase's
`## Completion` section.

### 3. Load the highlighter once, and only when it is needed

`app/static/js/main.js` `loadPrismIfNeeded()` keeps its conditional gate — a page
without a code block must not fetch the highlighter — but it changes what it
injects:

- The **stylesheet** is no longer injected. There is one stylesheet, linked from
  `base.html` like every other stylesheet, and it is not scheme-dependent.
- The **script** is the Vite-built bundle, and the languages are inside it, so
  there is no second script and no ordering problem.

The current implementation injects the stylesheet twice — once from `base.html`
with the `media="print"` swap and once from JavaScript — and injects the grammar
bundle in the highlighter script's `onload` handler, which is **after** Prism has
already scheduled its own `highlightAll()` on the next animation frame. Loading
the grammars inside the same bundle removes the race.

### 4. One stylesheet owns the code block

`app/static/css/base.css` owns `.prose`, so it owns the code block's layout and
its surface:

```css
.prose pre {
    margin: 1.5em 0;
    padding: 20px 24px;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow-x: auto;
    font-size: 0.88rem;
    line-height: 1.6;
}
```

The surface moves from `--bg-surface` to `--code-bg`. `--code-bg` is the theme's
own code surface and is already emitted for every bundled theme.

`app/static/css/prism.css` is **rewritten**. The six vendored palettes
(`prism-coy.css`, `prism-dark.css`, `prism-funky.css`, `prism-okaidia.css`,
`prism-tomorrow.css` and the current `prism.css`) are deleted, and one
token-driven stylesheet replaces them. It defines only `.token.*` colours, and it
uses theme tokens exclusively:

| Prism token class | Theme token |
|---|---|
| `comment`, `prolog`, `doctype`, `cdata` | `var(--text-dim)` |
| `punctuation`, `operator` | `var(--text-muted)` |
| `keyword`, `atrule`, `important`, `namespace`, `property`, `selector`, `attr-name`, `tag` | `var(--accent)` |
| `function`, `class-name`, `builtin`, `attr-value`, `string`, `char`, `regex`, `url`, `symbol`, `variable`, `constant` | `var(--green)` |
| `number`, `boolean`, `entity`, `inserted` | `var(--yellow)` |
| `deleted` | `var(--red)` |

The state colours are reused for syntax because the theme exposes exactly one
chromatic set. This is a deliberate, recorded decision: the mapping lives in one
file, so a future theme schema with dedicated code tokens replaces it without
touching any other stylesheet.

`.copy-code-btn` moves out of `prism-okaidia.css` — which is deleted — into
`base.css`, next to the code block it belongs to. It uses theme tokens only.

The `.prose pre code` rule stays at specificity 0,1,2, and the light-scheme
override is narrowed so it cannot reach into a block:

```css
[data-color-scheme="light"] .prose :not(pre) > code {
    background: var(--code-bg);
}
```

### 5. Retire `syntax_theme`

| File | Change |
|---|---|
| `app/models.py` | Remove the `syntax_theme` column from `SiteSettings`. |
| `app/templates/base.html` | Remove `data-syntax-theme` and the `{{ syntax_theme }}.css` link; link `prism.css`. |
| `app/templates/admin/base.html` | Same. |
| `app/templates/admin/login_base.html` | Same. |
| `app/context_processors.py` | Remove the `syntax_theme` context key from all three branches. |
| `app/themes/service.py` | Remove `syntax_theme` from the context dictionary. |
| `app/routes/admin/settings.py` | Remove the `syntax_themes` list, `valid_syntax_themes`, the form read and the assignment. |
| `app/templates/admin/settings.html` | Remove the "Syntax Highlighting Theme" select. |
| `app/static/css/prism-{coy,dark,funky,okaidia,tomorrow}.css` | Delete. |
| `app/static/js/prism-languages.js` | Delete. |

The `data-syntax-theme` attribute is also removed from the `<html>` element, so no
JavaScript or stylesheet may key off it afterwards.

### 6. Migration

One migration drops the column:

- `down_revision` is the current head, `add_appearance_settings_to_sitesettings`.
- The migration is named for what it does, follows the naming convention of the
  existing revisions in `migrations/versions/`, and has a working downgrade that
  restores the column with its default.
- `tests/test_migration_chain.py` must cover the new revision.

`SiteSettings.syntax_theme` had a default of `"prism"` and was never `NULL`, so
the downgrade restores `"prism"` for every row.

## Tests

1. **Language survives sanitisation (unit)** — render a document containing a
   ```` ```python ```` fence and assert the output contains
   `class="language-python"` on both the `<pre>` and the `<code>`.
2. **The sanitiser is unchanged (unit)** — assert
   `MARKDOWN_ALLOWED_ATTRIBUTES` still contains no `code` entry. This test exists
   to stop a future agent from "fixing" VD-01 by loosening the allowlist.
3. **The slug is validated (unit)** — a fence whose language contains characters
   outside `^[a-z0-9_+-]{1,32}$` produces no class. Assert no `language-` class
   survives.
4. **Count mismatch fails closed (unit)** — feed `apply_fence_languages()` markup
   whose `<pre>` count differs from the language list and assert the markup is
   returned unchanged.
5. **The grammar bundle parses (build)** — `npm run build` must fail if
   `app/static/js/prism.js` or any imported component does not parse. This is the
   regression test for VD-02.
6. **Prism loads and tokens appear (browser, `tests/e2e/`)** — on a page with a
   fenced block, assert `window.Prism` is defined, that
   `Prism.languages.python` is defined, and that the block contains at least one
   `.token.keyword` element.
7. **The copy button appears and copies (browser, `tests/e2e/`)** — assert a
   `.copy-code-btn` exists inside the block, that it has a non-zero rendered
   size, and that clicking it changes its label to "Copied!". Clipboard
   permission is not required to assert the label transition.
8. **The chip does not leak (browser)** — in the light scheme, assert the
   computed `background-color` of `code` inside `pre` is transparent, and that the
   computed `background-color` of `pre` is not equal to the page background.
9. **The block is separated from the tile (browser)** — assert the code block's
   composited background differs from the post tile's composited background by
   more than two units in every channel, in both schemes.
10. **The copy button is styled (unit)** — assert `base.css` contains a
    `.copy-code-btn` rule and that no `prism-*.css` file does.
11. **The vendored palettes are gone (unit)** — assert no file named
    `prism-*.css` other than `prism.css` exists in `app/static/css/`, and that
    `prism.css` contains no hex colour literal.
12. **The setting is gone (unit)** — assert the rendered public page contains no
    `data-syntax-theme` attribute and no reference to a `syntax_theme` stylesheet,
    and that the admin settings page renders no "Syntax Highlighting Theme"
    select.
13. **The migration round-trips (unit)** — assert the column exists before the
    migration and does not after it, and that the downgrade restores it.

## Expected files

- `app/markdown_renderer.py` (language extraction and re-attachment)
- `app/static/css/base.css` (code block surface, light-scheme override narrowing, copy button)
- `app/static/css/prism.css` (rewritten as the token palette)
- `app/static/css/prism-{coy,dark,funky,okaidia,tomorrow}.css` (deleted)
- `app/static/js/main.js` (load the highlighter once)
- `app/static/js/prism.js` (new Vite entry)
- `app/static/js/prism-languages.js` (deleted)
- `app/static/js/public/code-copy.js` (unchanged behaviour, now reachable)
- `package.json`, `vite.config.js` (the `prismjs` dependency and the second entry)
- `app/models.py`, `app/context_processors.py`, `app/themes/service.py`
- `app/routes/admin/settings.py`, `app/templates/admin/settings.html`
- `app/templates/base.html`, `app/templates/admin/base.html`, `app/templates/admin/login_base.html`
- `migrations/versions/<new>_drop_syntax_theme_column.py` (new)
- `tests/test_markdown_code_languages.py` (new)
- `tests/test_code_block_contracts.py` (new)
- `tests/e2e/test_code_blocks.py` (new)
- `tests/test_migration_chain.py` (new revision coverage)

## Acceptance criteria

- [ ] A fenced block renders with `class="language-<tag>"` on both the `<pre>` and the `<code>`.
- [ ] `MARKDOWN_ALLOWED_ATTRIBUTES` is unchanged and still permits `class` on `span` and `div` only.
- [ ] A code block on a public page has at least one `.token` element, and `Prism.languages.python` is defined.
- [ ] A code block has a visible Copy button that reports success when pressed.
- [ ] The Copy button is styled by `base.css`, and by no vendored palette.
- [ ] In the light scheme, the computed background of `code` inside `pre` is transparent.
- [ ] In both schemes, the code block's background is measurably distinct from the post tile's background and from the page background.
- [ ] The page contains no `data-syntax-theme` attribute and no reference to a `syntax_theme` stylesheet.
- [ ] The admin settings page no longer offers a syntax theme selector.
- [ ] `SiteSettings.syntax_theme` no longer exists, the migration round-trips, and `tests/test_migration_chain.py` covers it.
- [ ] The six vendored Prism stylesheets and the hand-assembled grammar bundle are deleted.
- [ ] `npm run build` succeeds, and the highlighter is fetched only on a page that has a code block.
- [ ] `pytest tests/` passes; `ruff` and `mypy` are clean.

## Dependencies

First in the series. Independent of every other phase, but Phase 03 edits the same
`.prose` block in `app/static/css/base.css` and therefore runs after it.

## Completion

**Status:** Complete — shipped 2026-10-27.

### What changed

**The fence language survives sanitisation.** `app/markdown_renderer.py` gained
`extract_fence_languages()` and `apply_fence_languages()`. The renderer reads the
language out of the unsanitised markup and writes it back after `nh3.clean()`, as
`class="language-<slug>"` on **both** the `<pre>` and its `<code>`. The sanitiser
allowlist did not move: `MARKDOWN_ALLOWED_ATTRIBUTES` still permits `class` on
`span` and `div` only, and `tests/test_markdown_code_languages.py` asserts it.

The slug is validated against `^[a-z0-9_+-]{1,32}$`; a value that does not match is
dropped, not escaped. The function fails closed: if the number of code blocks in
the sanitised markup does not match the number of languages, the markup is returned
unchanged, because an unhighlighted block is correct and a block labelled with the
wrong language is not.

**The grammar bundle is built, not hand-assembled.** `app/static/js/prism-languages.js`
and the vendored `app/static/js/prism.min.js` are deleted. Prism is now the
`prismjs` npm devDependency and a second Vite entry, `app/static/js/prism.js`, which
imports the core plus eighteen grammars and calls `highlightCodeBlocks(Prism)`. A
syntax error in a grammar is now a build failure rather than a browser console
error. The built chunk is 64 kB, about 20 kB gzipped, and is fetched only on a page
that has a code block.

`app/static/js/main.js` `loadPrismIfNeeded()` injects one module script pointing at
`data-prism-js-url`. It no longer injects a stylesheet — `base.html` already links
`css/prism.css` — and it no longer injects a separate grammar script after Prism
had already scheduled its highlight pass.

**The line numbering survives the highlighter.** Prism replaces the code element's
content wholesale, which would have destroyed the renderer's per-line spans and
with them the CSS counter that numbers them. `app/static/js/shared/prism-blocks.js`
restores the renderer's structure: it reads the existing line spans, splits the
highlighted markup into one fragment per line, and rebalances the tags so a token
that spans lines keeps its colour on every line it covers. It does not name the
`code-line` class — the renderer remains the only producer of those spans, and
`tests/test_code_line_numbers.py` still asserts that no JavaScript takes part in
the numbering.

**One palette, mapped onto the theme.** The six vendored stylesheets
`prism-{coy,dark,funky,okaidia,tomorrow}.css` are deleted, and `prism.css` is
rewritten to contain only `.token.*` colour rules mapped onto theme tokens, with no
colour literal. `base.css` owns the code block's layout, its surface and the copy
button; `prism.css` owns the token colours and nothing else.

**The light-scheme chip no longer leaks.** The inline-code override was narrowed
from `[data-color-scheme="light"] .prose code` to
`[data-color-scheme="light"] .prose :not(pre) > code`, and the light-scheme
`.prose pre` rule was deleted, so the code block paints `--code-bg` in both
schemes.

**The setting is retired.** `SiteSettings.syntax_theme`, the `syntax_theme` context
key, the `syntax_theme` argument on the theme service, the admin selector and the
`data-syntax-theme` attribute are all gone. `migrations/versions/drop_syntax_theme_column.py`
drops the column and round-trips.

### Deviations from the plan

Two, both recorded here rather than left implicit.

**The highlighter had to restore the line structure.** The plan did not account for
Prism replacing the code element's content, which destroys the spans the CSS
counter numbers. Restoring them in the highlighter is what keeps the numbering
alive; the alternative — highlighting each line separately — loses multi-line
strings and block comments.

**`prism.min.js` was deleted as well.** The plan listed `prism-languages.js` for
deletion but not the vendored core. With Prism coming from npm, the vendored copy
had no remaining caller.

### Verification

- `tests/test_markdown_code_languages.py` — 28 tests: the language survives
  sanitisation, the allowlist is unchanged, the slug is validated, the count
  mismatch fails closed, and raw HTML cannot smuggle a class past the slug check.
- `tests/test_code_block_contracts.py` — 25 tests: the block paints `--code-bg`,
  the light override is narrowed, no vendored palette survives, `prism.css` has no
  colour literal and uses only theme tokens, the copy button is styled by
  `base.css` and by no vendored palette, the setting is gone from the model, the
  routes and the templates, and the bundle is a Vite entry.
- `tests/e2e/test_code_blocks.py` — 9 browser tests: the highlighter loads and
  tokenises, the copy button appears and copies the exact source including its
  trailing newline, the inline chip does not leak in either scheme, the block has
  a surface measurably distinct from the page and the tile, the line numbering
  survives the highlighting, a token that spans lines keeps its colour on every
  line, and the admin settings page offers no syntax theme.
- `tests/test_migration_chain.py` — the new revision is the single head, the
  column is dropped and restored, and the fresh-install schema still matches the
  models.
- Chromium on the running instance: `window.Prism` is defined with 41 languages
  registered, `Prism.languages.python` resolves, a Python block produced 17 tokens
  and 3 keywords, the `<pre>` and `<code>` both carry `language-python`, the copy
  button measured 44x29 px and reported "Copied!", and the clipboard held the code
  source byte for byte.
