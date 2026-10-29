"""Tests for the database-backed synchronisation lease.

The lease gives one worker exclusive ownership of a project synchronisation
scope so that two workers cannot interleave their work on the same project.
"""

from datetime import timedelta

import base64
import pytest

from app.models import Project
from app.services import sync_lease
from app.services.project_docs_sync import ProjectDocsSyncError, sync_project_docs


def _project(db, slug="leased-project") -> Project:
    project = Project(
        title="Leased project",
        slug=slug,
        body="",
        summary="",
        published=True,
        docs_enabled=True,
        github_owner="example",
        github_repository="sample",
    )
    db.session.add(project)
    db.session.commit()
    return project


def test_a_lease_is_held_by_one_owner_at_a_time(db):
    project = _project(db)

    owner = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) == owner
    with pytest.raises(sync_lease.SyncLeaseError):
        sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)


def test_releasing_a_lease_frees_the_scope(db):
    project = _project(db)
    owner = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    sync_lease.release(project.id, sync_lease.DOCS_SCOPE, owner)

    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) is None
    assert sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)


def test_releasing_a_lease_does_not_clear_a_lease_held_by_another_worker(db):
    project = _project(db)
    first = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    sync_lease.release(project.id, sync_lease.DOCS_SCOPE, "another-worker")

    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) == first


def test_an_expired_lease_can_be_taken_over(db):
    project = _project(db)
    first = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE, ttl=timedelta(seconds=-1))

    second = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    assert second != first
    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) == second


def test_renew_extends_a_lease_the_caller_still_holds(db):
    project = _project(db)
    owner = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    assert sync_lease.renew(project.id, sync_lease.DOCS_SCOPE, owner) is True
    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) == owner


def test_renew_reports_a_lease_that_was_taken_over(db):
    project = _project(db)
    first = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE, ttl=timedelta(seconds=-1))
    second = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    assert sync_lease.renew(project.id, sync_lease.DOCS_SCOPE, first) is False
    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) == second


def test_the_documentation_sync_aborts_when_the_lease_is_lost(db, monkeypatch):
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.extensions import db
    from app.models import Project
    from app.services import project_docs_sync

    project = _project(db)
    monkeypatch.setattr(
        project_docs_sync.sync_lease,
        "policy",
        lambda scope: sync_lease.LeasePolicy(
            ttl=timedelta(minutes=10), renew_interval=timedelta(seconds=0)
        ),
    )
    commit_sha = "c" * 40
    body = "# Readme"

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            if path_segments[-2:] == ("commits", "HEAD"):
                return type(
                    "Response",
                    (),
                    {"data": {"sha": commit_sha}, "etag": '"v1"', "not_modified": False},
                )()
            if path_segments[-2:] == ("trees", commit_sha):
                return type(
                    "Response",
                    (),
                    {
                        "data": {
                            "tree": [
                                {
                                    "path": "README.md",
                                    "type": "blob",
                                    "mode": "100644",
                                    "size": len(body.encode()),
                                }
                            ],
                            "truncated": False,
                        },
                        "etag": None,
                        "not_modified": False,
                    },
                )()
            db.session.execute(
                update(Project)
                .where(Project.id == project.id)
                .values(
                    docs_sync_lease_owner="another-worker",
                    docs_sync_lease_expires_at=datetime.now(UTC) + timedelta(minutes=10),
                )
                .execution_options(synchronize_session=False)
            )
            db.session.commit()
            return type(
                "Response",
                (),
                {
                    "data": {
                        "encoding": "base64",
                        "content": base64.b64encode(body.encode()).decode(),
                    },
                    "etag": None,
                    "not_modified": False,
                },
            )()

    with pytest.raises(ProjectDocsSyncError, match="lease was lost"):
        sync_project_docs(project.id, client=FakeClient())

    assert project.docs_sync_status == "failed"
    assert project.active_docs_snapshot_id is None


def test_the_documentation_and_release_scopes_are_independent(db):
    project = _project(db)

    docs_owner = sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)
    releases_owner = sync_lease.acquire(project.id, sync_lease.RELEASES_SCOPE)

    assert docs_owner != releases_owner


def test_a_second_documentation_sync_is_refused_while_the_lease_is_held(db):
    project = _project(db)
    sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            raise AssertionError("a refused sync must not reach the network")

    with pytest.raises(ProjectDocsSyncError, match="already running"):
        sync_project_docs(project.id, client=FakeClient())


def test_a_refused_documentation_sync_does_not_overwrite_the_running_status(db):
    project = _project(db)
    sync_lease.acquire(project.id, sync_lease.DOCS_SCOPE)
    project.docs_sync_status = "syncing"
    db.session.commit()

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            raise AssertionError("a refused sync must not reach the network")

    with pytest.raises(ProjectDocsSyncError):
        sync_project_docs(project.id, client=FakeClient())

    assert project.docs_sync_status == "syncing"


def test_a_failed_documentation_sync_releases_the_lease(db):
    project = _project(db)

    class FailingClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            from app.services.github_client import GitHubApiError

            raise GitHubApiError("GitHub API request failed")

    with pytest.raises(ProjectDocsSyncError):
        sync_project_docs(project.id, client=FailingClient())

    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) is None
    assert project.docs_sync_status == "failed"


def test_a_successful_documentation_sync_releases_the_lease(db):
    import base64

    project = _project(db)
    commit_sha = "b" * 40
    files = {"README.md": "# Readme"}

    class FakeClient:
        def get_json(self, path_segments, *, params=None, etag=None):
            if path_segments[-2:] == ("commits", "HEAD"):
                return type(
                    "Response",
                    (),
                    {"data": {"sha": commit_sha}, "etag": '"v1"', "not_modified": False},
                )()
            if path_segments[-2:] == ("trees", commit_sha):
                return type(
                    "Response",
                    (),
                    {
                        "data": {
                            "tree": [
                                {
                                    "path": path,
                                    "type": "blob",
                                    "mode": "100644",
                                    "size": len(body.encode()),
                                }
                                for path, body in files.items()
                            ],
                            "truncated": False,
                        },
                        "etag": None,
                        "not_modified": False,
                    },
                )()
            payload = base64.b64encode(files["/".join(path_segments[4:])].encode()).decode()
            return type(
                "Response",
                (),
                {
                    "data": {"encoding": "base64", "content": payload},
                    "etag": None,
                    "not_modified": False,
                },
            )()

    sync_project_docs(project.id, client=FakeClient())

    assert sync_lease.holder(project.id, sync_lease.DOCS_SCOPE) is None
    assert project.docs_sync_status == "success"
