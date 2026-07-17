from __future__ import annotations

from app.deployment.drift import (
    DriftStatus,
    check_drift,
    compute_content_hash,
    load_managed_manifest,
    save_managed_manifest,
)
from pathlib import Path


class TestComputeContentHash:
    def test_consistent_hashes(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_content_hash("hello")
        h2 = compute_content_hash("world")
        assert h1 != h2

    def test_returns_sha256_hex(self):
        h = compute_content_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_string(self):
        h = compute_content_hash("")
        assert len(h) == 64


class TestCheckDrift:
    def test_no_drift(self, tmp_path):
        f1 = tmp_path / "file1.txt"
        f1.write_text("content1")
        f2 = tmp_path / "file2.txt"
        f2.write_text("content2")
        managed = {
            f1: compute_content_hash("content1"),
            f2: compute_content_hash("content2"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is True
        assert report.drift_count == 0
        assert report.managed_count == 2

    def test_missing_files(self, tmp_path):
        missing = tmp_path / "missing.txt"
        managed = {
            missing: compute_content_hash("expected"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is False
        assert report.drift_count == 1
        assert report.items[0].status == DriftStatus.MISSING

    def test_modified_files(self, tmp_path):
        f = tmp_path / "modified.txt"
        f.write_text("actual content")
        managed = {
            f: compute_content_hash("expected content"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is False
        assert report.drift_count == 1
        assert report.items[0].status == DriftStatus.MODIFIED
        assert report.items[0].actual_hash is not None

    def test_unmanaged_files(self, tmp_path):
        managed_file = tmp_path / "managed.txt"
        managed_file.write_text("managed")
        unmanaged_file = tmp_path / "unmanaged.txt"
        unmanaged_file.write_text("unmanaged")
        managed = {
            managed_file: compute_content_hash("managed"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is False
        assert report.unmanaged_count == 1
        assert report.items[0].status == DriftStatus.UNMANAGED

    def test_ignores_bak_tmp_files(self, tmp_path):
        managed_file = tmp_path / "managed.txt"
        managed_file.write_text("content")
        bak_file = tmp_path / "managed.txt.bak"
        bak_file.write_text("old")
        tmp_file = tmp_path / "managed.txt.tmp"
        tmp_file.write_text("temp")
        managed = {
            managed_file: compute_content_hash("content"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is True
        assert report.unmanaged_count == 0

    def test_ignores_subdirectories(self, tmp_path):
        managed_file = tmp_path / "managed.txt"
        managed_file.write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "child.txt").write_text("child")
        managed = {
            managed_file: compute_content_hash("content"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is True

    def test_mixed_drift(self, tmp_path):
        ok_file = tmp_path / "ok.txt"
        ok_file.write_text("ok")
        missing_file = tmp_path / "missing.txt"
        mod_file = tmp_path / "mod.txt"
        mod_file.write_text("actual")
        unmanaged = tmp_path / "extra.txt"
        unmanaged.write_text("extra")
        managed = {
            ok_file: compute_content_hash("ok"),
            missing_file: compute_content_hash("missing"),
            mod_file: compute_content_hash("expected"),
        }
        report = check_drift(managed, tmp_path)
        assert report.clean is False
        assert report.drift_count == 2
        assert report.unmanaged_count == 1
        assert report.managed_count == 3

    def test_scan_dir_not_exists(self, tmp_path):
        scan = tmp_path / "nonexistent"
        managed = {}
        report = check_drift(managed, scan)
        assert report.clean is True


class TestManagedManifest:
    def test_load_nonexistent(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        result = load_managed_manifest(manifest_path)
        assert result == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        files = {
            Path("/etc/unit.service"): "abc123",
            Path("/etc/config.conf"): "def456",
        }
        save_managed_manifest(manifest_path, files)
        loaded = load_managed_manifest(manifest_path)
        assert len(loaded) == 2
        assert loaded[Path("/etc/unit.service")] == "abc123"
        assert loaded[Path("/etc/config.conf")] == "def456"

    def test_atomic_write(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        files = {Path("/f.txt"): "hash"}
        save_managed_manifest(manifest_path, files)
        assert not (tmp_path / "manifest.json.tmp").exists()

    def test_creates_parent_dirs(self, tmp_path):
        manifest_path = tmp_path / "sub" / "dir" / "manifest.json"
        files = {Path("/f.txt"): "hash"}
        save_managed_manifest(manifest_path, files)
        assert manifest_path.exists()

    def test_corrupt_manifest_returns_empty(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("not valid json {{{")
        result = load_managed_manifest(manifest_path)
        assert result == {}

    def test_empty_dict(self, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        save_managed_manifest(manifest_path, {})
        loaded = load_managed_manifest(manifest_path)
        assert loaded == {}
