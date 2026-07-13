from __future__ import annotations

from pathlib import Path

import pytest

from app.themes import halloy
from app.themes.halloy import (
    HalloyTheme,
    SCHEMA_VERSION,
    ThemeColorError,
    ThemeParseError,
    ThemeSchemaError,
    parse_halloy_theme,
    parse_halloy_theme_bytes,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CATALOG = Path(__file__).resolve().parent.parent.parent / "themes"


def _load(name: str) -> HalloyTheme:
    return parse_halloy_theme(FIXTURES / name)


def _theme_text(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestMinimal:
    def test_parses(self) -> None:
        theme = _load("minimal.toml")
        assert theme.schema_version == SCHEMA_VERSION
        assert theme.source_name == "minimal.toml"

    def test_general_section(self) -> None:
        theme = _load("minimal.toml")
        assert theme.general.background.red == 0x10

    def test_all_required_sections_present(self) -> None:
        theme = _load("minimal.toml")
        assert theme.text.primary.green == 0xAA
        assert theme.buffer.background.green == 0x20
        assert theme.buttons.primary["background_hover"].red == 0x22
        assert theme.buttons.secondary["background_hover"].green == 0x66


class TestLightDark:
    def test_light_classified(self) -> None:
        theme = _load("light.toml")
        from app.themes import colors

        bg = theme.general.background
        assert colors.is_light_background(bg)

    def test_dark_classified(self) -> None:
        theme = _load("dark.toml")
        from app.themes import colors

        bg = theme.general.background
        assert colors.is_dark_background(bg)


class TestAlphaColors:
    def test_alpha_preserved(self) -> None:
        theme = _load("alpha.toml")
        assert theme.buffer.border.alpha == 0.0
        assert theme.buffer.code.alpha == 1.0

    def test_eight_digit_normalized(self) -> None:
        theme = _load("alpha.toml")
        from app.themes import colors

        css = colors.to_hex(
            theme.text.secondary.rgb,
            include_alpha=theme.text.secondary.alpha,
        )
        assert css == "#ccccccdd"


class TestExtraSections:
    def test_parsed_silently(self) -> None:
        theme = _load("extra_sections.toml")
        assert "metadata" in theme.extra_top_sections
        assert "experimental" in theme.extra_top_sections

    def test_no_failure_for_unknown(self) -> None:
        theme = _load("extra_sections.toml")
        assert theme.general.background.red == 0x10


class TestFailures:
    def test_malformed_toml(self) -> None:
        with pytest.raises(ThemeParseError) as exc:
            parse_halloy_theme(FIXTURES / "malformed.toml")
        assert "malformed.toml" in str(exc.value)

    def test_empty_file(self) -> None:
        with pytest.raises(ThemeParseError):
            parse_halloy_theme_bytes(b"", source_name="empty.toml")

    def test_invalid_color(self) -> None:
        with pytest.raises(ThemeColorError) as exc:
            _load("invalid_color.toml")
        assert exc.value.field_path == "general.background"
        assert exc.value.raw_value == "rgb(0, 0, 0)"

    def test_injection_attempt(self) -> None:
        with pytest.raises(ThemeColorError):
            _load("injection.toml")

    def test_missing_general(self) -> None:
        data = b"""
[text]
primary = "#000000"
secondary = "#000000"
tertiary = "#000000"
success = "#000000"
error = "#000000"
"""
        with pytest.raises(ThemeSchemaError) as exc:
            parse_halloy_theme_bytes(data, source_name="no_general.toml")
        assert exc.value.field_path == "general"

    def test_missing_buffer_section(self) -> None:
        data = b"""
[general]
background = "#000000"
border = "#000000"
horizontal_rule = "#000000"
unread_indicator = "#000000"

[text]
primary = "#000000"
secondary = "#000000"
tertiary = "#000000"
success = "#000000"
error = "#000000"

[buttons.primary]
background = "#000000"
background_hover = "#000000"
background_selected = "#000000"
background_selected_hover = "#000000"

[buttons.secondary]
background = "#000000"
background_hover = "#000000"
background_selected = "#000000"
background_selected_hover = "#000000"
"""
        with pytest.raises(ThemeSchemaError) as exc:
            parse_halloy_theme_bytes(data, source_name="no_buffer.toml")
        assert exc.value.field_path == "buffer"

    def test_wrong_section_type(self) -> None:
        data = b"""
[general]
background = 42
border = "#202020"
horizontal_rule = "#303030"
unread_indicator = "#404040"
"""
        with pytest.raises(ThemeColorError) as exc:
            parse_halloy_theme_bytes(data, source_name="wrong.toml")
        assert exc.value.field_path == "general.background"


class TestErrorContext:
    def test_source_name_in_error(self) -> None:
        with pytest.raises(ThemeParseError) as exc:
            parse_halloy_theme_bytes(b"[general\nbackground=1", source_name="myfile.toml")
        assert "myfile.toml" in str(exc.value)

    def test_field_path_in_color_error(self) -> None:
        with pytest.raises(ThemeColorError) as exc:
            parse_halloy_theme_bytes(
                b"""
[general]
background = "#FFFFFF"
border = "#202020"
horizontal_rule = "#303030"
unread_indicator = "bad"
""",
                source_name="ctx.toml",
            )
        assert exc.value.field_path == "general.unread_indicator"
        assert exc.value.raw_value == "bad"

    def test_parse_error_carries_source(self) -> None:
        with pytest.raises(ThemeParseError) as exc:
            parse_halloy_theme_bytes(b"", source_name="empty.toml")
        assert exc.value.source == "empty.toml"


class TestBytesAPI:
    def test_parse_halloy_theme_bytes(self) -> None:
        data = _theme_text("full.toml")
        theme = parse_halloy_theme_bytes(data, source_name="full.toml")
        assert theme.source_name == "full.toml"

    def test_parse_halloy_theme_bytes_with_default_source(self) -> None:
        data = _theme_text("full.toml")
        theme = parse_halloy_theme_bytes(data, source_name="x.toml")
        assert theme.source_name == "x.toml"

    def test_parse_halloy_theme_path(self) -> None:
        theme = parse_halloy_theme(FIXTURES / "full.toml")
        assert isinstance(theme, HalloyTheme)

    def test_parse_halloy_theme_stream(self) -> None:
        from io import BytesIO

        data = _theme_text("full.toml")
        theme = parse_halloy_theme(BytesIO(data))
        assert isinstance(theme, HalloyTheme)

    def test_parse_halloy_theme_unsupported_type(self) -> None:
        with pytest.raises(TypeError):
            parse_halloy_theme(12345)  # type: ignore[arg-type]

    def test_path_not_found(self) -> None:
        with pytest.raises(ThemeParseError):
            parse_halloy_theme("/nonexistent/path.toml")


class TestCatalog:
    @pytest.fixture
    def catalog_files(self) -> list[Path]:
        return sorted(
            p
            for p in CATALOG.glob("*.toml")
            if not p.name.startswith("._") and not p.name.startswith(".")
        )

    @pytest.mark.parametrize(
        "path",
        [p for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
        ids=[p.stem for p in sorted(CATALOG.glob("*.toml")) if not p.name.startswith("._")],
    )
    def test_each_catalog_theme_parses(self, path: Path) -> None:
        data = path.read_bytes()
        assert len(data) > 0, f"{path.name} is empty"
        assert len(data) < 100_000, f"{path.name} is unexpectedly large: {len(data)} bytes"
        theme = parse_halloy_theme_bytes(data, source_name=path.name)
        assert theme.schema_version == SCHEMA_VERSION
        assert theme.source_name == path.name
        assert theme.general.background.red >= 0
        assert theme.buffer.border_selected.green >= 0
        assert theme.buttons.primary
        assert theme.buttons.secondary
        assert theme.buffer.server_messages.default is not None

    def test_catalog_size(self, catalog_files: list[Path]) -> None:
        assert len(catalog_files) == 50


class TestNoCoupling:
    def test_parser_imports_no_flask(self) -> None:
        source = Path(halloy.__file__).read_text(encoding="utf-8")
        forbidden = ["from flask", "import flask", "from app import", "from app.routes"]
        for token in forbidden:
            assert token not in source, f"halloy.py must not import {token!r}"

    def test_colors_imports_no_flask(self) -> None:
        from app.themes import colors

        source = Path(colors.__file__).read_text(encoding="utf-8")
        forbidden = ["from flask", "import flask", "from app import"]
        for token in forbidden:
            assert token not in source, f"colors.py must not import {token!r}"
