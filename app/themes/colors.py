from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RGB:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for name in ("red", "green", "blue"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be int, got {type(value).__name__}")
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be in 0..255, got {value}")


@dataclass(frozen=True, slots=True)
class RGBA:
    red: int
    green: int
    blue: int
    alpha: float

    def __post_init__(self) -> None:
        for name in ("red", "green", "blue"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be int, got {type(value).__name__}")
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be in 0..255, got {value}")
        if not isinstance(self.alpha, (int, float)) or isinstance(self.alpha, bool):
            raise TypeError(f"alpha must be numeric, got {type(self.alpha).__name__}")
        if not 0.0 <= float(self.alpha) <= 1.0:
            raise ValueError(f"alpha must be in 0.0..1.0, got {self.alpha}")
        object.__setattr__(self, "alpha", float(self.alpha))

    @property
    def rgb(self) -> RGB:
        return RGB(self.red, self.green, self.blue)


def _coerce_byte(value: int) -> int:
    if value <= 0:
        return 0
    if value >= 255:
        return 255
    return value


def bytes_to_rgb(red: int, green: int, blue: int) -> RGB:
    return RGB(_coerce_byte(red), _coerce_byte(green), _coerce_byte(blue))


def alpha_composite(fg: RGBA, bg: RGB) -> RGB:
    a = fg.alpha
    r = round(fg.red * a + bg.red * (1.0 - a))
    g = round(fg.green * a + bg.green * (1.0 - a))
    b = round(fg.blue * a + bg.blue * (1.0 - a))
    return RGB(_coerce_byte(r), _coerce_byte(g), _coerce_byte(b))


def relative_luminance(color: RGB | RGBA) -> float:
    if isinstance(color, RGBA):
        rgb = alpha_composite(color, RGB(255, 255, 255))
    else:
        rgb = color

    def channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r = channel(rgb.red)
    g = channel(rgb.green)
    b = channel(rgb.blue)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: RGB | RGBA, b: RGB | RGBA) -> float:
    la = relative_luminance(a)
    lb = relative_luminance(b)
    lighter = max(la, lb)
    darker = min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def is_dark_background(color: RGB | RGBA, threshold: float = 0.5) -> bool:
    return relative_luminance(color) < threshold


def is_light_background(color: RGB | RGBA, threshold: float = 0.5) -> bool:
    return relative_luminance(color) >= threshold


def mix(a: RGB | RGBA, b: RGB | RGBA, weight: float = 0.5) -> RGB:
    if not isinstance(weight, (int, float)) or isinstance(weight, bool):
        raise TypeError(f"weight must be numeric, got {type(weight).__name__}")
    weight = float(weight)
    if not 0.0 <= weight <= 1.0:
        raise ValueError(f"weight must be in 0.0..1.0, got {weight}")
    ra = a if isinstance(a, RGB) else alpha_composite(a, RGB(255, 255, 255))
    rb = b if isinstance(b, RGB) else alpha_composite(b, RGB(255, 255, 255))
    r = round(ra.red * (1 - weight) + rb.red * weight)
    g = round(ra.green * (1 - weight) + rb.green * weight)
    b_ = round(ra.blue * (1 - weight) + rb.blue * weight)
    return RGB(_coerce_byte(r), _coerce_byte(g), _coerce_byte(b_))


def adjust_lightness(color: RGB | RGBA, factor: float) -> RGB:
    if not isinstance(factor, (int, float)) or isinstance(factor, bool):
        raise TypeError(f"factor must be numeric, got {type(factor).__name__}")
    factor = float(factor)
    if factor < 0:
        raise ValueError(f"factor must be >= 0, got {factor}")
    base = color if isinstance(color, RGB) else alpha_composite(color, RGB(255, 255, 255))

    def channel(c: int) -> int:
        value = c / 255.0
        if factor >= 1.0:
            new = value + (1.0 - value) * (factor - 1.0)
        else:
            new = value * factor
        return _coerce_byte(round(new * 255))

    return RGB(channel(base.red), channel(base.green), channel(base.blue))


def to_hex(rgb: RGB, *, include_alpha: float | None = None) -> str:
    if include_alpha is not None:
        if not isinstance(include_alpha, (int, float)) or isinstance(include_alpha, bool):
            raise TypeError(f"include_alpha must be numeric, got {type(include_alpha).__name__}")
        if not 0.0 <= float(include_alpha) <= 1.0:
            raise ValueError(f"include_alpha must be in 0.0..1.0, got {include_alpha}")
        a = round(float(include_alpha) * 255)
        return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}{a:02x}"
    return f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"


def to_css(rgb: RGB, *, alpha: float | None = None) -> str:
    if alpha is None:
        return to_hex(rgb)
    return to_hex(rgb, include_alpha=alpha)


def from_hex(value: str) -> RGBA:
    if not isinstance(value, str):
        raise TypeError(f"color value must be str, got {type(value).__name__}")
    if not value:
        raise ValueError("color value is empty")
    if value != value.strip():
        raise ValueError(f"color contains leading or trailing whitespace: {value!r}")
    if not value.startswith("#"):
        raise ValueError(f"color must start with '#': {value!r}")
    body = value[1:]
    if any(ch.isspace() for ch in body):
        raise ValueError(f"color contains whitespace: {value!r}")
    if ";" in body or "," in body or "(" in body or ")" in body:
        raise ValueError(f"color contains forbidden delimiter: {value!r}")
    if any(not (ch.isalnum()) for ch in body):
        raise ValueError(f"color contains non-alphanumeric character: {value!r}")
    lowered = body.lower()
    if not all(ch in "0123456789abcdef" for ch in lowered):
        raise ValueError(f"color contains non-hex character: {value!r}")

    if len(lowered) == 6:
        red = int(lowered[0:2], 16)
        green = int(lowered[2:4], 16)
        blue = int(lowered[4:6], 16)
        return RGBA(red, green, blue, 1.0)
    if len(lowered) == 8:
        red = int(lowered[0:2], 16)
        green = int(lowered[2:4], 16)
        blue = int(lowered[4:6], 16)
        alpha_byte = int(lowered[6:8], 16)
        return RGBA(red, green, blue, alpha_byte / 255.0)
    raise ValueError(f"hex color must be 6 or 8 digits, got {len(lowered)}: {value!r}")


def wcag_level(ratio: float) -> str:
    if ratio >= 7.0:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3.0:
        return "AA-large"
    return "fail"


def _hsl_to_rgb(h: float, s: float, lightness: float) -> RGB:
    h = h % 1.0
    s = max(0.0, min(1.0, s))
    lightness = max(0.0, min(1.0, lightness))

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    if s == 0:
        value = lightness
        return RGB(
            _coerce_byte(round(value * 255)),
            _coerce_byte(round(value * 255)),
            _coerce_byte(round(value * 255)),
        )

    q = lightness + s - lightness * s if lightness < 0.5 else lightness + s - lightness * s
    p = 2 * lightness - q
    r = hue_to_rgb(p, q, h + 1 / 3)
    g = hue_to_rgb(p, q, h)
    b = hue_to_rgb(p, q, h - 1 / 3)
    return RGB(
        _coerce_byte(round(r * 255)), _coerce_byte(round(g * 255)), _coerce_byte(round(b * 255))
    )


def _rgb_to_hsl(color: RGB) -> tuple[float, float, float]:
    r = color.red / 255.0
    g = color.green / 255.0
    b = color.blue / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    delta = mx - mn
    lightness = (mx + mn) / 2.0
    if delta == 0:
        return 0.0, 0.0, lightness
    denom = mx + mn if mx + mn > 0 else 1.0
    s = delta / (2 - mx - mn) if lightness > 0.5 else delta / denom
    if mx == r:
        h = ((g - b) / delta) % 6
    elif mx == g:
        h = (b - r) / delta + 2
    else:
        h = (r - g) / delta + 4
    h /= 6.0
    if h < 0:
        h += 1.0
    return h, s, lightness


def shift_lightness(color: RGB | RGBA, delta: float) -> RGB:
    if not isinstance(delta, (int, float)) or isinstance(delta, bool):
        raise TypeError(f"delta must be numeric, got {type(delta).__name__}")
    base = color if isinstance(color, RGB) else alpha_composite(color, RGB(255, 255, 255))
    h, s, lightness = _rgb_to_hsl(base)
    new_l = max(0.0, min(1.0, lightness + float(delta)))
    return _hsl_to_rgb(h, s, new_l)


__all__ = [
    "RGB",
    "RGBA",
    "adjust_lightness",
    "alpha_composite",
    "bytes_to_rgb",
    "contrast_ratio",
    "from_hex",
    "is_dark_background",
    "is_light_background",
    "mix",
    "relative_luminance",
    "shift_lightness",
    "to_css",
    "to_hex",
    "wcag_level",
]
