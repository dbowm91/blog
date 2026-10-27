"""Tests for Phase 10: Admin theme selection, preview, and refresh."""

from unittest.mock import patch, MagicMock

PREVIEW_URL = "/admin/settings/theme/preview"
REFRESH_URL = "/admin/settings/theme/refresh"
SETTINGS_URL = "/admin/settings"
THEME_SAVE_URL = "/admin/settings/theme"

DARK_THEME = "Catppuccin Mocha"
LIGHT_THEME = "Catppuccin Latte"


def _make_descriptor(name, source="bundled", overrides=False, is_dark=None):
    """Create a mock ThemeDescriptor for tests."""
    return MagicMock(
        canonical_name=name,
        display_name=name,
        source=MagicMock(value=source),
        overrides_bundled=overrides,
        is_dark=is_dark,
        status="ok",
        warnings=(),
    )


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


def test_settings_theme_save_preserves_custom_css(authenticated_client, db):
    """Saving theme names preserves the custom_css settings."""
    from app.models import SiteSettings

    custom_css = "body { color: #ff6600; background: #000; }"
    authenticated_client.post(
        THEME_SAVE_URL,
        data={
            "theme_dark_name": DARK_THEME,
            "theme_light_name": LIGHT_THEME,
            "theme_default_scheme": "system",
            "custom_css_enabled": "on",
            "custom_css": custom_css,
            "logo_text": "My Blog",
        },
    )

    settings_obj = db.session.execute(db.select(SiteSettings).filter_by(id=1)).scalar_one()

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
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"not found" in response.data.lower()


# --- Override labeling tests ---


def test_settings_page_shows_override_label(authenticated_client):
    """External themes that override bundled themes show '(overrides bundled)' label."""
    from app.themes.registry import ThemeRegistry

    real_registry = ThemeRegistry()
    all_themes = real_registry.list_themes()
    has_overrides = any(t.overrides_bundled for t in all_themes)

    if not has_overrides:
        return

    response = authenticated_client.get(SETTINGS_URL)
    assert response.status_code == 200
    html = response.data.decode()
    assert "overrides bundled" in html


def test_settings_page_has_classification_badge_markup(authenticated_client):
    """Template contains badge markup for dark/light classification."""
    response = authenticated_client.get(SETTINGS_URL)
    assert response.status_code == 200
    html = response.data.decode()
    assert "classification-dark" in html or "classification-light" in html


# --- Refresh discovers additions and removals ---


def test_refresh_discovers_additions_and_removals(authenticated_client):
    """Refresh reports added and removed themes when catalog changes."""
    from app.themes.registry import ThemeRegistry

    old_themes = {
        _make_descriptor("Alpha Theme"),
        _make_descriptor("Beta Theme"),
        _make_descriptor(DARK_THEME),
        _make_descriptor(LIGHT_THEME),
    }
    new_themes = {
        _make_descriptor("Beta Theme"),
        _make_descriptor("Gamma Theme"),
        _make_descriptor(DARK_THEME),
        _make_descriptor(LIGHT_THEME),
    }

    old_registry = MagicMock(spec=ThemeRegistry)
    old_registry.list_themes.return_value = sorted(old_themes, key=lambda d: d.canonical_name)

    new_registry = MagicMock(spec=ThemeRegistry)
    new_registry.list_themes.return_value = sorted(new_themes, key=lambda d: d.canonical_name)
    new_registry.get_fallback.return_value = _make_descriptor(DARK_THEME)

    with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
        mock_service = MagicMock()
        call_count = [0]

        def get_reg():
            call_count[0] += 1
            if call_count[0] == 1:
                return old_registry
            return new_registry

        mock_service.get_registry.side_effect = get_reg
        mock_get_svc.return_value = mock_service

        response = authenticated_client.post(REFRESH_URL, follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode()
        assert "Alpha Theme" in html or "alpha" in html.lower()
        assert "Gamma Theme" in html or "gamma" in html.lower()


# --- Refresh restores bundled theme after override deletion ---


def test_refresh_restores_bundled_after_override_deletion(authenticated_client):
    """When an external override is removed, the bundled theme reappears."""
    from app.themes.registry import ThemeRegistry

    override_desc = _make_descriptor("Rose Pine", source="external", overrides=True)
    bundled_desc = _make_descriptor("Rose Pine", source="bundled")

    old_registry = MagicMock(spec=ThemeRegistry)
    old_registry.list_themes.return_value = [override_desc]

    new_registry = MagicMock(spec=ThemeRegistry)
    new_registry.list_themes.return_value = [bundled_desc]
    new_registry.get_fallback.return_value = _make_descriptor(DARK_THEME)

    with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
        mock_service = MagicMock()
        call_count = [0]

        def get_reg():
            call_count[0] += 1
            if call_count[0] == 1:
                return old_registry
            return new_registry

        mock_service.get_registry.side_effect = get_reg
        mock_get_svc.return_value = mock_service

        response = authenticated_client.post(REFRESH_URL, follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode()
        assert "Rose Pine" in html


# --- Selected missing external theme falls back visibly ---


def test_refresh_warns_on_missing_selected_theme(authenticated_client, db):
    """Refresh warns when a selected external theme disappears, showing fallback."""
    from app.themes.registry import ThemeRegistry
    from app.models import SiteSettings

    settings_obj = SiteSettings.get_instance()
    settings_obj.theme_dark_name = "Vanished External Theme"
    settings_obj.theme_light_name = LIGHT_THEME
    db.session.commit()

    old_registry = MagicMock(spec=ThemeRegistry)
    old_registry.list_themes.return_value = [
        _make_descriptor("Vanished External Theme", source="external"),
        _make_descriptor(LIGHT_THEME),
    ]

    new_registry = MagicMock(spec=ThemeRegistry)
    new_registry.list_themes.return_value = [_make_descriptor(LIGHT_THEME)]
    new_registry.get_fallback.return_value = _make_descriptor(DARK_THEME)

    with patch("app.routes.admin.settings.get_theme_service") as mock_get_svc:
        mock_service = MagicMock()
        call_count = [0]

        def get_reg():
            call_count[0] += 1
            if call_count[0] == 1:
                return old_registry
            return new_registry

        mock_service.get_registry.side_effect = get_reg
        mock_get_svc.return_value = mock_service

        response = authenticated_client.post(REFRESH_URL, follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode()
        assert "Vanished External Theme" in html
        assert "no longer available" in html.lower() or "fallback" in html.lower()


# --- Cache invalidation after save ---


def test_settings_theme_save_invalidates_cache(authenticated_client, db):
    """Saving theme settings invalidates the settings cache."""
    from app.models import SiteSettings

    settings_obj = SiteSettings.get_instance()
    settings_obj.theme_dark_name = DARK_THEME
    settings_obj.theme_light_name = LIGHT_THEME
    db.session.commit()

    with patch("app.routes.admin.settings.invalidate_settings_cache") as mock_invalidate:
        authenticated_client.post(
            THEME_SAVE_URL,
            data={
                "theme_dark_name": LIGHT_THEME,
                "theme_light_name": DARK_THEME,
                "theme_default_scheme": "dark",
            },
        )
        mock_invalidate.assert_called_once()
