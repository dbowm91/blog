from __future__ import annotations

from pathlib import Path

from app.deployment.install import (
    backup_file,
    execute_installation,
    plan_installation,
    restore_backups,
)
from app.deployment.model import RenderResult


class TestPlanInstallation:
    def test_new_files(self, tmp_path):
        rendered = [
            RenderResult(content="file1", filename="unit1.service", managed=True),
            RenderResult(content="file2", filename="unit2.service", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        assert len(plan.files) == 2
        assert plan.files[0].content == "file1"
        assert plan.files[1].content == "file2"

    def test_skips_existing_without_force(self, tmp_path):
        existing = tmp_path / "unit.service"
        existing.write_text("old content")
        rendered = [
            RenderResult(content="new content", filename="unit.service", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        assert len(plan.files) == 0
        assert any("already exists, skipping" in w for w in plan.warnings)

    def test_overwrites_with_force(self, tmp_path):
        existing = tmp_path / "unit.service"
        existing.write_text("old content")
        rendered = [
            RenderResult(content="new content", filename="unit.service", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path, force=True)
        assert len(plan.files) == 1
        assert plan.files[0].content == "new content"
        assert plan.files[0].backup_path is not None
        assert any("Overwriting" in w for w in plan.warnings)

    def test_preserves_permissions(self, tmp_path):
        rendered = [
            RenderResult(content="c", filename="f.conf", managed=True, permissions=0o600),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        assert plan.files[0].permissions == 0o600

    def test_absolute_filename_not_prepended(self, tmp_path):
        rendered = [
            RenderResult(content="c", filename="/tmp/absolute.conf", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        assert plan.files[0].path == Path("/tmp/absolute.conf")

    def test_empty_rendered_files(self, tmp_path):
        plan = plan_installation([], base_dir=tmp_path)
        assert len(plan.files) == 0
        assert plan.warnings == []


class TestExecuteInstallation:
    def test_writes_files(self, tmp_path):
        rendered = [
            RenderResult(content="hello", filename="a.txt", managed=True),
            RenderResult(content="world", filename="b.txt", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        result = execute_installation(plan)
        assert result.ok is True
        assert len(result.installed_files) == 2
        assert (tmp_path / "a.txt").read_text() == "hello"
        assert (tmp_path / "b.txt").read_text() == "world"

    def test_sets_permissions(self, tmp_path):
        rendered = [
            RenderResult(content="secret", filename="secret.env", managed=True, permissions=0o600),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        result = execute_installation(plan)
        assert result.ok is True
        import os

        mode = os.stat(str(tmp_path / "secret.env")).st_mode & 0o777
        assert mode == 0o600

    def test_dry_run_no_writes(self, tmp_path):
        rendered = [
            RenderResult(content="hello", filename="a.txt", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        result = execute_installation(plan, dry_run=True)
        assert result.ok is True
        assert len(result.installed_files) == 1
        assert not (tmp_path / "a.txt").exists()
        assert any("Dry run" in w for w in result.warnings)

    def test_atomic_write(self, tmp_path):
        rendered = [
            RenderResult(content="content", filename="atomic.txt", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path)
        result = execute_installation(plan)
        assert result.ok is True
        assert (tmp_path / "atomic.txt").read_text() == "content"
        assert not (tmp_path / "atomic.txt.tmp").exists()

    def test_backup_files_tracked(self, tmp_path):
        existing = tmp_path / "unit.service"
        existing.write_text("old")
        rendered = [
            RenderResult(content="new", filename="unit.service", managed=True),
        ]
        plan = plan_installation(rendered, base_dir=tmp_path, force=True)
        result = execute_installation(plan)
        assert result.ok is True
        assert len(result.backed_up_files) == 1
        assert result.backed_up_files[0].suffix == ".bak"


class TestBackupFile:
    def test_creates_backup(self, tmp_path):
        original = tmp_path / "test.txt"
        original.write_text("original content")
        backup = backup_file(original)
        assert backup is not None
        assert backup.exists()
        assert backup.read_text() == "original content"
        assert backup.suffix == ".bak"

    def test_returns_none_for_nonexistent(self, tmp_path):
        nonexistent = tmp_path / "nope.txt"
        result = backup_file(nonexistent)
        assert result is None


class TestRestoreBackups:
    def test_restores_files(self, tmp_path):
        original = tmp_path / "test.txt"
        original.write_text("modified")
        backup = tmp_path / "test.txt.bak"
        backup.write_text("original")
        ok = restore_backups([(original, backup)])
        assert ok is True
        assert original.read_text() == "original"

    def test_returns_false_for_missing_backup(self, tmp_path):
        original = tmp_path / "test.txt"
        original.write_text("content")
        backup = tmp_path / "missing.bak"
        ok = restore_backups([(original, backup)])
        assert ok is False

    def test_empty_list(self):
        ok = restore_backups([])
        assert ok is True

    def test_multiple_files(self, tmp_path):
        files = []
        for i in range(3):
            original = tmp_path / f"file{i}.txt"
            original.write_text(f"modified{i}")
            backup = tmp_path / f"file{i}.txt.bak"
            backup.write_text(f"original{i}")
            files.append((original, backup))
        ok = restore_backups(files)
        assert ok is True
        for i in range(3):
            assert (tmp_path / f"file{i}.txt").read_text() == f"original{i}"


class TestInstallPlan:
    def test_dry_run_default_false(self, tmp_path):
        plan = plan_installation([], base_dir=tmp_path)
        assert plan.dry_run is False

    def test_warnings_populated(self, tmp_path):
        (tmp_path / "existing.txt").write_text("old")
        rendered = [RenderResult(content="new", filename="existing.txt", managed=True)]
        plan = plan_installation(rendered, base_dir=tmp_path)
        assert len(plan.warnings) == 1
