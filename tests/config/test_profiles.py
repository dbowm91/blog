from __future__ import annotations

from app.config.model import DevLogConfig
from app.config.profiles import PROFILES, Profile, get_profile, list_profiles


class TestProfiles:
    def test_all_expected_profiles_exist(self) -> None:
        expected = {"development", "native-production", "docker-production", "minimal", "full"}
        assert set(PROFILES.keys()) == expected

    def test_profiles_are_profile_instances(self) -> None:
        for name, profile in PROFILES.items():
            assert isinstance(profile, Profile)
            assert profile.name == name
            assert isinstance(profile.config, DevLogConfig)

    def test_development_profile(self) -> None:
        profile = PROFILES["development"]
        assert profile.config.server.debug is True
        assert profile.config.session_cookie_secure is False
        assert profile.config.server.host == "127.0.0.1"

    def test_native_production_profile(self) -> None:
        profile = PROFILES["native-production"]
        assert profile.config.server.debug is False
        assert profile.config.session_cookie_secure is True
        assert profile.config.scheduler.enabled is True

    def test_docker_production_profile(self) -> None:
        profile = PROFILES["docker-production"]
        assert profile.config.server.debug is False
        assert profile.config.session_cookie_secure is True
        assert profile.config.scheduler.enabled is False

    def test_minimal_profile(self) -> None:
        profile = PROFILES["minimal"]
        assert profile.config.server.debug is False
        assert profile.config.session_cookie_secure is False

    def test_full_profile(self) -> None:
        profile = PROFILES["full"]
        assert profile.config.server.debug is False
        assert profile.config.session_cookie_secure is True
        assert profile.config.scheduler.enabled is True


class TestGetProfile:
    def test_existing_profile(self) -> None:
        profile = get_profile("development")
        assert profile is not None
        assert profile.name == "development"

    def test_nonexistent_profile(self) -> None:
        assert get_profile("nonexistent") is None

    def test_case_sensitive(self) -> None:
        assert get_profile("Development") is None


class TestListProfiles:
    def test_returns_all_profiles(self) -> None:
        result = list_profiles()
        assert len(result) == len(PROFILES)

    def test_returns_name_and_description(self) -> None:
        result = list_profiles()
        for item in result:
            assert "name" in item
            assert "description" in item
            assert isinstance(item["name"], str)
            assert isinstance(item["description"], str)

    def test_matches_profiles_keys(self) -> None:
        result = list_profiles()
        names = {item["name"] for item in result}
        assert names == set(PROFILES.keys())
