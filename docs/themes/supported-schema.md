# Supported Halloy Theme Schema — Phase 01 Catalog Snapshot

> Version: `0.1.0` (Phase 01 inventory snapshot)
> Intent: Authoritative input contract for Phase 02 parser implementation and Phase 03 translator consumption.
> Source catalog: 50 checked-in Halloy TOML files under `themes/`.

This document defines the Halloy TOML schema subset that Phase 02's parser must accept and Phase 03's translator must consume. It is not a general Halloy reference. Only fields confirmed across the 50-file source catalog are specified here.

---

## Top-level structure

A supported Halloy theme file contains the following TOML sections:

```toml
[general]
background = "#..."
border = "#..."
horizontal_rule = "#..."
unread_indicator = "#..."

[text]
primary = "#..."
secondary = "#..."
tertiary = "#..."
success = "#..."
error = "#..."

[buffer]
action = "#..."
background = "#..."
background_text_input = "#..."
background_title_bar = "#..."
border = "#..."
border_selected = "#..."
code = "#..."
highlight = "#..."
nickname = "#..."
selection = "#..."
timestamp = "#..."
topic = "#..."
url = "#..."

  [buffer.server_messages]
  default = "#..."

[buttons.primary]
background = "#..."
background_hover = "#..."
background_selected = "#..."
background_selected_hover = "#..."

[buttons.secondary]
background = "#..."
background_hover = "#..."
background_selected = "#..."
background_selected_hover = "#..."
```

All color values are strings. No boolean, integer, or array values appear in any section across the catalog.

---

## Section-by-section schema

### `[general]`

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `background` | hex color | yes | — | Page background color. Every theme sets this. |
| `border` | hex color | yes | — | General border color. |
| `horizontal_rule` | hex color | yes | — | Color for `<hr>` or horizontal rule separators. |
| `unread_indicator` | hex color | yes | — | Color for unread message indicators. |

All 50 catalog files provide all 4 fields. No optional fields were observed.

### `[text]`

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `primary` | hex color | yes | — | Primary body text color. |
| `secondary` | hex color | yes | — | Secondary or muted text color. |
| `tertiary` | hex color | yes | — | Tertiary or accent text color. |
| `success` | hex color | yes | — | Success state text color. |
| `error` | hex color | yes | — | Error state text color. |

All 50 catalog files provide all 5 fields. No optional fields were observed.

### `[buffer]`

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `action` | hex color | yes | — | Action message text color. |
| `background` | hex color | yes | — | Message buffer background. |
| `background_text_input` | hex color | yes | — | Text input field background in buffer. |
| `background_title_bar` | hex color | yes | — | Title bar background in buffer. |
| `border` | hex color | yes | — | Buffer border color. Some themes use `#00000000` (fully transparent). |
| `border_selected` | hex color | yes | — | Border color for selected buffer. |
| `code` | hex color | yes | — | Inline code text color. |
| `highlight` | hex color | yes | — | Highlighted text or background color. |
| `nickname` | hex color | yes | — | Nickname text color. |
| `selection` | hex color | yes | — | Selection highlight color. |
| `timestamp` | hex color | yes | — | Timestamp text color. |
| `topic` | hex color | yes | — | Channel topic text color. |
| `url` | hex color | yes | — | URL link text color. |

All 50 catalog files provide all 14 fields. No optional fields were observed.

### `[buffer.server_messages]`

This section is nested inside `[buffer]` using TOML dotted-key syntax.

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `default` | hex color | yes | — | Default server message text color. Present in all 50 themes. |
| `join` | hex color | no | — | Join message color. Present in 3 themes. |
| `part` | hex color | no | — | Part message color. Present in 3 themes. |
| `quit` | hex color | no | — | Quit message color. Present in 3 themes. |
| `monitored_online` | hex color | no | — | Monitored user online color. Present in 2 themes. |
| `monitored_offline` | hex color | no | — | Monitored user offline color. Present in 2 themes. |
| `standard_reply_fail` | hex color | no | — | Standard reply fail color. Present in 2 themes. |
| `standard_reply_warn` | hex color | no | — | Standard reply warn color. Present in 2 themes. |
| `standard_reply_note` | hex color | no | — | Standard reply note color. Present in 2 themes. |

**Phase 02 parser behavior:** The `default` key is the only required key. All other keys are optional and will be parsed if present but not consumed by Phase 03's initial translator. They should be silently ignored with no warning. See "Defaults and tolerance" below.

**Distribution across catalog:**
- 45 themes contain only `default` (no extra keys)
- 3 themes contain `default` + `join` + `part` + `quit`: `base16-atelier-forest-light.toml`, `Discord.toml`, `Discord (80_ Saturation).toml`
- 2 themes contain the full 9-key set: `Discord.toml`, `Discord (80_ Saturation).toml`
- 1 theme contains `default` + `join`: `Dark Green.toml`, `plum.toml`

### `[buttons.primary]`

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `background` | hex color | yes | — | Primary button background. |
| `background_hover` | hex color | yes | — | Primary button hover background. |
| `background_selected` | hex color | yes | — | Primary button selected background. |
| `background_selected_hover` | hex color | yes | — | Primary button selected+hover background. |

All 50 catalog files provide all 4 fields. No optional fields were observed.

### `[buttons.secondary]`

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `background` | hex color | yes | — | Secondary button background. |
| `background_hover` | hex color | yes | — | Secondary button hover background. |
| `background_selected` | hex color | yes | — | Secondary button selected background. |
| `background_selected_hover` | hex color | yes | — | Secondary button selected+hover background. |

All 50 catalog files provide all 4 fields. No optional fields were observed.

---

## Color format acceptance

### Accepted formats

| Format | Example | Description |
|---|---|---|
| `#RRGGBB` | `#2E3440` | 6-digit hex, no alpha. Opaque. |
| `#RRGGBBAA` | `#27273DE2` | 8-digit hex with alpha. |

Alpha byte semantics: `00` = fully transparent, `FF` = fully opaque. The alpha channel follows the standard CSS `rgba()` interpretation.

### Rejected formats

The parser must reject and raise `ThemeColorError` for:

- Named colors (`red`, `tomato`, etc.)
- CSS functions (`rgb(...)`, `rgba(...)`, `hsl(...)`, `hsla(...)`, `oklab(...)`)
- Hex strings with wrong length (`#RGB`, `#RRGGBBB`, `#RRGGBBAAA`, etc.)
- Whitespace-padded or semicolon-terminated values
- Any non-hex characters after `#` (except valid hex digits)

### Normalization rules

| Input | Normalized form | Notes |
|---|---|---|
| `#AABBCC` | `#aabbcc` | Lowercase hex digits. |
| `#AABBCCFF` | `#aabbccff` | Lowercase hex digits, alpha preserved. |
| `#AABBCC00` | `#aabbcc00` | Fully transparent. Normalized to lowercase. |

All color normalization is lowercase hex. Mixed-case input (`#AAbbCC`) is normalized to lowercase (`#aabbcc`) before validation.

---

## Filename acceptance rules

Phase 02 does not implement filename validation, but this contract defines the rules for Phase 04's safe-name logic and Phase 05's packaging.

### Allowed characters

| Character class | Example | Notes |
|---|---|---|
| Alphanumeric | `Nord.toml` | Any letter or digit. Case-preserved. |
| Spaces | `black but with important highlights.toml` | Multiple consecutive spaces allowed in source catalog. |
| Hyphens | `base16-atelier-forest-light.toml` | Common in base16 theme names. |
| Underscores | (not observed) | Allowed for completeness but not present in catalog. |
| Parentheses | `Discord (80_ Saturation).toml` | Observed once. |
| Dots | `base16-atelier-forest-light.toml` | The stem `base16-atelier-forest-light` contains hyphens, not dots. The extension `.toml` is the only dot-separated segment. |

### Rejected characters

| Character class | Reason |
|---|---|
| `/` and `\` | Path separators — traversal risk. |
| `..` | Directory traversal component. |
| Control characters (U+0000–U+001F, U+007F) | Non-printable, injection risk. |
| Empty names | No filename to resolve. |
| Leading `.` | Hidden files, could collide with macOS metadata `._*.toml` pattern. |
| Names exceeding 100 characters | Safety limit. Longest catalog filename is `black but with important highlights.toml` (46 characters). |

### Filename edge cases observed in catalog

| Pattern | Example | Count |
|---|---|---|
| Spaces in name | `black but with important highlights.toml`, `Catppuccin Mocha.toml`, etc. | 32 |
| Parentheses | `Discord (80_ Saturation).toml` | 1 |
| Mixed case | `Booberry.toml`, `Catppuccin Latte.toml`, `VESPER.toml` | 32 uppercase-start, 18 lowercase-start |
| Dots in stem | None observed (hyphens used instead) | 0 |
| Leading dots | None (only `._*.toml` metadata files have leading dots) | 0 |

---

## Defaults and tolerance

### Required fields

All fields marked `Required: yes` in the tables above must be present in the parsed TOML. If a required field is missing, the parser raises `ThemeSchemaError` with the missing field path.

Across the 50-file catalog, every required field is present in every file. There are no themes that rely on defaults for any required section or field.

### Optional fields

No optional fields were observed in the catalog. The only optional concept is the extra `buffer.server_messages` keys (`join`, `part`, `quit`, `monitored_online`, `monitored_offline`, `standard_reply_fail`, `standard_reply_warn`, `standard_reply_note`).

If future Halloy versions add new fields, the parser must tolerate them (log a debug-level notice) without raising errors.

### Behavior for unknown sections or fields

| Scenario | Behavior |
|---|---|
| Unknown top-level section (e.g., `[metadata]`) | Parsed but ignored. No warning. |
| Unknown field in a known section (e.g., `[general] unknown_field = "..."`) | Parsed but ignored. No warning. |
| Unknown nested section (e.g., `[buffer.server_messages.join]` if it were a table) | Parsed but ignored. |
| Known section with wrong type (e.g., `[text]` containing a string instead of a table) | Raise `ThemeSchemaError`. |

### Behavior for `[buffer.server_messages]` extras

Extra keys in `[buffer.server_messages]` beyond `default` are parsed and stored in the model but not consumed by Phase 03's translator. The parser should silently accept them. No warning is logged for their presence, because they are valid Halloy schema fields — just not yet translated.

---

## Behavioral contract for the parser

### Parse failure vs. successful parse with warnings

| Condition | Result |
|---|---|
| Invalid TOML syntax | **Parse failure.** Raise `ThemeParseError` with line/column context. |
| Missing required section (e.g., `[general]` absent) | **Parse failure.** Raise `ThemeSchemaError` with missing section path. |
| Missing required field (e.g., `[text].primary` absent) | **Parse failure.** Raise `ThemeSchemaError` with missing field path. |
| Invalid color value (e.g., `rgb(0,0,0)`) | **Parse failure.** Raise `ThemeColorError` with field path and raw value. |
| Unknown section or field present | **Successful parse.** Unknown data silently discarded. |
| Extra `buffer.server_messages` keys | **Successful parse.** Keys accepted, not translated in Phase 03. |
| Empty file (no content) | **Parse failure.** Raise `ThemeParseError`. |
| Non-TOML file content | **Parse failure.** Raise `ThemeParseError`. |

### Schema-version string

The parser must embed a schema version in every parsed `HalloyTheme` model:

```
schema_version = "halloy-supported-v1"
```

This version string identifies the schema subset defined by this document. It is not the upstream Halloy schema version. It must be included in model metadata for traceability and future migration.

---

## Catalog statistics

| Metric | Value |
|---|---|
| Total theme files in source catalog | 50 |
| Total color values in catalog | 1,571 |
| 6-digit hex (`#RRGGBB`) | 1,531 (97.5%) |
| 8-digit hex (`#RRGGBBAA`) | 40 (2.5%) |
| Files containing at least one alpha color | 26 of 50 (52%) |
| Files with only `buffer.server_messages.default` | 45 |
| Files with extra `buffer.server_messages` keys | 5 |
| Distinct `buffer.server_messages` keys observed | 9 (`default` + 8 extras) |
| Sections observed | 6 (`general`, `text`, `buffer`, `buffer.server_messages`, `buttons.primary`, `buttons.secondary`) |
| Non-string values in any field | 0 |

### Files containing 8-digit alpha colors

| File | Alpha color values |
|---|---|
| `Booberry.toml` | `#00000000` |
| `Catppuccin Latte.toml` | `#00000000` |
| `Catppuccin Macchiato.toml` | `#00000000` |
| `Catppuccin Mocha.toml` | `#00000000` |
| `Cyber Red.toml` | `#73000054` |
| `Cyberpunk.toml` | `#00000000` |
| `Dark Green.toml` | `#00000000` |
| `Dracula.toml` | `#00000000` |
| `Ferra Light.toml` | `#00000000` |
| `Flexor Dark.toml` | `#00000000` |
| `Gruvbox.toml` | `#00000000` |
| `IntelliJ Light.toml` | `#00000000` |
| `Kanagawa.toml` | `#00000000` |
| `Macaw Dark.toml` | `#00000000` |
| `Macaw Light.toml` | `#00000000` |
| `Noctis Lilac.toml` | `#00000000`, `#7060EB22`, `#7060EB66`, `#A599FF77`, `#A599FFDD`, `#B4ADEB77` |
| `One Dark.toml` | `#00000000` |
| `Oxocarbon.toml` | `#00000000` |
| `Rose Pine Dawn.toml` | `#00000000` |
| `Rose Pine Moon.toml` | `#00000000` |
| `Rose Pine.toml` | `#00000000` |
| `Tokyo Night Storm.toml` | `#545C7E32`, `#E0AF6819` |
| `VESPER.toml` | `#00000000` |
| `Zenburn.toml` | `#00000000` |
| `ferra.toml` | `#00000000` |
| `plum.toml` | `#00000000`, `#242424B4`, `#27273DE2`, `#C5B15CAA` |

Note: 18 of these 26 files use only `#00000000` (fully transparent). The remaining 8 files use non-trivial alpha values.

### Filename edge cases in catalog

| Character pattern | Example filenames | Count |
|---|---|---|
| Spaces | `black but with important highlights.toml`, `Catppuccin Mocha.toml` | 32 |
| Parentheses | `Discord (80_ Saturation).toml` | 1 |
| Uppercase start | `Booberry.toml`, `Catppuccin Mocha.toml`, `VESPER.toml` | 32 |
| Lowercase start | `acton.toml`, `bam.toml`, `ferra.toml` | 18 |
| Dots in stem | None | 0 |
| Leading dots | None | 0 |
| Double dots | None | 0 |

---

## Schema-source reference

The source themes in `themes/` are derived from the [Halloy IRC client project](https://github.com/halloy-im/halloy). Halloy themes define a broader schema than what this project consumes. This document specifies only the subset confirmed across the 50-file catalog in this repository.

Sections not present in the catalog and therefore **not supported** include (but are not limited to):

- `[metadata]` (attribution, license, author)
- `[chat]` (message styling)
- `[sidebar]` (sidebar-specific colors)
- `[scrollbar]` (scrollbar styling)
- Any `[buffer.*]` subsections beyond `server_messages`

When the upstream Halloy schema evolves, this document must be updated to reflect any new fields that appear in the catalog. Do not assume upstream fields are supported unless confirmed by catalog inspection.
