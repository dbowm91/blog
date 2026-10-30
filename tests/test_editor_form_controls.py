"""Contracts for the post editor's field headers, AI actions and native controls.

Every control on the editor page has one owner: ``forms.css`` owns the form
controls, ``admin.css`` owns the editor surfaces, and ``base.css`` owns the
buttons. These tests pin that ownership so a second stylesheet, a duplicated
checkbox rule or a malformed inline style cannot creep back in.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = REPO_ROOT / "app" / "static" / "css"
TEMPLATE_DIR = REPO_ROOT / "app" / "templates" / "admin"


def _css(name: str) -> str:
    return (CSS_DIR / name).read_text()


def _rules(css: str) -> list[tuple[str, str]]:
    """Return every (selector list, declaration body) pair in a stylesheet."""
    without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return [
        (match.group(1), match.group(2))
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", without_comments)
    ]


def _rule_bodies(css: str, selector: str) -> list[str]:
    """Return the declaration body of every rule that names this selector.

    A selector list counts only when one of its parts is exactly the given
    selector, so ``.wrapper input[type="checkbox"]`` never matches
    ``input[type="checkbox"]``.
    """
    bodies: list[str] = []
    for selector_list, body in _rules(css):
        parts = [part.strip() for part in selector_list.split(",")]
        if selector in parts:
            bodies.append(body.strip())
    return bodies


class TestAiActionControls:
    def test_every_ai_button_shares_one_line_with_its_field_label(self) -> None:
        template = (TEMPLATE_DIR / "editor.html").read_text()
        rows = re.findall(r'<div class="form-label-row">(.*?)</div>', template, re.DOTALL)
        ai_rows = [row for row in rows if "ai-assist-button" in row]
        assert len(ai_rows) == 3, f"expected one AI action per field header, found {len(ai_rows)}"
        for action in ("title", "summary", "tags"):
            assert f'data-ai-action="{action}"' in template

    def test_the_page_editor_carries_no_ai_actions(self) -> None:
        page_editor = (TEMPLATE_DIR / "page_editor.html").read_text()
        shared_body = (TEMPLATE_DIR / "_editor_body.html").read_text()
        assert "ai-assist" not in page_editor
        assert "ai-assist" not in shared_body

    def test_the_ai_button_is_styled_by_the_admin_sheet(self) -> None:
        bodies = _rule_bodies(_css("admin.css"), ".ai-assist-button")
        assert bodies, "admin.css has no .ai-assist-button rule"
        assert "min-height" in bodies[0]
        assert "var(--accent-text)" in bodies[0]

    def test_the_ai_button_is_not_styled_by_the_form_sheet(self) -> None:
        assert ".ai-assist-button" not in _css("forms.css")

    def test_the_result_region_is_styled_and_hidden_while_empty(self) -> None:
        css = _css("admin.css")
        assert _rule_bodies(css, ".ai-assist-result")
        empty = _rule_bodies(css, ".ai-assist-result:empty")
        assert empty and "display: none" in empty[0]

    def test_the_disclosure_note_carries_an_accent_rule(self) -> None:
        bodies = _rule_bodies(_css("admin.css"), ".ai-assist-disclosure")
        assert bodies
        assert "border-left" in bodies[0]
        assert "var(--accent)" in bodies[0]


class TestFieldHeaderRow:
    def test_the_header_row_is_a_single_line_flex_row(self) -> None:
        bodies = _rule_bodies(_css("forms.css"), ".form-label-row")
        assert bodies, "forms.css has no .form-label-row rule"
        assert "display: flex" in bodies[0]
        assert "align-items: center" in bodies[0]

    def test_the_header_row_owns_the_label_spacing(self) -> None:
        bodies = _rule_bodies(_css("forms.css"), ".form-label-row label")
        assert bodies, "forms.css does not reset the label margin inside a header row"
        assert "margin-bottom: 0" in bodies[0]


class TestNativeControlStyling:
    def test_only_the_form_sheet_sizes_a_checkbox(self) -> None:
        assert _rule_bodies(_css("forms.css"), 'input[type="checkbox"]')
        assert 'input[type="checkbox"]' not in _css("admin.css")

    def test_the_checkbox_uses_the_theme_accent(self) -> None:
        bodies = _rule_bodies(_css("forms.css"), 'input[type="checkbox"]')
        assert "accent-color: var(--accent)" in bodies[0]

    def test_the_file_picker_button_is_styled(self) -> None:
        forms = _css("forms.css")
        assert 'input[type="file"]::file-selector-button' in forms
        assert "var(--bg-elevated)" in forms

    def test_the_colour_scheme_is_declared_for_both_schemes(self) -> None:
        base = _css("base.css")
        assert "color-scheme: dark" in base
        assert "color-scheme: light" in base

    def test_a_disabled_button_is_visibly_disabled(self) -> None:
        bodies = _rule_bodies(_css("base.css"), ".btn:disabled")
        assert bodies, "base.css has no .btn:disabled rule"
        assert "opacity" in bodies[0]
        assert "not-allowed" in bodies[0]


class TestEditorTemplate:
    def test_the_image_preview_uses_a_conditional_style_attribute(self) -> None:
        template = (TEMPLATE_DIR / "editor.html").read_text()
        assert '{% if not img %} style="display:none"{% endif %}' in template

    def test_the_image_preview_is_hidden_without_a_cover_image(self, authenticated_client) -> None:
        response = authenticated_client.get("/admin/new")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        match = re.search(r'<img[^>]*id="image-preview-img"[^>]*>', html)
        assert match is not None
        tag = match.group(0)
        assert "&#34;" not in tag, (
            "the style attribute was escaped into the value, so the browser "
            "ignored it and drew a broken image"
        )
        assert 'style="display:none"' in tag
