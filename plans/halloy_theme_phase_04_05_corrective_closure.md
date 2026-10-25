# Halloy Theme Phases 04–05 Corrective Closure Plan

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Completion Status

**Status: COMPLETE** — 2026-07-13

All 10 sections of this corrective closure plan have been implemented and validated:

- 1110 theme tests pass (full test suite)
- `ruff check .` — clean
- `ruff format --check .` — clean
- `mypy app/` — clean

The corrective closure pass addressed: catalog entry precedence binding, cache freshness validation, named invalidation semantics, canonical-name normalization, package-resource abstraction, wheel/sdist verification, end-to-end regression coverage, structured exception types, and documentation reconciliation. Phases 04 and 05 are complete.

---

## Purpose

Close the correctness and release-verification gaps found after implementation of the Halloy theme registry, external override model, cache, and packaged catalog.

This plan must be completed before Phase 06 persistence/configuration integration begins. The existing runtime should continue using the legacy preset system until this closure pass is complete and validated.

## Scope

This pass is narrowly focused on:

- external override correctness;
- registry resolution consistency;
- cache freshness and invalidation;
- canonical name/default-theme behavior;
- true package-resource loading;
- actual wheel and source-distribution verification;
- end-to-end tests that assert loaded theme content rather than only metadata;
- final Phase 04–05 documentation and status cleanup.

Do not add the admin selector, database migration, Jinja runtime integration, visitor scheme behavior, or broad CSS replacement in this pass.

---

# 1. Correct registry source precedence

## Problem

The merged catalog correctly marks a same-name external theme as the selected descriptor, but the loader independently searches bundled files before external files. This can return bundled content while reporting an external descriptor.

## Required change

Eliminate independent source re-resolution after descriptor selection.

Preferred design:

```python
@dataclass(frozen=True, slots=True)
class ThemeCatalogEntry:
    descriptor: ThemeDescriptor
    file_info: ThemeFileInfo
```

Store the authoritative `ThemeFileInfo` alongside each catalog entry during `_rebuild_catalog()`. Then:

- `resolve()` returns or internally locates the selected catalog entry;
- `load()` reads exactly the `file_info` selected by catalog precedence;
- external override precedence cannot diverge between metadata and content;
- loading does not rescan both sources merely to rediscover the file.

If preserving the public `ThemeDescriptor` API, use an internal `_CatalogEntry` and return only its descriptor publicly.

Do not merely reverse `_find_file_info()` order. Tying the descriptor and source object together is safer and prevents future precedence drift.

## Required tests

Create two visibly different themes with the same name:

- bundled copy uses one unmistakable background/accent;
- external copy uses another.

Assert that:

- `resolve()` reports external;
- `load()` returns the translated external colors;
- `LoadedTheme.descriptor.source` matches the source actually read;
- removing the external file and invalidating restores the bundled translated colors;
- provenance and diagnostics correspond to the loaded source.

## Acceptance criteria

- No code path can report one source while reading another.
- External same-name themes override bundled content end-to-end.
- Novel external themes continue to load.
- Removing an override restores the bundled file after refresh.

---

# 2. Fix cache freshness validation

## Problem

The current cache validates an entry using the cached entry's own stored `mtime` and size, making validation tautological. External edits and deletions can remain stale indefinitely.

## Required change

Validate cache entries against current source metadata.

Recommended flow:

1. resolve the authoritative catalog entry;
2. obtain current source identity and metadata;
3. compare current metadata to the cached entry;
4. return the cache hit only when identity and freshness match;
5. otherwise evict and reload.

Cache identity should include:

- canonical name;
- source type;
- stable source identifier;
- external root identity where relevant;
- file size;
- nanosecond modification time where available;
- translation schema/version.

For packaged resources that do not expose meaningful filesystem mtimes, use a deterministic resource fingerprint. Acceptable options:

- content hash computed once during catalog construction;
- manifest-provided hash validated against resource bytes;
- immutable package version plus filename when packaged resources are guaranteed immutable for process lifetime.

External files should use `st_mtime_ns` rather than floating-point seconds. Consider a content hash when size/mtime equality could miss rapid replacement on coarse filesystems.

Refactor `ThemeCache.validate_entry()` so callers pass current source metadata, not values copied from the cached object.

## Required tests

- First load populates cache.
- Second unchanged load returns cached objects or avoids reparsing.
- Editing an external file changes loaded tokens without full process restart.
- Replacing external content with the same byte length still invalidates.
- Deleting an external override restores bundled content after refresh/automatic validation according to documented behavior.
- Changing source from bundled to external with the same name invalidates the bundled cache key.
- Changing translation schema invalidates prior entries.

Use parser call-count instrumentation or monkeypatching to prove warm loads avoid reparsing and changed files do reparse.

## Acceptance criteria

- Cache hits are accepted only after comparison with current source state.
- External edits are observable without process replacement.
- Same-size replacements do not remain stale.
- Warm unchanged loads avoid repeated parsing.
- Bundled caches remain stable and bounded.

---

# 3. Correct named invalidation semantics

## Problem

`invalidate(name)` removes an entry from the current catalog while leaving the catalog marked initialized. Subsequent lookup can permanently miss that name until a full invalidation occurs.

## Required change

Choose one explicit policy:

### Preferred simple policy

For any named invalidation:

- evict all cache variants for that canonical name;
- set the catalog to `None` so the next lookup rebuilds deterministically.

The catalog is small; a complete rescan is safer than partial mutation.

### Alternative

Rebuild only the affected catalog entry from both bundled and external sources, preserving correct precedence and collision behavior. Use this only if the implementation remains straightforward and fully tested.

Normalize or resolve the requested name before invalidating. Named invalidation should work with case-insensitive lookup only if `resolve()` supports it consistently.

## Required tests

Add a test that actually calls:

```python
registry.invalidate("Dracula")
```

Assert:

- the theme remains resolvable after rebuild;
- an external override removed from disk reveals bundled content;
- an external override added after initial listing becomes selected;
- cache entries for both prior bundled/external variants cannot leak through;
- unrelated themes remain available.

Rename any existing test whose name does not match its behavior.

## Acceptance criteria

- Named invalidation never leaves the catalog in a partially deleted state.
- Refreshing one theme correctly re-evaluates source precedence.
- Tests exercise the named API, not only full invalidation.

---

# 4. Normalize canonical-name semantics

## Problems

- `validate_theme_name()` returns a stem, but callers discard it.
- names with `.toml` can validate and then fail lookup;
- the default theme identifier does not match the packaged canonical name;
- filename, canonical name, display name, and compatibility aliases are not clearly separated.

## Required change

Define one canonical-name policy and apply it everywhere.

Recommended policy:

- canonical name is the exact validated filename stem, preserving spaces and case as stored;
- lookup supports exact canonical name and case-insensitive matching;
- `.toml` suffix is either rejected explicitly or stripped consistently before lookup;
- punctuation transformations such as hyphen-to-space are not performed implicitly;
- display labels are separate presentation metadata;
- legacy names and configuration aliases are resolved through an explicit alias map.

Refactor name validation into a function whose return value is always consumed:

```python
def normalize_theme_name(name: str) -> str:
    ...
```

or make validation return `None` and reject suffixes if no normalization is desired.

Correct the registry default to an actual packaged canonical name, for example:

```python
default_theme="Catppuccin Mocha"
```

Alternatively, use a known-good bundled fallback whose canonical name is verified by a test.

Add an explicit alias table for planned legacy migration, but do not implement database migration yet. Example aliases may include:

```text
catppuccin-mocha -> Catppuccin Mocha
github-dark -> chosen bundled equivalent
solarized-dark -> Solarized Dark
```

Do not use broad punctuation normalization that could collapse distinct theme names.

## Required tests

- exact canonical lookup;
- case-insensitive lookup;
- `.toml` suffix behavior;
- default fallback resolves to a packaged theme;
- explicit aliases resolve;
- unknown punctuation variants do not accidentally resolve;
- invalid separators/control characters remain rejected;
- names with spaces and parentheses resolve correctly.

## Acceptance criteria

- Validation/normalization return values are consumed consistently.
- The configured/default fallback resolves to a real bundled theme.
- Canonical, display, filename, and alias concepts are explicit.
- No accidental punctuation-based collisions are introduced.

---

# 5. Complete package-resource abstraction

## Problem

The project contains an `importlib.resources` discovery helper, but the default registry still uses a filesystem-relative `Path` and file reads. Package-resource discovery is not the actual default loading path.

## Required change

Make packaged resources first-class source objects rather than converting them prematurely to filesystem `Path` values.

Refactor `ThemeFileInfo` or introduce a source abstraction capable of reading bytes from:

- filesystem paths for external themes;
- `importlib.resources.abc.Traversable` for bundled themes.

Possible design:

```python
@dataclass(frozen=True, slots=True)
class ThemeResource:
    canonical_name: str
    filename: str
    source: ThemeSource
    size_bytes: int
    fingerprint: str
    filesystem_path: Path | None
    traversable: Traversable | None

    def read_bytes(self) -> bytes:
        ...
```

Requirements:

- the default `ThemeRegistry()` discovers bundled resources through `importlib.resources.files()`;
- external themes continue to use hardened filesystem containment checks;
- loading uses the source object's `read_bytes()` method;
- bundled resources do not require `Path(str(traversable))` to be valid;
- tests can inject a temporary filesystem bundled root where useful, but production default uses package resources.

Retain a filesystem bundled-root option only as an explicit test/development override.

## Required tests

- default registry lists bundled themes without passing a filesystem root;
- default registry loads dark and light themes;
- bundled loading succeeds from a wheel-installed package outside the repository;
- source code contains no default `Path(__file__).parent / "bundled"` dependency for production discovery;
- external override still wins over package resources;
- a non-filesystem or traversable test double can be read without path conversion if practical.

## Acceptance criteria

- `importlib.resources` is the production default, not an unused helper.
- Bundled loading is decoupled from repository/install layout.
- External security controls remain unchanged.

---

# 6. Build and verify real release artifacts

## Problem

Current tests inspect source files and packaging configuration but do not build/install a wheel or verify an sdist in isolation.

## Required change

Add a true artifact smoke test or release script.

### Wheel verification

1. build a wheel using the project's standard build command;
2. create an isolated virtual environment or isolated import target;
3. install the wheel without the source tree on `PYTHONPATH`;
4. change working directory outside the repository;
5. import `app.themes`;
6. instantiate the default registry;
7. assert the exact bundled catalog set/count;
8. load at least one dark and one light theme;
9. verify manifest and attribution resources are accessible;
10. verify an external temporary theme can extend and override the installed catalog.

### Source-distribution verification

Build the sdist and inspect/archive-test that it contains:

- all approved theme TOML files;
- `catalog_manifest.json`;
- `ATTRIBUTION.md`;
- required Python modules;
- no unintended dependency on the top-level source catalog at runtime.

Where CI runtime makes full virtualenv installation expensive, separate tests into:

- fast archive-content assertions in normal CI;
- isolated install smoke test in release/package CI.

However, at least one automated workflow must actually install and import the built wheel.

## Required files

Likely additions or updates:

- `tests/themes/test_build_artifact.py` rewritten to build/inspect real artifacts;
- `scripts/verify_theme_package.py` or equivalent reusable verifier;
- CI workflow/package job;
- build-system dependency declaration if `python -m build` is not already available.

## Acceptance criteria

- Wheel resources are proven present after installation.
- Default registry works outside the repository root.
- Sdist contents are verified.
- External override behavior works against installed bundled resources.
- Artifact verification is automated, not a manual release note.

---

# 7. Strengthen end-to-end regression coverage

## Required additions

Add tests that exercise the full chain:

```text
catalog discovery -> precedence -> source read -> Halloy parse -> translation -> CSS output -> cache -> refresh
```

Minimum scenarios:

1. bundled theme load;
2. novel external theme load;
3. same-name external override with content assertion;
4. external edit with same size;
5. external deletion restoring bundled;
6. malformed external override falling back or reporting failure according to policy;
7. invalid default selecting valid packaged fallback;
8. named invalidation;
9. full invalidation;
10. case collision handling;
11. names with spaces and parentheses;
12. installed-wheel registry load.

Tests should assert meaningful translated values or source fingerprints, not only descriptor flags.

Add targeted tests for emergency fallback output. The emergency `LoadedTheme` should provide usable CSS and variable mappings rather than empty strings/maps unless callers explicitly generate them later. Prefer consistency:

- `css` should serialize `EMERGENCY_DEFAULT`;
- `css_vars` and `legacy_vars` should be populated;
- diagnostics should identify emergency fallback.

## Acceptance criteria

- Every defect identified in the repository review has a failing-before/fixed-after regression test.
- Tests verify content/source consistency.
- Emergency fallback is immediately renderable.

---

# 8. Error and logging cleanup

## Required change

Preserve structured internal errors and avoid collapsing all failures into generic `ValueError` where callers need to distinguish:

- invalid name;
- not found;
- unreadable source;
- parse failure;
- translation failure;
- fallback activation.

Introduce registry-level exception types or return structured failure information. Public/runtime integration later can map these to safe fallback behavior.

Logging requirements:

- malformed bundled resource: error-level release/package problem;
- malformed external resource: warning-level operator problem;
- fallback activation: warning with canonical requested/default names;
- no public metadata or future template context exposes absolute external paths;
- logs may include operator paths only under existing repository logging/privacy conventions.

## Acceptance criteria

- Tests can distinguish failure categories without string parsing.
- Public descriptors remain path-free.
- Fallback reasons are observable.

---

# 9. Documentation and plan status reconciliation

## Required change

Update relevant documentation after fixes:

- roadmap phase status;
- Phase 04 and Phase 05 plan completion notes;
- architecture overview;
- theme contract/resource behavior;
- agent/skill documentation;
- packaging/release test documentation.

Document:

- exact external override precedence;
- cache refresh behavior;
- canonical-name and alias policy;
- default theme canonical name;
- installed package-resource behavior;
- wheel/sdist verification command;
- external edit visibility guarantees.

Do not mark Phases 04–05 complete until all closure acceptance criteria pass.

---

# 10. Validation sequence

Run the following in order:

1. focused theme registry/security/cache tests;
2. catalog-wide parser and translation tests;
3. full theme test suite;
4. lint and formatting checks;
5. type checking;
6. full repository test suite with coverage threshold;
7. wheel build and isolated install smoke test;
8. sdist content verification;
9. container build or packaging smoke test where supported;
10. final repository diff/stale-reference audit.

Record exact commands and results in the implementation commit or closure notes.

No CI statuses were visible during the review, so the implementation agent must explicitly verify whether GitHub Actions is configured to run these checks on direct pushes and pull requests. Add or repair a package-verification job if needed.

---

# Files likely to change

Primary:

- `app/themes/registry.py`;
- `app/themes/resources.py`;
- `app/themes/cache.py`;
- `app/themes/__init__.py`;
- tests under `tests/themes/`;
- packaging verification scripts/workflows.

Possible supporting changes:

- `app/themes/model.py` or serializers for emergency fallback consistency;
- `catalog_manifest.json` if hashes/fingerprints are added;
- `pyproject.toml` build-system/package metadata;
- CI workflow files;
- architecture and theme documentation;
- roadmap/plan status notes.

Avoid changes to:

- `SiteSettings` database schema;
- current Jinja theme integration;
- admin theme forms;
- public dark/light JavaScript;
- broad CSS tokenization.

---

# Definition of done

This corrective closure pass is complete only when:

- external override descriptors and loaded content always identify the same source;
- cache validation compares against current source state;
- same-size external edits are detected;
- named invalidation rebuilds correctly;
- canonical-name normalization and alias behavior are explicit and tested;
- the registry default resolves to a real packaged theme;
- default bundled discovery/loading uses `importlib.resources`;
- wheel installation works outside the repository tree;
- sdist contents are verified;
- external themes extend and override an installed catalog;
- emergency fallback emits complete usable CSS and mappings;
- all identified defects have regression tests;
- full lint, type, test, coverage, and artifact checks pass;
- Phases 04 and 05 documentation accurately reflects completion;
- Phase 06 can integrate the registry without compensating for unresolved backend defects.

Until these criteria are met, leave the legacy theme preset system as the runtime authority.
