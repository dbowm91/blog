from app.markdown_renderer import FEED_EXTENSIONS, render_markdown


def test_html_block_allows_sandboxed_youtube_nocookie_embed():
    rendered = render_markdown(
        ':::html\n<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk" '
        'title="Video" width="560" height="315"></iframe>\n:::'
    )

    assert '<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk"' in rendered
    assert 'sandbox="allow-scripts allow-same-origin allow-presentation"' in rendered
    assert 'loading="lazy"' in rendered
    assert 'referrerpolicy="no-referrer"' in rendered
    assert "onload" not in rendered


def test_html_block_strips_unapproved_iframe_and_hostile_attributes():
    rendered = render_markdown(
        ':::html\n<iframe src="https://youtube.com.evil.example/embed/abcdefghijk" '
        'onload="alert(1)"></iframe>\n:::'
    )

    assert "<iframe" not in rendered
    assert "evil.example" not in rendered
    assert "onload" not in rendered


def test_html_block_strips_invalid_youtube_paths_and_query_parameters():
    for src in (
        "https://www.youtube-nocookie.com/watch?v=abcdefghijk",
        "https://www.youtube-nocookie.com/embed/abcdefghijk?autoplay=1",
        "https://www.youtube-nocookie.com:444/embed/abcdefghijk",
        "https://user@www.youtube-nocookie.com/embed/abcdefghijk",
    ):
        rendered = render_markdown(f':::html\n<iframe src="{src}"></iframe>\n:::')
        assert "<iframe" not in rendered


def test_nested_html_block_markers_do_not_bypass_sanitization():
    rendered = render_markdown(
        ':::html\n<div>\n:::html\n<iframe src="https://evil.example/embed/abcdefghijk" '
        'onload="alert(1)"></iframe>\n:::\n</div>\n:::'
    )
    assert "<iframe" not in rendered
    assert "onload" not in rendered
    assert "evil.example" not in rendered


def test_malformed_or_unclosed_html_blocks_remain_sanitized():
    rendered = render_markdown(
        ':::html\n<iframe src="https://evil.example/embed/abcdefghijk" onload="alert(1)"></iframe>'
    )
    assert "<iframe" not in rendered
    assert "evil.example" not in rendered
    assert "onload" not in rendered


def test_uploaded_video_markup_survives_only_for_local_uploads():
    safe = render_markdown(
        '<video controls><source src="/static/uploads/clip.mp4" type="video/mp4"></video>'
    )
    assert (
        '<video controls=""><source src="/static/uploads/clip.mp4" type="video/mp4"></video>'
        in safe
    )

    external = render_markdown('<video controls src="https://evil.example/clip.mp4"></video>')
    assert "evil.example" not in external


def test_html_block_marker_inside_fenced_code_is_not_interpreted():
    rendered = render_markdown("```text\n:::html\n<iframe src='bad'>\n:::\n```")
    assert "&lt;iframe" in rendered
    assert "<iframe" not in rendered


def test_admin_preview_uses_the_same_safe_embed_policy(authenticated_client):
    response = authenticated_client.post(
        "/admin/preview-markdown",
        json={
            "text": ':::html\n<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk" '
            'title="Video"></iframe>\n:::'
        },
    )
    assert response.status_code == 200
    assert "www.youtube-nocookie.com/embed/abcdefghijk" in response.get_json()["html"]


def test_feed_extensions_keep_the_same_safe_embed_policy():
    rendered = render_markdown(
        ':::html\n<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk" '
        'title="Video"></iframe>\n:::',
        extensions=FEED_EXTENSIONS,
    )
    assert '<iframe src="https://www.youtube-nocookie.com/embed/abcdefghijk"' in rendered
