# Project Pages Phase 06 — Opt-in Binary Mirrors and Installer Distribution

> **Plan status: MANIFEST-ONLY; binary mirrors deferred.** See [project_pages_roadmap.md](project_pages_roadmap.md).

**Date:** 2026-10-28
**Plan ID:** PROJ-06
**Status:** DevLog-native metadata manifest implemented; mirrors deferred by operator decision
**Prerequisite:** Phase 05 release metadata implemented and proven stable.

## Objective

Permit selected GitHub release assets to be mirrored by the blog, and optionally expose a stable machine-readable software distribution interface. **GitHub remains canonical** for upstream version/release identity and remains a working download fallback. Mirroring is off by default, controlled per site/project and limited by storage/bandwidth policy.

## Before implementation: evidence gate

Inspect the actual eggpack and eggup repositories, install/update manifest specifications, platform-triplet vocabulary, digest/signature requirements, canonical-host assumptions and update/rollback expectations. Record exact compatible versions, URLs/schemas, fixtures and ownership boundaries. If unavailable, implement only an explicitly versioned DevLog release manifest, **not** an endpoint claiming installer compatibility. An adapter must be validated end-to-end with a real installer before exposing an eggpack/eggup-specific endpoint.

Choose an explicit target environment and delivery architecture: local storage + reverse proxy offload, or S3/object storage + signed/presigned redirects. Confirm backup and retention policy and acceptable bandwidth/storage use before enabling mirroring.

## Model and artifact contract

Extend `ProjectReleaseAsset` or create `ProjectArtifactMirror` keyed to immutable upstream provider asset ID and content identity: project/release/asset FK, canonical GitHub source, upstream size/digest if supplied, expected bytes, verified SHA-256, storage key, state (`pending|downloading|verified|failed|retired`), verified time, last attempt/error, and content type. Never mark verified from filename or metadata alone.

Add global and per-project enable flags, max total GiB, max individual file size, concurrency/throughput, retention age and request quotas with safe defaults. Reject arbitrary admin-supplied fetch URLs; only a known asset from a release synchronized in Phase 05 can be queued.

Mirror bytes outside image `/static/uploads`, with an explicit project/artifact namespace and no executable content served inline. Integrate with `app/filesystem/layout.py` (managed data paths) and storage backend configuration. Existing `app/storage.py` `save(filename, data: bytes)` and `load() -> bytes` are whole-buffer APIs and must **not** be used to buffer large binaries into memory; provide a separate streaming artifact interface with bounded memory/disk usage.

## Transfer, verification and publication

The transfer worker fetches only source-bound GitHub assets with a fixed allowed-host policy, DNS/IP validation where applicable, bounded redirects, timeouts, content-length limits, retry/backoff and cancellation. Stream into a private temporary file/object, hash bytes incrementally, enforce configured size quotas and storage limits, then publish atomically only when complete and verified. Prefer immutable hash-addressed objects and preserve upstream ID + tag provenance. Reject unexpected content, stale/mutated asset identity or mismatched checksum.

Do not overwrite a verified asset on changed tag metadata. An upstream replacement yields a new candidate and a controlled supersession policy. A failed/incomplete transfer never becomes visible as downloadable.

Implement `HEAD` and `GET` support with appropriate Content-Type (`application/octet-stream` default), `Content-Disposition: attachment`, content-length, ETag, cache headers, byte-range (`206`/`416`) and no content sniffing. Avoid giant Flask streaming responses when reverse-proxy file serving or object-storage redirects are available. Preserve GitHub fallback when mirror is missing, failed, disabled or retired; never generate fake healthy mirror links.

## Machine-readable distribution and trust

Use a documented, versioned release-manifest contract with precise platform and architecture identifiers, immutable version/tag, source GitHub URL, mirror URL only when verified, size, SHA-256 and optional upstream digital signatures. Signatures and checksums are separate properties; DevLog must not claim to have authenticated an upstream signer merely because it computed a hash.

Only publish an eggpack/eggup-specific manifest once the concrete installer protocol has been verified, including compatibility fixtures and an installer test using the emitted manifest. A generic feed is fine earlier, but it must be labeled DevLog-native. Respect installer cache semantics, rollback/version pinning and immutable artifact URLs.

## Scheduler and operations

Use bounded scheduled or manually triggered mirroring without requiring new services on ordinary blog installations. Scheduler work must respect the documented single-instance APScheduler rule, or use a safe DB-backed idempotent job claim. Provide admin controls for sync status, retry, removal, reserved bytes, capacity and last verification. Explicitly keep GitHub as source of truth when local artifacts are evicted.

Separate backups: DB metadata is backed up with the existing DB backup service; local mirror bytes need a distinct recoverable storage/manifest plan or may be treated as safely reconstructible with documented resync steps. Never assume the current SQLite backup includes mirrored files.

## Tests and acceptance

1. Feature disabled by default: no artifacts downloaded or background worker started; no new dependencies necessary for blog-only mode.
2. Mock a large binary stream and verify bounded process RSS, incremental SHA-256, atomic publish and correct cleanup on network cutoff, timeout, disk full, quota exhaustion, digest mismatch and process restart.
3. Verify correct `GET`/`HEAD`, 200/206/416 Range semantics, ETag, attachment headers, secure MIME and reverse proxy/object-storage handoff.
4. SSRF/redirect/private-address, path traversal, symlink/TOCTOU, untrusted asset URL and duplicate/concurrent-sync defenses have adversarial tests.
5. GitHub direct URL remains usable whenever mirror is unavailable; no broken download action when mirror state is `pending` or `failed`.
6. Build a real installer protocol compatibility fixture for every advertised eggpack/eggup variant. Validate manifest parsing and end-to-end artifact checks, not just JSON field equality.
7. Verify retention/eviction, backup/recovery, telemetry and graceful migration downgrade. Document operator bandwidth, storage, security and update assumptions.

**Likely files:** dedicated `app/services/project_artifacts.py` and streamed artifact backend; `app/filesystem/layout.py` integration; models/migration; admin management UI; download/public manifest route; scheduler or job adapter; reverse-proxy/storage settings; tests and operator docs.

## Go/no-go criteria

Do not ship mirroring before streaming delivery, content integrity, safe canonical fallback, storage quotas and operational restore policy are all verified in the deployment modes that claim support. It is acceptable and preferable to leave Phase 06 unimplemented while Phases 01–05 are released.

## Completion

**Status:** Manifest-only slice implemented; mirroring remains deferred.

**Operator decision:** Use a DevLog-native manifest only; do not mirror artifacts yet. No supported deployment hosting architecture was selected because mirroring is deferred.

**Implemented:** `GET /projects/<slug>/releases/manifest.json` emits format `devlog-release-manifest`, schema version 1, cached GitHub release metadata, canonical GitHub URLs, optional provider-reported digest, `integrity_status: unverified`, and unknown platform/architecture fields as `null`. The payload explicitly sets `installer_compatibility: null`. It is not eggpack or eggup compatible by assertion.

**Not implemented:** No binary download, mirror storage, streaming verification, platform inference, checksum verification, signature validation, or installer-specific adapter. No protocol fixtures or end-to-end installer tests are available; do not advertise installer compatibility. Reopen the hosting gate before implementing mirrors.
