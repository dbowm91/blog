from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Project, ProjectDocument, ProjectDocsSnapshot
from app.services import sync_lease
from app.services.github_client import GitHubApiClient, GitHubApiError, validate_repository_identity
from app.services.project_docs import (
    MAX_DOC_BODY,
    MAX_DOC_DEPTH,
    DocumentPathError,
    normalize_document_path,
)

MAX_SYNC_DOCUMENTS = 80
MAX_SYNC_BYTES = 1_000_000
MAX_TREE_ENTRIES = 10_000
MAX_DOCS_ROOT_DEPTH = 12
ROOT_README = "README.md"
GITHUB_CONTENT_PATH_OVERHEAD = 4
MAX_CONTENT_PATH_SEGMENTS = GITHUB_CONTENT_PATH_OVERHEAD + MAX_DOCS_ROOT_DEPTH + MAX_DOC_DEPTH
_ROOT_SEGMENT = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")

logger = logging.getLogger(__name__)


class ProjectDocsSyncError(ValueError):
    pass


def _require_path_capacity(api: GitHubApiClient) -> None:
    """Reject a client that cannot address the deepest supported document path.

    The content endpoint needs one segment per documentation root component
    plus one per document component. A client with a smaller limit would reject
    the request long after the tree was read, so the mismatch is reported
    before any upstream call is made.
    """
    limit = getattr(api, "max_path_segments", None)
    if isinstance(limit, int) and limit < MAX_CONTENT_PATH_SEGMENTS:
        raise ProjectDocsSyncError(
            "The GitHub client path limit is too small for this project's documentation depth."
        )


def _renew_lease(project_id: int, lease_owner: str | None, renewed_at: float, label: str) -> float:
    """Extend the synchronisation lease when it is close to expiring.

    The lease is renewed inside the read loop, before any pending database
    writes exist, so renewing cannot commit a partially built snapshot. A
    lease that was lost to another worker ends the synchronisation instead of
    letting two workers write the same project.
    """
    if lease_owner is None:
        return renewed_at
    interval = sync_lease.policy(sync_lease.DOCS_SCOPE).renew_interval
    if interval is None:
        return renewed_at
    now = time.monotonic()
    if now - renewed_at < interval.total_seconds():
        return renewed_at
    if not sync_lease.renew(project_id, sync_lease.DOCS_SCOPE, lease_owner):
        raise ProjectDocsSyncError(f"The {label} sync lease was lost to another worker")
    return now


def _normalize_root(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ProjectDocsSyncError("Documentation root is invalid")
    if value.startswith("/") or "\\" in value or "%" in value or "\x00" in value:
        raise ProjectDocsSyncError("Documentation root is invalid")
    parts = value.split("/")
    if len(parts) > MAX_DOCS_ROOT_DEPTH or any(
        not _ROOT_SEGMENT.fullmatch(part) or part in {".", ".."} for part in parts
    ):
        raise ProjectDocsSyncError("Documentation root is invalid")
    return "/".join(parts)


def _title_for(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if name.lower() in {"readme.md", "index.md"}:
        parent = path.rsplit("/", 1)[0] if "/" in path else "Overview"
        return parent.replace("-", " ").replace("_", " ").title()
    return name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()


def _decode_markdown(data: Any, expected_size: int) -> str:
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        raise ProjectDocsSyncError("GitHub returned an unsupported document encoding")
    encoded = data.get("content")
    if not isinstance(encoded, str) or len(encoded) > MAX_DOC_BODY * 2:
        raise ProjectDocsSyncError("A repository document exceeds the configured size limit")
    try:
        raw = base64.b64decode(encoded, validate=False)
        text = raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProjectDocsSyncError("A repository document is not valid UTF-8 Markdown") from exc
    if len(raw) != expected_size or len(raw) > MAX_DOC_BODY:
        raise ProjectDocsSyncError("A repository document exceeds the configured size limit")
    if text.startswith("version https://git-lfs.github.com/spec/v1"):
        raise ProjectDocsSyncError("Git LFS documents are not supported")
    return text


def _collect_paths(tree: Any, root: str) -> list[tuple[str, str, int]]:
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        raise ProjectDocsSyncError("GitHub returned an invalid repository tree")
    entries = tree["tree"]
    if len(entries) > MAX_TREE_ENTRIES or tree.get("truncated") is True:
        raise ProjectDocsSyncError("The repository tree exceeds the configured limits")
    output: list[tuple[str, str, int]] = []
    prefix = f"{root}/"
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") != "blob":
            continue
        upstream_path = entry.get("path")
        mode = entry.get("mode")
        size = entry.get("size")
        if not isinstance(upstream_path, str) or mode != "100644":
            continue
        if upstream_path == ROOT_README:
            relative = ROOT_README
        elif upstream_path.startswith(prefix):
            relative = upstream_path[len(prefix) :]
        else:
            continue
        try:
            normalized = normalize_document_path(relative)
        except DocumentPathError:
            continue
        if not isinstance(size, int) or size < 0 or size > MAX_DOC_BODY:
            raise ProjectDocsSyncError("A repository document exceeds the configured size limit")
        output.append((normalized, upstream_path, size))
    output.sort(key=lambda item: item[0].casefold())
    if len(output) > MAX_SYNC_DOCUMENTS:
        raise ProjectDocsSyncError("The repository contains too many Markdown documents")
    return output


def sync_project_docs(
    project_id: int, *, client: GitHubApiClient | None = None
) -> ProjectDocsSnapshot:
    project = db.session.get(Project, project_id)
    if project is None:
        raise ProjectDocsSyncError("Project not found")
    try:
        lease_owner = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)
    except sync_lease.SyncLeaseError as exc:
        raise ProjectDocsSyncError(str(exc)) from exc
    try:
        return _sync_project_docs(project_id, client=client, lease_owner=lease_owner)
    finally:
        try:
            sync_lease.release(project_id, sync_lease.DOCS_SCOPE, lease_owner)
        except SQLAlchemyError:
            logger.warning(
                "Could not release the documentation sync lease for project %s", project_id
            )


def _sync_project_docs(
    project_id: int,
    *,
    client: GitHubApiClient | None = None,
    lease_owner: str | None = None,
) -> ProjectDocsSnapshot:
    project = db.session.get(Project, project_id)
    if project is None:
        raise ProjectDocsSyncError("Project not found")
    try:
        if not project.github_owner or not project.github_repository:
            raise ProjectDocsSyncError("Configure a public GitHub repository before syncing")
        try:
            owner, repository = validate_repository_identity(
                project.github_owner, project.github_repository
            )
        except ValueError as exc:
            raise ProjectDocsSyncError(str(exc)) from exc
        root = _normalize_root(project.github_docs_root)
        ref = (project.github_docs_ref or "HEAD").strip()
        if not ref or len(ref) > 256 or any(ord(char) < 32 for char in ref):
            raise ProjectDocsSyncError("GitHub documentation ref is invalid")
        api = client or GitHubApiClient(max_path_segments=MAX_CONTENT_PATH_SEGMENTS)
        _require_path_capacity(api)
        previous = (
            db.session.get(ProjectDocsSnapshot, project.active_docs_snapshot_id)
            if project.active_docs_snapshot_id is not None
            else None
        )
        previous_etag = previous.etag if previous else None

        project.docs_sync_status = "syncing"
        project.docs_sync_error = None
        db.session.commit()
        commit_response = api.get_json(
            ("repos", owner, repository, "commits", ref), etag=previous_etag
        )
        if commit_response.not_modified and previous is not None:
            project.docs_sync_status = "success"
            project.docs_sync_error = None
            project.docs_synced_at = datetime.now(UTC)
            db.session.commit()
            return previous
        commit = commit_response.data
        commit_sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
            raise ProjectDocsSyncError("GitHub did not return a valid commit identity")
        commit_sha = commit_sha.lower()
        if previous is not None and previous.commit_sha == commit_sha:
            previous.etag = commit_response.etag or previous.etag
            project.docs_sync_status = "success"
            project.docs_synced_at = datetime.now(UTC)
            db.session.commit()
            return previous

        tree_response = api.get_json(
            ("repos", owner, repository, "git", "trees", commit_sha),
            params={"recursive": 1},
        )
        documents = _collect_paths(tree_response.data, root)
        total_bytes = sum(size for _, _, size in documents)
        if total_bytes > MAX_SYNC_BYTES:
            raise ProjectDocsSyncError("Repository documentation exceeds the total size limit")
        if not documents:
            raise ProjectDocsSyncError("No supported Markdown documents were found")

        content_rows: list[tuple[str, str, str]] = []
        renewed_at = time.monotonic()
        for relative_path, upstream_path, size in documents:
            content_response = api.get_json(
                ("repos", owner, repository, "contents", *upstream_path.split("/")),
                params={"ref": commit_sha},
            )
            content = _decode_markdown(content_response.data, size)
            content_rows.append((relative_path, _title_for(relative_path), content))
            renewed_at = _renew_lease(project_id, lease_owner, renewed_at, "documentation")
        manifest = hashlib.sha256(
            json.dumps(
                [
                    (path, hashlib.sha256(body.encode("utf-8")).hexdigest())
                    for path, _, body in content_rows
                ],
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("ascii")
        ).hexdigest()

        existing = db.session.execute(
            select(ProjectDocsSnapshot).where(
                ProjectDocsSnapshot.project_id == project.id,
                ProjectDocsSnapshot.commit_sha == commit_sha,
            )
        ).scalar_one_or_none()
        if existing is not None:
            snapshot = existing
        else:
            snapshot = ProjectDocsSnapshot(
                project_id=project.id,
                source_ref=ref,
                commit_sha=commit_sha,
                acquired_at=datetime.now(UTC),
                status="active",
                file_count=len(content_rows),
                total_bytes=total_bytes,
                manifest_sha256=manifest,
                etag=commit_response.etag,
            )
            db.session.add(snapshot)
            db.session.flush()
            for nav_order, (path, title, body) in enumerate(content_rows):
                db.session.add(
                    ProjectDocument(
                        project_id=project.id,
                        version_key=f"github-{commit_sha}",
                        snapshot_id=snapshot.id,
                        path=path,
                        title=title,
                        body=body,
                        nav_order=nav_order * 10,
                        published=True,
                    )
                )
        if previous is not None and previous.id != snapshot.id:
            previous.status = "superseded"
        snapshot.status = "active"
        project.active_docs_snapshot_id = snapshot.id
        project.docs_source_kind = "github"
        project.docs_sync_status = "success"
        project.docs_sync_error = None
        project.docs_synced_at = datetime.now(UTC)
        db.session.commit()
        return snapshot
    except (GitHubApiError, ProjectDocsSyncError, IntegrityError) as exc:
        db.session.rollback()
        project = db.session.get(Project, project_id)
        if project is not None:
            project.docs_sync_status = "failed"
            project.docs_sync_error = str(exc)[:500]
            db.session.commit()
        if isinstance(exc, (GitHubApiError, ProjectDocsSyncError)):
            raise ProjectDocsSyncError(str(exc)) from exc
        raise ProjectDocsSyncError("A concurrent documentation sync conflicted") from exc
