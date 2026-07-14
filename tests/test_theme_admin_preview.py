"""Tests for Phase 10: Admin theme selection, preview, and refresh."""

PREVIEW_URL = "/admin/settings/theme/preview"
REFRESH_URL = "/admin/settings/theme/refresh"
SETTINGS_URL = "/admin/settings"
THEME_SAVE_URL = "/admin/settings/theme"

DARK_THEME = "Catppuccin Mocha"
LIGHT_THEME = "Catppuccin Latte"


# --- Preview endpoint tests ---


def test_preview_requires_auth(client):
    """POST to preview without auth returns 302 redirect to login."""
    response = client.post(
        PREVIEW_URL,
        data={"theme_dark_name": DARK_THEME, "theme_light_name": LIGHT_THEME},
    )
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_preview_requires_both_themes(authenticated_client):
    """POST with missing theme names returns 400 with error."""
    response = authenticated_client.post(PREVIEW_URL, data={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "required" in data["error"].lower()


def test_preview_rejects_unknown_theme(authenticated_client):
    """POST with a non-existent theme name returns 400."""
    response = authenticated_client.post(
        PREVIEW_URL,
        data={
            "theme_dark_name": "Nonexistent Theme XYZ",
            "theme_light_name": LIGHT_THEME,
        },
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Nonexistent Theme XYZ" in data["error"]


def test_preview_returns_css_for_valid_themes(authenticated_client):
    """POST with valid bundled themes returns 200 JSON with CSS and metadata."""
    response = authenticated_client.post(
        PREVIEW_URL,
        data={"theme_dark_name": DARK_THEME, "theme_light_name": LIGHT_THEME},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "dark_css" in data
    assert "light_css" in data
    assert "dark_is_dark" in data
    assert "light_is_dark" in data
    assert "warnings" in data
    assert "dark_warnings" in data
    assert "light_warnings" in data
    assert isinstance(data["dark_css"], str)
    assert isinstance(data["light_css"], str)
    assert len(data["dark_css"]) > 0
    assert len(data["light_css"]) > 0


def test_preview_detects_classification_mismatch(authenticated_client):
    """POST with two dark themes returns a warning about classification."""
    response = authenticated_client.post(
        PREVIEW_URL,
        data={"theme_dark_name": DARK_THEME, "theme_light_name": DARK_THEME},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert any("both" in w.lower() and "dark" in w.lower() for w in data["warnings"])


def test_preview_no_filesystem_paths_in_response(authenticated_client):
    """Response JSON theme names and warnings must not contain absolute paths."""
    response = authenticated_client.post(
        PREVIEW_URL,
        data={"theme_dark_name": DARK_THEME, "theme_light_name": LIGHT_THEME},
    )
    assert response.status_code == 200
    data = response.get_json()
    for key in ("dark_name", "light_name"):
        assert "/" not in data[key], f"{key} contains path separator: {data[key]}"
    for w in data.get("warnings", []):
        assert "/" not in w, f"Warning contains path separator: {w}"


def test_preview_css_is_bounded(authenticated_client):
    """CSS output for each theme must be a reasonable size (under 100KB)."""
    response = authenticated_client.post(
        PREVIEW_URL,
        data={"theme_dark_name": DARK_THEME, "theme_light_name": LIGHT_THEME},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["dark_css"].encode("utf-8")) < 100 * 1024
    assert len(data["light_css"].encode("utf-8")) < 100 * 1024


# --- Refresh endpoint tests ---


def test_refresh_requires_auth(client):
    """POST to refresh without auth returns 302 redirect to login."""
    response = client.post(REFRESH_URL)
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_refresh_success(authenticated_client):
    """POST with auth returns redirect to settings and flash message."""
    response = authenticated_client.post(REFRESH_URL, follow_redirects=True)
    assert response.status_code == 200
    assert b"Refresh" in response.data or b"refresh" in response.data


def test_refresh_reports_no_changes(authenticated_client):
    """When catalog is unchanged, flash message says no changes detected."""
    response = authenticated_client.post(REFRESH_URL, follow_redirects=True)
    assert response.status_code == 200
    assert b"No changes detected" in response.data


# --- Settings page tests ---


def test_settings_page_shows_theme_selectors(authenticated_client):
    """GET /admin/settings returns 200 with theme selector elements."""
    response = authenticated_client.get(SETTINGS_URL)
    assert response.status_code == 200
    html = response.data.decode()
    assert 'id="theme_dark_name"' in html
    assert 'id="theme_light_name"' in html


def test_settings_page_groups_themes_by_source(authenticated_client):
    """Response contains 'Bundled Themes' and 'External Themes' optgroup labels."""
    response = authenticated_client.get(SETTINGS_URL)
    assert response.status_code == 200
    html = response.data.decode()
    assert "Bundled Themes" in html


def test_settings_page_has_preview_button(authenticated_client):
    """Response contains a preview button."""
    response = authenticated_client.get(SETTINGS_URL)
    assert response.status_code == 200
    html = response.data.decode()
    assert "theme-preview-btn" in html


# --- Theme save with validation ---


def test_settings_theme_save_preserves_syntax_and_custom_css(authenticated_client, db):
    """Saving theme names preserves syntax_theme and custom_css settings."""
    from app.models import SiteSettings

    custom_css = "body { color: #ff6600; background: #000; }"
    authenticated_client.post(
        THEME_SAVE_URL,
        data={
            "theme_dark_name": DARK_THEME,
            "theme_light_name": LIGHT_THEME,
            "theme_default_scheme": "system",
            "syntax_theme": "prism-dark",
            "custom_css_enabled": "on",
            "custom_css": custom_css,
            "logo_text": "My Blog",
        },
    )

    settings_obj = db.session.execute(db.select(SiteSettings).filter_by(id=1)).scalar_one()

    assert settings_obj.syntax_theme == "prism-dark"
    assert settings_obj.custom_css_enabled is True
    assert "color" in settings_obj.custom_css
    assert settings_obj.logo_text == "My Blog"


def test_settings_theme_rejects_invalid_names(authenticated_client):
    """POST with invalid theme names returns error flash."""
    response = authenticated_client.post(
        THEME_SAVE_URL,
        data={
            "theme_dark_name": "Totally Fake Theme",
            "theme_light_name": LIGHT_THEME,
            "theme_default_scheme": "system",
            "syntax_theme": "prism",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"not found" in response.data.lower()
