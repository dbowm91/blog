from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldProvenance:
    source: str
    file_path: str | None = None
    env_var: str | None = None


class ProvenanceTracker:
    def __init__(self) -> None:
        self._records: dict[str, FieldProvenance] = {}

    def record(self, field_path: str, provenance: FieldProvenance) -> None:
        self._records[field_path] = provenance

    def get(self, field_path: str) -> FieldProvenance:
        return self._records.get(field_path, FieldProvenance(source="default"))

    def all(self) -> dict[str, FieldProvenance]:
        return dict(self._records)
