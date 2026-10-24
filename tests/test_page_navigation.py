"""Tests for the page navigation menu and the public pages index."""

import json

import pytest

from app.extensions import db
from app.models import Page, SiteSettings
from app.routes.public import public
from app.routes.public.pages import register_page_routes
from app.services.navigation import resolve_page_menu

register_page_routes(public)

PUBLIC_SHELL_ENDPOINTS = ("public.login", "public.account", "public.logout")


def _require_public_shell(app):
    """Skip when the shared public shell references unregistered endpoints.

    The public nav in ``base.html`` links to the public auth endpoints. Until
    those are registered every public page fails to render, which would mask
    the behaviour this module asserts.
    """
    missing = [name for name in PUBLIC_SHELL_ENDPOINTS if name not in app.view_functions]
    if missing:
        pytest.skip(f"public shell endpoints not registered yet: {', '.join(missing)}")


def _make_page(title, slug, published=True, show_in_menu=False):
    page = Page(
        title=title,
        slug=slug,
        body=f"{title} body.",
        published=published,
        show_in_menu=show_in_menu,
    )
    db.session.add(page)
    db.session.commit()
    return page


def _settings_row():
    row = db.session.execute(
        db.select(SiteSettings).order_by(SiteSettings.id).limit(1)
    ).scalar_one_or_none()
    if row is None:
        row = SiteSettings()
        db.session.add(row)
    return row


def _set_menu(raw, show_pages_in_menu=True):
    row = _settings_row()
    row.menu_pages = raw
    row.show_pages_in_menu = show_pages_in_menu
    db.session.commit()
    return row


def test_resolve_page_menu_uses_explicit_order(db):
    about = _make_page("About", "about")
    contact = _make_page("Contact", "contact")
    legal = _make_page("Legal", "legal")
    _set_menu(json.dumps([contact.id, about.id]))

    menu = resolve_page_menu()

    assert [page.id for page in menu] == [contact.id, about.id]
    assert legal.id not in [page.id for page in menu]


def test_resolve_page_menu_falls_back_to_show_in_menu_pages(db):
    _make_page("About", "about", show_in_menu=True)
    _make_page("Contact", "contact", show_in_menu=True)
    _make_page("Legal", "legal", show_in_menu=False)
    _set_menu("")

    menu = resolve_page_menu()

    assert [page.title for page in menu] == ["About", "Contact"]


def test_resolve_page_menu_drops_missing_and_unpublished_pages(db):
    about = _make_page("About", "about")
    draft = _make_page("Draft", "draft", published=False)
    _set_menu(json.dumps([draft.id, 999999, about.id]))

    menu = resolve_page_menu()

    assert [page.id for page in menu] == [about.id]


def test_resolve_page_menu_is_empty_when_disabled(db):
    _make_page("About", "about", show_in_menu=True)
    _set_menu("", show_pages_in_menu=False)

    assert resolve_page_menu() == []


def test_pages_index_lists_published_pages(app, client, db):
    _require_public_shell(app)
    _make_page("About", "about")
    _make_page("Draft page", "draft-page", published=False)

    response = client.get("/pages")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "About" in html
    assert "/page/about" in html
    assert "Draft page" not in html


def test_pages_index_shows_a_summary_of_the_first_paragraph(app, client, db):
    _require_public_shell(app)
    _make_page("About", "about")
    page = _make_page("Contact", "contact")
    page.body = "First paragraph of the contact page.\n\nSecond paragraph."
    db.session.commit()

    html = client.get("/pages").get_data(as_text=True)

    assert "First paragraph of the contact page." in html
    assert "Second paragraph." not in html


def test_admin_pages_list_shows_menu_control_and_toggle_persists(authenticated_client, db):
    page = _make_page("About", "about")

    html = authenticated_client.get("/admin/pages").get_data(as_text=True)
    assert "Show in menu" in html

    response = authenticated_client.post(
        f"/admin/pages/{page.id}/menu",
        data={"show_in_menu": "on"},
    )

    assert response.status_code == 302
    assert db.session.get(Page, page.id).show_in_menu is True
    assert [p.id for p in resolve_page_menu()] == [page.id]


def test_admin_pages_list_toggle_can_clear_the_flag(authenticated_client, db):
    page = _make_page("About", "about", show_in_menu=True)

    response = authenticated_client.post(f"/admin/pages/{page.id}/menu", data={})

    assert response.status_code == 302
    assert db.session.get(Page, page.id).show_in_menu is False


def test_admin_pages_list_links_to_the_public_url(authenticated_client, db):
    _make_page("About", "about")

    html = authenticated_client.get("/admin/pages").get_data(as_text=True)

    assert 'href="/page/about"' in html


def test_admin_pages_list_notes_pages_missing_from_the_menu(authenticated_client, db):
    _make_page("About", "about")
    _make_page("Contact", "contact", show_in_menu=True)

    html = authenticated_client.get("/admin/pages").get_data(as_text=True)

    assert "Not shown in the site menu." in html
    assert html.count("Not shown in the site menu.") == 1


def test_publishing_a_page_updates_the_menu_without_a_restart(db):
    page = _make_page("About", "about", published=False, show_in_menu=True)

    assert resolve_page_menu() == []

    page.published = True
    db.session.commit()

    assert [p.id for p in resolve_page_menu()] == [page.id]

    page.published = False
    db.session.commit()

    assert resolve_page_menu() == []


def test_admin_page_create_accepts_show_in_menu(authenticated_client, db):
    response = authenticated_client.post(
        "/admin/pages/new",
        data={
            "title": "Colophon",
            "body": "How this site is built.",
            "published": "on",
            "show_in_menu": "on",
        },
    )

    assert response.status_code == 302
    page = db.session.execute(db.select(Page).filter_by(slug="colophon")).scalar_one()
    assert page.show_in_menu is True


@pytest.mark.parametrize("data", [{}, {"show_in_menu": "on"}])
def test_admin_page_edit_keeps_the_menu_flag(authenticated_client, db, data):
    page = _make_page("About", "about", show_in_menu=True)

    response = authenticated_client.post(
        f"/admin/pages/edit/{page.id}",
        data={
            "title": "About us",
            "body": "About this site.",
            "published": "on",
            **data,
        },
    )

    assert response.status_code == 302
    assert db.session.get(Page, page.id).show_in_menu is True
