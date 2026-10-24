"""Tests for the site-level settings surface.

Covers the comments switch, the editable footer, the footer column switches
and the pages menu, plus the validation service that owns the form payload.
"""

from __future__ import annotations

import json

from app.models import Page, SiteSettings
from app.services.site_settings import (
    MAX_FOOTER_TEXT,
    parse_menu_pages,
    validate_site_settings,
)


def _set_site_settings(**values) -> SiteSettings:
    settings = SiteSettings.get_instance()
    for key, value in values.items():
        setattr(settings, key, value)
    return settings


def test_validate_site_settings_reads_checkboxes_and_text():
    payload = validate_site_settings(
        {
            "comments_enabled": "on",
            "footer_text": "  Built by hand.  ",
            "footer_show_posts": "on",
            "show_pages_in_menu": "on",
        }
    )

    assert payload.comments_enabled is True
    assert payload.footer_text == "Built by hand."
    assert payload.footer_show_posts is True
    assert payload.footer_show_tags is False
    assert payload.show_pages_in_menu is True


def test_validate_site_settings_caps_footer_text():
    payload = validate_site_settings({"footer_text": "x" * (MAX_FOOTER_TEXT + 50)})

    assert len(payload.footer_text) == MAX_FOOTER_TEXT


def test_parse_menu_pages_accepts_a_json_array():
    assert parse_menu_pages("[3, 1, 2]") == [3, 1, 2]


def test_parse_menu_pages_accepts_a_plain_list():
    assert parse_menu_pages(["4", "2"]) == [4, 2]


def test_parse_menu_pages_discards_bad_values():
    assert parse_menu_pages('[0, -1, "x", null, true, 2, 2]') == [2]
    assert parse_menu_pages("not json") == []
    assert parse_menu_pages(None) == []


def test_validate_site_settings_serialises_the_menu():
    payload = validate_site_settings({"menu_pages": "[5, 4]"})

    assert json.loads(payload.menu_pages) == [5, 4]


def test_footer_text_renders_and_falls_back(client):
    _set_site_settings(footer_text="A custom footer line")
    response = client.get("/")
    assert response.status_code == 200
    assert b"A custom footer line" in response.data

    _set_site_settings(footer_text="")
    response = client.get("/")
    assert response.status_code == 200
    assert b"Built with Flask" in response.data


def test_footer_text_is_escaped(client):
    _set_site_settings(footer_text="<script>alert(1)</script>")
    response = client.get("/")

    assert response.status_code == 200
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;" in response.data


def test_footer_columns_can_be_hidden(client):
    _set_site_settings(footer_show_posts=False, footer_show_tags=False)
    response = client.get("/")

    assert response.status_code == 200
    assert b"Latest from the blog" not in response.data
    assert b"Browse by tag" not in response.data


def test_subscribe_form_lives_in_the_footer_on_every_page(client, db):
    """The newsletter form is in the footer, so it is on every public page."""
    post = _published_post(db)

    for path in ("/", f"/post/{post.slug}"):
        response = client.get(path)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        footer = html.split('<footer class="footer"', 1)[1]
        assert 'action="/subscribe"' in footer
        assert 'class="subscribe-form-footer"' in footer
        assert 'name="csrf_token"' in footer
        assert "hero-subscribe" not in html


def test_footer_subscribe_form_posts_to_the_subscribe_endpoint(client):
    """The footer form is wired to the public subscribe route."""
    response = client.get("/")
    html = response.get_data(as_text=True)
    footer = html.split('<footer class="footer"', 1)[1]

    assert 'action="/subscribe"' in footer
    assert 'name="email"' in footer


def test_comments_block_hidden_when_comments_are_closed(client, db):
    post = _published_post(db)
    _set_site_settings(comments_enabled=False)

    response = client.get(f"/post/{post.slug}")

    assert response.status_code == 200
    assert b'<section class="comments"' not in response.data
    assert b'name="author_email"' not in response.data


def test_comment_endpoint_refuses_when_comments_are_closed(client, db):
    post = _published_post(db)
    _set_site_settings(comments_enabled=False)

    response = client.post(
        f"/post/{post.slug}/comment",
        data={
            "author_name": "Someone",
            "author_email": "someone@example.com",
            "content": "A perfectly reasonable comment body.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Comments are closed" in response.data

    from app.models import Comment

    assert Comment.query.count() == 0


def test_settings_site_saves_the_payload(authenticated_client, app):
    response = _post(
        authenticated_client,
        "/admin/settings/site",
        {
            "footer_text": "Saved footer",
            "footer_show_posts": "on",
            "show_pages_in_menu": "on",
            "menu_pages": "[2]",
        },
    )
    assert response.status_code in (302, 303)
    response = authenticated_client.get("/admin/settings")

    assert response.status_code == 200
    settings = SiteSettings.get_instance()
    assert settings.footer_text == "Saved footer"
    assert settings.footer_show_posts is True
    assert settings.footer_show_tags is False
    assert settings.comments_enabled is False
    assert settings.show_pages_in_menu is True
    assert json.loads(settings.menu_pages) == [2]


def test_settings_page_renders_the_site_section(authenticated_client):
    response = authenticated_client.get("/admin/settings")

    assert response.status_code == 200
    html = response.data.decode()
    assert "<h2>Site</h2>" in html
    assert 'name="comments_enabled"' in html
    assert 'name="footer_text"' in html
    assert 'name="show_pages_in_menu"' in html
    assert 'name="menu_pages"' in html


def test_menu_pages_are_offered_in_the_settings_page(authenticated_client, db):
    page = Page(title="About", slug="about", body="Body", published=True)
    db.session.add(page)
    db.session.commit()

    response = authenticated_client.get("/admin/settings")

    assert response.status_code == 200
    assert 'value="%d"' % page.id in response.data.decode()


def _post(client, path: str, data: dict):
    token = "a" * 64
    with client.session_transaction() as sess:
        sess["csrf_tokens"] = [token]
    return client.post(path, data=data, headers={"X-CSRF-Token": token})


def _published_post(db) -> object:
    from app.models import Post

    post = Post(
        title="Site settings post",
        slug="site-settings-post",
        body="Body",
        summary="",
        published=True,
    )
    db.session.add(post)
    db.session.commit()
    return post
