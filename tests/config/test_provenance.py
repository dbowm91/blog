from __future__ import annotations

import pytest

from app.config.provenance import FieldProvenance, ProvenanceTracker


class TestFieldProvenance:
    def test_creation(self) -> None:
        fp = FieldProvenance(source="toml")
        assert fp.source == "toml"
        assert fp.file_path is None
        assert fp.env_var is None

    def test_with_all_fields(self) -> None:
        fp = FieldProvenance(source="env", file_path="/path", env_var="SECRET_KEY")
        assert fp.source == "env"
        assert fp.file_path == "/path"
        assert fp.env_var == "SECRET_KEY"

    def test_frozen(self) -> None:
        fp = FieldProvenance(source="default")
        with pytest.raises(AttributeError):
            fp.source = "new"  # type: ignore[misc]


class TestProvenanceTracker:
    def test_record_and_get(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("secret_key", FieldProvenance(source="env", env_var="SECRET_KEY"))
        result = tracker.get("secret_key")
        assert result.source == "env"
        assert result.env_var == "SECRET_KEY"

    def test_get_unknown_returns_default(self) -> None:
        tracker = ProvenanceTracker()
        result = tracker.get("unknown.field")
        assert result.source == "default"
        assert result.file_path is None
        assert result.env_var is None

    def test_all_returns_full_dict(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("a", FieldProvenance(source="toml"))
        tracker.record("b", FieldProvenance(source="env"))
        result = tracker.all()
        assert len(result) == 2
        assert "a" in result
        assert "b" in result

    def test_all_returns_copy(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("a", FieldProvenance(source="toml"))
        result = tracker.all()
        result["c"] = FieldProvenance(source="cli")
        assert "c" not in tracker.all()

    def test_overwrite_record(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("key", FieldProvenance(source="toml"))
        tracker.record("key", FieldProvenance(source="env"))
        result = tracker.get("key")
        assert result.source == "env"

    def test_multiple_fields(self) -> None:
        tracker = ProvenanceTracker()
        tracker.record("secret_key", FieldProvenance(source="env"))
        tracker.record("admin_password", FieldProvenance(source="env"))
        tracker.record("app.title", FieldProvenance(source="toml", file_path="/etc/config.toml"))
        result = tracker.all()
        assert len(result) == 3

    def test_empty_tracker(self) -> None:
        tracker = ProvenanceTracker()
        assert tracker.all() == {}
        assert tracker.get("anything").source == "default"
