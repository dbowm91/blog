# Release 4 Phase I — Backup, Verification, and Recovery Lifecycle

## Objective

Turn the existing backup primitives into a complete, verifiable, automation-safe backup and restore lifecycle that protects configuration, secrets, database state, uploads, themes, installation metadata, and other persistent operator-owned data.

This phase must complete before update/uninstall work because Release 4 Phase J depends on a trustworthy pre-update backup and recovery mechanism.

## Scope

Implement or complete:

```text
devlog backup create
devlog backup list
devlog backup inspect PATH
devlog backup verify PATH
devlog backup restore PATH
devlog backup prune
devlog backup policy
devlog backup status
```

The lifecycle must support native system, native user, and Docker installations using RuntimePaths and installation metadata.

## Non-goals

- Do not provide distributed database backup semantics.
- Do not claim PostgreSQL support unless fully implemented and tested.
- Do not silently upload backups to remote providers.
- Do not restore application code from data archives.
- Do not imply database downgrade support where migrations are irreversible.

## Workstream I1 — canonical backup manifest

Define a versioned manifest included in every archive.

Required fields:

- manifest schema version
- DevLog package version
- config schema version
- database migration revision
- installation mode and native scope
- creation timestamp and timezone
- archive format and compression
- encryption status and algorithm identifier
- included path categories
- excluded path categories
- per-entry size and hash
- database checkpoint/integrity status
- selected theme identifiers
- source installation metadata identifier
- minimum compatible restore version
- warnings/degraded conditions

The manifest must not contain secret values. It may record that a secret file is included and its hash.

## Workstream I2 — backup set definition

Use the lifecycle categories defined by RuntimePaths.

Default inclusion:

- configuration
- secrets
- database and required sidecar state after checkpoint
- uploads
- external themes
- installation metadata
- exports only if configured

Default exclusion:

- application code/releases
- logs
- runtime files
- caches
- existing backups
- regenerable frontend assets

Allow explicit component selection, but reject archives that would be misleadingly labeled complete when required recovery components are omitted.

## Workstream I3 — consistent database capture

For SQLite:

1. identify the resolved database through RuntimePaths/configuration
2. prevent or coordinate writers
3. perform WAL checkpoint or use SQLite backup API
4. verify database integrity at the chosen level
5. copy to staging
6. record migration revision and hash
7. release writer quiescence

Prefer SQLite's online backup API where practical. Raw file copy while writers remain active is not sufficient.

Classify backup as degraded or failed if checkpoint/integrity cannot complete. Do not report success merely because an archive file was created.

## Workstream I4 — staging and atomic publication

Backup creation flow:

1. validate configuration and paths
2. validate destination free space
3. create private staging directory
4. capture components
5. construct manifest
6. create compressed/encrypted archive
7. verify archive structure and hashes
8. fsync where practical
9. atomically rename to final destination
10. update backup index/status

Partial files must use a distinct extension and be cleaned or reported safely after interruption.

## Workstream I5 — compression and encryption

Retain compatibility with existing supported formats where possible.

Requirements:

- authenticated encryption
- explicit key source through environment or secret file
- no key in CLI arguments, process list, logs, manifest, or JSON
- encryption dependency validation before capture
- clear distinction between encrypted and unencrypted archives
- restore must authenticate before extraction
- compression bomb and archive size safeguards

Do not invent custom cryptography where a maintained standard/library format is available.

## Workstream I6 — archive inspection and verification

`inspect` reads metadata without restoring.

`verify` performs:

- archive format validation
- encryption authentication
- manifest schema validation
- path safety validation
- per-entry hash validation
- expected component presence
- database integrity on an extracted temporary copy
- migration/config compatibility assessment
- package version compatibility assessment

Verification result must distinguish:

- valid and restorable
- valid but degraded/incomplete
- valid but incompatible with current version
- corrupt
- authentication failure
- unsupported format

## Workstream I7 — safe restore planner

Restore must begin with a non-mutating plan:

```text
devlog backup restore PATH --dry-run
```

Plan includes:

- current installation identity
- archive source identity
- version/config/migration compatibility
- components to replace/preserve
- required free space
- service quiescence actions
- pre-restore backup location
- expected downtime
- rollback path
- conflicts and warnings

Cross-installation restores require explicit confirmation and clear handling of secrets, hostnames, and deployment metadata.

## Workstream I8 — restore transaction

Required restore sequence:

1. validate current installation
2. verify archive fully
3. ensure compatibility
4. create and verify pre-restore backup
5. stop or quiesce web/worker/scheduler through Phase G lifecycle adapters
6. extract into private staging
7. validate paths and permissions
8. validate database and migration revision
9. atomically replace components where possible
10. restore ownership/modes
11. start services
12. run `devlog doctor --production`
13. commit restore metadata only after readiness succeeds

On failure:

- stop further mutation
- restore prior state from the pre-restore snapshot where safe
- preserve failure evidence
- return actionable recovery commands

## Workstream I9 — component restore policy

Support full restore first. Component restores may include:

- uploads only
- themes only
- configuration only
- database only

Each component mode must define consistency constraints. For example, database-only restore may reference uploads absent from the current installation and must warn or verify referential consistency.

Secrets should not be replaced by default during cross-host restore unless explicitly selected.

## Workstream I10 — backup listing, index, and status

Provide a resilient index derived from archive manifests, not a database that becomes a single point of failure.

`backup list/status` should report:

- timestamp
- size
- verified state
- encryption
- DevLog version
- migration revision
- completeness
- age
- retention eligibility

If an index cache is used, it must be rebuildable by scanning manifests.

## Workstream I11 — retention and pruning

Implement explicit policies such as:

- keep last N
- keep daily/weekly/monthly tiers
- keep newer than duration
- minimum verified backups
- protect named/pinned backups

Pruning requirements:

- dry-run by default or readily available
- never delete unverified archives merely because they are old without explicit policy
- never prune the only valid recovery point
- exclude in-progress/partial archives
- atomic metadata updates
- clear freed-space result

## Workstream I12 — Docker considerations

For Docker:

- execute capture/restore through a documented management container or host CLI
- resolve named volumes and bind mounts through installation metadata
- quiesce all writer containers
- preserve UID/GID expectations
- ensure archive destination is external to the data volume being restored
- test container replacement after restore

Do not rely on copying a live Docker volume blindly.

## Workstream I13 — diagnostics integration

Extend `devlog doctor` with:

- backup directory writability
- last successful verified backup
- backup age policy
- latest archive compatibility
- encryption key availability
- incomplete/partial archive detection
- retention health

Production doctor should warn or fail according to configured backup policy.

## Workstream I14 — testing

Unit tests:

- manifest serialization/versioning
- component selection
- hash verification
- path traversal rejection
- encryption redaction
- retention decisions
- compatibility rules

Integration tests:

- SQLite WAL database capture
- archive creation and verification
- corrupted archive
- wrong encryption key
- interrupted creation
- insufficient disk
- full restore
- failed post-restore doctor rollback
- component restore consistency

End-to-end matrix:

- native system backup/restore
- native user backup/restore
- Docker backup/restore and container replacement
- restore across patch versions
- supported migration-boundary restore
- cross-host restore with explicit secret policy

## Explicit acceptance criteria

1. Every backup contains a versioned, secret-free manifest.
2. Backup creation uses RuntimePaths and lifecycle categories rather than hard-coded locations.
3. SQLite capture is transactionally consistent through backup API or verified checkpoint/quiescence.
4. Archive creation is staged, verified, and atomically published.
5. A created but unverified archive is never reported as successful.
6. Encryption is authenticated and keys never appear in CLI arguments, logs, manifests, or JSON.
7. Verification detects corruption, wrong keys, missing components, unsafe paths, and incompatibility.
8. Restore always performs a complete dry-run-compatible plan.
9. Restore requires a verified pre-restore backup unless explicitly overridden through a documented emergency path.
10. Web, worker, and scheduler writers are quiesced before state replacement.
11. Restored state is validated before services restart.
12. Post-restore production doctor must pass before restore is committed successful.
13. Restore failure leaves the prior installation recoverable.
14. Cross-host secret replacement is explicit, not automatic.
15. Retention never deletes the only valid recovery point.
16. Backup index/status can be rebuilt from archive manifests.
17. Native system, native user, and Docker round-trip tests preserve content, users, uploads, themes, and configuration according to policy.
18. Documentation includes disaster-recovery procedures and emergency failure recovery.

## Definition of done

Phase I is complete when DevLog can create a verified recovery point, prove its integrity without restoring, safely replace an installation from that archive, and recover from a failed restore without losing the previous valid state.
