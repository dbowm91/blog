from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from scripts.check_release_artifacts import (
    compute_sha256,
    parse_checksums,
    verify_checksums,
    verify_wheel_filename,
    verify_wheel_contents,
    main,
)


class TestComputeSha256:
    def test_returns_correct_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "data.txt"
        f.write_text("hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert compute_sha256(f) == expected

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert compute_sha256(f) == expected


class TestParseChecksums:
    def test_valid_checksums(self, tmp_path: Path) -> None:
        cs = tmp_path / "checksums.txt"
        cs.write_text("aaa111  file1.txt\nbbb222  file2.whl\n")
        result = parse_checksums(cs)
        assert result == {"file1.txt": "aaa111", "file2.whl": "bbb222"}

    def test_ignores_blank_lines(self, tmp_path: Path) -> None:
        cs = tmp_path / "checksums.txt"
        cs.write_text("\n\naaa111  file.txt\n\n\n")
        result = parse_checksums(cs)
        assert result == {"file.txt": "aaa111"}

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        cs = tmp_path / "checksums.txt"
        cs.write_text("badline\naaa111  file.txt\n")
        result = parse_checksums(cs)
        assert result == {"file.txt": "aaa111"}


class TestVerifyChecksums:
    def test_pass_when_all_match(
        self, artifacts_dir: Path, sample_wheel: Path, sample_checksums: Path
    ) -> None:
        checksums = parse_checksums(sample_checksums)
        passed, failed, errors = verify_checksums(checksums, artifacts_dir)
        assert passed == 1
        assert failed == 0
        assert errors == []

    def test_fail_on_mismatch(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "a.txt").write_text("data")
        bad = artifacts_dir / "checksums.txt"
        bad.write_text("0000000000000000000000000000000000000000000000000000000000000000  a.txt\n")
        checksums = parse_checksums(bad)
        passed, failed, errors = verify_checksums(checksums, artifacts_dir)
        assert passed == 0
        assert failed == 1
        assert len(errors) == 1
        assert "CHECKSUM MISMATCH" in errors[0]

    def test_fail_on_missing_file(self, artifacts_dir: Path) -> None:
        bad = artifacts_dir / "checksums.txt"
        bad.write_text("aaa111  missing.txt\n")
        checksums = parse_checksums(bad)
        passed, failed, errors = verify_checksums(checksums, artifacts_dir)
        assert passed == 0
        assert failed == 1
        assert "MISSING" in errors[0]


class TestVerifyWheelFilename:
    def test_valid_wheel_name(self, artifacts_dir: Path, sample_wheel: Path) -> None:
        ok, msg = verify_wheel_filename(artifacts_dir)
        assert ok is True
        assert "1.0.0" in msg

    def test_no_wheels_returns_false(self, artifacts_dir: Path) -> None:
        ok, msg = verify_wheel_filename(artifacts_dir)
        assert ok is False
        assert "no .whl files" in msg

    def test_wrong_pattern_returns_false(self, artifacts_dir: Path) -> None:
        bad = artifacts_dir / "wrong_name-1.0.0.whl"
        bad.write_text("fake")
        ok, msg = verify_wheel_filename(artifacts_dir)
        assert ok is False
        assert "no wheel matches" in msg


class TestVerifyWheelContents:
    def test_valid_wheel_passes_all_prefixes(self, artifacts_dir: Path, sample_wheel: Path) -> None:
        from scripts.check_release_artifacts import EXPECTED_WHEEL_PREFIXES

        passed, failed, errors = verify_wheel_contents(sample_wheel)
        assert passed == len(EXPECTED_WHEEL_PREFIXES)
        assert failed == 0
        assert errors == []

    def test_bad_zip_returns_error(self, artifacts_dir: Path) -> None:
        bad = artifacts_dir / "bad.whl"
        bad.write_text("not a zip")
        passed, failed, errors = verify_wheel_contents(bad)
        assert passed == 0
        assert failed == 1
        assert "bad wheel file" in errors[0]

    def test_missing_prefix_fails(self, artifacts_dir: Path) -> None:
        minimal = artifacts_dir / "minimal.whl"
        with zipfile.ZipFile(minimal, "w") as zf:
            zf.writestr("app/static/css/base.css", "body{}")
        passed, failed, errors = verify_wheel_contents(minimal)
        assert failed > 0
        assert any("MISSING" in e for e in errors)


class TestMainFunction:
    def test_missing_directory_returns_one(self, tmp_path: Path) -> None:
        assert (
            main(["--directory", str(tmp_path / "nope"), "--checksums", str(tmp_path / "nope")])
            == 1
        )

    def test_missing_checksums_returns_one(self, artifacts_dir: Path) -> None:
        assert (
            main(
                ["--directory", str(artifacts_dir), "--checksums", str(artifacts_dir / "nope.txt")]
            )
            == 1
        )

    def test_valid_artifacts_return_zero(
        self, artifacts_dir: Path, sample_wheel: Path, sample_checksums: Path
    ) -> None:
        assert main(["--directory", str(artifacts_dir), "--checksums", str(sample_checksums)]) == 0

    def test_empty_checksums_file_returns_one(self, artifacts_dir: Path) -> None:
        cs = artifacts_dir / "checksums.txt"
        cs.write_text("")
        assert main(["--directory", str(artifacts_dir), "--checksums", str(cs)]) == 1
