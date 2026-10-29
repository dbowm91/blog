"""A settings change must reach the next request.

The theme context and the appearance context are derived from the
``SiteSettings`` row and cached per process. The application runs several
worker processes, and a change saved by one of them used to stay invisible to
the others until the cache expired five minutes later.

The suite therefore wrote the setting through the database - the way another
process would - and the rendered page had to reflect it immediately.
"""

from __future__ import annotations


def _set_default_scheme(app, scheme: str) -> None:
    from app.extensions import db
    from app.models import SiteSettings

    with app.app_context():
        settings = SiteSettings.get_instance()
        settings.theme_default_scheme = scheme
        db.session.commit()


def test_a_theme_change_is_visible_on_the_next_request(app, client):
    """The page renders the scheme that is in the database right now."""
    _set_default_scheme(app, "light")

    response = client.get("/")

    assert response.status_code == 200
    assert b'data-default-scheme="light"' in response.data


def test_a_later_theme_change_replaces_the_earlier_one(app, client):
    """The cached context is dropped again, not only on the first request."""
    _set_default_scheme(app, "light")
    client.get("/")

    _set_default_scheme(app, "dark")

    response = client.get("/")

    assert b'data-default-scheme="dark"' in response.data
