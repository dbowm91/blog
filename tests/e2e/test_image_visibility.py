"""End-to-end assertion that post card images are actually painted.

A DOM-only assertion cannot catch FE-IMG-03: the ``<img>`` element is present
and its ``src`` is correct, but the stylesheet keeps every lazily-loaded image
at ``opacity: 0`` forever because the ``.loaded`` restoration class is never
applied. These tests assert the computed style and the rendered geometry, which
is the only way to prove the image is painted.
"""

import base64

import pytest

pytestmark = pytest.mark.e2e

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
_FILENAME = "e2e-image-visibility.png"
_TARGET = ".post-card-img[data-e2e-target]"


@pytest.fixture(scope="session")
def post_with_image(app, app_server):
    """Create a published post backed by a real file in the storage backend."""
    from app.extensions import db
    from app.models import Post
    from app.storage import get_storage
    from app.utils import utc_now

    storage = get_storage()
    storage.save(_FILENAME, _TINY_PNG)

    with app.app_context():
        post = Post(
            title="Image Visibility Post",
            slug="image-visibility-post",
            body="# Image Visibility\n\nA post with a cover image.",
            summary="A post with a cover image.",
            published=True,
            published_at=utc_now(),
            image=_FILENAME,
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    yield post_id


def _mark_target(page):
    """Tag the card image belonging to the test post so later lookups are stable."""
    page.evaluate(
        """
        (filename) => {
            const img = document.querySelector(`.post-card-img[src*="${filename}"]`);
            if (img) img.setAttribute('data-e2e-target', '1');
        }
        """,
        _FILENAME,
    )


def test_card_image_is_painted(page, app_server, post_with_image):
    """The card image has a valid URL, a non-zero box, and opacity 1."""
    page.goto(f"{app_server}/")

    card_image = page.locator(f'.post-card-img[src*="{_FILENAME}"]').first
    card_image.wait_for(state="attached", timeout=10_000)
    card_image.scroll_into_view_if_needed()

    src = card_image.get_attribute("src") or ""
    assert "/static/uploads//static/uploads/" not in src, f"double-prefixed image URL: {src}"
    assert src.endswith(_FILENAME), f"unexpected image URL: {src}"

    page.wait_for_function(
        f"() => {{ const i = document.querySelector('.post-card-img[src*=\"{_FILENAME}\"]');"
        " return i && i.complete && i.naturalWidth > 0; }",
        timeout=10_000,
    )

    _mark_target(page)
    page.wait_for_function(
        f"() => {{ const i = document.querySelector('{_TARGET}');"
        " return i && getComputedStyle(i).opacity === '1'; }",
        timeout=10_000,
    )

    opacity = card_image.evaluate("el => getComputedStyle(el).opacity")
    assert opacity == "1", f"lazy image is not painted: computed opacity is {opacity}"

    box = card_image.bounding_box()
    assert box is not None
    assert box["width"] > 0 and box["height"] > 0, f"image has no rendered size: {box}"


def test_broken_image_does_not_stay_invisible(page, app_server, post_with_image):
    """A failed image load must not leave the element permanently invisible."""
    page.goto(f"{app_server}/")

    _mark_target(page)
    page.wait_for_function(f"() => !!document.querySelector('{_TARGET}')", timeout=10_000)

    page.evaluate(
        """
        () => {
            const img = document.querySelector('.post-card-img[data-e2e-target]');
            if (!img) return;
            img.src = '/static/uploads/definitely-missing-file.png';
        }
        """
    )

    page.wait_for_function(
        f"() => {{ const i = document.querySelector('{_TARGET}');"
        " return i && i.classList.contains('loaded'); }",
        timeout=10_000,
    )
    page.wait_for_function(
        f"() => {{ const i = document.querySelector('{_TARGET}');"
        " return i && getComputedStyle(i).opacity === '1'; }",
        timeout=10_000,
    )

    opacity = page.evaluate(f"() => getComputedStyle(document.querySelector('{_TARGET}')).opacity")
    assert opacity == "1", f"broken image left at opacity {opacity}"
