# Release 4 Phase J — Updates, Rollback, and Uninstall

## Objective

Provide a safe application lifecycle for checking, planning, applying, validating, and rolling back DevLog application updates, plus a predictable uninstall path that preserves operator-owned data by default.

This phase depends on:

- Release 2 versioned installation layout and installation metadata
- Release 3 deployment/lifecycle adapters and `devlog doctor`
- Release 4 Phase I verified backup and restore primitives

No update operation may proceed without satisfying those dependencies.

## Scope

Implement:

```text
devlog update --check
devlog update --plan
devlog update
devlog update --version VERSION
devlog update --dry-run
devlog update --rollback VERSION

devlog uninstall
devlog uninstall --dry-run
devlog uninstall --purge
```

Support native system, native user, and Docker installations.

## Non-goals

- Do not provide silent unattended updates by default.
- Do not claim database downgrade capability when migrations are irreversible.
- Do not remove user data during normal uninstall.
- Do not modify external reverse-proxy packages or unrelated host services.
- Do not support arbitrary third-party package repositories without an explicit trust model.

## Workstream J1 — update source and trust model

Define the authoritative release metadata source.

Required metadata:

- version
- publication timestamp
- supported upgrade source range
- wheel/sdist checksums
- installer/checksum-manifest checksum
- Docker image digest
- config schema version range
- migration head and compatibility boundary
- required Python/runtime versions
- release notes URL or packaged summary
- security/advisory flag where relevant

The update client must verify release metadata and artifacts before installation. Reuse the Release 2 checksum/signature model; do not create a second verification system.

## Workstream J2 — update detection and version policy

`devlog update --check` should report:

- current version
- available version
- channel/source
- whether update is newer, same, or downgrade
- config migration requirement
- database migration requirement
- supported direct upgrade status
- backup requirement
- expected service restart
- release notes summary

Use semantic version comparison. Downgrades must require an explicit rollback command and compatibility checks.

Support stable channel first. Additional channels are out of scope unless release metadata already supports them cleanly.

## Workstream J3 — update planner

`devlog update --plan` and `--dry-run` must be non-mutating.

Plan steps:

1. resolve installation mode/scope/backend
2. validate current installation metadata
3. run production config/path checks
4. run required doctor checks
5. resolve target release
6. verify upgrade path compatibility
7. calculate required disk space
8. identify config migration
9. identify database migration
10. identify deployment-file regeneration/drift
11. identify service stop/restart actions
12. identify backup destination
13. identify rollback release and limitations

Return human and stable JSON output.

## Workstream J4 — pre-update safety gate

Before mutation:

- current `devlog doctor --production` passes required checks
- current database migration state is known
- target artifacts are verified
- sufficient disk space exists for current + target + staging + backup
- a full verified backup is created through Phase I
- backup is restorable/compatible
- current release directory/image digest is recorded
- unmanaged deployment drift is reported and requires explicit handling
- no other update/restore/migration lock is active

Failure of any required gate stops the update before service interruption.

## Workstream J5 — native update transaction

For native installations:

1. download verified target wheel/artifacts to staging
2. create `/opt/devlog/releases/<target>` or user-equivalent versioned release
3. create isolated environment
4. install exact wheel and dependencies
5. verify CLI/version/assets/migrations from target release
6. run config migration in staged/dry-run form
7. quiesce services
8. apply atomic config migration if needed
9. run database migrations using target release
10. regenerate managed deployment artifacts if required
11. atomically switch current-release symlink
12. start services
13. run readiness and production doctor
14. record successful update metadata

Do not modify the current release directory in place.

## Workstream J6 — Docker update transaction

For Docker:

1. resolve and verify target image digest
2. verify Compose/deployment compatibility
3. create verified backup
4. pull target image
5. run target preflight/config/migration validation in a one-shot management container
6. quiesce writer containers
7. run migrations exactly once
8. replace services with target digest
9. verify health and doctor checks
10. record prior and current digests

Avoid floating tags during the transaction. Persist the resolved digest in managed deployment metadata.

## Workstream J7 — config migration policy

Config migration must:

- use the existing versioned config migration registry
- produce a dry-run diff
- preserve comments where practical or clearly document canonical rewrite behavior
- back up the prior config
- never expose secrets
- fail before database mutation if target config cannot validate

Do not silently discard unknown user keys. Unsupported keys must be reported with migration guidance.

## Workstream J8 — database migration policy

Before applying migrations:

- confirm current revision
- confirm target expected head
- confirm direct upgrade path
- confirm verified backup
- quiesce writers

After applying:

- verify revision
- run database connectivity/integrity checks
- run target application smoke check

If migration fails before the release switch, retain the current release and present restore instructions. If migration partially succeeds and is irreversible, do not claim simple code rollback is sufficient.

## Workstream J9 — rollback semantics

Distinguish:

### Application rollback

Switch release symlink or image digest back when:

- database schema remains compatible
- config schema remains compatible
- prior release still exists

### Full state rollback

Use Phase I restore when:

- database migration is incompatible with prior code
- config migration is incompatible
- application rollback alone fails readiness

`devlog update --rollback` must explain which rollback type is possible and require explicit confirmation for state restoration.

Never automatically downgrade database migrations unless that path is explicitly tested and supported.

## Workstream J10 — failed update recovery

Failure handling should classify stage:

- preflight failure: no mutation
- artifact installation failure: current service unaffected
- config migration failure: restore config backup, current service retained
- database migration failure: current release retained; invoke documented restore decision
- release switch/start failure: switch code back if schema compatible, otherwise restore full backup
- post-start doctor failure: same rollback policy

Preserve logs, target staging information, and exact recovery commands.

## Workstream J11 — release retention and cleanup

Keep a configurable number of prior native releases/images.

Rules:

- never delete current release
- never delete the recorded rollback release before update validation completes
- do not remove releases referenced by failed-update evidence
- pruning supports dry run
- application release cleanup is separate from data backup pruning

## Workstream J12 — uninstall planner

Normal uninstall should remove managed application/runtime components while preserving operator-owned state.

Default preserved:

- configuration
- secrets
- database
- uploads
- external themes
- backups
- exports
- installation metadata sufficient for recovery/reinstall, or an explicit preservation record

Default removed:

- package/release code
- managed service units/Compose wrappers
- current symlink
- transient runtime files
- managed logs according to documented policy

Show exact actions before mutation.

## Workstream J13 — uninstall transaction

Normal uninstall:

1. detect mode/backend
2. validate managed-file inventory
3. stop/disable services
4. remove managed deployment files
5. remove code/releases or Docker management bundle
6. preserve data categories
7. write a preservation summary with paths and reinstall guidance
8. verify no service remains active

Do not delete unmanaged reverse-proxy configuration or user-modified files without explicit confirmation.

## Workstream J14 — purge

`--purge` is destructive and must require:

- interactive typed confirmation naming the installation
- or explicit non-interactive confirmation token/flag combination
- a final inventory of paths
- refusal when path provenance is ambiguous
- optional final verified backup, enabled by default

Purge removes categories marked removable by lifecycle policy, but must never follow unsafe symlinks or delete outside managed roots.

Backups may require a separate explicit `--purge-backups` decision so the last recovery point is not removed accidentally.

## Workstream J15 — concurrency and locks

Introduce a shared lifecycle lock covering:

- update
- restore
- filesystem migration
- uninstall
- destructive backup pruning

The lock should include owner, PID, operation, start time, and recovery guidance. Detect stale locks safely without deleting active-operation state.

## Workstream J16 — audit trail and status

Record lifecycle events in installation metadata or a dedicated local journal:

- operation ID
- from/to version
- mode/backend
- backup ID
- artifact hashes/digests
- config/database migration state
- result
- rollback action
- timestamps

Do not record secrets.

Expose recent lifecycle status through `devlog status` or a dedicated command.

## Workstream J17 — CI and end-to-end testing

Test matrix:

- native system patch update
- native user patch update
- Docker digest update
- config migration update
- database migration update
- artifact checksum failure
- insufficient disk
- doctor preflight failure
- service start failure
- post-start health failure
- application rollback
- full backup restore rollback
- normal uninstall preserves data
- reinstall discovers preserved data
- purge confirmation and path safety
- interrupted update/resume/recovery
- concurrent lifecycle lock rejection

Use released-artifact fixtures representing at least two versions rather than updating a version to itself.

## Explicit acceptance criteria

1. Update checks and plans are non-mutating and available in human and JSON formats.
2. Target release metadata and artifacts are verified before any installation mutation.
3. A verified full backup is required before config/database/service mutation.
4. Native updates install into a new versioned release rather than modifying the active release.
5. Docker updates use verified immutable image digests.
6. Config migration validates successfully before database migration begins.
7. Database migration runs with writers quiesced and revision verification before/after.
8. Release switch is atomic for native installations.
9. Post-update health and production doctor must pass before success is recorded.
10. Failed updates preserve actionable evidence and a recoverable prior state.
11. Rollback distinguishes code rollback from full-state restore and never implies unsupported database downgrade.
12. Current and rollback releases are retained until validation completes.
13. Normal uninstall preserves all operator-owned data categories.
14. Uninstall does not remove unmanaged or modified deployment/proxy files without explicit confirmation.
15. Purge refuses ambiguous paths, protects against symlink traversal, and requires destructive confirmation.
16. Backups require separate explicit purge handling.
17. Update, restore, migration, and uninstall share one lifecycle lock.
18. Lifecycle audit records contain versions, hashes/digests, backup ID, stages, and results without secrets.
19. Native system, native user, and Docker update tests use distinct source and target release artifacts.
20. Reinstall after normal uninstall can discover and reuse preserved data safely.
21. Documentation covers update planning, failure recovery, rollback limits, uninstall preservation, and purge behavior.

## Definition of done

Phase J and Release 4 are complete when DevLog can move between supported releases using verified artifacts and recovery points, prove the updated service is healthy before committing success, recover safely from failure, and remove application code without deleting operator-owned data unless an explicit guarded purge is requested.
