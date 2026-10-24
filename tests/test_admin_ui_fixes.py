"""Regression tests for the admin/public UI defects found during review.

Covers the reported problems:

1. nav links sat high in the bar and the active underline floated far below
   the text;
2. form inputs outside a ``.form-group`` fell back to the browser's white
   default, and the admin panel never loaded the stylesheet that styled
   ``.search-input``;
3. share icons sat 4px above the centre of their button;
4. the dashboard metrics list had a header with two cells over rows with
   four, so the columns did not line up;
5. the All/Published/Draft/Scheduled links reloaded the page and threw the
   reader back to the top;
6. ``/admin/analytics`` raised ``'str object' has no attribute 'strftime'``;
7. the theme preview injected ``--blog-*`` variables that no stylesheet
   reads, ignored which theme was being previewed, repainted the whole
   admin panel, and was rejected by CSRF as soon as the page had already
   submitted once;
8. the users list squeezed its action cluster into a 150px column;
9. the theme preview panel sat below the theme selector, was hidden until a
   preview had been loaded, and jumped in size when it appeared.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CSS_DIR = REPO_ROOT / "app" / "static" / "css"
JS_DIR = REPO_ROOT / "app" / "static" / "js"
TEMPLATE_DIR = REPO_ROOT / "app" / "templates"


def read_css(name: str) -> str:
    return (CSS_DIR / name).read_text(encoding="utf-8")


def read_js(*parts: str) -> str:
    return JS_DIR.joinpath(*parts).read_text(encoding="utf-8")


def read_template(*parts: str) -> str:
    return TEMPLATE_DIR.joinpath(*parts).read_text(encoding="utf-8")


def rule_body(css: str, selector: str) -> str:
    """Return the declaration block of the first rule for ``selector``."""
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"selector not found: {selector}"
    return match.group(1)


# ---------------------------------------------------------------------------
# 1. Nav bar: link alignment and underline position
# ---------------------------------------------------------------------------


def test_nav_link_centres_its_label_without_taking_over_display():
    """The link is a flex item 44px tall; the label must sit in the middle.

    The centring is done with symmetric padding rather than ``display`` on the
    link, because an unconditional ``display`` declaration on a ``.nav-links``
    descendant would break the mobile-breakpoint ownership contract.
    """
    body = rule_body(read_css("layout.css"), ".nav-links a")
    assert "display:" not in body
    assert "padding: 12px 0" in body
    assert "min-height: 44px" in body


def test_nav_underline_is_anchored_to_the_label_not_the_hit_area():
    css = read_css("layout.css")
    assert ".nav-links a.active .nav-link-text::after" in css
    # The old rule anchored the tick to the bottom of the 44px hit area,
    # which put it 23px below the text.
    assert ".nav-links a.active::after" not in css


def test_nav_link_labels_are_wrapped_in_the_positioning_span():
    for template in (
        read_template("base.html"),
        read_template("admin", "base.html"),
    ):
        assert 'class="nav-link-text"' in template


def test_nav_underline_mobile_override_targets_the_new_selector():
    assert ".nav-links a.active .nav-link-text::after" in read_css("base.css")


# ---------------------------------------------------------------------------
# 2. Form controls
# ---------------------------------------------------------------------------


def test_search_input_is_styled_in_a_stylesheet_the_admin_loads():
    # admin/base.html does not load public.css, so the canonical definition
    # has to live in forms.css.
    assert ".search-input" in read_css("forms.css")
    public = read_css("public.css")
    # The base rule must not be defined twice; other selectors may still
    # refine it.
    assert not re.search(r"^\.search-input\s*\{", public, re.M)


def test_admin_templates_load_forms_css():
    assert "css/forms.css" in read_template("admin", "base.html")


def test_form_controls_have_a_global_baseline():
    body = read_css("forms.css")
    assert 'input[type="text"]' in body
    assert 'input[type="password"]' in body
    assert "background: var(--bg-surface)" in body
    assert "border: 1px solid var(--border)" in body


def test_comment_form_honeypot_is_hidden():
    # `.hidden-field` was used by the comment form but never defined, so the
    # trap input rendered as a visible white text box.
    assert ".hidden-field" in read_css("utilities.css")


# ---------------------------------------------------------------------------
# 3. Share icons
# ---------------------------------------------------------------------------


def test_share_button_centres_its_icon():
    body = rule_body(read_css("public.css"), ".share-btn")
    assert "display: inline-flex" in body
    assert "align-items: center" in body
    assert "justify-content: center" in body


# ---------------------------------------------------------------------------
# 4 / 8. Admin list grids
# ---------------------------------------------------------------------------


def test_admin_lists_share_one_column_template_with_their_header():
    css = read_css("admin.css")
    assert "grid-template-columns: subgrid" in css
    assert "--post-list-cols" in css
    for modifier in (
        "post-list--posts",
        "post-list--with-check",
        "post-list--with-metrics",
        "post-list--pages",
    ):
        assert modifier in css


@pytest.mark.parametrize(
    ("template", "modifier"),
    [
        ("dashboard.html", "post-list--posts"),
        ("subscribers.html", "post-list--with-check"),
        ("tags.html", "post-list--with-metrics"),
        ("pages.html", "post-list--pages"),
    ],
)
def test_admin_lists_declare_their_column_variant(template, modifier):
    assert modifier in read_template("admin", template)


def test_dashboard_header_has_a_cell_for_every_item_column():
    html = read_template("admin", "dashboard.html")
    header = html.split('class="post-list-header"', 1)[1].split("</div>", 1)[0]
    assert header.count("<span") == 4


def test_dashboard_header_labels_sit_on_the_item_columns():
    html = read_template("admin", "dashboard.html")
    header = html.split('class="post-list-header"', 1)[1].split("</div>", 1)[0]
    assert "Title" in header
    assert "Metrics" in header
    assert "post-list-header-metrics" in header


def test_users_list_gives_the_action_cluster_its_own_row():
    html = read_template("admin", "users.html")
    assert "post-list-item--stacked" in html
    assert "post-list-extra" in html
    header = html.split('class="post-list-header"', 1)[1].split("</div>", 1)[0]
    assert header.count("<span") == 2


def test_users_list_header_matches_the_item_columns():
    html = read_template("admin", "users.html")
    header = html.split('class="post-list-header"', 1)[1].split("</div>", 1)[0]
    # The action cluster moved to a second, full-width row, so the first row
    # has two columns and the header has two cells.
    assert header.count("<span") == 2
    assert 'class="post-list-info"' in html
    assert 'class="post-list-actions"' in html
    assert 'class="post-list-extra"' in html


# ---------------------------------------------------------------------------
# 5. Scroll position across filter navigation
# ---------------------------------------------------------------------------


def test_scroll_preservation_is_wired_into_the_shared_utils():
    src = read_js("shared", "utils.js")
    assert "initScrollPreservation" in src
    assert "a.filter-link" in src
    assert "sessionStorage" in src


def test_shared_utils_registers_scroll_preservation():
    src = read_js("shared", "utils.js")
    body = src.split("export function initSharedUtils", 1)[1]
    assert "initScrollPreservation()" in body


# ---------------------------------------------------------------------------
# 6. Analytics
# ---------------------------------------------------------------------------


def test_analytics_coerces_sql_date_strings_into_dates():
    from datetime import date

    from app.routes.admin.helpers.analytics import _coerce_date

    assert _coerce_date("2026-10-23") == date(2026, 10, 23)
    assert _coerce_date(date(2026, 10, 23)) == date(2026, 10, 23)
    assert _coerce_date(None) is None
    assert _coerce_date("not-a-date") is None


def test_analytics_page_renders_with_daily_view_rows(authenticated_client, db, sample_post):
    from datetime import timedelta

    from app.models import PageView
    from app.utils import utc_now

    db.session.add(
        PageView(
            post_id=sample_post.id,
            referrer=None,
            created_at=utc_now() - timedelta(days=1),
        )
    )
    db.session.commit()

    response = authenticated_client.get("/admin/analytics")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Views Over Time" in body


# ---------------------------------------------------------------------------
# 7. Theme preview and the admin colour toggle
# ---------------------------------------------------------------------------


def test_legacy_css_serializer_emits_the_names_the_stylesheets_use():
    from app.themes.translate import to_legacy_css

    css = to_legacy_css({"name": "Nord", "bg": "#2e3440", "text": "#eceff4"})
    assert "--bg: #2e3440;" in css
    assert "--text: #eceff4;" in css
    assert "--name" not in css


def test_theme_preview_endpoint_returns_legacy_variables():
    from app.themes.registry import ThemeRegistry

    registry = ThemeRegistry()
    loaded = registry.load("Nord")
    from app.themes.translate import to_legacy_css

    css = to_legacy_css(loaded.legacy_vars)
    assert "--bg:" in css
    # The blog-semantic names are not consumed by any stylesheet.
    assert "--blog-bg-page" not in css


def test_preview_stylesheet_is_scoped_to_the_preview_container():
    src = read_template("admin", "settings.html")
    assert '#theme-preview-container[data-color-scheme="dark"]' in src
    # A bare `:root` rule repainted the whole admin panel.
    assert "':root { '" not in src


def test_preview_button_honours_its_data_target():
    src = read_template("admin", "settings.html")
    assert "getAttribute('data-target')" in src
    assert "previewRequestId" in src


def test_admin_panel_exposes_the_colour_scheme_toggle():
    assert 'class="nav-actions"' in read_template("admin", "base.html")

    src = read_js("main.js")
    admin_block = src.split("ROUTE_MODULES = {", 1)[1]
    assert admin_block.count("'./shared/color-scheme.js'") >= 5


def test_admin_nav_host_exists_for_the_toggle():
    src = read_js("shared", "color-scheme.js")
    assert ".nav-actions" in src


# ---------------------------------------------------------------------------
# 9. Theme preview panel placement
# ---------------------------------------------------------------------------


def settings_html(authenticated_client) -> str:
    response = authenticated_client.get("/admin/settings")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def section_headings(html: str) -> list[str]:
    headings = []
    for match in re.finditer(r'<div class="settings-section[^"]*"[^>]*>', html):
        heading = re.search(r"<h2>(.*?)</h2>", html[match.end() :], re.S)
        headings.append(heading.group(1).strip() if heading else "")
    return headings


def test_theme_preview_section_is_rendered_above_the_theme_selector(authenticated_client):
    html = settings_html(authenticated_client)

    assert section_headings(html) == ["Theme Preview", "Theme", "Theme Registry"]

    first_section = re.search(r'<div class="settings-section[^"]*"[^>]*>', html)
    assert first_section is not None
    assert 'id="theme-preview-section"' in first_section.group(0)

    assert html.index('id="theme-preview-section"') < html.index("<h2>Theme</h2>")
    assert html.index("<h2>Theme</h2>") < html.index("<h2>Theme Registry</h2>")


def test_theme_preview_section_is_visible_by_default(authenticated_client):
    html = settings_html(authenticated_client)

    assert 'id="theme-preview-section" style="display: none;"' not in html

    section_tag = re.search(r'<div class="settings-section" id="theme-preview-section"[^>]*>', html)
    assert section_tag is not None
    assert "display: none" not in section_tag.group(0)

    assert "Select a theme below and press its Preview button to see it here." in html
    assert 'Click "Preview" to see theme styling' not in html


def test_theme_preview_container_cannot_change_height_when_the_preview_loads():
    src = read_template("admin", "settings.html")

    bodies = re.findall(r"\.theme-preview-container\s*\{([^}]*)\}", src)
    assert bodies

    values = []
    for body in bodies:
        min_match = re.search(r"min-height:\s*([^;]+);", body)
        max_match = re.search(r"max-height:\s*([^;]+);", body)
        if min_match is None and max_match is None:
            continue
        assert min_match is not None and max_match is not None, body
        assert min_match.group(1).strip() == max_match.group(1).strip(), body
        values.append(min_match.group(1).strip())

    assert values
    assert "380px" in values


def test_clearing_the_preview_keeps_the_panel_and_restores_the_placeholder():
    src = read_template("admin", "settings.html")

    clear_handler = src.split("if (clearBtn) {", 1)[1].split("});", 1)[0]

    assert "previewSection.style.display = 'none'" not in src
    assert "previewSection.style.display" not in clear_handler
    assert "replaceChildren" in clear_handler
    assert "previewPlaceholder" in clear_handler


def test_preview_buttons_stay_next_to_the_theme_selects(authenticated_client):
    html = settings_html(authenticated_client)

    buttons = re.findall(r"<button[^>]*theme-preview-btn[^>]*>", html)
    assert len(buttons) == 2

    for select_id, target in (("theme_dark_name", "dark"), ("theme_light_name", "light")):
        button = next(b for b in buttons if f'data-target="{target}"' in b)
        select_at = html.index(f'id="{select_id}"')
        button_at = html.index(button)
        assert select_at < button_at
        assert "<h2>" not in html[select_at:button_at]


# ---------------------------------------------------------------------------
# 7b. CSRF: a page must be able to submit more than once
# ---------------------------------------------------------------------------


def test_csrf_token_can_be_used_for_more_than_one_request(app, client, monkeypatch):
    """A rendered page issues one token; several requests may use it."""
    # The app fixture is session-scoped, so the config has to be restored.
    monkeypatch.setitem(app.config, "CSRF_ENABLED", True)
    monkeypatch.setitem(app.config, "TESTING", False)

    token = "a" * 64
    with client.session_transaction() as sess:
        sess["csrf_tokens"] = [token]

    for _ in range(3):
        # An unknown path still runs the global CSRF check before routing,
        # so a 404 means the token was accepted and a 403 means it was not.
        response = client.post("/csrf-token-probe", headers={"X-CSRF-Token": token})
        assert response.status_code == 404, "token was consumed by an earlier request"


def test_csrf_rejects_an_unknown_token(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "CSRF_ENABLED", True)
    monkeypatch.setitem(app.config, "TESTING", False)

    response = client.post("/admin/logout", headers={"X-CSRF-Token": "0" * 64})
    assert response.status_code == 403
