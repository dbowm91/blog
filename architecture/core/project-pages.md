# Project Pages, Documentation and Releases

Project records are independent of static `Page` records. Public project and documentation/release routes require a published project; documentation additionally requires `docs_enabled`, and each displayed document must be published. Admin authoring lives in `app/routes/admin/project_docs.py`; public rendering lives in `app/routes/public/project_docs.py` and `project_releases.py`.

## Local documentation

`ProjectDocument` stores Markdown in the database. `app.services.project_docs.normalize_document_path()` is the path-policy owner: a stored path is canonical and never contains `.` or `..` segments. Relative *references* are a separate concern — `resolve_document_path()` and `resolve_asset_path()` in the same module resolve them against the linking document's directory, drop `.` segments, pop one directory per `..`, and reject a reference that would climb above the documentation root. Markdown output is produced by `app/markdown_renderer.py`; `app.routes.public.project_docs` rewrites rendered links and images through project-scoped document/asset records. Uploaded document images are represented by `ProjectDocumentAsset` and resolved through the existing media URL producer. The public reader does not fetch GitHub.

The admin documentation screen supports project docs settings, local document create/edit/delete and publish state, navigation order, draft preview, and document image upload/removal. Preview and mutation routes are admin protected and subject to global POST CSRF enforcement.

## GitHub documentation source

`app.services.github_client.GitHubApiClient` builds requests only for `api.github.com`, validates owner/repository identifiers, applies bounded response and retry limits, rejects redirects, and handles ETags/rate-limit metadata. Its path-segment limit is a client setting; `MAX_CONTENT_PATH_SEGMENTS` in `app.services.project_docs_sync` derives the segment count the content endpoint needs from the documentation root depth and the document depth limit, and the sync refuses a client that cannot address the deepest supported path before it makes a network call.

`app.services.project_docs_sync.sync_project_docs()` reads a pinned commit tree and Markdown files under the configured documentation root (plus root `README.md`), applies path/count/body/total-byte limits, and creates `ProjectDocsSnapshot` plus snapshot-bound document rows. Only after all reads and validation succeed does one DB commit activate the new snapshot. Existing local rows are retained; switching source controls which version the docs resolver serves. A failed sync records bounded project status without changing the active snapshot.

`app.services.sync_lease` gives one worker exclusive ownership of a project synchronisation scope. The lease lives on the project row, so acquiring it is a single conditional `UPDATE`: two workers racing for the same project observe one winner and the loser reports the conflict instead of interleaving activation. The lease is advisory and time-bounded, so a worker that dies does not block the scope permanently. A long-running worker renews the lease while it still holds it — the documentation scope uses a short lifetime with renewal, because its request count is bounded by the document limit and a lease that expired mid-synchronisation would let a second worker start. The release scope makes at most three requests, so its longer lifetime never needs renewal. A lease lost to another worker ends the synchronisation instead of allowing two workers to write the same project. Documentation and release synchronisation use independent scopes, and a refused synchronisation does not overwrite the running worker's status. Sync remains manual; periodic scheduling is not implemented yet.

The importer currently imports Markdown documents only. GitHub image files are not mirrored into `ProjectDocumentAsset`; repository-relative images therefore require a separately uploaded project asset to resolve. GitHub API access is limited to public repositories and depends on GitHub availability at admin sync time.

## Release catalog

`app.services.project_releases.sync_project_releases()` caches public GitHub release metadata using the same restricted client, ETag support and a three-page maximum. Drafts are never stored; prereleases are excluded unless enabled. Release and asset identifiers are persisted as provider metadata, while downloads remain canonical GitHub browser-download URLs. DevLog checks the HTTPS `github.com` host but does not fetch asset bytes or verify a provider digest. The release pages render cached data only, and release notes pass through `markdown_safe`. No periodic refresh is installed.

The upstream ETag says only that GitHub's release list is unchanged, while the cached catalog also depends on the repository and on the prerelease preference. `releases_sync_config` stores a fingerprint of that configuration beside the ETag; when the fingerprint no longer matches the current settings the conditional request is dropped and the catalog is fetched in full, so changing the preference always reconciles the local cache.

Public endpoints are `/projects/<slug>/releases`, `/projects/<slug>/releases/<release_id>`, and `/projects/<slug>/releases/manifest.json`. The stable identifier is the local numeric release row ID; the mutable Git tag is display data. The manifest is versioned DevLog-native metadata only: it leaves platform and architecture unknown, marks provider digests unverified, and declares no installer compatibility.

## Migrations and constraints

The feature migrations are linear: `add_project_documents` → `add_project_github_docs_snapshots` → `add_project_releases` → `add_project_sync_leases`. The last revision adds the synchronisation lease columns and the release configuration fingerprint. New features remain disabled by default. The project model total is 23. Mirror storage, streamed downloads, signatures, independent SHA-256 verification, and eggpack/eggup compatibility are out of scope until the Phase 06 operator decision and protocol evidence gates are met.
