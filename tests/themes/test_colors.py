from __future__ import annotations

import pytest

from app.themes import colors
from app.themes.colors import RGB, RGBA, from_hex


class TestFromHex:
    def test_six_digit(self) -> None:
        result = from_hex("#FF0000")
        assert result.red == 255
        assert result.green == 0
        assert result.blue == 0
        assert result.alpha == 1.0

    def test_eight_digit(self) -> None:
        result = from_hex("#FF0000FF")
        assert result.red == 255
        assert result.green == 0
        assert result.blue == 0
        assert result.alpha == 1.0

    def test_lowercase_normalization(self) -> None:
        result = from_hex("#AaBbCc")
        assert (result.red, result.green, result.blue) == (0xAA, 0xBB, 0xCC)

    def test_alpha_byte_values(self) -> None:
        assert from_hex("#00000000").alpha == 0.0
        assert from_hex("#FFFFFFFF").alpha == 1.0
        assert from_hex("#00000080").alpha == pytest.approx(128 / 255)

    @pytest.mark.parametrize(
        "bad",
        [
            "rgb(0,0,0)",
            "rgba(0,0,0,0.5)",
            "red",
            " #FFFFFF",
            "#FFFFFF ",
            "FF0000",
            "#FFFFFFA",
            "#FFF",
            "#FFFFFFFFF",
            "#000000;",
            "#000000,0",
            "#FFFFFF\t",
            " #FFFFFF",
        ],
    )
    def test_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            from_hex(bad)

    def test_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            from_hex(123)  # type: ignore[arg-type]

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            from_hex("")


class TestHexRoundtrip:
    @pytest.mark.parametrize(
        "value",
        ["#000000", "#FFFFFF", "#123456", "#ABCDEF"],
    )
    def test_six_digit_roundtrip(self, value: str) -> None:
        parsed = from_hex(value)
        assert colors.to_hex(parsed.rgb) == value.lower()

    @pytest.mark.parametrize(
        "value, alpha_int",
        [
            ("#00000000", 0),
            ("#FFFFFFFF", 255),
            ("#12345680", 128),
            ("#ABCDEFCC", 204),
        ],
    )
    def test_eight_digit_roundtrip(self, value: str, alpha_int: int) -> None:
        parsed = from_hex(value)
        out = colors.to_hex(parsed.rgb, include_alpha=alpha_int / 255)
        assert out == value.lower()


class TestToCss:
    def test_no_alpha(self) -> None:
        assert colors.to_css(RGB(255, 0, 0)) == "#ff0000"

    def test_with_alpha(self) -> None:
        assert colors.to_css(RGB(255, 0, 0), alpha=0.5) == "#ff000080"

    def test_alpha_clamped(self) -> None:
        with pytest.raises(ValueError):
            colors.to_css(RGB(0, 0, 0), alpha=1.5)


class TestAlphaComposite:
    def test_fully_opaque_unchanged(self) -> None:
        fg = RGBA(255, 0, 0, 1.0)
        bg = RGB(0, 0, 0)
        assert colors.alpha_composite(fg, bg) == RGB(255, 0, 0)

    def test_fully_transparent_returns_background(self) -> None:
        fg = RGBA(255, 0, 0, 0.0)
        bg = RGB(0, 0, 255)
        assert colors.alpha_composite(fg, bg) == RGB(0, 0, 255)

    def test_half_alpha_on_white(self) -> None:
        fg = RGBA(255, 0, 0, 0.5)
        assert colors.alpha_composite(fg, RGB(255, 255, 255)) == RGB(255, 128, 128)

    def test_half_alpha_on_black(self) -> None:
        fg = RGBA(255, 0, 0, 0.5)
        assert colors.alpha_composite(fg, RGB(0, 0, 0)) == RGB(128, 0, 0)


class TestRelativeLuminance:
    def test_white(self) -> None:
        assert colors.relative_luminance(RGB(255, 255, 255)) == pytest.approx(1.0)

    def test_black(self) -> None:
        assert colors.relative_luminance(RGB(0, 0, 0)) == pytest.approx(0.0)

    def test_rgba_against_white(self) -> None:
        op = colors.relative_luminance(RGBA(0, 0, 0, 1.0))
        trans = colors.relative_luminance(RGBA(0, 0, 0, 0.0))
        assert op < trans


class TestContrastRatio:
    def test_black_vs_white(self) -> None:
        assert colors.contrast_ratio(RGB(0, 0, 0), RGB(255, 255, 255)) == pytest.approx(21.0)

    def test_symmetric(self) -> None:
        a = RGB(255, 0, 0)
        b = RGB(0, 255, 0)
        assert colors.contrast_ratio(a, b) == colors.contrast_ratio(b, a)

    @pytest.mark.parametrize(
        "ratio, level",
        [
            (21.0, "AAA"),
            (7.0, "AAA"),
            (4.5, "AA"),
            (3.0, "AA-large"),
            (2.9, "fail"),
        ],
    )
    def test_wcag_levels(self, ratio: float, level: str) -> None:
        assert colors.wcag_level(ratio) == level


class TestDarkLightClassification:
    def test_black_is_dark(self) -> None:
        assert colors.is_dark_background(RGB(0, 0, 0))

    def test_white_is_light(self) -> None:
        assert colors.is_light_background(RGB(255, 255, 255))

    def test_threshold(self) -> None:
        threshold = 0.5
        approx_eq = RGB(127, 127, 127)
        lum = colors.relative_luminance(approx_eq)
        if lum >= threshold:
            assert colors.is_light_background(approx_eq)
        else:
            assert colors.is_dark_background(approx_eq)


class TestMix:
    def test_equal_mix(self) -> None:
        assert colors.mix(RGB(255, 0, 0), RGB(0, 0, 255)) == RGB(128, 0, 128)

    def test_full_weight_returns_other(self) -> None:
        assert colors.mix(RGB(255, 0, 0), RGB(0, 0, 255), weight=1.0) == RGB(0, 0, 255)

    def test_zero_weight_returns_first(self) -> None:
        assert colors.mix(RGB(255, 0, 0), RGB(0, 0, 255), weight=0.0) == RGB(255, 0, 0)

    def test_invalid_weight(self) -> None:
        with pytest.raises(ValueError):
            colors.mix(RGB(0, 0, 0), RGB(255, 255, 255), weight=1.5)


class TestAdjustLightness:
    def test_darken(self) -> None:
        result = colors.adjust_lightness(RGB(128, 128, 128), 0.5)
        assert result == RGB(64, 64, 64)

    def test_lighten(self) -> None:
        result = colors.adjust_lightness(RGB(128, 128, 128), 1.5)
        assert result.red > 128

    def test_zero_factor(self) -> None:
        assert colors.adjust_lightness(RGB(128, 128, 128), 0.0) == RGB(0, 0, 0)

    def test_negative_factor_rejected(self) -> None:
        with pytest.raises(ValueError):
            colors.adjust_lightness(RGB(128, 128, 128), -0.5)


class TestShiftLightness:
    def test_positive_delta_lightens(self) -> None:
        result = colors.shift_lightness(RGB(128, 128, 128), 0.5)
        assert colors.relative_luminance(result) > colors.relative_luminance(RGB(128, 128, 128))

    def test_negative_delta_darkens(self) -> None:
        result = colors.shift_lightness(RGB(128, 128, 128), -0.5)
        assert colors.relative_luminance(result) < colors.relative_luminance(RGB(128, 128, 128))

    def test_clamps_to_range(self) -> None:
        result = colors.shift_lightness(RGB(255, 255, 255), 0.5)
        assert result == RGB(255, 255, 255)
        result = colors.shift_lightness(RGB(0, 0, 0), -0.5)
        assert result == RGB(0, 0, 0)


class TestRgbValidation:
    def test_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            RGB(256, 0, 0)

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            RGB(-1, 0, 0)

    def test_rejects_non_int(self) -> None:
        with pytest.raises(TypeError):
            RGB(1.5, 0, 0)  # type: ignore[arg-type]

    def test_rgba_alpha_validation(self) -> None:
        with pytest.raises(ValueError):
            RGBA(0, 0, 0, 1.5)
        with pytest.raises(ValueError):
            RGBA(0, 0, 0, -0.1)


class TestDeterminism:
    def test_round_trip_does_not_change_normalized_value(self) -> None:
        original = from_hex("#aAbBcC")
        out = colors.to_hex(original.rgb)
        again = from_hex(out)
        assert original == again

    def test_eight_digit_roundtrip_deterministic(self) -> None:
        original = from_hex("#aAbBcC80")
        out = colors.to_hex(original.rgb, include_alpha=original.alpha)
        again = from_hex(out)
        assert original == again
