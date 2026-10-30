"""Tests for the appearance layer: fonts, backdrops and the settings they use.

Covers the font and backdrop registries, the appearance service that turns a
choice into runtime CSS, the SVG sanitiser that makes an uploaded backdrop
safe to serve, and the admin route that stores the choices.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.appearance.backdrops import (
    BUNDLED_BACKDROPS,
    CUSTOM_BACKDROP_PREFIX,
    BackdropRegistry,
)
from app.appearance.fonts import (
    BUNDLED_FONTS,
    CUSTOM_FONT_PREFIX,
    FontRegistry,
    custom_family_name,
    font_stack,
)
from app.appearance.model import (
    CATEGORY_MONO,
    CATEGORY_SANS,
    SOURCE_BUNDLED,
    SOURCE_CUSTOM,
)
from app.appearance.service import DEFAULT_BACKDROP, AppearanceService
from app.appearance.svg import SvgSanitisationError, sanitize_svg
from app.appearance.uploads import save_custom_backdrop, save_custom_font
from app.models import SiteSettings
from app.services.appearance_settings import (
    CUSTOM_OPTION,
    resolve_backdrop_key,
    resolve_font_key,
    validate_appearance_settings,
)


class _FakeStorage:
    """A storage backend that keeps everything in memory."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, filename: str, data: bytes) -> str:
        self.files[filename] = data
        return filename

    def delete(self, filename: str) -> bool:
        return self.files.pop(filename, None) is not None

    def exists(self, filename: str) -> bool:
        return filename in self.files

    def list_files(self, prefix: str = "") -> list[str]:
        return [name for name in self.files if name.startswith(prefix)]

    def url(self, filename: str) -> str:
        return f"/static/uploads/{filename}"


def _set_site_settings(**values) -> SiteSettings:
    settings = SiteSettings.get_instance()
    for key, value in values.items():
        setattr(settings, key, value)
    return settings


# --- registries ---------------------------------------------------------------


def test_bundled_fonts_cover_sans_and_mono():
    sans = [f for f in BUNDLED_FONTS if f.category == CATEGORY_SANS]
    mono = [f for f in BUNDLED_FONTS if f.category == CATEGORY_MONO]

    assert {f.key for f in sans} == {
        "inter",
        "ibm-plex-sans",
        "space-grotesk",
        "atkinson-hyperlegible",
    }
    assert {f.key for f in mono} == {
        "jetbrains-mono",
        "ibm-plex-mono",
        "fira-code",
        "cascadia-code",
        "spline-sans-mono",
        "meslo-nerd-font",
    }


def test_the_bundled_fonts_are_distinctly_named():
    families = [f for f in BUNDLED_FONTS if f.category == CATEGORY_SANS]

    assert len({f.css_family for f in families}) == len(families)
    assert len({f.key for f in BUNDLED_FONTS}) == len(BUNDLED_FONTS)


def test_the_nerd_font_is_bundled_for_the_mono_slot():
    nerd = [f for f in BUNDLED_FONTS if f.key == "meslo-nerd-font"]

    assert len(nerd) == 1
    assert nerd[0].category == CATEGORY_MONO
    assert nerd[0].css_family == "MesloLGS Nerd Font"


def test_bundled_font_files_exist_on_disk():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "app" / "static" / "fonts"
    for family in BUNDLED_FONTS:
        for filename in family.files:
            assert (root / filename).is_file(), filename


def test_font_registry_resolves_bundled_families():
    registry = FontRegistry(storage=_FakeStorage())

    family = registry.resolve("ibm-plex-sans")

    assert family is not None
    assert family.source == SOURCE_BUNDLED
    assert family.css_family == "IBM Plex Sans"


def test_font_registry_lists_custom_fonts_from_storage():
    storage = _FakeStorage()
    storage.save(f"{CUSTOM_FONT_PREFIX}my-font-1234abcd.woff2", b"wOF2")
    registry = FontRegistry(storage=storage)

    families = registry.list_families(CATEGORY_SANS)
    custom = [f for f in families if f.source == SOURCE_CUSTOM]

    assert len(custom) == 1
    assert custom[0].url == "/static/uploads/custom-font-my-font-1234abcd.woff2"


def test_font_registry_rejects_a_custom_font_in_the_wrong_slot():
    registry = FontRegistry(storage=_FakeStorage())

    assert registry.resolve_for_slot("jetbrains-mono", CATEGORY_SANS) is None
    assert registry.resolve_for_slot("jetbrains-mono", CATEGORY_MONO) is not None


def test_font_registry_forgets_a_custom_font_whose_file_was_removed():
    storage = _FakeStorage()
    filename = f"{CUSTOM_FONT_PREFIX}my-font-1234abcd.woff2"
    storage.save(filename, b"wOF2")
    registry = FontRegistry(storage=storage)

    assert registry.resolve(filename) is not None

    storage.delete(filename)

    assert registry.resolve(filename) is None


def test_backdrop_registry_forgets_a_custom_backdrop_whose_file_was_removed():
    storage = _FakeStorage()
    filename = f"{CUSTOM_BACKDROP_PREFIX}shape-1234abcd.svg"
    storage.save(filename, b"<svg></svg>")
    registry = BackdropRegistry(storage=storage)

    assert registry.resolve(filename) is not None

    storage.delete(filename)

    assert registry.resolve(filename) is None


def test_font_stack_leads_with_the_chosen_family():
    registry = FontRegistry(storage=_FakeStorage())
    family = registry.resolve("fira-code")

    stack = font_stack(family)

    assert stack.startswith("'Fira Code'")
    assert "JetBrains Mono" in stack


def test_font_stack_quotes_multi_word_fallbacks():
    registry = FontRegistry(storage=_FakeStorage())
    family = registry.resolve("jetbrains-mono")

    stack = font_stack(family)

    assert stack == "'JetBrains Mono', 'Fira Code', monospace"


def test_font_stack_leaves_generic_keywords_unquoted():
    registry = FontRegistry(storage=_FakeStorage())
    family = registry.resolve("inter")

    stack = font_stack(family)

    assert stack == "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"


def test_custom_family_name_is_namespaced():
    assert custom_family_name(f"{CUSTOM_FONT_PREFIX}my-font.woff2").startswith("DevLog Custom")


def test_backdrop_registry_lists_bundled_backdrops():
    registry = BackdropRegistry(storage=_FakeStorage())

    keys = [b.key for b in registry.list_backdrops()]

    assert "grid" in keys
    assert "neural-mesh" in keys
    assert "circuit-bloom" in keys


def test_the_retired_backdrop_keys_are_gone():
    """A key that resolves to nothing leaves the page with no backdrop."""
    registry = BackdropRegistry(storage=_FakeStorage())

    keys = [b.key for b in registry.list_backdrops()]

    assert "default" not in keys
    assert "waves" not in keys


def test_every_bundled_backdrop_has_its_file():
    """The registry skips a graphic that is not on disk."""
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "img" / "backdrops"

    missing = [
        filename for _key, _label, filename in BUNDLED_BACKDROPS if not (root / filename).is_file()
    ]

    assert missing == [], f"a bundled backdrop has no file: {missing}"


def test_the_blueprint_grid_is_the_default_backdrop():
    assert DEFAULT_BACKDROP == "grid"
    assert SiteSettings.__table__.c.backdrop.default.arg == "grid"


def test_a_bundled_backdrop_is_drawn_in_a_single_colour():
    """The graphic supplies a shape; the theme supplies the colour.

    The SVG is applied as a mask, so its own fill is irrelevant — a graphic
    that carried a colour of its own would only be misleading.
    """
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "img" / "backdrops"

    for _key, _label, filename in BUNDLED_BACKDROPS:
        source = (root / filename).read_text(encoding="utf-8")
        colours = set(re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{3,8})"', source))
        assert colours <= {"#ffffff"}, f"{filename} carries its own colour: {colours}"


def test_a_bundled_backdrop_is_drawn_with_heavy_forms():
    """The tint is faint, so a hairline graphic would not read at all.

    The graphic is a mask, so only its alpha matters: a shape drawn with thin
    strokes disappears against the page at the alpha the theme produces. The
    blueprint grid is the exception — it is a dense repeating pattern, which
    reads as a texture rather than as a line.
    """
    root = Path(__file__).resolve().parents[1] / "app" / "static" / "img" / "backdrops"

    for key, _label, filename in BUNDLED_BACKDROPS:
        if key == "grid":
            continue
        source = (root / filename).read_text(encoding="utf-8")
        widths = [float(w) for w in re.findall(r'stroke-width="([\d.]+)"', source)]
        assert widths, f"{filename} has no strokes"
        assert max(widths) >= 4, f"{filename} is drawn with hairline strokes"


def test_backdrop_registry_resolves_a_custom_backdrop():
    storage = _FakeStorage()
    storage.save("custom-backdrop-art-1234abcd.svg", b"<svg/>")
    registry = BackdropRegistry(storage=storage)

    descriptor = registry.resolve("custom-backdrop-art-1234abcd.svg")

    assert descriptor is not None
    assert descriptor.source == SOURCE_CUSTOM


# --- svg sanitiser ------------------------------------------------------------


def test_sanitize_svg_removes_scripts():
    cleaned = sanitize_svg(
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect/></svg>'
    )

    assert "script" not in cleaned.lower()
    assert "<rect" in cleaned


def test_sanitize_svg_removes_event_handlers():
    cleaned = sanitize_svg(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)" fill="#fff"/></svg>'
    )

    assert "onload" not in cleaned.lower()


def test_sanitize_svg_removes_javascript_links():
    cleaned = sanitize_svg(
        '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><rect/></a></svg>'
    )

    assert "javascript:" not in cleaned.lower()


def test_sanitize_svg_keeps_the_drawing():
    cleaned = sanitize_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect x="1" y="2" width="3" height="4" fill="#ffffff"/></svg>'
    )

    assert "rect" in cleaned
    assert "#ffffff" in cleaned


def test_sanitize_svg_rejects_a_doctype():
    with pytest.raises(SvgSanitisationError):
        sanitize_svg('<!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg"/>')


def test_sanitize_svg_rejects_a_non_svg_root():
    with pytest.raises(SvgSanitisationError):
        sanitize_svg("<html><body/></html>")


def test_sanitize_svg_rejects_broken_xml():
    with pytest.raises(SvgSanitisationError):
        sanitize_svg("<svg><rect>")


# --- uploads ------------------------------------------------------------------


def test_save_custom_font_stores_a_valid_font():
    storage = _FakeStorage()
    upload = _Upload("MyFont.woff2", b"wOF2" + b"\x00" * 32)

    name, error = save_custom_font(storage, upload)

    assert error is None
    assert name.startswith(CUSTOM_FONT_PREFIX)
    assert name.endswith(".woff2")
    assert storage.files[name].startswith(b"wOF2")


def test_save_custom_font_rejects_a_file_that_is_not_a_font():
    storage = _FakeStorage()
    upload = _Upload("evil.woff2", b"<html>")

    name, error = save_custom_font(storage, upload)

    assert name is None
    assert error is not None
    assert storage.files == {}


def test_save_custom_font_rejects_an_unsupported_extension():
    storage = _FakeStorage()
    upload = _Upload("evil.ttf", b"wOF2")

    name, error = save_custom_font(storage, upload)

    assert name is None
    assert error is not None


def test_save_custom_backdrop_sanitises_before_storing():
    storage = _FakeStorage()
    upload = _Upload(
        "art.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>x</script><rect/></svg>'
    )

    name, error = save_custom_backdrop(storage, upload)

    assert error is None
    assert name.startswith("custom-backdrop-")
    assert b"script" not in storage.files[name]


def test_save_custom_backdrop_rejects_a_non_svg():
    storage = _FakeStorage()
    upload = _Upload("art.png", b"\x89PNG")

    name, error = save_custom_backdrop(storage, upload)

    assert name is None
    assert error is not None


class _Upload:
    """The parts of a werkzeug upload the appearance layer reads."""

    def __init__(self, filename: str, data: bytes) -> None:
        self.filename = filename
        self._data = data

    def read(self) -> bytes:
        return self._data


# --- settings validation ------------------------------------------------------


def test_validate_appearance_settings_reads_the_form():
    payload = validate_appearance_settings(
        {
            "font_sans": "ibm-plex-sans",
            "font_mono": "fira-code",
            "backdrop": "grid",
        }
    )

    assert payload.font_sans == "ibm-plex-sans"
    assert payload.font_mono == "fira-code"
    assert payload.backdrop == "grid"
    assert payload.wants_custom_sans is False


def test_validate_appearance_settings_detects_the_custom_sentinel():
    payload = validate_appearance_settings(
        {"font_sans": CUSTOM_OPTION, "font_mono": CUSTOM_OPTION, "backdrop": CUSTOM_OPTION}
    )

    assert payload.wants_custom_sans is True
    assert payload.wants_custom_mono is True
    assert payload.wants_custom_backdrop is True


def test_resolve_font_key_accepts_a_bundled_family():
    registry = FontRegistry(storage=_FakeStorage())

    key, error = resolve_font_key("ibm-plex-sans", None, "", registry, CATEGORY_SANS, "sans")

    assert error is None
    assert key == "ibm-plex-sans"


def test_resolve_font_key_rejects_an_unknown_family():
    registry = FontRegistry(storage=_FakeStorage())

    key, error = resolve_font_key("comic-sans", None, "", registry, CATEGORY_SANS, "sans")

    assert key is None
    assert error is not None


def test_resolve_font_key_requires_an_upload_for_a_custom_family():
    registry = FontRegistry(storage=_FakeStorage())

    key, error = resolve_font_key(CUSTOM_OPTION, None, "", registry, CATEGORY_SANS, "sans")

    assert key is None
    assert error is not None


def test_resolve_font_key_keeps_the_current_custom_family():
    storage = _FakeStorage()
    name = f"{CUSTOM_FONT_PREFIX}my-font-1234abcd.woff2"
    storage.save(name, b"wOF2")
    registry = FontRegistry(storage=storage)

    key, error = resolve_font_key(CUSTOM_OPTION, None, name, registry, CATEGORY_SANS, "sans")

    assert error is None
    assert key == name


def test_resolve_backdrop_key_accepts_none():
    registry = BackdropRegistry(storage=_FakeStorage())

    key, error = resolve_backdrop_key("", None, "grid", registry)

    assert error is None
    assert key == ""


def test_resolve_backdrop_key_rejects_an_unknown_backdrop():
    registry = BackdropRegistry(storage=_FakeStorage())

    key, error = resolve_backdrop_key("nope", None, "grid", registry)

    assert key is None
    assert error is not None


# --- the appearance service ----------------------------------------------------


def test_appearance_service_emits_the_font_stacks(app, db):
    _set_site_settings(font_sans="ibm-plex-sans", font_mono="fira-code", backdrop="grid")
    service = AppearanceService()

    context = service.get_context()

    assert context["appearance_font_sans"] == "ibm-plex-sans"
    assert "IBM Plex Sans" in context["appearance_font_sans_stack"]
    assert "Fira Code" in context["appearance_font_mono_stack"]


def test_appearance_service_emits_the_backdrop_css(app, db):
    _set_site_settings(font_sans="inter", font_mono="jetbrains-mono", backdrop="grid")
    service = AppearanceService()

    css = service.get_context()["appearance_css"]

    assert "--backdrop-image" in css
    assert "backdrops/grid.svg" in css
    assert "--backdrop-tint" in css


def test_appearance_service_omits_the_backdrop_when_none_is_chosen(app, db):
    _set_site_settings(font_sans="inter", font_mono="jetbrains-mono", backdrop="")
    service = AppearanceService()

    css = service.get_context()["appearance_css"]

    assert "--backdrop-image: none" in css
    assert "--backdrop-tint: transparent" in css


def test_appearance_service_declares_a_custom_font_face(app, db):
    storage = _FakeStorage()
    name = f"{CUSTOM_FONT_PREFIX}my-font-1234abcd.woff2"
    storage.save(name, b"wOF2")
    _set_site_settings(font_sans=name, font_mono="jetbrains-mono", backdrop="grid")
    service = AppearanceService()
    service.get_font_registry()._storage = storage
    service.get_font_registry().invalidate()

    css = service.get_context()["appearance_css"]

    assert "@font-face" in css
    assert "DevLog Custom my-font-1234abcd" in css


def test_appearance_service_falls_back_when_the_choice_is_unknown(app, db):
    _set_site_settings(font_sans="gone", font_mono="gone", backdrop="gone")
    service = AppearanceService()

    context = service.get_context()

    assert context["appearance_font_sans"] == "inter"
    assert context["appearance_font_mono"] == "jetbrains-mono"
    assert context["appearance_backdrop"] == ""


def test_appearance_service_falls_back_when_the_custom_font_file_is_gone(app, db):
    storage = _FakeStorage()
    name = f"{CUSTOM_FONT_PREFIX}my-font-1234abcd.woff2"
    storage.save(name, b"wOF2")
    _set_site_settings(font_sans=name, font_mono="jetbrains-mono", backdrop="grid")
    service = AppearanceService()
    service.get_font_registry()._storage = storage
    service.get_font_registry().invalidate()

    assert service.get_context()["appearance_font_sans"] == name

    storage.delete(name)

    service.invalidate_settings_cache()

    context = service.get_context()
    assert context["appearance_font_sans"] == "inter"
    assert "DevLog Custom my-font-1234abcd" not in context["appearance_css"]


def test_appearance_service_tint_differs_between_schemes(app, db):
    _set_site_settings(font_sans="inter", font_mono="jetbrains-mono", backdrop="grid")
    service = AppearanceService()

    context = service.get_context()

    assert context["appearance_backdrop_tint_dark"] != context["appearance_backdrop_tint_light"]
    assert context["appearance_backdrop_tint_dark"].startswith("rgba(")


def test_appearance_service_preloads_the_selected_fonts(app, db):
    _set_site_settings(font_sans="ibm-plex-sans", font_mono="jetbrains-mono", backdrop="grid")
    service = AppearanceService()

    preloads = service.get_context()["appearance_preload_fonts"]

    assert len(preloads) == 2
    assert "ibm-plex-sans-latin.woff2" in preloads[0]["url"]
    assert "jetbrains-mono-400-latin.woff2" in preloads[1]["url"]
    assert all(entry["type"] == "font/woff2" for entry in preloads)


# --- the admin route ------------------------------------------------------------


def _login(client, admin_user):
    client.post(
        "/admin/login",
        data={"username": "admin", "password": "test-password-123"},
        follow_redirects=True,
    )


def test_settings_page_lists_the_appearance_choices(authenticated_client, db):
    response = authenticated_client.get("/admin/settings")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Typography" in body
    assert "ibm-plex-sans" in body
    assert 'value="grid"' in body


def test_settings_appearance_stores_the_choices(authenticated_client, db):
    _set_site_settings(font_sans="inter", font_mono="jetbrains-mono", backdrop="grid")

    response = authenticated_client.post(
        "/admin/settings/appearance",
        data={"font_sans": "ibm-plex-sans", "font_mono": "fira-code", "backdrop": "circuit-bloom"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    settings = SiteSettings.get_instance()
    assert settings.font_sans == "ibm-plex-sans"
    assert settings.font_mono == "fira-code"
    assert settings.backdrop == "circuit-bloom"


def test_settings_appearance_rejects_an_unknown_font(authenticated_client, db):
    _set_site_settings(font_sans="inter", font_mono="jetbrains-mono", backdrop="grid")

    response = authenticated_client.post(
        "/admin/settings/appearance",
        data={"font_sans": "comic-sans", "font_mono": "jetbrains-mono", "backdrop": "grid"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert SiteSettings.get_instance().font_sans == "inter"
    assert "not an available" in response.get_data(as_text=True)


def test_settings_appearance_requires_authentication(client, db):
    response = client.post(
        "/admin/settings/appearance",
        data={"font_sans": "inter", "font_mono": "jetbrains-mono", "backdrop": "grid"},
    )

    assert response.status_code in (302, 401, 403)


def test_the_public_page_carries_the_appearance_css(client, db):
    _set_site_settings(font_sans="ibm-plex-sans", font_mono="jetbrains-mono", backdrop="grid")

    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "--font-sans: 'IBM Plex Sans'" in body
    assert "--backdrop-image" in body
