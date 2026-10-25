# Halloy Theme System Final Verification and Policy Pass

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Purpose

Perform the final release-candidate verification and policy review for the Halloy theme roadmap. This pass does not introduce another feature phase. Its purpose is to establish whether the completed theme subsystem is safe, supportable, accessible, migration-correct, reproducibly packaged, and ready to be treated as closed production infrastructure.

The pass must resolve the two remaining material review concerns:

1. The accessibility exception manifest currently permits documented mandatory contrast failures across most bundled themes, but the exceptions have not yet been separated into false-positive checks, acceptable advisory deviations, and genuine accessibility defects.
2. Existing migration tests reproduce individual schema operations but do not execute the real Alembic revision chain against representative legacy data.

The pass must also produce verifiable release evidence for CI, packaging, browser behavior, operator commands, migration behavior, and runtime fallback behavior.

## Scope

This pass covers:

- `app/themes/ACCESSIBILITY_EXCEPTIONS.json`
- `app/themes/diagnostics.py`
- `app/themes/translate.py`
- `app/themes/registry.py`
- `app/themes/service.py`
- `app/cli.py`
- `migrations/versions/add_theme_config_to_sitesettings.py`
- `migrations/versions/preserve_legacy_scheme.py`
- `migrations/versions/drop_theme_preset_column.py`
- `tests/themes/`
- `tests/e2e/`
- `tests/benchmarks/`
- `tests/test_migration_drop_theme_preset.py`
- `.github/workflows/`
- `scripts/theme_accessibility_report.py`
- `scripts/verify_theme_package.py`
- `docs/themes/`
- release/readiness documentation

This pass must not add new theme-selection features, redesign the admin UI, alter the Halloy schema, or create another compatibility layer for removed legacy presets.

## Required Outcomes

At completion:

- Every accessibility exception has an explicit policy classification and evidence.
- Genuine mandatory accessibility failures are corrected, excluded from default availability, or explicitly accepted through a narrowly defined product policy.
- Accessibility checks do not assert token/background combinations that cannot occur in rendered UI.
- The real Alembic revision chain is tested from a representative pre-Halloy schema through current head.
- Wheel and sdist artifacts are built, inspected, installed in isolation, and exercised outside the source checkout.
- Current-head CI contains explicit, independently visible gates for unit/integration tests, migrations, artifacts, browser accessibility, and performance smoke tests.
- The final release record identifies exact commands, artifact contents, supported behavior, known deviations, and rollback expectations.

---

## Workstream A — Accessibility Exception Policy Audit

### A1. Define the exception taxonomy

Create a policy document, preferably `docs/themes/accessibility-policy.md`, defining exactly three classes:

1. **Invalid or unreachable check**
   - The validator compares a token pair that is not rendered together in the application.
   - Resolution: remove or narrow the check. Do not retain an exception.

2. **Advisory product deviation**
   - The UI remains understandable and operable, and the checked element is non-textual, decorative, redundant, or otherwise outside the mandatory policy adopted by the project.
   - Resolution: retain only with a precise reason, rendered-context reference, owner, and review date.

3. **Mandatory accessibility defect**
   - Includes body text, form text, code text, essential navigation text, focus indicators, selection readability, input boundaries where visual identification is required, or another mandatory project gate.
   - Resolution: correct the translation, correct the source theme, disable the theme from default selection, or reject it from the bundled catalog. A generic “design choice” is not sufficient.

The policy must define which WCAG success criteria and project-level thresholds are mandatory. At minimum, explicitly address:

- normal text contrast;
- large text contrast;
- non-text UI component contrast;
- keyboard focus appearance;
- form controls and boundaries;
- placeholder text policy;
- selected text readability;
- status colors and redundant indicators;
- forced-colors/high-contrast behavior.

### A2. Audit all existing manifest entries

For every entry in `ACCESSIBILITY_EXCEPTIONS.json`:

- identify the actual CSS selector or component using the token;
- identify the actual background used in that component;
- capture the computed ratio from the current translator;
- classify the entry using the taxonomy;
- replace vague reasons such as “design choice” or “palette-derived” with concrete rationale;
- remove stale entries where translation fixes already resolved the failure;
- reject wildcard or overly broad exceptions;
- ensure exceptions are bound to theme name, token pair, expected ratio range, required threshold, and validator version.

Add manifest metadata:

- schema version;
- validator version;
- reviewed date;
- policy version;
- optional owner/reviewer;
- expiration or next-review date for accepted deviations.

### A3. Correct invalid checks

Review all validator pairs in `diagnostics.py` against actual CSS usage.

Examples requiring explicit confirmation:

- status foreground on page background versus status foreground on status background;
- input border against page background versus the actual input container surface;
- navbar text against effective navbar background after transparency/compositing;
- focus ring against both adjacent colors, not only page background;
- code text against the actual code block background;
- selection foreground against the browser-applied selection background;
- placeholder text against input background.

Remove checks that cannot occur. For checks that depend on alpha or layered surfaces, calculate the actual composited color before evaluating contrast.

### A4. Correct genuine defects

Prioritize mandatory defects in this order:

1. primary and input text;
2. code text;
3. navigation text;
4. focus and keyboard indicators;
5. selection readability;
6. form boundaries and required state indicators;
7. links and status messaging.

Use deterministic translator corrections where possible:

- contrast-aware foreground selection;
- controlled lightness adjustment;
- background compositing before foreground choice;
- minimum-contrast clamping;
- separate semantic tokens when one Halloy source color cannot safely serve multiple UI roles.

Do not silently mutate source Halloy theme files unless the project explicitly decides the bundled copy is a maintained derivative. Prefer translation-layer correction with provenance diagnostics.

### A5. Establish bundled-theme eligibility policy

Define one of these explicit release policies:

- **Strict catalog:** every bundled theme passes all mandatory gates with no mandatory exceptions.
- **Tiered catalog:** themes are labeled `recommended`, `compatible-with-exceptions`, or `experimental`; only recommended themes appear by default.
- **Permissive catalog:** all themes remain selectable, but the admin and CLI clearly expose mandatory deviations and require an explicit operator acknowledgement.

The chosen policy must be implemented consistently in:

- registry descriptors or catalog manifest metadata;
- admin selectors;
- CLI output and exit codes;
- operator documentation;
- tests.

Do not claim “all themes pass” when the actual policy is “all themes pass after exceptions.” Use exact language.

### A6. Accessibility verification tests

Add tests proving:

- every exception maps to an active finding;
- no exception is orphaned;
- no finding is accepted by token name alone without theme and pair identity;
- ratio drift outside an allowed tolerance invalidates the exception;
- expired exceptions fail validation;
- strict mode rejects unexpected mandatory failures;
- the default dark and light themes have no mandatory exceptions;
- admin and public pages expose visible focus indicators;
- forced-colors mode remains operable;
- reduced-motion behavior is respected;
- color is not the sole indicator for error/success states.

---

## Workstream B — Real Alembic Revision-Chain Validation

### B1. Identify the supported upgrade boundary

Document the oldest database revision from which the Halloy migration is supported. Determine the exact revision immediately before:

- `add_theme_config_to_sitesettings`;
- `preserve_legacy_scheme`;
- `drop_theme_preset_column`.

Confirm there is a single valid revision chain and no accidental branch head or incorrect `down_revision` linkage.

### B2. Build real migration-chain tests

Create tests that invoke Alembic through its actual configuration and revision scripts rather than reproducing operations inline.

Required scenarios:

1. Create a temporary database at the supported pre-Halloy revision.
2. Insert representative rows for:
   - `github-dark`;
   - `github-light`;
   - `solarized-dark`;
   - `monokai`;
   - an unknown/custom legacy value;
   - null/empty values where the historical schema permits them.
3. Run `alembic upgrade head` using the real revision chain.
4. Verify:
   - dark and light Halloy names;
   - preserved default visual scheme;
   - syntax theme and custom CSS preservation;
   - removal of `theme_preset`;
   - no duplicate `SiteSettings` rows;
   - correct constraints/defaults.
5. Start the Flask application against the upgraded database and render a public page.
6. Downgrade to the revision immediately before `drop_theme_preset_column` and verify the restored column and documented downgrade semantics.
7. Upgrade to head again and verify idempotent data behavior.

### B3. Test supported databases

Run the revision-chain test on:

- SQLite, which uses batch table operations;
- PostgreSQL, if PostgreSQL is a supported production database.

If PostgreSQL is not supported by current deployment documentation, state that explicitly rather than leaving the status ambiguous.

### B4. Validate fresh-install behavior

For a fresh empty database:

- upgrade directly to head;
- create default settings;
- confirm default dark/light names and `system` scheme;
- confirm no obsolete column exists;
- render both public and admin templates.

### B5. Migration failure and recovery documentation

Document:

- pre-upgrade backup requirement;
- migration command;
- verification command;
- expected columns after upgrade;
- rollback limitations;
- behavior of the restored legacy column on downgrade;
- how to recover if a selected external theme is unavailable after upgrade.

---

## Workstream C — CI and Release Gate Verification

### C1. Split CI into explicit jobs

Use independently visible jobs rather than one monolithic test command. Recommended jobs:

- `lint`
  - Ruff formatting/checks as adopted by the project;
  - mypy.

- `unit-integration`
  - full non-browser pytest suite;
  - coverage threshold.

- `theme-policy`
  - catalog parse and translation;
  - strict accessibility policy;
  - exception-manifest integrity;
  - default-theme zero-exception gate.

- `migration-chain`
  - real Alembic pre-Halloy-to-head test;
  - fresh-install migration test.

- `package-artifacts`
  - build wheel and sdist;
  - inspect contents;
  - isolated install;
  - run package-resource and CLI smoke tests outside checkout.

- `browser-smoke`
  - public dark/light/system behavior;
  - admin preview;
  - keyboard/focus accessibility;
  - no first-paint palette mismatch where test infrastructure can detect it.

- `performance-smoke`
  - stable, generous thresholds;
  - non-flaky warm-path and registry-load checks.

### C2. Make artifact verification explicit

The artifact job must:

1. remove stale `dist/` and build directories;
2. build wheel and sdist;
3. list archive contents;
4. verify all 50 bundled TOML files;
5. verify attribution, catalog manifest, and accessibility policy/manifest resources;
6. install the wheel into a clean virtual environment;
7. change working directory outside the repository;
8. import the application/theme package;
9. enumerate and load bundled themes via `importlib.resources`;
10. run representative CLI commands;
11. confirm no source-tree path dependency.

### C3. Confirm current-head status visibility

Ensure pushes to `main` and pull requests create visible GitHub check runs. Remove duplicate or obsolete workflows that cause ambiguous status. Establish required checks in branch protection if repository policy permits.

### C4. Record exact release evidence

Create a machine-readable or Markdown release verification record containing:

- commit SHA;
- Python and Node versions;
- test counts and skipped-test reasons;
- coverage;
- accessibility exact-pass/exception/failure counts;
- migration scenarios executed;
- artifact hashes;
- browser matrix;
- benchmark summary;
- known accepted deviations.

Suggested path:

- `docs/themes/release-verification.md`, or
- `release/halloy-theme-verification.md`.

---

## Workstream D — Runtime and Operator Acceptance Tests

### D1. Default behavior

Verify a fresh deployment:

- defaults to configured Catppuccin dark/light pair;
- applies the administrator default scheme to a first-time visitor;
- honors visitor local-storage preference afterward;
- responds to OS scheme changes only while visitor preference is `system`;
- produces no missing CSS variables.

### D2. External themes

Verify:

- novel external theme discovery;
- same-name bundled override;
- malformed override isolation;
- deleted override restoration after explicit refresh;
- symlink/traversal/oversized-file rejection;
- refresh logging and counters;
- documented explicit-refresh semantics.

### D3. Admin workflow

Verify:

- selectors display source and policy classification;
- preview does not persist;
- invalid crafted names return controlled 400/validation responses;
- save invalidates settings cache;
- refresh reports additions/removals/overrides;
- unavailable selected themes fall back with an operator-visible warning;
- CSRF and admin authentication remain enforced.

### D4. CLI workflow

Verify exit codes and output for:

- list;
- inspect;
- validate file;
- validate registered name;
- refresh;
- paths;
- accessibility normal mode;
- accessibility strict mode;
- JSON output;
- malformed theme;
- missing external directory;
- permission-denied external directory.

JSON output must remain valid JSON with diagnostics sent to stderr where appropriate.

### D5. Emergency fallback

Inject failures at each boundary:

- database unavailable;
- settings row missing;
- registry initialization failure;
- bundled resource missing or malformed;
- external theme malformed;
- translation failure.

Confirm the application still renders a complete safe palette, logs the cause, and does not expose filesystem paths or internal exception details to visitors.

---

## Workstream E — Documentation and Policy Reconciliation

### E1. Correct roadmap and phase language

Make Phase 14 and Phase 15 boundaries unambiguous:

- Phase 14: documentation, operator migration guidance, and compatibility audit.
- Phase 15: destructive runtime/schema cleanup and release closure.

Remove duplicated or contradictory claims.

### E2. Reconcile accessibility language

Across README, AGENTS, operator guide, CLI help, and release notes, use language matching the selected policy:

- exact mandatory pass;
- pass with approved deviations;
- experimental theme with known failures.

Never conflate documented exceptions with conformance.

### E3. Reconcile migration language

Clarify that legacy names are migrated by database revisions during upgrade but are no longer valid runtime selections after the legacy column is dropped.

### E4. Publish support contract

Document:

- bundled theme support level;
- external theme compatibility contract;
- explicit refresh requirement;
- package resource guarantees;
- accessibility policy;
- migration support boundary;
- rollback expectations;
- deprecation policy for token/schema changes.

---

## Implementation Sequence

Execute in this order:

1. Freeze theme feature work during verification.
2. Define accessibility policy and exception taxonomy.
3. Audit validator pairs against rendered CSS contexts.
4. Correct invalid checks and genuine mandatory defects.
5. Rebuild and review the exception manifest.
6. Implement bundled-theme eligibility classification.
7. Add exception-integrity and strict-policy tests.
8. Add real Alembic-chain tests.
9. Add fresh-install and downgrade/upgrade tests.
10. Split and harden CI jobs.
11. Run isolated wheel/sdist verification.
12. Run browser and operator acceptance tests.
13. Produce release evidence and reconcile documentation.
14. Perform final reviewer sign-off against the exit checklist.

Do not generate the release sign-off document until all required jobs have completed successfully on the exact candidate commit.

---

## Detailed Acceptance Criteria

### Accessibility

- [ ] Every validator pair corresponds to a rendered UI context.
- [ ] Every manifest entry has a policy class and concrete rationale.
- [ ] No orphaned or stale exceptions exist.
- [ ] Default dark and light themes have zero mandatory exceptions.
- [ ] Unexpected mandatory failures cause strict CI failure.
- [ ] Theme eligibility is visible in CLI/admin metadata.
- [ ] Documentation does not claim unconditional conformance when exceptions remain.

### Migration

- [ ] Actual Alembic revisions are invoked in tests.
- [ ] Pre-Halloy legacy rows migrate to expected Halloy values.
- [ ] Visual mode is preserved.
- [ ] `theme_preset` is absent at head.
- [ ] Fresh install to head works.
- [ ] Downgrade and re-upgrade behavior is documented and tested.
- [ ] Supported database engines are tested or explicitly scoped.

### Packaging

- [ ] Wheel and sdist build cleanly.
- [ ] Both artifacts contain all required theme resources.
- [ ] Isolated installation works outside the checkout.
- [ ] Registry loads resources through `importlib.resources`.
- [ ] CLI smoke tests pass from the installed artifact.

### Runtime

- [ ] First-time visitor default scheme works.
- [ ] Visitor preference overrides server default.
- [ ] External override and refresh behavior matches documentation.
- [ ] Emergency fallback renders complete CSS variables.
- [ ] No legacy preset runtime authority remains.

### CI

- [ ] Current-head checks are visible on GitHub.
- [ ] Required jobs are independently identifiable.
- [ ] Migration and artifact jobs are mandatory.
- [ ] Browser skips are justified and recorded.
- [ ] Performance thresholds are stable across repeated CI runs.

### Documentation

- [ ] Accessibility policy is published.
- [ ] Migration boundary and rollback behavior are published.
- [ ] Operator guide matches current CLI and runtime behavior.
- [ ] Phase 14/15 terminology is consistent.
- [ ] Final verification record references the exact candidate SHA.

---

## Non-Goals

This pass does not:

- add more bundled themes;
- redesign the semantic token model;
- implement automatic filesystem watching;
- restore legacy preset names as runtime aliases;
- introduce a remote theme marketplace;
- guarantee third-party external themes meet accessibility requirements;
- replace the existing Flask/Jinja rendering architecture.

---

## Release Decision Rules

### Release approved

Approve closure only when:

- all mandatory CI jobs pass on the candidate SHA;
- no unexpected mandatory accessibility failures remain in bundled themes;
- the selected exception policy is documented and enforced;
- real migration-chain tests pass;
- isolated wheel and sdist verification passes;
- default themes pass without mandatory exceptions;
- no unresolved severity-one or severity-two theme defects remain.

### Conditional approval

Conditional approval is allowed only for explicitly documented advisory deviations that:

- do not affect essential text, controls, focus, or navigation;
- have an owner and review date;
- are visible in operator diagnostics;
- cannot silently expand to other themes or token pairs.

### Release blocked

Block closure if any of the following remain:

- primary/input/code text mandatory contrast failures;
- inaccessible keyboard focus;
- migration-chain data loss or incorrect revision linkage;
- missing resources in wheel/sdist;
- source-tree-only imports;
- current-head CI not executing required gates;
- generic blanket accessibility exceptions without rendered-context evidence.

---

## Definition of Done

This verification/policy pass is complete when the repository contains:

1. an approved accessibility policy and audited exception manifest;
2. corrected validator contexts and mandatory defects;
3. a clear bundled-theme eligibility policy;
4. actual Alembic revision-chain tests with representative legacy data;
5. explicit CI jobs for policy, migration, packaging, browser, and performance gates;
6. isolated wheel and sdist verification;
7. a final release-verification record tied to one commit SHA;
8. consistent documentation and operator guidance;
9. no unresolved release-blocking findings.

After these criteria are met, the Halloy roadmap can be marked fully closed and future work should proceed as ordinary maintenance rather than another migration phase.
