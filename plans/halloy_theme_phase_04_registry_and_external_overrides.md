# Halloy Theme Phase 04 — Safe Registry and External Overrides

> **Status: COMPLETE**

## Objective

Implement the authoritative theme registry that discovers bundled themes, merges an optional external theme directory, resolves names safely, loads and translates themes, caches results, and applies deterministic fallback behavior.

This phase establishes the runtime resource boundary but does not yet replace the current Flask/Jinja theme integration.

## Dependencies

Requires:

- Phase 01 resource and naming decisions;
- Phase 02 parser and validated color model;
- Phase 03 translator and `BlogTheme` CSS serialization.

## Proposed module shape

```text
app/themes/
  registry.py
  resources.py
  cache.py
```

A single module is acceptable if responsibilities remain explicit and testable.

## Required public API

Provide a narrow service API similar to:

```python
class ThemeRegistry:
    def list_themes(self) -> list[ThemeDescriptor]: ...
    def resolve(self, name: str) -> ThemeDescriptor | None: ...
    def load(self, name: str) -> LoadedTheme: ...
    def invalidate(self, name: str | None = None) -> None: ...
```

`ThemeDescriptor` should expose only safe public metadata:

- canonical theme name;
- display name;
- source (`bundled` or `external`);
- whether it overrides a bundled theme;
- dark/light classification when already known;
- validation or translation status;
- safe warning summary.

Do not expose absolute paths in template/public metadata.

## Required implementation work

### 1. Define safe theme names

Use a strict allowlist matching the actual catalog established in Phase 01. Theme names may support spaces, parentheses, dots, underscores, and hyphens only if required by checked-in themes.

Reject:

- empty names;
- `/` and `\\`;
- `..` path segments;
- absolute paths;
- NUL/control characters;
- percent-encoded separator tricks after appropriate decoding boundaries;
- names outside the documented maximum length.

Theme identity should be based on a validated filename stem. Display labels may be derived separately.

### 2. Discover bundled resources

Use `importlib.resources` abstractions rather than repository-relative `Path` assumptions. The registry should work when resources are inside an installed wheel or zip-compatible package representation.

Bundled discovery must:

- inspect only the package's designated theme resource directory;
- include regular `.toml` resources;
- ignore unrelated files;
- sort deterministically;
- isolate malformed files from catalog enumeration where possible while recording failure metadata.

The exact resources may not be moved until Phase 05; provide test fixtures or an injectable resource root so registry behavior can be implemented first.

### 3. Discover external themes

Support an optional configured external directory.

Rules:

- no recursive discovery;
- only regular `.toml` files;
- enforce the documented maximum file size;
- resolve the external root once;
- ensure candidates remain inside the resolved root;
- reject symlink escapes;
- ignore directories, devices, FIFOs, and sockets;
- handle unreadable files without failing the entire catalog;
- deterministic ordering.

If the directory is absent or unreadable, log/report a registry warning and continue with bundled themes.

### 4. Implement precedence

Merge by validated canonical name:

1. external theme;
2. bundled theme.

A same-name external theme overrides the bundled theme. `ThemeDescriptor` must identify this state. Removing the external file should reveal the bundled theme after invalidation/rescan.

Case-collision behavior must be explicit and safe across macOS/Linux filesystems. Prefer rejecting ambiguous collisions rather than choosing nondeterministically.

### 5. Load and translate themes

Loading flow:

1. validate requested name;
2. resolve descriptor according to precedence;
3. enforce file/resource size limit;
4. parse Halloy TOML;
5. translate to `BlogTheme`;
6. produce CSS/mapping;
7. cache loaded result;
8. return structured metadata and warnings.

Do not permit a request-supplied arbitrary path. The loader accepts registry names only.

### 6. Implement fallback semantics

The registry/service should support a caller-provided configured default plus a built-in known-good bundled fallback and Phase 03's emergency theme.

Return structured information indicating whether fallback occurred and why. Logging should include operator-useful details, while public metadata must redact sensitive paths and raw internal exceptions.

Avoid recursive fallback loops when the configured default itself is invalid.

### 7. Add caching

Cache at least:

- merged theme catalog;
- parsed Halloy themes;
- translated `BlogTheme` values;
- generated CSS.

Cache identity should account for:

- theme name;
- source type;
- external directory identity;
- external file modification time and size or a content signature;
- translation schema/version.

Warm loads should not reread TOML. External edits must become visible after explicit invalidation and preferably through metadata revalidation.

Keep cache implementation bounded. There are only dozens of themes; a simple in-process cache is preferable to introducing Redis or database storage.

### 8. Add observability

Use existing logging conventions. Record:

- malformed bundled theme as an application/release error;
- malformed external theme as an operator configuration warning;
- invalid configured/requested name;
- fallback activation;
- external override activation;
- cache refresh failures.

Do not log full file contents.

## Files expected to change

Likely:

- `app/themes/registry.py`;
- `app/themes/resources.py`;
- `app/themes/cache.py` or equivalent;
- `tests/themes/test_registry.py`;
- `tests/themes/test_theme_resolution_security.py`;
- temporary test resource packages/fixtures.

## Testing requirements

Add tests for:

- bundled-only listing;
- external-only additions;
- same-name external override;
- override removal revealing bundled theme;
- missing external directory;
- unreadable or malformed external theme isolation;
- traversal and absolute-path rejection;
- symlink escape rejection;
- case-collision rejection;
- file-size limit;
- warm-cache behavior;
- invalidation after modification;
- configured-default and emergency fallback;
- no absolute path leakage in public descriptors/errors.

Use temporary directories and avoid platform-specific assumptions where possible. Mark symlink tests appropriately on platforms lacking support, but do not omit containment coverage.

## Acceptance criteria

- One registry API is the authoritative name-to-theme boundary.
- Bundled and external catalogs merge deterministically.
- External themes extend the catalog and override same-name bundled themes.
- Traversal, separators, absolute paths, and symlink escapes are blocked.
- Malformed external themes do not break unrelated themes or public rendering callers.
- Warm loads avoid repeated parsing.
- Explicit invalidation exposes external edits/removals.
- Fallback behavior is deterministic and nonrecursive.
- Registry metadata is safe for admin/template use.

## Non-goals

- changing `SiteSettings`;
- replacing `THEME_PRESETS` in rendering;
- admin forms;
- visitor color-scheme behavior;
- final wheel packaging, which is Phase 05.

## Handoff notes

Phase 05 must connect this registry to actual package resources and prove installation behavior. Later runtime phases should call the registry rather than adding independent file resolution helpers.
