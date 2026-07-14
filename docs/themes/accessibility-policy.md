# DevLog Theme Accessibility Policy

This document defines the accessibility requirements, exception classification, and bundled-theme eligibility policy for the DevLog Halloy theme system.

## 1. Mandatory Accessibility Requirements

DevLog enforces WCAG 2.1 Level AA compliance for all bundled themes. The following success criteria and project-level thresholds are mandatory and non-negotiable:

| Category | WCAG Criterion | Threshold | Notes |
|----------|---------------|-----------|-------|
| Normal text contrast | 1.4.3 (Minimum) | 4.5:1 | Body text, paragraphs, headings, list items, table cell content |
| Large text contrast | 1.4.3 (Minimum) | 3:1 | Text ≥18pt or ≥14pt bold |
| Non-text UI component contrast | 1.4.11 (Non-text Contrast) | 3:1 | Form input boundaries, buttons, focus indicators, selection controls |
| Keyboard focus appearance | 2.4.7 (Focus Visible) | Visible indicator | Focus ring or border must be distinguishable from surrounding UI |
| Form controls and boundaries | 1.4.11 + 3.3.2 | 3:1 | Input fields, textareas, select elements must have visible boundaries |
| Placeholder text policy | 1.3.5 (Identify Input Purpose) | 4.5:1 | Placeholder text must meet normal text contrast when rendered |
| Selected text readability | 1.4.3 (Minimum) | 4.5:1 | Text on selection background must remain readable |
| Status colors and redundant indicators | 1.4.1 (Use of Color) | Redundant indicator | Status messages must not rely solely on color; text labels or icons required |
| Forced-colors/high-contrast behavior | 1.4.11 + 2.4.7 | System colors | Focus indicators and boundaries must adapt to forced-colors mode |

### Project-Level Thresholds

- **Text tokens** (primary, input, code, link, secondary): 4.5:1 minimum contrast ratio
- **Large text tokens** (muted, dim): 3:1 minimum contrast ratio
- **UI component tokens** (borders, focus rings, input boundaries): 3:1 minimum contrast ratio
- **Status colors** (success, error, warning, info foreground): Must pass contrast on their designated composited backgrounds, not on page background
- **Navbar text**: Must pass contrast against the effective composited navbar background (accounting for semi-transparent overlays), not the raw `--blog-navbar-bg` color

## 2. Exception Classification

Every accessibility exception must be classified into exactly one of three policy classes. No exception may be retained without a classification.

### 2.1 Invalid or Unreachable Check

**Definition:** The validator compares a token pair that is not rendered together in the application. The check produces a false positive because the two colors never coexist as foreground/background in the actual UI.

**Resolution:** Remove or narrow the check. Do not retain an exception. If the pair is never rendered together, the validator should be updated to exclude it, and any existing exception entry for this pair must be deleted.

**Examples:**
- A token that is only rendered against a different background than the one being checked
- A composited color that is never used directly against the page background
- A token pair where one side is always alpha-composited before rendering

### 2.2 Advisory Product Deviation

**Definition:** The UI remains understandable and operable, and the checked element is non-textual, decorative, redundant, or otherwise outside the mandatory policy scope. The deviation does not impair a user's ability to perceive, understand, or interact with the application.

**Resolution:** Retain only with a precise reason, rendered-context reference, owner, and review date. Advisory deviations must document:
- Why the element falls outside mandatory scope
- Where the token pair actually appears in the rendered UI
- Who is responsible for reviewing the exception
- When the exception was last reviewed

**Examples:**
- Thin decorative input borders (non-essential visual delineation, not information-carrying)
- Status foreground colors checked against page background instead of their composited status background
- Navbar text checked against raw background color when the actual rendered background includes a semi-transparent overlay
- Secondary/metadata text with intentionally reduced contrast for visual hierarchy
- Link hover states (transient interactive feedback)
- Focus indicators using alternative mechanisms permitted by WCAG 2.2

### 2.3 Mandatory Accessibility Defect

**Definition:** A failure that directly impairs a user's ability to perceive, read, or interact with essential content. Includes body text, form text, code text, essential navigation text, focus indicators (when no alternative mechanism exists), selection readability, and input boundaries where visual identification is required.

**Resolution:** Correct the translation, correct the source theme, disable the theme from default selection, or reject it from the bundled catalog.

**Examples:**
- Primary body text (`--blog-text-primary`) failing 4.5:1 on page background or surfaces
- Form input text (`--blog-input-text`) failing 4.5:1 on input background
- Code block text (`--blog-code-text`) failing 4.5:1 on code background
- Link text (`--blog-text-link`) failing 4.5:1 on page background or surfaces
- Selected text (`--blog-text-primary` on `--blog-selection-bg`) failing 4.5:1
- Focus indicators that are invisible in any rendering context

## 3. Bundled-Theme Eligibility Policy

Bundled themes are classified into three tiers based on their accessibility compliance status. Tier assignment determines whether a theme may be offered as a default selection.

### 3.1 Recommended

**Gate:** All mandatory accessibility checks pass. Zero mandatory failures. Zero expected exceptions for mandatory defects.

**Default selection:** Yes. These themes may be set as the default theme and are offered first in theme selection UIs.

**Requirements:**
- All text contrast pairs meet their required thresholds
- All UI component contrast pairs meet their required thresholds
- Focus indicators are visible and meet contrast requirements
- Selection text is readable
- Form input boundaries are identifiable
- No advisory deviations exist (or all advisory deviations are documented)

### 3.2 Compatible with Exceptions

**Gate:** Advisory deviations are documented in the exception manifest. All mandatory checks pass (with documented exceptions where applicable). No unexpected mandatory failures.

**Default selection:** No. These themes are available for manual selection but are not offered as defaults.

**Requirements:**
- All mandatory text contrast pairs pass
- All mandatory UI component contrast pairs pass
- Advisory deviations are fully documented with:
  - Policy class classification
  - Concrete rationale (no vague "design choice" or "palette-derived")
  - WCAG criteria affected
  - Rendered context reference
  - Owner and review date
- No stale or orphaned exception entries

### 3.3 Experimental

**Gate:** Known mandatory failures exist. These are themes where the translation or source palette produces contrast ratios below mandatory thresholds for essential content.

**Default selection:** Never. These themes are excluded from default selection and clearly marked as experimental.

**Requirements:**
- All mandatory failures are documented in the exception manifest
- Each mandatory failure includes remediation guidance
- The theme owner must acknowledge the failures
- The theme must not be offered as a default or recommended option

## 4. Exception Manifest Structure

The exception manifest (`app/themes/ACCESSIBILITY_EXCEPTIONS.json`) follows this structure:

```json
{
  "schema_version": 2,
  "validator_version": "1.0",
  "reviewed_date": "YYYY-MM-DD",
  "policy_version": "1.0",
  "owner": "theme-maintainer",
  "version": 1,
  "description": "Accessibility exception manifest for bundled themes",
  "exceptions": {
    "Theme Name": {
      "total_failures": 0,
      "policy_class": "recommended|compatible-with-exceptions|experimental",
      "pairs": [
        {
          "token": "--blog-token-name",
          "description": "token on background",
          "ratio": 3.5,
          "required": 4.5,
          "policy_class": "invalid_check|advisory_deviation|mandatory_defect",
          "rationale": "Concrete reason for this exception",
          "wcag_criteria": ["1.4.3", "1.4.11"],
          "rendered_context": "Where this pair appears in the UI"
        }
      ]
    }
  },
  "summary": {
    "total_bundled": 50,
    "themes_with_exceptions": 0,
    "themes_passing": 0,
    "policy_version": "1.0",
    "reviewed_date": "YYYY-MM-DD",
    "eligible_categories": {
      "recommended": 0,
      "compatible-with-exceptions": 0,
      "experimental": 0
    }
  }
}
```

## 5. Review Process

1. All exceptions must be reviewed at least once per release cycle
2. Stale exceptions (where translation fixes resolved the failure) must be removed
3. New exceptions require owner approval and policy class justification
4. The exception manifest is validated against the actual rendered theme output
5. Changes to the exception manifest require updating `reviewed_date`

## 6. Scope

This policy applies to:
- All themes in the bundled catalog (`app/themes/bundled/`)
- All themes validated by the accessibility diagnostic tooling (`app/themes/diagnostics.py`)
- All themes offered through the admin theme selector

This policy does not apply to:
- External themes installed by operators (outside the bundled catalog)
- Custom CSS overrides applied on top of bundled themes
- Themes in development or testing states
