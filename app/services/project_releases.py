from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Project, ProjectRelease, ProjectReleaseAsset
from app.services import sync_lease
from app.services.github_client import GitHubApiClient, GitHubApiError, validate_repository_identity
from app.services.project_docs_sync import ProjectDocsSyncError

MAX_RELEASE_PAGES = 3
PAGE_SIZE = 100
MAX_ASSETS_PER_RELEASE = 100

logger = logging.getLogger(__name__)


def _release_config_fingerprint(owner: str, repository: str, include_prereleases: bool) -> str:
    """Describe the local projection of the upstream release catalog.

    The upstream ETag only says that GitHub's release list is unchanged. The
    cached catalog additionally depends on the repository and on whether
    prereleases are included, so the fingerprint records which configuration
    produced the stored ETag. A configuration change invalidates the
    conditional request even when upstream did not change at all.
    """
    payload = json.dumps(
        {
            "owner": owner,
            "repository": repository,
            "prereleases": bool(include_prereleases),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _github_url(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 1024:
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
        ):
            return None
    except ValueError:
        return None
    return value


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def sync_project_releases(
    project_id: int, *, client: GitHubApiClient | None = None
) -> list[ProjectRelease]:
    project = db.session.get(Project, project_id)
    if project is None:
        raise ProjectDocsSyncError("Project not found")
    try:
        lease_owner = sync_lease.acquire(project.id, sync_lease.RELEASES_SCOPE)
    except sync_lease.SyncLeaseError as exc:
        raise ProjectDocsSyncError(str(exc)) from exc
    try:
        return _sync_project_releases(project_id, client=client)
    finally:
        try:
            sync_lease.release(project_id, sync_lease.RELEASES_SCOPE, lease_owner)
        except SQLAlchemyError:
            logger.warning("Could not release the release sync lease for project %s", project_id)


def _sync_project_releases(
    project_id: int, *, client: GitHubApiClient | None = None
) -> list[ProjectRelease]:
    project = db.session.get(Project, project_id)
    if project is None:
        raise ProjectDocsSyncError("Project not found")
    try:
        if not project.github_owner or not project.github_repository:
            raise ProjectDocsSyncError(
                "Configure a public GitHub repository before syncing releases"
            )
        try:
            owner, repository = validate_repository_identity(
                project.github_owner, project.github_repository
            )
        except ValueError as exc:
            raise ProjectDocsSyncError(str(exc)) from exc
        api = client or GitHubApiClient()
        fingerprint = _release_config_fingerprint(
            owner, repository, project.releases_include_prereleases
        )
        conditional_etag = (
            project.releases_etag if project.releases_sync_config == fingerprint else None
        )
        project.releases_sync_status = "syncing"
        project.releases_sync_error = None
        db.session.commit()
        upstream: list[dict[str, Any]] = []
        next_etag = None
        for page in range(1, MAX_RELEASE_PAGES + 1):
            response = api.get_json(
                ("repos", owner, repository, "releases"),
                params={"per_page": PAGE_SIZE, "page": page},
                etag=conditional_etag if page == 1 else None,
            )
            if response.not_modified and page == 1:
                project.releases_sync_status = "success"
                project.releases_sync_error = None
                project.releases_synced_at = datetime.now(UTC)
                project.releases_sync_config = fingerprint
                db.session.commit()
                return list(
                    db.session.execute(
                        select(ProjectRelease)
                        .where(ProjectRelease.project_id == project.id)
                        .order_by(ProjectRelease.published_at.desc(), ProjectRelease.id.desc())
                    ).scalars()
                )
            if page == 1:
                next_etag = response.etag
            if not isinstance(response.data, list):
                raise ProjectDocsSyncError("GitHub returned an invalid release catalog")
            upstream.extend(item for item in response.data if isinstance(item, dict))
            if len(response.data) < PAGE_SIZE:
                break
        else:
            raise ProjectDocsSyncError("Release catalog exceeds the configured page limit")

        now = datetime.now(UTC)
        seen: set[str] = set()
        for item in upstream:
            if item.get("draft") is True:
                continue
            if item.get("prerelease") is True and not project.releases_include_prereleases:
                continue
            release_id = item.get("id")
            html_url = _github_url(item.get("html_url"))
            tag_name = item.get("tag_name")
            if (
                not isinstance(release_id, (str, int))
                or not isinstance(tag_name, str)
                or not tag_name
            ):
                continue
            if html_url is None or len(tag_name) > 256:
                continue
            provider_id = str(release_id)
            if len(provider_id) > 32:
                continue
            seen.add(provider_id)
            release = db.session.execute(
                select(ProjectRelease).where(
                    ProjectRelease.project_id == project.id,
                    ProjectRelease.provider_release_id == provider_id,
                )
            ).scalar_one_or_none()
            if release is None:
                release = ProjectRelease(project_id=project.id, provider_release_id=provider_id)
                db.session.add(release)
            release.tag_name = tag_name
            release.title = str(item.get("name") or tag_name)[:256]
            release.notes_markdown = str(item.get("body") or "")[:100_000]
            release.html_url = html_url
            release.published_at = _parse_datetime(item.get("published_at"))
            release.created_at = _parse_datetime(item.get("created_at"))
            release.prerelease = item.get("prerelease") is True
            release.source_synced_at = now
            db.session.flush()

            assets = item.get("assets")
            if not isinstance(assets, list) or len(assets) > MAX_ASSETS_PER_RELEASE:
                raise ProjectDocsSyncError("A release contains too many assets")
            seen_assets: set[str] = set()
            for asset_data in assets:
                if not isinstance(asset_data, dict):
                    continue
                asset_id = asset_data.get("id")
                download_url = _github_url(asset_data.get("browser_download_url"))
                filename = asset_data.get("name")
                size = asset_data.get("size")
                if (
                    not isinstance(asset_id, (str, int))
                    or not isinstance(filename, str)
                    or not filename
                    or len(filename) > 512
                    or not isinstance(size, int)
                    or size < 0
                    or download_url is None
                ):
                    continue
                asset_provider_id = str(asset_id)
                if len(asset_provider_id) > 32:
                    continue
                seen_assets.add(asset_provider_id)
                asset = db.session.execute(
                    select(ProjectReleaseAsset).where(
                        ProjectReleaseAsset.release_id == release.id,
                        ProjectReleaseAsset.provider_asset_id == asset_provider_id,
                    )
                ).scalar_one_or_none()
                if asset is None:
                    asset = ProjectReleaseAsset(
                        release_id=release.id,
                        provider_asset_id=asset_provider_id,
                    )
                    db.session.add(asset)
                asset.filename = filename
                asset.content_type = (
                    str(asset_data.get("content_type"))[:128]
                    if asset_data.get("content_type")
                    else None
                )
                asset.size_bytes = size
                asset.browser_download_url = download_url
                digest = asset_data.get("digest")
                asset.provider_digest = str(digest)[:128] if digest else None
            for old_asset in list(release.assets):
                if old_asset.provider_asset_id not in seen_assets:
                    db.session.delete(old_asset)

        for existing in list(project.releases):
            if existing.provider_release_id not in seen:
                db.session.delete(existing)
        project.releases_etag = next_etag
        project.releases_sync_config = fingerprint
        project.releases_sync_status = "success"
        project.releases_sync_error = None
        project.releases_synced_at = now
        db.session.commit()
    except (GitHubApiError, ProjectDocsSyncError, IntegrityError) as exc:
        db.session.rollback()
        project = db.session.get(Project, project_id)
        if project is not None:
            project.releases_sync_status = "failed"
            project.releases_sync_error = str(exc)[:500]
            db.session.commit()
        if isinstance(exc, (GitHubApiError, ProjectDocsSyncError)):
            raise ProjectDocsSyncError(str(exc)) from exc
        raise ProjectDocsSyncError("Release metadata sync conflicted") from exc
    return list(
        db.session.execute(
            select(ProjectRelease)
            .where(ProjectRelease.project_id == project_id)
            .order_by(ProjectRelease.published_at.desc(), ProjectRelease.id.desc())
        ).scalars()
    )
