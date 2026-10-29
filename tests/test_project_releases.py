from datetime import UTC, datetime

from app.models import Project, ProjectRelease, ProjectReleaseAsset
from app.services.project_releases import sync_project_releases


def test_sync_releases_filters_drafts_and_prereleases_and_validates_urls(db):
    project = Project(
        title="Release test",
        slug="release-test",
        summary="",
        body="",
        published=True,
        github_owner="owner",
        github_repository="repo",
        releases_include_prereleases=False,
        releases_enabled=True,
    )
    db.session.add(project)
    db.session.commit()
    upstream = [
        {
            "id": 101,
            "tag_name": "v1.0.0",
            "name": "One",
            "body": "<script>alert(1)</script>Release notes",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "published_at": "2026-10-28T12:00:00Z",
            "created_at": "2026-10-28T11:00:00Z",
            "prerelease": False,
            "draft": False,
            "assets": [
                {
                    "id": 900,
                    "name": "app.zip",
                    "size": 12,
                    "content_type": "application/zip",
                    "browser_download_url": "https://github.com/owner/repo/releases/download/v1.0.0/app.zip",
                    "digest": "sha256:abc",
                },
                {
                    "id": 901,
                    "name": "evil.zip",
                    "size": 100,
                    "browser_download_url": "https://evil.example/binary",
                },
            ],
        },
        {
            "id": 102,
            "tag_name": "v2.0.0-rc1",
            "name": "RC",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0-rc1",
            "prerelease": True,
            "draft": False,
            "assets": [],
        },
        {
            "id": 103,
            "tag_name": "draft",
            "name": "Draft",
            "html_url": "https://github.com/owner/repo/releases/tag/draft",
            "draft": True,
            "prerelease": False,
            "assets": [],
        },
    ]

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            return type(
                "Response",
                (),
                {"data": upstream, "etag": '"release-etag"', "not_modified": False},
            )()

    releases = sync_project_releases(project.id, client=FakeClient())
    assert [release.tag_name for release in releases] == ["v1.0.0"]
    assert len(releases[0].assets) == 1
    asset = releases[0].assets[0]
    assert asset.browser_download_url.startswith("https://github.com/")
    assert asset.provider_digest == "sha256:abc"
    assert project.releases_sync_status == "success"


def test_public_release_catalog_is_db_only_and_gated(client, db, monkeypatch):
    from app.services import project_releases

    project = Project(
        title="Cached",
        slug="cached-releases",
        summary="",
        body="",
        published=True,
        releases_enabled=False,
    )
    db.session.add(project)
    db.session.commit()
    monkeypatch.setattr(
        project_releases,
        "GitHubApiClient",
        lambda: (_ for _ in ()).throw(AssertionError("public request made a GitHub client")),
    )
    assert client.get("/projects/cached-releases/releases").status_code == 404
    project.releases_enabled = True
    db.session.commit()
    response = client.get("/projects/cached-releases/releases")
    assert response.status_code == 200
    assert b"No published releases" in response.data

    release = ProjectRelease(
        project_id=project.id,
        provider_release_id="77",
        tag_name="v1",
        title="Safe notes",
        notes_markdown="<script>alert(1)</script>**Release notes**",
        html_url="https://github.com/owner/repo/releases/tag/v1",
        published_at=datetime.now(UTC),
        source_synced_at=datetime.now(UTC),
    )
    release.assets.append(
        ProjectReleaseAsset(
            provider_asset_id="78",
            filename="archive.tar.gz",
            size_bytes=42,
            browser_download_url="https://github.com/owner/repo/releases/download/v1/archive.tar.gz",
            provider_digest="sha256:reported",
        )
    )
    db.session.add(release)
    db.session.commit()
    response = client.get("/projects/cached-releases/releases")
    assert response.status_code == 200
    assert b"Safe notes" in response.data
    assert b"No published releases" not in response.data
    detail = client.get(f"/projects/cached-releases/releases/{release.id}")
    assert detail.status_code == 200
    assert b"<script>" not in detail.data
    assert b"Release notes" in detail.data
    manifest_response = client.get("/projects/cached-releases/releases/manifest.json")
    assert manifest_response.status_code == 200
    manifest = manifest_response.get_json()
    assert manifest["format"] == "devlog-release-manifest"
    assert manifest["schema_version"] == 1
    assert manifest["installer_compatibility"] is None
    assert manifest["releases"][0]["source_url"].startswith("https://github.com/")
    asset_data = manifest["releases"][0]["assets"][0]
    assert asset_data["integrity_status"] == "unverified"
    assert asset_data["provider_digest"] == "sha256:reported"
    assert asset_data["platform"] is None
    assert asset_data["architecture"] is None


def test_release_sync_refetches_when_the_prerelease_preference_changes(db):
    project = Project(
        title="Filtered releases",
        slug="filtered-releases",
        summary="",
        body="",
        published=True,
        github_owner="owner",
        github_repository="repo",
        releases_include_prereleases=False,
        releases_enabled=True,
    )
    db.session.add(project)
    db.session.commit()
    upstream = [
        {
            "id": 201,
            "tag_name": "v1.0.0",
            "name": "One",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "published_at": "2026-10-28T12:00:00Z",
            "prerelease": False,
            "draft": False,
            "assets": [],
        },
        {
            "id": 202,
            "tag_name": "v2.0.0-rc1",
            "name": "RC",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0-rc1",
            "published_at": "2026-10-28T13:00:00Z",
            "prerelease": True,
            "draft": False,
            "assets": [],
        },
    ]

    class FakeClient:
        def __init__(self):
            self.sent_etags = []

        def get_json(self, path_segments, *, params=None, etag=None):
            self.sent_etags.append(etag)
            if etag is not None:
                return type(
                    "Response",
                    (),
                    {"data": None, "etag": etag, "not_modified": True},
                )()
            return type(
                "Response",
                (),
                {"data": upstream, "etag": '"release-etag"', "not_modified": False},
            )()

    client = FakeClient()
    releases = sync_project_releases(project.id, client=client)
    assert [release.tag_name for release in releases] == ["v1.0.0"]
    assert project.releases_etag == '"release-etag"'

    project.releases_include_prereleases = True
    db.session.commit()

    client = FakeClient()
    releases = sync_project_releases(project.id, client=client)

    assert client.sent_etags == [None]
    assert sorted(release.tag_name for release in releases) == ["v1.0.0", "v2.0.0-rc1"]


def test_release_sync_keeps_the_conditional_request_when_the_configuration_is_unchanged(db):
    project = Project(
        title="Conditional releases",
        slug="conditional-releases",
        summary="",
        body="",
        published=True,
        github_owner="owner",
        github_repository="repo",
        releases_include_prereleases=False,
        releases_enabled=True,
    )
    db.session.add(project)
    db.session.commit()

    class FakeClient:
        def __init__(self):
            self.sent_etags = []

        def get_json(self, path_segments, *, params=None, etag=None):
            self.sent_etags.append(etag)
            if etag is not None:
                return type(
                    "Response",
                    (),
                    {"data": None, "etag": etag, "not_modified": True},
                )()
            return type(
                "Response",
                (),
                {"data": [], "etag": '"release-etag"', "not_modified": False},
            )()

    client = FakeClient()
    sync_project_releases(project.id, client=client)
    assert client.sent_etags == [None]

    client = FakeClient()
    sync_project_releases(project.id, client=client)

    assert client.sent_etags == ['"release-etag"']


def test_release_sync_drops_prereleases_again_when_the_preference_is_turned_off(db):
    project = Project(
        title="Prerelease releases",
        slug="prerelease-releases",
        summary="",
        body="",
        published=True,
        github_owner="owner",
        github_repository="repo",
        releases_include_prereleases=True,
        releases_enabled=True,
    )
    db.session.add(project)
    db.session.commit()
    upstream = [
        {
            "id": 301,
            "tag_name": "v1.0.0",
            "name": "One",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "published_at": "2026-10-28T12:00:00Z",
            "prerelease": False,
            "draft": False,
            "assets": [],
        },
        {
            "id": 302,
            "tag_name": "v2.0.0-rc1",
            "name": "RC",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0-rc1",
            "published_at": "2026-10-28T13:00:00Z",
            "prerelease": True,
            "draft": False,
            "assets": [],
        },
    ]

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            if etag is not None:
                return type(
                    "Response",
                    (),
                    {"data": None, "etag": etag, "not_modified": True},
                )()
            return type(
                "Response",
                (),
                {"data": upstream, "etag": '"release-etag"', "not_modified": False},
            )()

    releases = sync_project_releases(project.id, client=FakeClient())
    assert sorted(release.tag_name for release in releases) == ["v1.0.0", "v2.0.0-rc1"]

    project.releases_include_prereleases = False
    db.session.commit()

    releases = sync_project_releases(project.id, client=FakeClient())

    assert [release.tag_name for release in releases] == ["v1.0.0"]
