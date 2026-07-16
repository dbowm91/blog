from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.generate_checksums import generate_checksums, main


class TestGenerateChecksums:
    def test_generates_for_files_in_directory(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "file1.txt").write_text("hello")
        (artifacts_dir / "file2.bin").write_bytes(b"\x00\x01\x02")

        assert generate_checksums(artifacts_dir) is True

        output = artifacts_dir / "checksums.txt"
        assert output.exists()

        lines = [line for line in output.read_text().splitlines() if line.strip()]
        assert len(lines) == 2

    def test_output_format_is_sha256sum_standard(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "test.txt").write_text("content")

        generate_checksums(artifacts_dir)

        line = (artifacts_dir / "checksums.txt").read_text().strip()
        parts = line.split("  ", maxsplit=1)
        assert len(parts) == 2
        sha, name = parts
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)
        assert name == "test.txt"

    def test_sha_values_are_correct(self, artifacts_dir: Path) -> None:
        data = b"hello world"
        (artifacts_dir / "a.txt").write_bytes(data)

        generate_checksums(artifacts_dir)

        line = (artifacts_dir / "checksums.txt").read_text().strip()
        expected = hashlib.sha256(data).hexdigest()
        actual = line.split("  ", maxsplit=1)[0]
        assert actual == expected

    def test_output_sorted_by_filename(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "z.txt").write_text("z")
        (artifacts_dir / "a.txt").write_text("a")
        (artifacts_dir / "m.txt").write_text("m")

        generate_checksums(artifacts_dir)

        names = []
        for line in (artifacts_dir / "checksums.txt").read_text().splitlines():
            if line.strip():
                names.append(line.split("  ", maxsplit=1)[1])
        assert names == ["a.txt", "m.txt", "z.txt"]

    def test_empty_directory_returns_false(self, artifacts_dir: Path) -> None:
        assert generate_checksums(artifacts_dir) is False

    def test_missing_directory_returns_false(self, tmp_path: Path) -> None:
        assert generate_checksums(tmp_path / "nonexistent") is False

    def test_custom_output_path(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "data.bin").write_bytes(b"\xff")

        custom = artifacts_dir / "custom" / "my_checksums.txt"
        custom.parent.mkdir()
        assert generate_checksums(artifacts_dir, output=custom) is True
        assert custom.exists()

    def test_skips_subdirectories(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "file.txt").write_text("ok")
        sub = artifacts_dir / "subdir"
        sub.mkdir()
        (sub / "nested.txt").write_text("nested")

        generate_checksums(artifacts_dir)

        lines = [
            line
            for line in (artifacts_dir / "checksums.txt").read_text().splitlines()
            if line.strip()
        ]
        assert len(lines) == 1
        assert "file.txt" in lines[0]

    def test_main_returns_zero_on_success(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "ok.txt").write_text("data")
        assert main(["--directory", str(artifacts_dir)]) == 0

    def test_main_returns_one_on_empty_directory(self, artifacts_dir: Path) -> None:
        assert main(["--directory", str(artifacts_dir)]) == 1

    def test_main_with_custom_output(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "x.txt").write_text("x")
        out = artifacts_dir / "out.txt"
        assert main(["--directory", str(artifacts_dir), "--output", str(out)]) == 0
        assert out.exists()
