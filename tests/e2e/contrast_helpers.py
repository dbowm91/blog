"""Contrast measurement helpers for the browser-level tests.

The page is painted in layers: a translucent tile over a gradient over the
theme's page colour. A contrast measurement has to composite all of them, and
Chromium serialises a `color-mix()` result as `color(srgb r g b / a)` rather than
as `rgba()`, so a helper that only understands `rgba()` silently measures the
wrong background.
"""

from __future__ import annotations

MEASURE_JS = """(selector) => {
  const parse = (value) => {
    let match = value.match(/rgba?\\(([^)]+)\\)/);
    if (match) {
      const parts = match[1].split(',').map((part) => parseFloat(part.trim()));
      return { rgb: parts.slice(0, 3), alpha: parts.length > 3 ? parts[3] : 1 };
    }
    match = value.match(/color\\(srgb\\s+([^)]+)\\)/);
    if (match) {
      const halves = match[1].split('/');
      const rgb = halves[0].trim().split(/\\s+/).map(parseFloat).map((c) => c * 255);
      const alpha = halves.length > 1 ? parseFloat(halves[1]) : 1;
      return { rgb, alpha };
    }
    return null;
  };

  const el = document.querySelector(selector);
  if (!el) return null;

  const layers = [];
  let node = el;
  while (node) {
    const layer = parse(getComputedStyle(node).backgroundColor);
    if (layer && layer.alpha > 0) {
      layers.push(layer);
      if (layer.alpha === 1) break;
    }
    node = node.parentElement;
  }

  let background = [255, 255, 255];
  for (let i = layers.length - 1; i >= 0; i--) {
    const { rgb, alpha } = layers[i];
    for (let c = 0; c < 3; c++) background[c] = rgb[c] * alpha + background[c] * (1 - alpha);
  }

  const style = getComputedStyle(el);
  return {
    color: style.color,
    background: background.map(Math.round),
    fontSize: style.fontSize,
    fontWeight: style.fontWeight,
  };
}"""


def parse_rgb(value: str) -> list[float]:
    """Parse a computed `rgb()` / `rgba()` / `color(srgb ...)` colour."""
    import re

    match = re.match(r"rgba?\(([^)]+)\)", value)
    if match:
        parts = [float(part) for part in match.group(1).split(",")[:3]]
        return parts
    match = re.match(r"color\(srgb\s+([^)]+)\)", value)
    if match:
        halves = match.group(1).split("/")
        return [float(part) * 255 for part in halves[0].split()]
    raise ValueError(f"cannot parse colour: {value}")


def relative_luminance(rgb: list[float]) -> float:
    def channel(value: float) -> float:
        c = value / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def contrast_ratio(foreground: list[float], background: list[float]) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)
