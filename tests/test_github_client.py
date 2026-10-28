from unittest.mock import Mock

import pytest

from app.services.github_client import (
    GitHubApiClient,
    GitHubApiError,
    validate_repository_identity,
)


def _response(
    status=200,
    *,
    body=b'{"ok":true}',
    headers=None,
    chunks=None,
):
    response = Mock()
    response.status_code = status
    response.headers = headers or {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
        "ETag": '"abc123"',
        "X-RateLimit-Remaining": "55",
        "X-RateLimit-Reset": "1793210000",
    }
    response.iter_content.return_value = chunks if chunks is not None else [body]
    response.close = Mock()
    return response


def test_client_uses_fixed_host_etag_timeout_and_no_redirects():
    session = Mock()
    session.get.return_value = _response()
    client = GitHubApiClient(session=session)

    result = client.get_json(
        ("repos", "example", "sample", "commits", "feature/docs"),
        params={"per_page": 100},
        etag='"previous"',
    )

    call = session.get.call_args
    kwargs = call.kwargs
    assert call.args[0] == ("https://api.github.com/repos/example/sample/commits/feature%2Fdocs")
    assert kwargs["allow_redirects"] is False
    assert kwargs["stream"] is True
    assert kwargs["timeout"] == (3.05, 10.0)
    assert kwargs["headers"]["If-None-Match"] == '"previous"'
    assert result.data == {"ok": True}
    assert result.etag == '"abc123"'
    assert result.rate_limit_remaining == 55
    session.get.return_value.close.assert_called_once()


def test_client_returns_not_modified_without_reading_a_body():
    session = Mock()
    response = _response(304, body=b"", headers={"ETag": '"same"'})
    session.get.return_value = response

    result = GitHubApiClient(session=session).get_json(("repos", "example", "sample"))

    assert result.not_modified is True
    assert result.data is None
    response.iter_content.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_client_rejects_redirects(status):
    session = Mock()
    session.get.return_value = _response(status)

    with pytest.raises(GitHubApiError, match="redirects"):
        GitHubApiClient(session=session, max_retries=0).get_json(("repos", "example", "sample"))


def test_client_rejects_oversized_content_length():
    session = Mock()
    response = _response(headers={"Content-Length": "9", "Content-Type": "application/json"})
    session.get.return_value = response

    with pytest.raises(GitHubApiError, match="size limit"):
        GitHubApiClient(session=session, max_response_bytes=8).get_json(
            ("repos", "example", "sample")
        )
    response.iter_content.assert_not_called()


def test_client_enforces_streamed_size_limit_without_content_length():
    session = Mock()
    response = _response(
        headers={"Content-Type": "application/json"},
        chunks=[b"12345", b"67890"],
    )
    session.get.return_value = response

    with pytest.raises(GitHubApiError, match="size limit"):
        GitHubApiClient(session=session, max_response_bytes=8).get_json(
            ("repos", "example", "sample")
        )
    response.close.assert_called_once()


def test_client_reports_rate_limit_reset_and_retry_after():
    session = Mock()
    response = _response(
        403,
        headers={
            "Content-Type": "application/json",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1793210000",
            "Retry-After": "3",
        },
    )
    session.get.return_value = response

    with pytest.raises(GitHubApiError) as raised:
        GitHubApiClient(session=session, max_retries=0).get_json(("repos", "example", "sample"))

    assert raised.value.status_code == 403
    assert raised.value.rate_limit_reset == 1793210000
    assert raised.value.retry_after_seconds == 3


def test_client_retries_transient_server_errors_with_a_bounded_backoff():
    session = Mock()
    session.get.side_effect = [_response(503), _response()]
    delays = []
    client = GitHubApiClient(session=session, sleep=delays.append)

    result = client.get_json(("repos", "example", "sample"))

    assert result.data == {"ok": True}
    assert session.get.call_count == 2
    assert delays == [0.1]


@pytest.mark.parametrize("segments", [(), ("repos", "..", "sample"), ("repos", "bad\\name")])
def test_client_rejects_invalid_path_segments_before_network(segments):
    session = Mock()

    with pytest.raises(ValueError):
        GitHubApiClient(session=session).get_json(segments)

    session.get.assert_not_called()


@pytest.mark.parametrize(
    ("owner", "repository"),
    [("sample-owner", "sample_repo.v2"), ("a", "b")],
)
def test_repository_identity_accepts_valid_components(owner, repository):
    assert validate_repository_identity(owner, repository) == (owner, repository)


@pytest.mark.parametrize(
    ("owner", "repository"),
    [("../other", "repo"), ("owner", "../repo"), ("owner", "bad/repo"), ("owner", "..")],
)
def test_repository_identity_rejects_path_injection(owner, repository):
    with pytest.raises(ValueError, match="identity"):
        validate_repository_identity(owner, repository)
