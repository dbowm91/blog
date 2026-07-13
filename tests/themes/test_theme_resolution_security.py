from pathlib import Path

import pytest

from app.themes.resources import (
    ThemeSource,
    _candidate_files,
    _is_inside,
    discover_external,
    validate_theme_name,
)


class TestValidateThemeNameSecurity:
    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_theme_name("")

    def test_forward_slash_rejected(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_theme_name("foo/bar")

    def test_backslash_rejected(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_theme_name("foo\\bar")

    def test_dotdot_top_level_rejected(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_theme_name("../etc/passwd")

    def test_dotdot_in_middle_rejected(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_theme_name("foo/../bar")

    def test_absolute_unix_rejected(self):
        with pytest.raises(ValueError):
            validate_theme_name("/etc/passwd")

    def test_absolute_windows_rejected(self):
        with pytest.raises(ValueError):
            validate_theme_name("C:\\Windows")

    def test_nul_character_rejected(self):
        with pytest.raises(ValueError, match="NUL or control"):
            validate_theme_name("foo\x00bar")

    def test_control_character_rejected(self):
        with pytest.raises(ValueError, match="NUL or control"):
            validate_theme_name("foo\x01bar")

    def test_control_character_bel_rejected(self):
        with pytest.raises(ValueError, match="NUL or control"):
            validate_theme_name("foo\x07bar")

    def test_control_char_below_32_rejected(self):
        with pytest.raises(ValueError):
            validate_theme_name("foo\x1fbar")

    def test_too_long_name_rejected(self):
        name = "a" * 201
        with pytest.raises(ValueError, match="must not exceed"):
            validate_theme_name(name)

    def test_max_length_name_accepted(self):
        name = "a" * 200
        result = validate_theme_name(name)
        assert result == name

    def test_dotdot_not_in_segments_not_rejected(self):
        result = validate_theme_name("foo..bar")
        assert result == Path("foo..bar").stem


class TestValidateThemeNameValidInputs:
    def test_catppuccin_mocha(self):
        assert validate_theme_name("catppuccin-mocha") == "catppuccin-mocha"

    def test_rose_pine_with_space(self):
        assert validate_theme_name("Rose Pine") == "Rose Pine"

    def test_discord_with_parentheses_and_underscores(self):
        assert validate_theme_name("Discord (80_ Saturation)") == "Discord (80_ Saturation)"

    def test_base16_hyphenated(self):
        assert validate_theme_name("base16-atelier-forest-light") == "base16-atelier-forest-light"

    def test_with_dots(self):
        assert validate_theme_name("my.theme.name") == Path("my.theme.name").stem

    def test_with_underscores(self):
        assert validate_theme_name("my_theme") == "my_theme"

    def test_with_multiple_spaces(self):
        assert validate_theme_name("hello world test") == "hello world test"

    def test_with_single_dot_extension(self):
        assert validate_theme_name("theme.toml") == "theme"

    def test_with_multiple_dots_extension(self):
        assert validate_theme_name("theme.test.toml") == "theme.test"

    def test_unicode_letters(self):
        assert validate_theme_name("T\u00e9ma Fran\u00e7ais") == "T\u00e9ma Fran\u00e7ais"

    def test_numbers_only(self):
        assert validate_theme_name("12345") == "12345"


class TestIsInside:
    def test_path_inside_root(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        child = root / "sub" / "file.toml"
        child.parent.mkdir()
        child.touch()
        assert _is_inside(child, root) is True

    def test_path_outside_root(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        other = tmp_path / "other" / "file.toml"
        other.parent.mkdir()
        other.touch()
        assert _is_inside(other, root) is False

    def test_symlink_escaping_root(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        outside_target = tmp_path / "outside"
        outside_target.mkdir()
        link = root / "escape"
        link.symlink_to(outside_target)
        assert _is_inside(link, root) is False


class TestSymlinkEscapeRejection:
    def test_symlink_pointing_outside_is_skipped(self, tmp_path):
        external_root = tmp_path / "themes"
        external_root.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "evil.toml"
        outside_file.write_text("[theme]\nname = 'evil'\n")

        symlink = external_root / "evil.toml"
        symlink.symlink_to(outside_file)

        results = discover_external(external_root)
        assert len(results) == 0

    def test_symlink_pointing_inside_is_accepted(self, tmp_path):
        external_root = tmp_path / "themes"
        external_root.mkdir()
        real_file = external_root / "real.toml"
        real_file.write_text("[theme]\nname = 'real'\n")

        symlink = external_root / "link.toml"
        symlink.symlink_to(real_file)

        results = discover_external(external_root)
        names = [r.canonical_name for r in results]
        assert "real" in names


class TestCandidateFilesSecurity:
    def test_hidden_files_skipped(self, tmp_path):
        hidden = tmp_path / ".hidden.toml"
        hidden.write_text("")
        visible = tmp_path / "visible.toml"
        visible.write_text("")

        results = _candidate_files(tmp_path)
        assert len(results) == 1
        assert results[0].name == "visible.toml"

    def test_non_toml_files_skipped(self, tmp_path):
        txt = tmp_path / "theme.txt"
        txt.write_text("")
        toml = tmp_path / "theme.toml"
        toml.write_text("")

        results = _candidate_files(tmp_path)
        assert len(results) == 1
        assert results[0].name == "theme.toml"

    def test_directories_skipped(self, tmp_path):
        d = tmp_path / "subdir.toml"
        d.mkdir()
        f = tmp_path / "file.toml"
        f.write_text("")

        results = _candidate_files(tmp_path)
        assert len(results) == 1
        assert results[0].name == "file.toml"

    def test_nonexistent_directory_returns_empty(self, tmp_path):
        missing = tmp_path / "nope"
        results = _candidate_files(missing)
        assert results == []


class TestDiscoverExternalSecurity:
    def test_nonexistent_root_returns_empty(self, tmp_path):
        results = discover_external(tmp_path / "nonexistent")
        assert results == []

    def test_file_outside_root_is_skipped(self, tmp_path):
        external_root = tmp_path / "themes"
        external_root.mkdir()
        real = external_root / "good.toml"
        real.write_text("[theme]\nname = 'good'\n")

        results = discover_external(external_root)
        assert len(results) == 1
        assert results[0].source == ThemeSource.EXTERNAL

    def test_permission_denied_on_root_returns_empty(self, tmp_path):
        external_root = tmp_path / "themes"
        external_root.mkdir()
        external_root.chmod(0o000)
        try:
            results = discover_external(external_root)
            assert results == []
        finally:
            external_root.chmod(0o755)

    def test_max_file_size_enforced(self, tmp_path):
        external_root = tmp_path / "themes"
        external_root.mkdir()
        big = external_root / "big.toml"
        big.write_text("x" * 1_048_577)

        small = external_root / "small.toml"
        small.write_text("[theme]\nname = 'small'\n")

        results = discover_external(external_root)
        assert len(results) == 1
        assert results[0].canonical_name == "small"

    def test_hidden_toml_files_skipped(self, tmp_path):
        external_root = tmp_path / "themes"
        external_root.mkdir()
        hidden = external_root / ".secret.toml"
        hidden.write_text("[theme]\nname = 'secret'\n")
        visible = external_root / "public.toml"
        visible.write_text("[theme]\nname = 'public'\n")

        results = discover_external(external_root)
        assert len(results) == 1
        assert results[0].canonical_name == "public"


class TestEncodedSeparatorAttacks:
    def test_percent_encoded_slash(self):
        result = validate_theme_name("foo%2Fbar")
        assert result == "foo%2Fbar"

    def test_double_encoded_slash(self):
        result = validate_theme_name("foo%252Fbar")
        assert result == "foo%252Fbar"

    def test_encoded_dotdot(self):
        result = validate_theme_name("foo%2E%2Ebar")
        assert result == "foo%2E%2Ebar"

    def test_unicode_slash_variant(self):
        result = validate_theme_name("foo\u2215bar")
        assert result == "foo\u2215bar"

    def test_unicode_backslash_variant(self):
        result = validate_theme_name("foo\u2216bar")
        assert result == "foo\u2216bar"
