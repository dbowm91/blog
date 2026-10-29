from __future__ import annotations

from flask import abort, jsonify, render_template
from flask.typing import ResponseReturnValue
from sqlalchemy import select

from app.extensions import db
from app.models import ProjectRelease
from app.services.projects import get_published_project


def register_project_release_routes(public) -> None:
    @public.route("/projects/<slug>/releases/manifest.json")
    def project_release_manifest(slug: str) -> ResponseReturnValue:
        project = get_published_project(slug)
        if project is None or not project.releases_enabled:
            abort(404)
        releases = list(
            db.session.execute(
                select(ProjectRelease)
                .where(ProjectRelease.project_id == project.id)
                .order_by(ProjectRelease.published_at.desc(), ProjectRelease.id.desc())
            ).scalars()
        )
        manifest = {
            "format": "devlog-release-manifest",
            "schema_version": 1,
            "project": {"slug": project.slug, "title": project.title},
            "canonical_source": "github",
            "installer_compatibility": None,
            "releases": [
                {
                    "tag": release.tag_name,
                    "title": release.title,
                    "published_at": (
                        release.published_at.isoformat() if release.published_at else None
                    ),
                    "prerelease": release.prerelease,
                    "source_url": release.html_url,
                    "source_synced_at": release.source_synced_at.isoformat(),
                    "assets": [
                        {
                            "filename": asset.filename,
                            "size_bytes": asset.size_bytes,
                            "canonical_url": asset.browser_download_url,
                            "provider_digest": asset.provider_digest,
                            "integrity_status": "unverified",
                            "platform": None,
                            "architecture": None,
                        }
                        for asset in sorted(
                            release.assets, key=lambda item: item.filename.casefold()
                        )
                    ],
                }
                for release in releases
            ],
        }
        return jsonify(manifest)

    @public.route("/projects/<slug>/releases")
    def project_releases(slug: str) -> ResponseReturnValue:
        project = get_published_project(slug)
        if project is None or not project.releases_enabled:
            abort(404)
        releases = list(
            db.session.execute(
                select(ProjectRelease)
                .where(ProjectRelease.project_id == project.id)
                .order_by(ProjectRelease.published_at.desc(), ProjectRelease.id.desc())
            ).scalars()
        )
        return render_template("projects/releases.html", project=project, releases=releases)

    @public.route("/projects/<slug>/releases/<int:release_id>")
    def project_release(slug: str, release_id: int) -> ResponseReturnValue:
        project = get_published_project(slug)
        if project is None or not project.releases_enabled:
            abort(404)
        release = db.session.execute(
            select(ProjectRelease).where(
                ProjectRelease.id == release_id,
                ProjectRelease.project_id == project.id,
            )
        ).scalar_one_or_none()
        if release is None:
            abort(404)
        return render_template("projects/release.html", project=project, release=release)
