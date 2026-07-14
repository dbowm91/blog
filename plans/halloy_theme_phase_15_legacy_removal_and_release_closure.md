# Halloy Theme Phase 15 — Legacy Removal and Release Closure

## Objective

Remove obsolete preset infrastructure, prove the Halloy system is the sole runtime theme authority, and complete release-readiness validation for the entire theming roadmap.

This phase must begin only after the corrective pass and Phases 11–14 are complete. It is a closure and verification phase, not a place to introduce new theme features.

## Legacy authority removal

Search the repository for:

```text
THEME_PRESETS
theme_preset
github-dark
github-light
solarized-dark
monokai
data-theme
localStorage.theme
localStorage.getItem('theme')
```

Classify every occurrence as:

- migration compatibility that must remain;
- documentation/history;
- test fixture;
- obsolete runtime code to remove.

Remove:

- `THEME_PRESETS` as a rendering or admin catalog source;
- legacy context-processor palette fallback;
- static preset option lists;
- duplicate old theme helpers;
- obsolete static light-palette selectors;
- stale JavaScript storage keys and `data-theme` behavior;
- compatibility exports no longer needed.

Retain only narrowly scoped migration aliases where required for existing database values or config compatibility.

## Final fallback architecture

The only runtime fallback hierarchy should be:

1. requested configured Halloy theme;
2. configured Halloy default;
3. known-good bundled Halloy theme;
4. hardcoded emergency `BlogTheme` serialized through the normal token path.

Database or service failures must not return to the old preset dictionary.

Add tests that deliberately break database access, packaged resources, and external themes while asserting the Halloy emergency context remains complete.

## Schema and compatibility closure

Decide whether to retain or remove the legacy `theme_preset` database column.

Preferred approach:

- retain for one compatibility release only if downgrade or old deployment tooling requires it;
- otherwise add a migration to drop it after proving all values migrated;
- document downgrade limitations clearly.

If retained, mark it deprecated and ensure no runtime writes or reads depend on it.

## Repository-wide frontend verification

Run the final literal and selector audit:

- no meaningful palette literals outside documented invariant assets and syntax themes;
- no duplicate palette ownership between critical and deferred CSS;
- all public/admin templates receive the app-scoped theme context;
- custom CSS remains last;
- CSP nonces remain present;
- JavaScript-disabled rendering remains usable;
- dark/light/system behavior remains consistent across public, login, and admin shells.

## Full release validation matrix

Run and enforce:

- Ruff and mypy;
- complete pytest suite and coverage threshold;
- migration upgrade/downgrade tests;
- catalog-wide parser, translation, and accessibility validation;
- security tests for traversal, symlink escape, oversized files, and CSS injection;
- CLI tests;
- admin preview/refresh tests;
- browser first-paint and scheme persistence tests;
- concurrency/reliability tests;
- wheel and sdist build/install verification;
- container resource and external-volume smoke tests;
- documentation sample validation.

CI must show these checks as explicit named gates where practical.

## Release artifact inspection

Build final wheel and source distribution, then verify from an isolated environment:

- all approved bundled themes are present;
- attribution and catalog manifest are included;
- the registry lists the expected catalog;
- a dark and light theme load;
- CLI commands run;
- no repository-root dependency exists;
- external themes extend and override bundled resources;
- emergency fallback works when a configured theme is unavailable.

## Upgrade rehearsal

Test representative upgrade paths:

- existing database using each legacy preset;
- existing custom CSS and syntax theme;
- missing or malformed selected external theme;
- source deployment to wheel/container deployment;
- rollback where supported.

Capture exact commands and expected results in release documentation.

## Cleanup and documentation synchronization

Remove completed temporary plans, generated scratch files, stale comments, misleading phase-complete claims, and duplicated architecture notes according to repository policy. Preserve roadmap/history documents if they are intentionally retained for handoff traceability.

Update the roadmap status and release notes with evidence-based completion claims.

## Definition of done

- Halloy registry/service is the only runtime palette authority;
- `THEME_PRESETS` is removed from normal rendering and admin behavior;
- legacy storage/selectors are absent from active frontend code;
- migration compatibility is narrow, documented, and tested;
- all bundled themes pass mandatory parser, translation, security, packaging, and accessibility gates;
- external themes can be validated, installed, refreshed, selected, and removed through documented workflows;
- first-time and returning visitor scheme behavior is correct;
- public/admin pages survive theme and database failures without 500 responses;
- wheel, sdist, and container validation pass from isolated environments;
- CI and release documentation provide auditable completion evidence.

## Non-goals

- arbitrary per-visitor named theme catalogs;
- theme uploads through the browser;
- typography/layout theme packs;
- new Halloy schema extensions;
- unrelated frontend redesign.
