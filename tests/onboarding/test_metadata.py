from __future__ import annotations


from app.onboarding.metadata import (
    OnboardingMetadata,
    is_complete,
    load_metadata,
    save_metadata,
)


def _make_metadata(**overrides) -> OnboardingMetadata:
    defaults = dict(
        version=1,
        mode="native",
        profile="development",
        package_version="1.0.0",
        completed_at="2025-01-01T00:00:00+00:00",
        config_path="/config.toml",
        data_path="/data",
        managed_paths=["/config.toml", ".env", "/data"],
        admin_username="admin",
    )
    defaults.update(overrides)
    return OnboardingMetadata(**defaults)


class TestLoadMetadataMissing:
    def test_returns_none_when_no_file(self, tmp_path):
        result = load_metadata(tmp_path / "noexist")

        assert result is None

    def test_returns_none_when_invalid_json(self, tmp_path):
        (tmp_path / "onboarding-metadata.json").write_text("not json {{{")

        result = load_metadata(tmp_path)

        assert result is None

    def test_returns_none_when_wrong_version(self, tmp_path):
        import json

        (tmp_path / "onboarding-metadata.json").write_text(json.dumps({"version": 99}))

        result = load_metadata(tmp_path)

        assert result is None


class TestSaveAndLoadRoundtrip:
    def test_roundtrip(self, tmp_path):
        meta = _make_metadata()
        save_metadata(tmp_path, meta)

        loaded = load_metadata(tmp_path)

        assert loaded is not None
        assert loaded.version == meta.version
        assert loaded.mode == meta.mode
        assert loaded.profile == meta.profile
        assert loaded.completed_at == meta.completed_at
        assert loaded.admin_username == meta.admin_username

    def test_creates_directory(self, tmp_path):
        target = tmp_path / "nested" / "data"
        meta = _make_metadata()

        save_metadata(target, meta)

        assert (target / "onboarding-metadata.json").exists()

    def test_preserves_managed_paths(self, tmp_path):
        meta = _make_metadata(managed_paths=["a", "b", "c"])
        save_metadata(tmp_path, meta)

        loaded = load_metadata(tmp_path)

        assert loaded is not None
        assert loaded.managed_paths == ["a", "b", "c"]

    def test_overwrites_existing(self, tmp_path):
        meta1 = _make_metadata(mode="native")
        save_metadata(tmp_path, meta1)

        meta2 = _make_metadata(mode="docker")
        save_metadata(tmp_path, meta2)

        loaded = load_metadata(tmp_path)

        assert loaded is not None
        assert loaded.mode == "docker"


class TestIsCompleteMetadata:
    def test_true_with_valid_metadata(self):
        meta = _make_metadata()

        assert is_complete(meta) is True

    def test_false_with_none(self):
        assert is_complete(None) is False

    def test_false_with_empty_completed_at(self):
        meta = _make_metadata(completed_at="")

        assert is_complete(meta) is False

    def test_false_with_wrong_version(self):
        meta = _make_metadata(version=99)

        assert is_complete(meta) is False

    def test_true_with_any_nonempty_completed_at(self):
        meta = _make_metadata(completed_at="2025-06-15T12:00:00")

        assert is_complete(meta) is True
