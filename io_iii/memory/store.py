"""
io_iii.memory.store — Phase 6 M6.1 memory store (ADR-022 §2).

Provides:
    MemoryRecord  — atomic, scoped, versioned memory record
    MemoryStore   — local file-backed store; deterministic key lookup only

Content policy (ADR-003, ADR-022 §6):
    MemoryRecord.value is CONTENT-PLANE and must never appear in any log field.
    Use MemoryRecord.to_log_safe() for all logging projections.
    MemoryStore emits no logging; callers are responsible for content-safe logging.
"""
from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Sensitivity tiers (ADR-022 §2.1)
# ---------------------------------------------------------------------------

SENSITIVITY_STANDARD = "standard"
SENSITIVITY_ELEVATED = "elevated"
SENSITIVITY_RESTRICTED = "restricted"

VALID_SENSITIVITY = frozenset({
    SENSITIVITY_STANDARD,
    SENSITIVITY_ELEVATED,
    SENSITIVITY_RESTRICTED,
})

# ---------------------------------------------------------------------------
# Provenance values (ADR-007, ADR-022 §2.1)
# ---------------------------------------------------------------------------

PROVENANCE_HUMAN = "human"
PROVENANCE_MIXED = "mixed"
# LLM provenance is "llm:<slug>" — validated by regex below.
_LLM_PROVENANCE_RE = re.compile(r"^llm:[a-zA-Z0-9._-]+$")

VALID_PROVENANCE_LITERALS = frozenset({"human", "mixed"})


def _validate_provenance(value: str) -> None:
    if value in VALID_PROVENANCE_LITERALS:
        return
    if _LLM_PROVENANCE_RE.match(value):
        return
    raise ValueError(
        f"MemoryRecord.provenance must be 'human', 'mixed', or 'llm:<slug>'; "
        f"got '{value}'"
    )


# ---------------------------------------------------------------------------
# MemoryRecord (ADR-022 §2.1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryRecord:
    """
    Atomic, scoped, versioned memory record (ADR-022 §2.1).

    Content policy:
        'value' is content-plane. It must never appear in any log field.
        Use to_log_safe() for all logging projections.

    Fields:
        key          — stable, human-readable identifier; unique within scope
        scope        — scope identifier; determines access boundaries
        value        — record content; NEVER log this field
        version      — monotonically increasing; starts at 1
        provenance   — "human" | "llm:<slug>" | "mixed"
        created_at   — ISO 8601 timestamp
        updated_at   — ISO 8601 timestamp
        sensitivity  — "standard" | "elevated" | "restricted"
    """

    key: str
    scope: str
    value: str
    version: int
    provenance: str
    created_at: str
    updated_at: str
    sensitivity: str

    def __post_init__(self) -> None:
        if not self.key or not isinstance(self.key, str):
            raise ValueError("MemoryRecord.key must be a non-empty string")
        if not self.scope or not isinstance(self.scope, str):
            raise ValueError("MemoryRecord.scope must be a non-empty string")
        if not isinstance(self.value, str):
            raise ValueError("MemoryRecord.value must be a string")
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("MemoryRecord.version must be an integer >= 1")
        _validate_provenance(self.provenance)
        if self.sensitivity not in VALID_SENSITIVITY:
            raise ValueError(
                f"MemoryRecord.sensitivity must be one of "
                f"{sorted(VALID_SENSITIVITY)}; got '{self.sensitivity}'"
            )
        if not self.created_at or not isinstance(self.created_at, str):
            raise ValueError("MemoryRecord.created_at must be a non-empty string")
        if not self.updated_at or not isinstance(self.updated_at, str):
            raise ValueError("MemoryRecord.updated_at must be a non-empty string")

    def to_log_safe(self) -> dict:
        """
        Content-safe projection for logging (ADR-003, ADR-022 §6.1).

        Never includes 'value'. Safe to write to metadata.jsonl or any log sink.
        """
        return {
            "key": self.key,
            "scope": self.scope,
            "version": self.version,
            "provenance": self.provenance,
            "sensitivity": self.sensitivity,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def identifier(self) -> str:
        """Return stable record identifier: <scope>/<key> (ADR-022 §7.1)."""
        return f"{self.scope}/{self.key}"


# ---------------------------------------------------------------------------
# MemoryStore (ADR-022 §2.2 / §2.3)
# ---------------------------------------------------------------------------

class MemoryStore:
    """
    Local file-backed memory store (ADR-022 §2.2).

    Storage layout:
        <storage_root>/<scope>/<key>.json  — one JSON file per record

    Properties:
        - Atomic writes via temp file + rename (POSIX atomic on same filesystem)
        - Deterministic lookup by key; no search or ranking
        - Scope isolation: list operations are strictly scoped
        - Storage root is configurable; no hardcoded paths permitted

    Content policy:
        This class performs no logging. Callers are responsible for
        content-safe log projections (use MemoryRecord.to_log_safe()).
    """

    def __init__(self, storage_root: str | Path) -> None:
        self._root = Path(storage_root)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_path(self, scope: str, key: str) -> Path:
        return self._root / scope / f"{key}.json"

    def _deserialise(self, path: Path) -> MemoryRecord:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MemoryRecord(**data)

    def _serialise(self, record: MemoryRecord) -> str:
        return json.dumps(dataclasses.asdict(record), ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, scope: str, key: str) -> Optional[MemoryRecord]:
        """
        Return the record for (scope, key), or None if it does not exist.

        Lookup is deterministic from (scope, key). No search or ranking.
        """
        path = self._record_path(scope, key)
        if not path.is_file():
            return None
        return self._deserialise(path)

    def put(self, record: MemoryRecord) -> None:
        """
        Write a record to the store (atomic: temp file + rename).

        Callers are responsible for version management (M6.6 write contract).
        Creates parent directories as needed.
        """
        path = self._record_path(record.scope, record.key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(self._serialise(record), encoding="utf-8")
        tmp.replace(path)  # POSIX-atomic rename

    def list_by_scope(self, scope: str) -> list[MemoryRecord]:
        """
        Return all records in scope, sorted by key (deterministic ordering).

        Returns an empty list if the scope directory does not exist.
        """
        scope_dir = self._root / scope
        if not scope_dir.is_dir():
            return []
        records = [
            self._deserialise(p)
            for p in sorted(scope_dir.glob("*.json"))
        ]
        return records

    def list_by_keys(self, scope: str, keys: list[str]) -> list[MemoryRecord]:
        """
        Return records for the declared key list, in declaration order.

        Missing keys are skipped silently (no error). This matches the
        M6.4 injection contract: overflow records are dropped without failure.
        """
        result = []
        for key in keys:
            record = self.get(scope, key)
            if record is not None:
                result.append(record)
        return result

    def exists(self, scope: str, key: str) -> bool:
        """Return True if a record exists for (scope, key)."""
        return self._record_path(scope, key).is_file()

    @staticmethod
    def record_identifier(scope: str, key: str) -> str:
        """Return stable record identifier: <scope>/<key> (ADR-022 §7.1)."""
        return f"{scope}/{key}"
