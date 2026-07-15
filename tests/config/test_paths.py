from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config.paths import resolve_config_path, resolve_env_file_path


class TestResolveConfigPath:
    def test_explicit_cli_path_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cli_file = tmp_path / "config.toml"
        cli_file.write_text("[app]\ntitle = 'CLI'\n")
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        result = resolve_config_path(cli_path=cli_file)
        assert result.selected is not None
        assert result.selected.path == cli_file
        assert result.selected.source == "cli"

    def test_env_var_used(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_config = tmp_path / "env_config.toml"
        env_config.write_text("[app]\ntitle = 'ENV'\n")
        monkeypatch.setenv("DEVLOG_CONFIG", str(env_config))
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.setenv("DEVLOG_CONFIG", str(env_config))
        result = resolve_config_path()
        assert result.selected is not None
        assert result.selected.source == "env_var"

    def test_nonexistent_candidates_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        nonexistent = tmp_path / "nonexistent.toml"
        result = resolve_config_path(cli_path=nonexistent)
        assert result.selected is None
        assert result.reason.startswith("No valid config file")

    def test_cwd_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text("[app]\ntitle = 'CWD'\n")
        result = resolve_config_path()
        assert result.selected is not None
        assert result.selected.source == "cwd"

    def test_symlink_handled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        real_file = tmp_path / "real.toml"
        real_file.write_text("[app]\ntitle = 'Symlink'\n")
        link = tmp_path / "link.toml"
        link.symlink_to(real_file)
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        result = resolve_config_path(cli_path=link)
        assert result.selected is not None
        assert result.selected.is_symlink is True
        assert result.selected.exists is True

    def test_unreadable_file_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        unreadable = tmp_path / "unreadable.toml"
        unreadable.write_text("[app]\ntitle = 'Bad'\n")
        os.chmod(unreadable, 0o000)
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        result = resolve_config_path(cli_path=unreadable)
        assert result.selected is None
        os.chmod(unreadable, 0o644)

    def test_candidates_list_populated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DEVLOG_CONFIG", raising=False)
        result = resolve_config_path()
        assert len(result.candidates) > 0
        sources = [c.source for c in result.candidates]
        assert "cwd" in sources


class TestResolveEnvFilePath:
    def test_explicit_cli_path_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val\n")
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        result = resolve_env_file_path(cli_path=env_file)
        assert result.selected is not None
        assert result.selected.source == "cli"

    def test_env_var_used(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_file = tmp_path / "custom.env"
        env_file.write_text("KEY=val\n")
        monkeypatch.setenv("DEVLOG_ENV_FILE", str(env_file))
        result = resolve_env_file_path()
        assert result.selected is not None
        assert result.selected.source == "env_var"

    def test_cwd_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val\n")
        result = resolve_env_file_path()
        assert result.selected is not None
        assert result.selected.source == "cwd"

    def test_no_env_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        result = resolve_env_file_path()
        assert result.selected is None

    def test_candidates_list_has_expected_sources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DEVLOG_ENV_FILE", raising=False)
        result = resolve_env_file_path()
        sources = [c.source for c in result.candidates]
        assert "cwd" in sources


class TestPathCandidate:
    def test_nonexistent_file_properties(self, tmp_path: Path) -> None:
        p = tmp_path / "nope.txt"
        from app.config.paths import _make_candidate

        c = _make_candidate(p, "test")
        assert c.exists is False
        assert c.is_file is False
        assert c.is_symlink is False
        assert c.readable is False
        assert c.writable is False

    def test_existing_file_properties(self, tmp_path: Path) -> None:
        f = tmp_path / "exists.txt"
        f.write_text("hi")
        from app.config.paths import _make_candidate

        c = _make_candidate(f, "test")
        assert c.exists is True
        assert c.is_file is True
        assert c.readable is True
        assert c.writable is True
