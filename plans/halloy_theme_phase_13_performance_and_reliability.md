# Halloy Theme Phase 13 — Performance, Caching, and Reliability

> **Plan status: HISTORICAL — shipped.** The outcome is documented in [architecture/core/themes.md](../architecture/core/themes.md); this file is the historical record.

## Objective

Make the Halloy theme subsystem operationally cheap, deterministic, and resilient under normal request load, external theme changes, database failures, and multi-worker deployment.

This phase should optimize measured bottlenecks only. The catalog is small, so prefer simple in-process structures over distributed cache infrastructure.

## Baseline measurements

Add benchmarks for:

- cold registry construction;
- bundled catalog enumeration;
- external directory scan with representative file counts;
- cold parse/translate/serialize;
- warm theme load;
- theme service context generation with and without settings cache;
- base template render overhead;
- admin catalog page render;
- registry refresh.

Record environment and percentile methodology. Establish practical thresholds rather than microbenchmarking implementation details.

## Cache contract

Document and enforce the freshness model.

Recommended first-release contract:

- bundled resources are immutable for the process lifetime;
- external changes become visible after explicit registry refresh/invalidation;
- admin and CLI refresh are authoritative;
- ordinary warm requests perform no filesystem reads or TOML parsing;
- settings updates explicitly invalidate the app-scoped context cache.

If automatic external detection remains supported, refresh current metadata/content before accepting a cache hit and test same-size/same-timestamp edge cases. Do not claim automatic freshness unless it is actually implemented.

## App-scoped lifecycle

Ensure registry and settings caches are owned by the Flask application, not shared accidentally across separately configured app instances.

Verify:

- one registry per app process;
- safe concurrent reads under WSGI threads;
- refresh does not expose a partially rebuilt catalog;
- tests can instantiate multiple apps independently;
- workers converge after explicit operator refresh/restart according to documented behavior.

For multi-worker deployments, document that an in-process refresh affects one worker unless the deployment control path broadcasts/restarts workers. Do not imply cross-process invalidation without implementation.

## Failure resilience

Test and harden behavior for:

- database unavailable during context generation;
- missing settings row;
- configured theme removed;
- malformed external override;
- unreadable external directory;
- packaged resource missing or corrupt;
- concurrent refresh and render;
- custom CSS sanitation failure;
- registry refresh failure.

Public rendering must use the known-good emergency Halloy context rather than fail with HTTP 500.

## Logging and observability

Add structured, rate-conscious logging for:

- fallback activation;
- malformed bundled versus external files;
- configured theme disappearance;
- refresh summaries;
- cache invalidation;
- cold-load latency above threshold.

Avoid logging every warm lookup or full filesystem paths in public-facing contexts.

Expose optional diagnostic counters through existing metrics/logging conventions where appropriate:

- catalog size;
- external override count;
- cache hit/miss count;
- fallback count;
- refresh count/failure count.

## Resource limits

Confirm and test:

- maximum external file size;
- maximum theme name length;
- bounded catalog/cache growth;
- no recursive scanning;
- no repeated parsing from malformed requests;
- CSS response/preview size limits.

## Concurrency testing

Add deterministic tests that run concurrent:

- `get_context()` calls;
- registry loads;
- refresh plus reads;
- settings invalidation plus reads.

Assert no partial results, deadlocks, or cross-app leakage.

## CI and benchmark policy

Keep correctness tests mandatory. Performance thresholds should allow normal CI variance while catching order-of-magnitude regressions.

Suggested goals:

- warm request theme lookup performs no disk access;
- warm context retrieval is negligible relative to template rendering;
- 50-theme catalog refresh remains comfortably subsecond on ordinary hardware;
- cold translation remains bounded and occurs outside hot request loops.

## Acceptance criteria

- cache/freshness behavior is explicit and accurately tested;
- warm request rendering performs no TOML parsing or external scans;
- app instances are isolated and concurrent reads are safe;
- public pages survive database, resource, and custom-theme failures;
- refresh behavior is documented for multi-worker deployments;
- benchmark suite and reliability tests prevent material regressions.
