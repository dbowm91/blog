from __future__ import annotations

from dataclasses import dataclass, field

from app.themes.colors import RGB, RGBA, alpha_composite, contrast_ratio, to_hex, wcag_level
from app.themes.model import BlogTheme

_WHITE = RGB(255, 255, 255)


def _resolve_rgb(color: RGB | RGBA) -> RGB:
    if isinstance(color, RGBA):
        return alpha_composite(color, _WHITE)
    return color


@dataclass(frozen=True, slots=True)
class ContrastWarning:
    token: str
    description: str
    foreground: str
    background: str
    ratio: float
    wcag: str


@dataclass(frozen=True, slots=True)
class ProvenanceEntry:
    blog_token: str
    halloy_source: str
    derivation: str


@dataclass
class TranslationDiagnostics:
    warnings: list[ContrastWarning] = field(default_factory=list)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    is_dark: bool = True
    source_name: str = ""

    @property
    def summary(self) -> str:
        lines: list[str] = []
        if self.source_name:
            lines.append(f"Theme: {self.source_name}")
        lines.append(f"Mode: {'dark' if self.is_dark else 'light'}")
        lines.append("")

        if self.warnings:
            lines.append(f"Contrast warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  - {w.token}: {w.description} ({w.ratio:.2f}:1, WCAG {w.wcag})")
                lines.append(f"    fg={w.foreground} bg={w.background}")
        else:
            lines.append("No contrast warnings.")

        lines.append("")

        if self.provenance:
            lines.append(f"Provenance ({len(self.provenance)}):")
            for p in self.provenance:
                lines.append(f"  - {p.blog_token}: {p.halloy_source} ({p.derivation})")
        else:
            lines.append("No provenance entries.")

        return "\n".join(lines)


def check_contrast(
    fg: RGB | RGBA,
    bg: RGB | RGBA,
    token: str,
    description: str,
    min_ratio: float = 4.5,
) -> ContrastWarning | None:
    ratio = contrast_ratio(fg, bg)
    if ratio < min_ratio:
        return ContrastWarning(
            token=token,
            description=description,
            foreground=to_hex(_resolve_rgb(fg)),
            background=to_hex(_resolve_rgb(bg)),
            ratio=round(ratio, 2),
            wcag=wcag_level(ratio),
        )
    return None


def check_blog_theme_contrast(blog_theme: BlogTheme) -> list[ContrastWarning]:
    checks: list[tuple[RGB | RGBA, RGB | RGBA, str, str, float]] = [
        (
            blog_theme.text_primary,
            blog_theme.bg_page,
            "--blog-text-primary",
            "text-primary on bg-page",
            4.5,
        ),
        (
            blog_theme.text_primary,
            blog_theme.surface_default,
            "--blog-text-primary",
            "text-primary on surface-default",
            4.5,
        ),
        (
            blog_theme.text_muted,
            blog_theme.surface_default,
            "--blog-text-muted",
            "text-muted on surface-default",
            3.0,
        ),
        (
            blog_theme.text_link,
            blog_theme.bg_page,
            "--blog-text-link",
            "text-link on bg-page",
            4.5,
        ),
        (
            blog_theme.text_link,
            blog_theme.surface_default,
            "--blog-text-link",
            "text-link on surface-default",
            4.5,
        ),
        (
            blog_theme.text_on_accent,
            blog_theme.accent,
            "--blog-text-on-accent",
            "text-on-accent on accent",
            4.5,
        ),
        (
            blog_theme.input_text,
            blog_theme.input_bg,
            "--blog-input-text",
            "input-text on input-bg",
            4.5,
        ),
        (
            blog_theme.accent_focus_ring,
            blog_theme.bg_page,
            "--blog-accent-focus-ring",
            "accent-focus-ring on bg-page",
            3.0,
        ),
        (
            blog_theme.accent_focus_ring,
            blog_theme.surface_default,
            "--blog-accent-focus-ring",
            "accent-focus-ring on surface-default",
            3.0,
        ),
    ]

    warnings: list[ContrastWarning] = []
    for fg, bg, token, description, min_ratio in checks:
        warning = check_contrast(fg, bg, token, description, min_ratio)
        if warning is not None:
            warnings.append(warning)
    return warnings


def build_provenance(mapping: dict[str, str]) -> list[ProvenanceEntry]:
    return [
        ProvenanceEntry(
            blog_token=token,
            halloy_source=source,
            derivation="direct",
        )
        for token, source in mapping.items()
    ]
