from __future__ import annotations

import json
import os
from dataclasses import replace
from unittest.mock import Mock

import pytest
from sqlalchemy import event, select

from app.config.model import AiConfig
from app.models import Post, Tag, User
from app.services import ai_assist


@pytest.fixture
def ai_admin_user(db):
    user = User(username="ai-test-admin", email="ai-test-admin@example.com", is_admin=True)
    user.set_password("test-password-123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def enabled_ai(authenticated_client):
    app = authenticated_client.application
    original = app.config["DEVLOG_CONFIG"]
    app.config["DEVLOG_CONFIG"] = replace(
        original,
        ai=AiConfig(model="test-model", api_key="test-private-key"),
    )
    yield authenticated_client
    app.config["DEVLOG_CONFIG"] = original


@pytest.fixture
def disabled_ai(authenticated_client):
    app = authenticated_client.application
    original = app.config["DEVLOG_CONFIG"]
    app.config["DEVLOG_CONFIG"] = replace(
        original,
        ai=AiConfig(provider="opencode_go"),
    )
    yield authenticated_client
    app.config["DEVLOG_CONFIG"] = original


def _provider_payload_response(payload: dict, *, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.iter_content.return_value = iter([json.dumps(payload).encode()])
    response.close.return_value = None
    return response


def _provider_response(content: str, *, status_code: int = 200) -> Mock:
    return _provider_payload_response(
        {"choices": [{"message": {"content": content}}]}, status_code=status_code
    )


def test_ai_controls_are_hidden_without_key(disabled_ai) -> None:
    response = disabled_ai.get("/admin/new")
    page_editor = disabled_ai.get("/admin/pages/new")
    assert response.status_code == 200
    assert page_editor.status_code == 200
    assert b"data-ai-action" not in response.data
    assert b"OpenCode Go" not in response.data
    assert b"data-ai-action" not in page_editor.data


def test_ai_is_opt_in_but_local_provider_needs_no_api_key() -> None:
    from app.config.model import DevLogConfig

    default_config = DevLogConfig()
    assert default_config.ai.model == ""
    assert not ai_assist.is_ai_assist_available(default_config)

    local_config = replace(default_config, ai=AiConfig(model="local-model"))
    assert ai_assist.is_ai_assist_available(local_config)
    assert local_config.ai.api_key == ""

    assert not ai_assist.is_ai_assist_available(
        DevLogConfig(ai=AiConfig(provider="opencode_go", model="", api_key=""))
    )


def test_ai_controls_are_hidden_by_default(authenticated_client, monkeypatch) -> None:
    monkeypatch.setitem(
        authenticated_client.application.config,
        "DEVLOG_CONFIG",
        replace(authenticated_client.application.config["DEVLOG_CONFIG"], ai=AiConfig()),
    )
    response = authenticated_client.get("/admin/new")
    assert response.status_code == 200
    assert b"data-ai-action" not in response.data


def test_ai_controls_are_hidden_for_existing_post_without_key(disabled_ai, db, admin_user) -> None:
    post = Post(
        title="Existing draft",
        slug="existing-ai-draft",
        body="Draft body",
        summary="",
        published=False,
        author_id=admin_user.id,
    )
    db.session.add(post)
    db.session.commit()
    response = disabled_ai.get(f"/admin/edit/{post.id}")
    assert response.status_code == 200
    assert b"data-ai-action" not in response.data


def test_ai_controls_render_when_configured(enabled_ai) -> None:
    response = enabled_ai.get("/admin/new")
    public = enabled_ai.application.test_client().get("/")
    assert response.status_code == 200
    assert b'data-ai-action="summary"' in response.data
    assert b'data-ai-action="tags"' in response.data
    assert b"current unsaved title and Markdown body" in response.data
    assert b"data-ai-action" not in public.data


def test_local_model_route_end_to_end(enabled_ai) -> None:
    if os.environ.get("RUN_LOCAL_AI_E2E") != "1":
        pytest.skip("set RUN_LOCAL_AI_E2E=1 to call the configured local model")

    app = enabled_ai.application
    original = app.config["DEVLOG_CONFIG"]
    app.config["DEVLOG_CONFIG"] = replace(
        original,
        ai=AiConfig(
            provider="openai_compatible",
            model=os.environ.get("AI_E2E_MODEL", "google/gemma-4-e2b"),
            base_url=os.environ.get("AI_E2E_BASE_URL", "http://127.0.0.1:1234/v1"),
            api_key=os.environ.get("AI_E2E_API_KEY", ""),
            timeout_seconds=180,
        ),
    )
    try:
        response = enabled_ai.post(
            "/admin/ai-assist",
            json={
                "action": "summary",
                "title": "Synthetic local model check",
                "body": "This synthetic test checks the authenticated DevLog route to a local model. No editorial or private text is included.",
            },
        )
    finally:
        app.config["DEVLOG_CONFIG"] = original

    assert response.status_code == 200
    assert isinstance(response.json.get("suggestion"), str)
    assert 1 <= len(response.json["suggestion"]) <= 500


def test_endpoint_fails_closed_without_key(disabled_ai, monkeypatch) -> None:
    outbound = Mock()
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    response = disabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Some text"},
    )
    assert response.status_code == 503
    outbound.assert_not_called()


def test_invalid_action_does_not_call_provider(enabled_ai, monkeypatch) -> None:
    outbound = Mock()
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    response = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "publish", "title": "T", "body": "Some text"},
    )
    assert response.status_code == 400
    outbound.assert_not_called()


def test_oversized_input_is_rejected_before_provider(enabled_ai, monkeypatch) -> None:
    outbound = Mock()
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    response = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "x" * (64 * 1024 + 1)},
    )
    assert response.status_code == 400
    outbound.assert_not_called()


def test_ai_rate_limit_is_unlimited_by_default(enabled_ai, monkeypatch) -> None:
    from app import limiter

    enabled_ai.application.config["RATELIMIT_ENABLED"] = True
    original_enabled = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    outbound = Mock(
        side_effect=lambda *args, **kwargs: _provider_response(
            '{"suggestion":"A concise factual summary."}'
        )
    )
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    try:
        responses = [
            enabled_ai.post(
                "/admin/ai-assist",
                json={"action": "summary", "title": "T", "body": "Body"},
            )
            for _ in range(105)
        ]
        assert all(response.status_code == 200 for response in responses)
        assert outbound.call_count == 105
    finally:
        limiter.reset()
        limiter.enabled = original_enabled


def test_configured_ai_rate_limit_is_enforced(enabled_ai, monkeypatch) -> None:
    from app import limiter

    app = enabled_ai.application
    original_config = app.config["DEVLOG_CONFIG"]
    app.config["DEVLOG_CONFIG"] = replace(
        original_config,
        ai=replace(original_config.ai, rate_limit_per_user="2 per hour"),
    )
    app.config["RATELIMIT_ENABLED"] = True
    original_enabled = limiter.enabled
    limiter.enabled = True
    limiter.reset()
    outbound = Mock(
        side_effect=lambda *args, **kwargs: _provider_response(
            '{"suggestion":"A concise factual summary."}'
        )
    )
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    try:
        responses = [
            enabled_ai.post(
                "/admin/ai-assist",
                json={"action": "summary", "title": "T", "body": "Body"},
            )
            for _ in range(3)
        ]
        assert [response.status_code for response in responses] == [200, 200, 429]
        assert outbound.call_count == 2
    finally:
        app.config["DEVLOG_CONFIG"] = original_config
        limiter.reset()
        limiter.enabled = original_enabled


def test_api_key_header_does_not_authenticate_editor_route(client, monkeypatch) -> None:
    app = client.application
    original_api_key = app.config.get("API_KEY")
    app.config["API_KEY"] = "test-legacy-api-key"
    outbound = Mock()
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    response = client.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Some text"},
        headers={"X-API-Key": "test-legacy-api-key"},
    )
    app.config["API_KEY"] = original_api_key
    assert response.status_code in {302, 401, 403}
    outbound.assert_not_called()


def test_malformed_json_does_not_call_provider(enabled_ai, monkeypatch) -> None:
    outbound = Mock()
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    response = enabled_ai.post(
        "/admin/ai-assist",
        data="{not valid JSON",
        content_type="application/json",
    )
    assert response.status_code == 400
    outbound.assert_not_called()


def test_csrf_is_required_for_ai_endpoint(app, enabled_ai, monkeypatch) -> None:
    app.config["CSRF_ENABLED"] = True
    with enabled_ai.session_transaction() as flask_session:
        flask_session["csrf_tokens"] = ["valid-csrf-token"]
    outbound = Mock(return_value=_provider_response('{"suggestion":"Safe summary"}'))
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)

    denied = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
    )
    allowed = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
        headers={"X-CSRF-Token": "valid-csrf-token"},
    )

    app.config["CSRF_ENABLED"] = False
    assert denied.status_code == 403
    assert allowed.status_code == 200
    outbound.assert_called_once()


def test_local_compatible_provider_works_without_api_key(enabled_ai, monkeypatch) -> None:
    from app.config.model import DevLogConfig

    app = enabled_ai.application
    app.config["DEVLOG_CONFIG"] = replace(
        app.config["DEVLOG_CONFIG"],
        ai=AiConfig(model="local-model", api_key=""),
    )
    post = Mock(return_value=_provider_response('{"suggestion":"A local summary."}'))
    monkeypatch.setattr(ai_assist.http_client, "post", post)

    response = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "Title", "body": "Local draft."},
    )

    assert response.status_code == 200
    assert response.json == {"suggestion": "A local summary."}
    assert "Authorization" not in post.call_args.kwargs["headers"]
    assert ai_assist.is_ai_assist_available(
        DevLogConfig(ai=AiConfig(model="local-model", api_key=""))
    )


def test_provider_request_uses_local_compatible_endpoint_and_long_timeout(
    enabled_ai, db, monkeypatch
) -> None:
    posts_before = db.session.execute(select(Post.id)).all()
    tags_before = db.session.execute(select(Tag.id)).all()
    post = Mock(
        side_effect=lambda *args, **kwargs: _provider_response(
            '{"suggestion":"A concise factual summary."}'
        )
    )
    monkeypatch.setattr(ai_assist.http_client, "post", post)
    first = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "Title", "body": "Current unsaved text."},
    )
    second = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "Title", "body": "Current unsaved text."},
    )
    assert first.status_code == 200
    assert first.json == {"suggestion": "A concise factual summary."}
    assert second.status_code == 200
    assert post.call_count == 2
    assert post.call_args_list[0].args[0] == (
        f"{ai_assist.DEFAULT_COMPATIBLE_BASE_URL}/chat/completions"
    )
    first_headers = post.call_args_list[0].kwargs["headers"]
    assert first_headers["Authorization"] == "Bearer test-private-key"
    assert "x-opencode-session" not in first_headers
    assert first_headers["User-Agent"].startswith("DevLog-")
    assert post.call_args_list[0].kwargs["timeout"] == (3, 180)
    assert post.call_args_list[0].kwargs["stream"] is True
    assert (
        "Current unsaved text." in post.call_args_list[0].kwargs["json"]["messages"][1]["content"]
    )
    assert db.session.execute(select(Post.id)).all() == posts_before
    assert db.session.execute(select(Tag.id)).all() == tags_before


def test_chat_content_text_parts_are_extracted(enabled_ai, monkeypatch) -> None:
    response = _provider_payload_response(
        {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": '{"suggestion":'},
                            {"type": "text", "text": '"A concise factual summary."}'},
                        ]
                    },
                    "finish_reason": "stop",
                }
            ]
        }
    )
    monkeypatch.setattr(ai_assist.http_client, "post", Mock(return_value=response))

    result = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
    )

    assert result.status_code == 200
    assert result.json == {"suggestion": "A concise factual summary."}


def test_truncated_chat_completion_retries_with_larger_token_budget(
    enabled_ai, monkeypatch
) -> None:
    truncated = _provider_payload_response(
        {
            "choices": [
                {
                    "message": {"content": '{"suggestion":"partial'},
                    "finish_reason": "length",
                }
            ]
        }
    )
    complete = _provider_response('{"suggestion":"A concise factual summary."}')
    outbound = Mock(side_effect=[truncated, complete])
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())

    result = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
    )

    assert result.status_code == 200
    assert result.json == {"suggestion": "A concise factual summary."}
    assert outbound.call_count == 2
    assert outbound.call_args_list[0].kwargs["json"]["max_tokens"] == 500
    assert outbound.call_args_list[1].kwargs["json"]["max_tokens"] == 2048
    truncated.close.assert_called_once()


def test_invalid_model_value_retries_once(enabled_ai, monkeypatch) -> None:
    outbound = Mock(
        side_effect=[
            _provider_response('{"suggestion":42}'),
            _provider_response('{"suggestion":"A concise factual summary."}'),
        ]
    )
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())

    result = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
    )

    assert result.status_code == 200
    assert result.json == {"suggestion": "A concise factual summary."}
    assert outbound.call_count == 2


def test_invalid_model_json_retries_once_without_logging_content(
    enabled_ai, monkeypatch, caplog
) -> None:
    private_text = "Synthetic private draft marker"
    outbound = Mock(
        side_effect=[
            _provider_response(f"not-json {private_text}"),
            _provider_response('{"suggestion":"A concise factual summary."}'),
        ]
    )
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())

    result = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": private_text},
    )

    assert result.status_code == 200
    assert result.json == {"suggestion": "A concise factual summary."}
    assert outbound.call_count == 2
    assert private_text not in caplog.text
    assert "not-json" not in caplog.text


@pytest.mark.parametrize(
    ("response_payload", "expected"),
    [
        (
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": '{"suggestion":"A concise summary."}'}
                        ],
                    }
                ]
            },
            '{"suggestion":"A concise summary."}',
        ),
        (
            {"output_text": '{"suggestion":"A concise summary."}', "output": []},
            '{"suggestion":"A concise summary."}',
        ),
    ],
)
def test_responses_model_uses_responses_endpoint_and_parses_output_text(
    response_payload: dict, expected: str, monkeypatch
) -> None:
    response = Mock()
    response.status_code = 200
    response.iter_content.return_value = iter([json.dumps(response_payload).encode()])
    response.close.return_value = None
    post = Mock(return_value=response)
    monkeypatch.setattr(ai_assist.http_client, "post", post)

    result = ai_assist._complete(
        api_key="test-key",
        model="muse-spark-1.3-contributor",
        provider="opencode_go",
        timeout_seconds=20,
        instruction="Return a JSON suggestion.",
        source='{"title":"Synthetic","body":"Synthetic input."}',
    )

    assert result == expected
    assert post.call_args.args[0] == f"{ai_assist.OPENCODE_GO_BASE_URL}/responses"
    request_payload = post.call_args.kwargs["json"]
    assert request_payload["model"] == "muse-spark-1.3-contributor"
    assert request_payload["instructions"] == "Return a JSON suggestion."
    assert request_payload["input"] == '{"title":"Synthetic","body":"Synthetic input."}'
    assert request_payload["max_output_tokens"] == 2048
    assert request_payload["reasoning"] == {"effort": "low"}
    assert "messages" not in request_payload
    assert post.call_args.kwargs["headers"]["x-opencode-session"]
    assert post.call_args.kwargs["timeout"] == (3, 20)
    response.close.assert_called_once()


def test_tag_candidates_validate_and_deduplicate_by_canonical_slug() -> None:
    candidates = ai_assist._tag_candidates(
        json.dumps({"tags": ["Python", "python", "!!!", "Flask", "Web Security", "x" * 51]})
    )
    assert candidates == ["Python", "Flask", "Web Security"]
    with pytest.raises(ai_assist.ProviderError):
        ai_assist._tag_candidates('{"tags":[]}')
    with pytest.raises(ai_assist.ProviderError):
        ai_assist._tag_candidates('```json {"tags":["Python"]} ```')


def test_summary_rejects_html_and_oversize_output(monkeypatch) -> None:
    monkeypatch.setattr(ai_assist, "_complete", lambda **kwargs: '{"suggestion":"<b>bad</b>"}')
    with pytest.raises(ai_assist.ProviderError):
        ai_assist.suggest_summary(title="Title", body="Body", api_key="secret", model="model")
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: json.dumps({"suggestion": "x" * 501}),
    )
    with pytest.raises(ai_assist.ProviderError):
        ai_assist.suggest_summary(title="Title", body="Body", api_key="secret", model="model")


def test_transient_provider_failure_retries_then_succeeds(enabled_ai, monkeypatch) -> None:
    retry_after = _provider_response("temporary upstream failure", status_code=503)
    success = _provider_response('{"suggestion":"A concise factual summary."}')
    outbound = Mock(side_effect=[retry_after, success])
    sleep = Mock()
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", sleep)

    result = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Some text"},
    )

    assert result.status_code == 200
    assert result.json == {"suggestion": "A concise factual summary."}
    assert outbound.call_count == 2
    sleep.assert_called_once_with(ai_assist.RETRY_DELAY_SECONDS)
    retry_after.close.assert_called_once()


def test_empty_local_completion_is_retried(enabled_ai, monkeypatch) -> None:
    outbound = Mock(
        side_effect=[
            _provider_response(""),
            _provider_response('{"suggestion":"A concise factual summary."}'),
        ]
    )
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())

    response = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Synthetic body"},
    )

    assert response.status_code == 200
    assert response.json == {"suggestion": "A concise factual summary."}
    assert outbound.call_count == 2


def test_provider_failure_is_retried_and_sanitized(enabled_ai, monkeypatch) -> None:
    response = _provider_response("private upstream detail", status_code=429)
    outbound = Mock(return_value=response)
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())
    result = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Some text"},
    )
    assert result.status_code == 502
    assert "private upstream detail" not in result.get_data(as_text=True)
    assert result.json["error"] == "The AI service is temporarily unavailable. Please try again."
    assert outbound.call_count == ai_assist.MAX_PROVIDER_ATTEMPTS


def test_nontransient_provider_error_is_not_retried(enabled_ai, monkeypatch) -> None:
    outbound = Mock(return_value=_provider_response("private detail", status_code=401))
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)

    response = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
    )

    assert response.status_code == 502
    assert (
        response.json["error"] == "The AI provider rejected the request. Check its configuration."
    )
    outbound.assert_called_once()


def test_provider_timeout_retries_and_displays_reachability_error(enabled_ai, monkeypatch) -> None:
    outbound = Mock(side_effect=ai_assist.http_client.TimeoutException)
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())
    response = enabled_ai.post(
        "/admin/ai-assist",
        json={"action": "summary", "title": "T", "body": "Body"},
    )
    assert response.status_code == 502
    assert response.json["error"] == (
        "The configured AI provider could not be reached. Check its URL and ensure it is running."
    )
    assert outbound.call_count == ai_assist.MAX_PROVIDER_ATTEMPTS


def test_response_size_is_limited() -> None:
    response = Mock()
    response.iter_content.return_value = iter([b"x" * (ai_assist.MAX_RESPONSE_BYTES + 1)])
    with pytest.raises(ai_assist.ProviderError, match="oversized"):
        ai_assist._read_bounded_response(response)


def test_fenced_json_object_is_accepted(monkeypatch) -> None:
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: '```json\n{"suggestion":"A concise factual summary."}\n```',
    )
    summary = ai_assist.suggest_summary(title="Title", body="Body", api_key="secret", model="model")
    assert summary == "A concise factual summary."


def test_prose_wrapped_json_object_is_accepted(monkeypatch) -> None:
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: (
            'Here is the result:\n{"suggestion":"A concise factual summary."}\nHope it helps.'
        ),
    )
    summary = ai_assist.suggest_summary(title="Title", body="Body", api_key="secret", model="model")
    assert summary == "A concise factual summary."


def test_fenced_tag_suggestions_are_accepted() -> None:
    candidates = ai_assist._tag_candidates(
        '```json\n{"tags": ["Python", "Flask", "Web Security"]}\n```'
    )
    assert candidates == ["Python", "Flask", "Web Security"]


def test_non_json_response_is_still_rejected(monkeypatch) -> None:
    monkeypatch.setattr(ai_assist, "_complete", lambda **kwargs: "I cannot help with that.")
    with pytest.raises(ai_assist.ProviderError):
        ai_assist.suggest_summary(title="Title", body="Body", api_key="secret", model="model")


def test_json_object_with_unexpected_keys_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: '{"suggestion":"A concise factual summary.","extra":true}',
    )
    with pytest.raises(ai_assist.ProviderError):
        ai_assist.suggest_summary(title="Title", body="Body", api_key="secret", model="model")


def test_empty_tag_catalog_needs_one_call_and_does_not_write(db, monkeypatch) -> None:
    calls: list[dict] = []

    def complete(**kwargs):
        calls.append(kwargs)
        return '{"tags":["Python","Flask","Web Security"]}'

    monkeypatch.setattr(ai_assist, "_complete", complete)
    before = db.session.execute(select(Tag.id)).scalars().all()
    result = ai_assist.suggest_tags(
        title="Title",
        body="Unsent body",
        api_key="secret",
        model="model",
        is_admin=True,
    )
    after = db.session.execute(select(Tag.id)).scalars().all()
    assert len(calls) == 1
    assert result == {
        "suggestions": ["Python", "Flask", "Web Security"],
        "reused": [],
        "new": ["Python", "Flask", "Web Security"],
    }
    assert before == after


def test_exact_tag_reuse_skips_second_call(db, ai_admin_user, monkeypatch) -> None:
    user = ai_admin_user
    tag = Tag(name="Python", slug="python")
    post = Post(
        title="Published example",
        slug="published-example",
        body="Example body",
        summary="",
        published=True,
        author_id=user.id,
        tags=[tag],
    )
    db.session.add(post)
    db.session.commit()
    calls: list[dict] = []
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: calls.append(kwargs) or '{"tags":["python","Flask","Web Security"]}',
    )

    result = ai_assist.suggest_tags(
        title="Title",
        body="Body",
        api_key="secret",
        model="model",
        is_admin=True,
    )

    assert len(calls) == 2
    assert result["suggestions"][0] == "Python"
    assert result["reused"] == ["Python"]
    assert result["new"] == ["Flask", "Web Security"]
    assert db.session.execute(select(Tag.id)).scalars().all() == [tag.id]


def test_non_admin_does_not_reuse_unpublished_only_tag(db, ai_admin_user, monkeypatch) -> None:
    user = ai_admin_user
    tag = Tag(name="Private Topic", slug="private-topic")
    draft = Post(
        title="Unpublished example",
        slug="unpublished-example",
        body="Draft text",
        summary="",
        published=False,
        author_id=user.id,
        tags=[tag],
    )
    db.session.add(draft)
    db.session.commit()
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: '{"tags":["Private Topic","Other One","Other Two"]}',
    )

    result = ai_assist.suggest_tags(
        title="Title",
        body="Body",
        api_key="secret",
        model="model",
        is_admin=False,
    )

    assert result["suggestions"][0] == "Private Topic"
    assert "Private Topic" not in result["reused"]


def test_semantic_tag_mapping_uses_only_catalog_ids(db, ai_admin_user, monkeypatch) -> None:
    user = ai_admin_user
    tag = Tag(name="Machine Learning", slug="machine-learning")
    post = Post(
        title="Published example",
        slug="published-example-2",
        body="Example body",
        summary="",
        published=True,
        author_id=user.id,
        tags=[tag],
    )
    db.session.add(post)
    db.session.commit()
    calls: list[dict] = []

    def complete(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return '{"tags":["ML","Flask","Web Security"]}'
        return (
            "```json\n"
            + json.dumps(
                {
                    "resolutions": [
                        {"candidate": "ML", "tag_id": tag.id},
                        {"candidate": "Flask", "new": True},
                        {"candidate": "Web Security", "new": True},
                    ]
                }
            )
            + "\n```"
        )

    monkeypatch.setattr(ai_assist, "_complete", complete)
    result = ai_assist.suggest_tags(
        title="Title",
        body="First pass only",
        api_key="secret",
        model="model",
        is_admin=True,
    )

    assert len(calls) == 2
    second_source = calls[1]["source"]
    assert "First pass only" not in second_source
    assert "published example" not in second_source
    assert "Machine Learning" in second_source
    assert result["suggestions"] == ["Machine Learning", "Flask", "Web Security"]
    assert result["reused"] == ["Machine Learning"]
    assert result["new"] == ["Flask", "Web Security"]
    assert db.session.execute(select(Tag.id)).scalars().all() == [tag.id]


def test_catalog_is_bounded_stable_and_uses_constant_queries(db, ai_admin_user) -> None:
    tags = [Tag(name=f"Topic {index:03d}", slug=f"topic-{index:03d}") for index in range(100)]
    db.session.add_all(tags)
    db.session.flush()
    popular_posts = [
        Post(
            title=f"Popular example {index}",
            slug=f"popular-example-{index}",
            body="Published body",
            summary="",
            published=True,
            author_id=ai_admin_user.id,
            tags=[tags[90]],
        )
        for index in range(5)
    ]
    db.session.add_all(popular_posts)
    db.session.commit()
    statements: list[str] = []

    def count_query(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", count_query)
    try:
        first = ai_assist._catalog(is_admin=True, candidates=["Topic 099"])
        first_query_count = len(statements)
        statements.clear()
        second = ai_assist._catalog(is_admin=True, candidates=["Topic 099"])
        second_query_count = len(statements)
    finally:
        event.remove(db.engine, "before_cursor_execute", count_query)

    serialized = json.dumps(first, separators=(",", ":"))
    assert first == second
    assert len(first) <= ai_assist.MAX_CATALOG_ITEMS
    assert len(serialized) <= ai_assist.MAX_CATALOG_CHARS
    assert first[0]["name"] == "Topic 099"
    assert {item["name"] for item in first} >= {"Topic 099", "Topic 090"}
    assert first_query_count <= 3
    assert second_query_count <= 3


def test_tag_second_pass_timeout_falls_back_without_mutation(
    db, ai_admin_user, monkeypatch
) -> None:
    tag = Tag(name="Existing Topic", slug="existing-topic")
    post = Post(
        title="Published example",
        slug="published-example-timeout",
        body="Published body",
        summary="",
        published=True,
        author_id=ai_admin_user.id,
        tags=[tag],
    )
    db.session.add(post)
    db.session.commit()
    outbound = Mock(
        side_effect=[
            _provider_response('{"tags":["Python","Flask","Web Security"]}'),
            ai_assist.http_client.TimeoutException,
            ai_assist.http_client.TimeoutException,
        ]
    )
    monkeypatch.setattr(ai_assist.http_client, "post", outbound)
    monkeypatch.setattr(ai_assist.time, "sleep", Mock())
    tags_before = db.session.execute(select(Tag.id)).all()
    result = ai_assist.suggest_tags(
        title="Title",
        body="Body",
        api_key="secret",
        model="model",
        is_admin=True,
    )
    assert outbound.call_count == 3
    assert result["suggestions"] == ["Python", "Flask", "Web Security"]
    assert db.session.execute(select(Tag.id)).all() == tags_before


def test_invalid_second_pass_falls_back_to_candidates(db, ai_admin_user, monkeypatch) -> None:
    user = ai_admin_user
    tag = Tag(name="Existing Topic", slug="existing-topic")
    post = Post(
        title="Published example",
        slug="published-example-3",
        body="Body",
        summary="",
        published=True,
        author_id=user.id,
        tags=[tag],
    )
    db.session.add(post)
    db.session.commit()
    monkeypatch.setattr(
        ai_assist,
        "_complete",
        lambda **kwargs: (
            '{"tags":["Python","Flask","Web Security"]}'
            if kwargs["instruction"].startswith("Return only a JSON object with one field tags")
            else '{"resolutions":[{"candidate":"Python","tag_id":999}]}'
        ),
    )
    result = ai_assist.suggest_tags(
        title="Title",
        body="Body",
        api_key="secret",
        model="model",
        is_admin=True,
    )
    assert result == {
        "suggestions": ["Python", "Flask", "Web Security"],
        "reused": [],
        "new": ["Python", "Flask", "Web Security"],
    }
