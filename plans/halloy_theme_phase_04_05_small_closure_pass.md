# Halloy Theme Phase 04–05 Small Closure Pass

## Objective

Close the remaining narrow gaps in the Halloy backend before beginning persistence and Flask integration. This pass should not redesign the parser, translator, registry, or packaging architecture. It should make their existing contracts precise, testable, and release-verifiable.

## Current state

The corrective implementation has already fixed the major defects:

- external overrides now load external content rather than bundled content;
- catalog entries bind descriptors to their selected resources;
- named invalidation rebuilds the catalog;
- the default theme name matches the packaged catalog;
- explicit aliases exist for slug-style and legacy names;
- package resources use an `importlib.resources` traversable abstraction;
- emergency fallback returns complete CSS and variable mappings;
- structured theme exceptions exist;
- end-to-end override and fallback tests exist.

The remaining issues are small but important for handoff quality:

1. external file edits are only observed after explicit invalidation, while some naming/tests imply automatic freshness;
2. artifact verification must be explicitly executed in CI;
3. the latest CI result must prove lint, type checks, tests, coverage, wheel, and sdist checks;
4. unrelated repository churn and copied skill material should be audited;
5. roadmap and operator documentation must state the actual refresh contract.

## Workstream A — Make cache freshness semantics explicit

Choose one supported contract and implement it consistently.

### Preferred first-release contract

External theme changes require an explicit registry refresh or invalidation. This aligns with the planned admin “refresh themes” action and avoids filesystem polling on every request.

Under this contract:

- document that warm registry instances do not automatically discover external file edits;
- rename tests that currently claim automatic cache invalidation;
- ensure `invalidate(name)` and `invalidate()` are the only supported refresh boundaries;
- verify add, edit, delete, and override removal behavior after explicit invalidation;
- ensure no documentation claims automatic mtime refresh.

### Optional stronger contract

If automatic freshness is retained as a requirement, re-stat or hash external files before accepting cache hits. Do not compare cached metadata to itself or to stale catalog metadata.

A correct automatic implementation should:

- obtain current external file metadata from the filesystem;
- detect same-size and same-second edits through content hashing or nanosecond timestamps;
- detect deletion and replacement;
- rebuild the relevant catalog entry when source precedence changes;
- avoid repeated hashing of packaged bundled resources.

Do not leave behavior halfway between these contracts.

## Workstream B — Tighten cache and fingerprint naming

Review `_compute_fingerprint`, `ThemeCache.validate_entry`, and associated tests.

Required outcomes:

- method and field names accurately describe whether values are content hashes or metadata fingerprints;
- bundled resource hashes may use SHA-256 rather than MD5 to avoid misleading security expectations, even though collision resistance is not a security boundary here;
- external cache tests cover the selected refresh contract;
- cache keys continue to distinguish source and canonical name;
- invalidating a canonical name clears both bundled and external variants.

## Workstream C — Make artifact verification a CI gate

The repository includes `scripts/verify_theme_package.py` and expanded artifact tests. Add an explicit CI step that:

1. builds a wheel and sdist from a clean checkout;
2. verifies both artifacts contain the complete theme catalog, manifest, and attribution;
3. installs the wheel into an isolated temporary environment or invokes the verification script against an isolated installation;
4. lists 50 bundled themes through `ThemeRegistry()` without a source-relative bundled root;
5. loads and translates one dark and one light theme;
6. proves import and resource loading work outside the repository root;
7. fails if top-level source themes and packaged resources diverge.

The CI command should be visible and independently diagnosable rather than hidden inside a broad test invocation.

## Workstream D — Validate the full quality gate

Run and record the canonical repository checks:

```text
ruff check .
mypy app
pytest tests/ --ignore=tests/e2e --cov=app --cov-fail-under=80
python scripts/verify_theme_package.py
```

Adapt commands to the existing repository scripts where appropriate. Fix real failures rather than reducing coverage or disabling checks.

If e2e/browser tests are intentionally excluded, document why and where they enter later phases.

## Workstream E — Audit unrelated churn

Review commits since the corrective plan for files with zero textual additions/deletions and for unrelated copied assets.

Specifically inspect:

- line-ending-only modifications across Python, CSS, JS, templates, migrations, and lockfiles;
- `plans/plan.md` for accidental duplication or stale content;
- `.opencode/skills/ainews/*` for relevance to this repository;
- any agent instruction changes unrelated to the Halloy work;
- mobile-menu changes that may be valid but should be separated conceptually from theme closure.

Do not rewrite history solely for cosmetic reasons if commits are already shared. Instead:

- remove clearly accidental files in a follow-up commit;
- document intentional normalization;
- avoid further unrelated modifications in theme implementation commits.

## Workstream F — Update documentation and roadmap state

Update the Halloy roadmap and corrective plan to state:

- Phases 01–05 are closed after this pass;
- the exact external-theme refresh contract;
- package artifact verification is a CI gate;
- Phase 06 may begin only after the quality gate passes;
- runtime rendering still uses the legacy preset system until Phase 07.

Update operator-facing documentation if it currently implies automatic external file discovery.

## Required tests

Add or correct tests for:

- external edit followed by `invalidate(name)`;
- external addition followed by full invalidation;
- external deletion restoring bundled theme after invalidation;
- override replacement after invalidation;
- named invalidation clearing both source cache variants;
- default alias and `.toml` suffix resolution;
- wheel and sdist catalog contents;
- isolated installed-package discovery;
- emergency fallback complete variable output.

## Acceptance criteria

- Cache freshness behavior is explicitly one contract, not ambiguous.
- Test names and documentation match actual behavior.
- CI explicitly builds and verifies wheel and sdist artifacts.
- The latest CI run passes lint, mypy, tests, coverage, and package verification.
- No known Phase 04–05 correctness issue remains.
- Accidental unrelated files are removed or intentionally documented.
- The roadmap marks Phases 01–05 closed.
- Phase 06 can proceed without revisiting resource resolution or packaging architecture.

## Non-goals

- database migration;
- Jinja integration;
- visitor dark/light behavior;
- admin theme selection;
- CSS token replacement.
