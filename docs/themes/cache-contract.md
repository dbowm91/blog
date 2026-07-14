# Cache Freshness Contract

This document defines the cache lifecycle, freshness boundaries, and invalidation API for the Halloy theme system.

## Overview

The theme system uses two in-process caches: a **catalog cache** (registry-level mapping of theme names to file metadata) and a **load cache** (parsed + translated `LoadedTheme` results). Both are lazily initialized, thread-safe for concurrent reads, and refreshed only through explicit invalidation calls. No filesystem polling occurs at any level.

## Bundled Resources

- **Immutable for process lifetime.** Bundled themes ship inside the Python package (`app/themes/bundled/`). Once the catalog is built, the set of bundled themes cannot change without a restart or explicit invalidation.
- **Fingerprinted via SHA-256 hash of file content.** The `_compute_fingerprint()` function in `registry.py` uses `hashlib.sha256(data).hexdigest()` for bundled sources, producing a 64-character hex string that changes with any content modification.
- **Changes require explicit `invalidate()` or `invalidate(name)`.** Because the package resources are loaded via `importlib.resources`, the cache assumes content is stable for the process lifetime. A content change (e.g., in a development environment after reinstalling the package) must be followed by an explicit invalidation call.

## External Resources

- **Changes become visible after explicit registry refresh/invalidation.** External theme files are discovered from a configurable directory (`external_root`). The catalog records `mtime` and `size` at discovery time, but does not re-stat the filesystem on subsequent loads.
- **No automatic filesystem polling.** There is no background thread, inotify watcher, or periodic re-stat. External file edits, additions, or deletions remain invisible until the caller triggers invalidation.
- **Admin and CLI refresh are authoritative.** The admin settings page and CLI commands call `service.invalidate_registry()` or `service.refresh_registry()`, which rebuild the catalog and evict affected cache entries.
- **Cache entries validated against current mtime/size/fingerprint.** On each `load()` call, the registry checks the cache entry's stored fingerprint against the catalog's current file metadata. For external themes, the fingerprint is `"{mtime}:{size}"`. A mismatch causes a re-parse from disk.

## Hot Path Behavior

| Operation | Cost |
|-----------|------|
| Warm request (cache hit) | O(1) dict lookup + mtime/size comparison, no filesystem reads, no TOML parsing |
| Cache miss | `read_bytes()` → `parse_halloy_theme_bytes()` → `translate_halloy_theme()` → `to_css_variables()` → cache store |
| Catalog build (first `list_themes()` or `resolve()`) | `scandir` + `stat` for each candidate file, no TOML parsing |

Ordinary warm requests for an already-loaded theme perform no I/O. The cache entry is validated by comparing stored mtime/size against the catalog's current metadata (no disk read required). If both match, the cached result is returned immediately. A mismatch (e.g., after an external file edit followed by invalidation and catalog rebuild) causes a cache miss and re-parse from disk.

## Settings Cache

The `ThemeService` maintains a separate **settings context cache** that caches the fully-resolved context dict (dark/light theme names, CSS variables, scheme, etc.) consumed by the template context processor.

- **TTL-based fallback.** The cache has a 300-second TTL (`_SETTINGS_CACHE_TTL` in `service.py:29`). After expiry, the next `get_context()` call re-reads `SiteSettings` from the database.
- **Explicit invalidation.** `service.invalidate_settings_cache()` immediately clears the cache, forcing a fresh database read on the next request.
- **Distinct from the registry cache.** The settings cache stores the final rendered context; the registry cache stores parsed theme data. Invalidating one does not automatically invalidate the other.

## Multi-Worker Deployment

- **In-process refresh affects one worker only.** `ThemeService` and `ThemeRegistry` are process-local singletons. Calling `invalidate()` on one worker's registry leaves other workers' caches untouched.
- **Deployment control path must broadcast/restart workers for cross-process invalidation.** To propagate theme changes across all replicas, the deployment must restart the application process (e.g., `docker compose restart blog`) or use a shared control mechanism that triggers invalidation on each worker.
- **Do not imply cross-process invalidation without implementation.** The current system has no IPC, shared-memory cache, or message bus for cross-process invalidation. Each process is an independent cache domain.

## Invalidation API

### Registry-Level (`ThemeRegistry`)

| Method | Scope | Effect |
|--------|-------|--------|
| `registry.invalidate()` | Full | Clears all cache entries and sets catalog to `None`. Next `list_themes()`, `resolve()`, or `load()` triggers a full catalog rebuild from disk/package resources. |
| `registry.invalidate(name)` | Single theme | Evicts cache entries matching the resolved theme name (via `invalidate_prefix`). Sets catalog to `None` for rebuild. |

### Service-Level (`ThemeService`)

| Method | Scope | Effect |
|--------|-------|--------|
| `service.invalidate_registry()` | Delegates to registry | Calls `registry.invalidate()` with the same signature. Pass `name` to invalidate a single theme, or `None` for all. |
| `service.invalidate_registry(name)` | Single theme | Delegates to `registry.invalidate(name)`. |
| `service.refresh_registry()` | Atomic full replace | Acquires `_registry_lock`, discards the old registry, creates a new `ThemeRegistry`. Entirely replaces the old instance. Thread-safe under the lock. |
| `service.invalidate_settings_cache()` | Settings context | Clears `_settings_cache` and resets `_settings_cache_time`. Next `get_context()` re-reads from the database. |

### Cache-Level (`ThemeCache`)

| Method | Scope | Effect |
|--------|-------|--------|
| `cache.invalidate(key)` | Single entry | Removes one entry by key. |
| `cache.invalidate()` | Full | Clears all entries (`dict.clear()`). |
| `cache.invalidate_prefix(prefix)` | Name-based | Removes all entries whose key ends with `":{prefix}"`. Used to evict both `bundled:{name}` and `external:{name}` variants. |
| `cache.clear()` | Full | Alias for `invalidate(None)`. |
| `cache.validate_entry(key, mtime, size, fingerprint)` | Validation | Returns `True` if the stored entry's `source_fingerprint` matches the provided `current_fingerprint`. For external themes where `current_fingerprint` is `None`, falls back to mtime+size comparison. |

## Fallback Chain

When a theme cannot be loaded, the system follows a fallback chain:

```
configured theme → default theme → emergency-default
```

1. **Configured theme** — the name from `SiteSettings` (e.g., `"Catppuccin Mocha"`).
2. **Default theme** — the `default_theme` parameter passed to `ThemeRegistry` (defaults to `"Catppuccin Mocha"`).
3. **Emergency default** — a hardcoded `BlogTheme` + `HalloyTheme` constructed in `_emergency_halloy_theme()`. This never fails; it performs no file I/O and no TOML parsing.

Each step catches `ThemeNotFoundError`, `ThemeParseFailure`, and `ThemeLoadError` before advancing to the next candidate. The emergency fallback logs a warning and returns a valid `LoadedTheme` with `status="fallback"`.

The `get_fallback()` method is called by `ThemeService._load_with_fallback()` whenever `registry.load()` raises one of the three exception types.

## Testing Expectations

Cache behavior should be verified by the following test patterns:

| Behavior | How to verify |
|----------|---------------|
| **Cache hit** | Load the same theme twice. Second `load()` returns the same `LoadedTheme` object (identity check via `is`). |
| **Warm path does no I/O** | Load a theme, then mock `_compute_fingerprint` and `parse_halloy_theme_bytes`. Load again. Mocks are not called — no bytes are read and no parsing occurs. |
| **Invalidation forces re-read** | Load a theme, call `invalidate(name)`, load again. The second load reads bytes from disk (mock `read_bytes` to assert call count). |
| **Fingerprint mismatch triggers re-parse** | Load a theme, modify the file's mtime/size, call `invalidate(name)`, load again. The cache entry is rebuilt. |
| **Fallback chain** | Configure a nonexistent theme name. Verify `get_fallback()` returns the default, then emergency if the default is also broken. |
| **Concurrent reads are safe** | Load the same theme from multiple threads simultaneously. No exceptions, no corruption, all threads receive valid `LoadedTheme` results. |
| **Settings cache TTL** | Call `get_context()`, advance time past `_SETTINGS_CACHE_TTL`, call again. Verify the second call re-reads from the database. |
| **`refresh_registry()` is atomic** | Call `refresh_registry()` while another thread is calling `load()`. The lock ensures no partial state is observed. |

## Summary: Invalidation Methods at a Glance

| Method | Clears load cache | Rebuilds catalog | Clears settings cache | Cross-process |
|--------|:-:|:-:|:-:|:-:|
| `registry.invalidate()` | Yes (all) | Yes | No | No |
| `registry.invalidate(name)` | Yes (one) | Yes | No | No |
| `service.invalidate_registry()` | Delegates | Delegates | No | No |
| `service.invalidate_registry(name)` | Delegates | Delegates | No | No |
| `service.refresh_registry()` | Yes (replaces registry) | N/A (new instance) | No | No |
| `service.invalidate_settings_cache()` | No | No | Yes | No |
| Process restart | Yes (new process) | Yes (new process) | Yes (new process) | Yes |
