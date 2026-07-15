"""Tests for the import/export transfer service."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select as sa_select

from app.models import Page, Post, Subscriber, Tag
from app.services.operations.transfer import (
    export_site_data,
    import_site_data,
    validate_import,
)
from app.utils import utc_now


def _write_import_file(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestExportSiteData:
    def test_atomic_export_success(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            tag = Tag(name="Python", slug="python")
            db.session.add(tag)
            post = Post(
                title="Hello",
                slug="hello",
                body="# Hello",
                summary="A post",
                published=True,
                published_at=utc_now(),
            )
            post.tags.append(tag)
            db.session.add(post)
            subscriber = Subscriber(email="alice@example.com", token="tok", confirmed=True)
            db.session.add(subscriber)
            page = Page(title="About", slug="about", body="About page", published=True)
            db.session.add(page)
            db.session.commit()

            dest = str(tmp_path / "export.json")
            result = export_site_data(dest)

            assert result.ok is True
            assert result.code == "export.success"
            assert result.posts == 1
            assert result.subscribers == 1
            assert result.tags == 1
            assert result.pages == 1
            assert result.path == dest

            written = json.loads(Path(dest).read_text(encoding="utf-8"))
            assert written["version"] == 1
            assert len(written["posts"]) == 1
            assert len(written["subscribers"]) == 1
            assert len(written["tags"]) == 1
            assert len(written["pages"]) == 1

    def test_atomic_export_no_temp_file_left(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            dest = str(tmp_path / "clean.json")
            export_site_data(dest)

            leftover = list(tmp_path.glob(".export-*"))
            assert leftover == []

    def test_export_empty_database(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            dest = str(tmp_path / "empty.json")
            result = export_site_data(dest)

            assert result.ok is True
            assert result.posts == 0
            assert result.subscribers == 0

            written = json.loads(Path(dest).read_text(encoding="utf-8"))
            assert written["posts"] == []
            assert written["subscribers"] == []

    def test_export_force_overwrites_existing(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            dest = tmp_path / "overwrite.json"
            dest.write_text("old content", encoding="utf-8")

            result = export_site_data(str(dest), force=True)

            assert result.ok is True
            assert dest.read_text(encoding="utf-8") != "old content"
            written = json.loads(dest.read_text(encoding="utf-8"))
            assert "version" in written

    def test_export_file_exists_without_force(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            dest = tmp_path / "exists.json"
            dest.write_text("existing", encoding="utf-8")

            with pytest.raises(FileExistsError, match="already exists"):
                export_site_data(str(dest), force=False)

            assert dest.read_text(encoding="utf-8") == "existing"

    def test_export_atomic_failure_cleans_temp(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            dest = tmp_path / "fail.json"
            with patch(
                "app.services.operations.transfer.os.replace",
                side_effect=OSError("rename failed"),
            ):
                with pytest.raises(OSError, match="rename failed"):
                    export_site_data(str(dest))

            leftover = list(tmp_path.glob(".export-*"))
            assert leftover == []


class TestValidateImport:
    def test_validate_import_success(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "exported_at": "2026-01-01T00:00:00+00:00",
                "posts": [
                    {"title": "P1", "slug": "p1", "body": "body", "tags": []},
                    {"title": "P2", "slug": "p2", "body": "body", "tags": []},
                ],
                "subscribers": [
                    {"email": "a@b.com", "confirmed": True},
                ],
                "tags": [{"name": "T", "slug": "t"}],
                "pages": [{"title": "Pg", "slug": "pg", "body": "b"}],
            }
            src = _write_import_file(tmp_path / "valid.json", import_data)

            result = validate_import(str(src))

            assert result.ok is True
            assert result.code == "import.valid"
            assert result.posts == 2
            assert result.subscribers == 1
            assert result.tags == 1
            assert result.pages == 1
            assert result.details["version"] == 1
            assert result.details["exported_at"] == "2026-01-01T00:00:00+00:00"

    def test_validate_import_bad_version(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 99,
                "posts": [],
                "subscribers": [],
                "tags": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "bad.json", import_data)

            result = validate_import(str(src))

            assert result.ok is False
            assert result.code == "import.unsupported_version"
            assert "99" in result.summary
            assert len(result.remediation) > 0

    def test_validate_import_missing_version_defaults_to_1(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {"posts": [], "subscribers": [], "tags": [], "pages": []}
            src = _write_import_file(tmp_path / "no_ver.json", import_data)

            result = validate_import(str(src))

            assert result.ok is True
            assert result.details["version"] == 1

    def test_validate_import_file_not_found(self, app, db) -> None:
        with app.app_context():
            with pytest.raises(FileNotFoundError):
                validate_import("/nonexistent/import.json")

    def test_validate_import_malformed_json(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            src = tmp_path / "broken.json"
            src.write_text("{not valid json", encoding="utf-8")

            with pytest.raises(json.JSONDecodeError):
                validate_import(str(src))


class TestImportSiteData:
    def test_import_dry_run(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "posts": [{"title": "P", "slug": "p", "body": "b", "tags": []}],
                "subscribers": [{"email": "x@y.com", "confirmed": False}],
                "tags": [{"name": "T", "slug": "t"}],
                "pages": [{"title": "Pg", "slug": "pg", "body": "b"}],
            }
            src = _write_import_file(tmp_path / "dry.json", import_data)

            result = import_site_data(str(src), dry_run=True)

            assert result.ok is True
            assert result.code == "import.dry_run"
            assert result.posts == 1
            assert result.subscribers == 1
            assert result.tags == 1
            assert result.pages == 1

            assert db.session.execute(sa_select(Post)).scalars().all() == []
            assert db.session.execute(sa_select(Tag)).scalars().all() == []
            assert db.session.execute(sa_select(Subscriber)).scalars().all() == []
            assert db.session.execute(sa_select(Page)).scalars().all() == []

    def test_import_dry_run_bad_version(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 99,
                "posts": [],
                "subscribers": [],
                "tags": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "dry_bad.json", import_data)

            result = import_site_data(str(src), dry_run=True)

            assert result.ok is False
            assert result.code == "import.unsupported_version"

    def test_import_with_dedup(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            existing_tag = Tag(name="Existing", slug="existing")
            db.session.add(existing_tag)
            existing_post = Post(
                title="Old",
                slug="old-post",
                body="old",
                published=False,
            )
            db.session.add(existing_post)
            db.session.commit()

            import_data = {
                "version": 1,
                "tags": [
                    {"name": "Existing", "slug": "existing"},
                    {"name": "New Tag", "slug": "new-tag"},
                ],
                "posts": [
                    {
                        "title": "Old",
                        "slug": "old-post",
                        "body": "skip",
                        "tags": [],
                    },
                    {
                        "title": "New",
                        "slug": "new-post",
                        "body": "new",
                        "tags": ["New Tag"],
                    },
                ],
                "subscribers": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "dedup.json", import_data)

            result = import_site_data(str(src))

            assert result.ok is True
            assert result.tags == 1
            assert result.posts == 1

            all_tags = db.session.execute(sa_select(Tag.slug).order_by(Tag.slug)).scalars().all()
            assert "new-tag" in all_tags
            assert all_tags.count("new-tag") == 1

            all_posts = db.session.execute(sa_select(Post.slug).order_by(Post.slug)).scalars().all()
            assert "new-post" in all_posts
            assert all_posts.count("old-post") == 1

    def test_import_skip_confirmed_subscribers(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "tags": [],
                "posts": [],
                "subscribers": [
                    {"email": "confirmed@test.com", "confirmed": True},
                    {"email": "unconfirmed@test.com", "confirmed": False},
                ],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "skip_confirmed.json", import_data)

            result = import_site_data(str(src), skip_confirmed=True)

            assert result.ok is True
            assert result.subscribers == 1

            subs = (
                db.session.execute(sa_select(Subscriber.email).order_by(Subscriber.email))
                .scalars()
                .all()
            )
            assert "unconfirmed@test.com" in subs
            assert "confirmed@test.com" not in subs

    def test_import_include_confirmed_subscribers(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "tags": [],
                "posts": [],
                "subscribers": [
                    {"email": "confirmed@test.com", "confirmed": True},
                    {"email": "unconfirmed@test.com", "confirmed": False},
                ],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "include_confirmed.json", import_data)

            result = import_site_data(str(src), skip_confirmed=False)

            assert result.ok is True
            assert result.subscribers == 2

    def test_import_bad_version(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 99,
                "posts": [],
                "subscribers": [],
                "tags": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "bad_ver.json", import_data)

            result = import_site_data(str(src))

            assert result.ok is False
            assert result.code == "import.unsupported_version"

    def test_import_rollback_on_error(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "tags": [
                    {"name": "T1", "slug": "t1"},
                    {"name": "T2", "slug": "t2"},
                ],
                "posts": [],
                "subscribers": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "rollback.json", import_data)

            def rollback_and_raise():
                db.session.rollback()
                raise IntegrityError("simulated", {}, Exception())

            with patch(
                "app.services.operations.transfer.commit_with_rollback",
                side_effect=rollback_and_raise,
            ):
                with pytest.raises(IntegrityError):
                    import_site_data(str(src))

            tags = db.session.execute(sa_select(Tag)).scalars().all()
            assert len(tags) == 0

    def test_import_rollback_session_usable_after_error(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "tags": [{"name": "T1", "slug": "t1"}],
                "posts": [],
                "subscribers": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "session_use.json", import_data)

            with patch(
                "app.services.operations.transfer.commit_with_rollback",
                side_effect=IntegrityError("simulated", {}, Exception()),
            ):
                with pytest.raises(IntegrityError):
                    import_site_data(str(src))

            new_tag = Tag(name="AfterError", slug="after-error")
            db.session.add(new_tag)
            db.session.commit()

            result = db.session.execute(
                sa_select(Tag).filter_by(slug="after-error")
            ).scalar_one_or_none()
            assert result is not None

    def test_import_rollback_preserves_previously_committed(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "tags": [{"name": "T1", "slug": "t1"}],
                "posts": [
                    {
                        "title": "P1",
                        "slug": "p1",
                        "body": "body",
                        "tags": ["T1"],
                    }
                ],
                "subscribers": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "partial.json", import_data)

            call_count = 0

            def fail_on_second():
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise IntegrityError("simulated", {}, Exception())
                from app.transaction import commit_with_rollback as real_commit

                return real_commit()

            with patch(
                "app.services.operations.transfer.commit_with_rollback",
                side_effect=fail_on_second,
            ):
                with pytest.raises(IntegrityError):
                    import_site_data(str(src))

            tags = db.session.execute(sa_select(Tag)).scalars().all()
            assert len(tags) == 1
            assert tags[0].slug == "t1"


class TestFTSSynchronization:
    def test_import_syncs_fts_for_new_posts(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            import_data = {
                "version": 1,
                "tags": [{"name": "TagA", "slug": "taga"}],
                "posts": [
                    {
                        "title": "Searchable",
                        "slug": "searchable",
                        "body": "unique term zebra",
                        "summary": "search summary",
                        "published": True,
                        "tags": ["TagA"],
                    }
                ],
                "subscribers": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "fts.json", import_data)

            result = import_site_data(str(src))

            assert result.ok is True
            assert result.posts == 1

            from sqlalchemy import text

            rows = db.session.execute(
                text("SELECT rowid FROM posts_fts WHERE posts_fts MATCH :q"),
                {"q": "zebra"},
            ).fetchall()
            post_ids = [r[0] for r in rows]
            assert len(post_ids) >= 1

    def test_import_skips_fts_for_existing_posts(self, app, db, tmp_path: Path) -> None:
        with app.app_context():
            existing = Post(
                title="Existing",
                slug="existing",
                body="existing content",
                published=True,
                published_at=utc_now(),
            )
            db.session.add(existing)
            db.session.commit()

            import_data = {
                "version": 1,
                "tags": [],
                "posts": [
                    {
                        "title": "Existing",
                        "slug": "existing",
                        "body": "updated content",
                        "tags": [],
                    }
                ],
                "subscribers": [],
                "pages": [],
            }
            src = _write_import_file(tmp_path / "fts_skip.json", import_data)

            result = import_site_data(str(src))

            assert result.ok is True
            assert result.posts == 0
