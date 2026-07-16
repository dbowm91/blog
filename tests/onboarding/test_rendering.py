from __future__ import annotations

import json

from app.onboarding.rendering import (
    CompletionInfo,
    render_completion_human,
    render_completion_json,
)


def _make_info(**overrides) -> CompletionInfo:
    defaults = dict(
        mode="native",
        config_path="/config.toml",
        data_path="/data",
        base_url="http://localhost:5000",
        admin_username="admin",
        validation_ok=True,
        next_command="python run.py",
        warnings=[],
    )
    defaults.update(overrides)
    return CompletionInfo(**defaults)


class TestRenderCompletionHuman:
    def test_contains_header(self):
        info = _make_info()
        output = render_completion_human(info)

        assert "Onboarding Complete" in output
        assert "=" * 40 in output

    def test_contains_mode(self):
        info = _make_info(mode="docker")
        output = render_completion_human(info)

        assert "Mode:       docker" in output

    def test_contains_config_path(self):
        info = _make_info(config_path="/etc/config.toml")
        output = render_completion_human(info)

        assert "/etc/config.toml" in output

    def test_contains_data_path(self):
        info = _make_info(data_path="/data/dir")
        output = render_completion_human(info)

        assert "/data/dir" in output

    def test_contains_base_url(self):
        info = _make_info(base_url="https://blog.example.com")
        output = render_completion_human(info)

        assert "https://blog.example.com" in output

    def test_contains_admin_username(self):
        info = _make_info(admin_username="superadmin")
        output = render_completion_human(info)

        assert "superadmin" in output

    def test_contains_next_command(self):
        info = _make_info(next_command="docker compose up")
        output = render_completion_human(info)

        assert "docker compose up" in output

    def test_shows_valid_yes(self):
        info = _make_info(validation_ok=True)
        output = render_completion_human(info)

        assert "yes" in output

    def test_shows_valid_no(self):
        info = _make_info(validation_ok=False)
        output = render_completion_human(info)

        assert "no" in output

    def test_contains_warnings(self):
        info = _make_info(warnings=["Warning one", "Warning two"])
        output = render_completion_human(info)

        assert "Warning one" in output
        assert "Warning two" in output
        assert "Warnings:" in output

    def test_no_warnings_section_when_empty(self):
        info = _make_info(warnings=[])
        output = render_completion_human(info)

        assert "Warnings:" not in output


class TestRenderCompletionJson:
    def test_valid_json(self):
        info = _make_info()
        output = render_completion_json(info)
        parsed = json.loads(output)

        assert isinstance(parsed, dict)
        assert parsed["mode"] == "native"
        assert parsed["config_path"] == "/config.toml"

    def test_contains_all_fields(self):
        info = _make_info(
            warnings=["w1"],
            validation_ok=True,
        )
        output = render_completion_json(info)
        parsed = json.loads(output)

        expected_keys = {
            "mode",
            "config_path",
            "data_path",
            "base_url",
            "admin_username",
            "validation_ok",
            "next_command",
            "warnings",
        }
        assert expected_keys == set(parsed.keys())

    def test_warnings_list_preserved(self):
        info = _make_info(warnings=["warn1", "warn2"])
        output = render_completion_json(info)
        parsed = json.loads(output)

        assert parsed["warnings"] == ["warn1", "warn2"]


class TestCompletionInfoRedactsNoSecrets:
    def test_no_secrets_in_human_output(self):
        info = _make_info()
        output = render_completion_human(info)

        assert "SECRET_KEY" not in output
        assert "ADMIN_PASSWORD" not in output
        assert "HEALTH_CHECK_SECRET" not in output

    def test_no_secrets_in_json_output(self):
        info = _make_info()
        output = render_completion_json(info)

        assert "SECRET_KEY" not in output
        assert "ADMIN_PASSWORD" not in output
        assert "HEALTH_CHECK_SECRET" not in output
