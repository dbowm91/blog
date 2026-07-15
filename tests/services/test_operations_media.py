"""Tests for app.services.operations.media — orphaned media cleanup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models import Post
from app.services.operations.media import (
    scan_orphaned_media,
    apply_orphaned_media_cleanup,
    _is_safe_filename,
)


# ---------------------------------------------------------------------------
# _is_safe_filename unit tests
# ---------------------------------------------------------------------------


class TestIsSafeFilename:
    @pytest.mark.parametrize(
        "name",
        [
            "photo.jpg",
            "image-2024.png",
            "deep_nest.webp",
            "a.b.jpg",
        ],
    )
    def test_valid_names(self, name: str) -> None:
        assert _is_safe_filename(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "",
            ".hidden",
            "../etc/passwd",
            "foo/bar",
            "foo\\bar",
            "a..b.jpg",
            "./foo",
            "..",
        ],
    )
    def test_suspicious_names(self, name: str) -> None:
        assert _is_safe_filename(name) is False


# ---------------------------------------------------------------------------
# scan_orphaned_media
# ---------------------------------------------------------------------------


class TestScanOrphanedMedia:
    def test_finds_orphaned_files(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["orphan.png", "used.jpg"]
        mock_storage.exists.return_value = True

        post = Post(
            title="Post",
            slug="post",
            body="body",
            image="used.jpg",
            published=True,
        )
        db.session.add(post)
        db.session.commit()

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = scan_orphaned_media()

        assert result.ok is True
        assert result.orphaned_deleted == 0
        assert result.missing_cleared == 0
        assert "orphan.png" in result.details["orphaned_files"]
        assert "used.jpg" not in result.details["orphaned_files"]

    def test_finds_missing_db_references(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = []
        mock_storage.exists.return_value = False

        post = Post(
            title="Post",
            slug="post",
            body="body",
            image="missing.png",
            published=True,
        )
        db.session.add(post)
        db.session.commit()

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = scan_orphaned_media()

        assert result.ok is True
        assert "missing.png" in result.details["missing_refs"]

    def test_no_orphans(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["used.jpg"]
        mock_storage.exists.return_value = True

        post = Post(
            title="Post",
            slug="post",
            body="body",
            image="used.jpg",
            published=True,
        )
        db.session.add(post)
        db.session.commit()

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = scan_orphaned_media()

        assert result.ok is True
        assert result.details["orphaned_files"] == []
        assert result.details["missing_refs"] == []

    def test_skips_suspicious_filenames(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["good.jpg", "../escape.png", "sub/dir.webp"]
        mock_storage.exists.return_value = True

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = scan_orphaned_media()

        assert result.ok is True
        assert "good.jpg" in result.details["orphaned_files"]
        assert "../escape.png" not in result.details["orphaned_files"]
        assert "sub/dir.webp" not in result.details["orphaned_files"]
        assert any("suspicious" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# apply_orphaned_media_cleanup
# ---------------------------------------------------------------------------


class TestApplyOrphanedMediaCleanup:
    def test_deletes_orphans_and_clears_references(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["orphan.png", "used.jpg"]
        mock_storage.exists.side_effect = lambda name: name != "missing-ref.png"

        post_with_orphan = Post(
            title="Missing",
            slug="missing",
            body="body",
            image="missing-ref.png",
            published=True,
        )
        post_with_valid = Post(
            title="Valid",
            slug="valid",
            body="body",
            image="used.jpg",
            published=True,
        )
        db.session.add_all([post_with_orphan, post_with_valid])
        db.session.commit()

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = apply_orphaned_media_cleanup()

        assert result.ok is True
        assert result.orphaned_deleted == 1
        assert result.missing_cleared == 1
        mock_storage.delete.assert_called_once_with("orphan.png")
        db.session.refresh(post_with_orphan)
        assert post_with_orphan.image is None

    def test_handles_storage_errors_gracefully(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.side_effect = OSError("disk error")
        mock_storage.exists.return_value = True

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = apply_orphaned_media_cleanup()

        assert result.ok is True
        assert result.orphaned_deleted == 0
        assert result.missing_cleared == 0
        assert any("disk error" in w for w in result.warnings)

    def test_no_false_positive_on_concurrent_upload(self, app, db) -> None:
        mock_storage = MagicMock()
        post = Post(
            title="Post",
            slug="post",
            body="body",
            image="known.jpg",
            published=True,
        )
        db.session.add(post)
        db.session.commit()

        call_count = 0

        def list_files_side_effect(prefix=""):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ["known.jpg"]
            return ["known.jpg", "concurrent.jpg"]

        mock_storage.list_files.side_effect = list_files_side_effect
        mock_storage.exists.return_value = True

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = apply_orphaned_media_cleanup()

        assert result.ok is True
        assert result.orphaned_deleted == 0
        mock_storage.delete.assert_not_called()

    def test_handles_delete_failure(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["orphan.png"]
        mock_storage.exists.return_value = True
        mock_storage.delete.return_value = False

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = apply_orphaned_media_cleanup()

        assert result.ok is True
        assert result.orphaned_deleted == 0
        assert any("Failed to delete" in w for w in result.warnings)

    def test_no_commit_when_no_missing_refs(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["orphan.png"]
        mock_storage.exists.side_effect = lambda name: name == "used.jpg"

        post = Post(
            title="Post",
            slug="post",
            body="body",
            image="used.jpg",
            published=True,
        )
        db.session.add(post)
        db.session.commit()

        with patch("app.storage.get_storage", return_value=mock_storage):
            with patch("app.extensions.db.session.commit") as mock_commit:
                result = apply_orphaned_media_cleanup()

        assert result.ok is True
        assert result.missing_cleared == 0
        mock_commit.assert_not_called()

    def test_skips_suspicious_filenames_during_cleanup(self, app, db) -> None:
        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["good.jpg", "../escape.png"]
        mock_storage.exists.return_value = True
        mock_storage.delete.return_value = True

        with patch("app.storage.get_storage", return_value=mock_storage):
            result = apply_orphaned_media_cleanup()

        assert result.ok is True
        assert result.orphaned_deleted == 1
        mock_storage.delete.assert_called_once_with("good.jpg")
        assert any("suspicious" in w.lower() for w in result.warnings)
