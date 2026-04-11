"""
test_memory_store_m61.py — Phase 6 M6.1 memory store tests (ADR-022 §2).

Verifies:

  Unit — MemoryRecord
  - construction and field access
  - is frozen (immutable)
  - to_log_safe() never includes value
  - identifier() returns <scope>/<key>
  - validation: empty key rejected
  - validation: empty scope rejected
  - validation: version < 1 rejected
  - validation: version = 0 rejected
  - validation: invalid sensitivity rejected
  - validation: valid sensitivity values accepted
  - validation: provenance "human" accepted
  - validation: provenance "mixed" accepted
  - validation: provenance "llm:slug" accepted
  - validation: provenance "llm:model-name.v2" accepted
  - validation: invalid provenance rejected

  Unit — MemoryStore
  - put and get roundtrip preserves all fields
  - get returns None for missing key
  - get is scope-isolated (key in scope A not returned for scope B)
  - put creates directories as needed
  - put is atomic (temp file replaced; no .tmp left on disk)
  - put overwrites existing record without error
  - exists returns True for present record
  - exists returns False for missing record
  - list_by_scope returns all records in scope
  - list_by_scope is deterministic (sorted by key)
  - list_by_scope returns empty list for missing scope
  - list_by_scope excludes records from other scopes
  - list_by_keys returns records in declaration order
  - list_by_keys skips missing keys silently
  - list_by_keys returns empty list when all keys missing
  - record_identifier returns <scope>/<key>

  Unit — failure model integration
  - MEMORY_WRITE_FAILED causal code extracted by failure_model
  - SNAPSHOT_SCHEMA_INVALID causal code extracted by failure_model
  - both codes classified as CONTRACT_VIOLATION
  - both codes are not retryable

  Content safety
  - to_log_safe() output contains no 'value' key
  - MemoryRecord.__repr__ is not called in tests (structural check only)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from io_iii.memory.store import (
    SENSITIVITY_ELEVATED,
    SENSITIVITY_RESTRICTED,
    SENSITIVITY_STANDARD,
    MemoryRecord,
    MemoryStore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def record() -> MemoryRecord:
    return MemoryRecord(
        key="session.last_intent",
        scope="io_iii",
        value="explain deterministic routing",
        version=1,
        provenance="human",
        created_at="2026-04-12T10:00:00Z",
        updated_at="2026-04-12T10:00:00Z",
        sensitivity=SENSITIVITY_STANDARD,
    )


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(storage_root=tmp_path)


# ---------------------------------------------------------------------------
# MemoryRecord — construction and field access
# ---------------------------------------------------------------------------

def test_record_field_access(record: MemoryRecord) -> None:
    assert record.key == "session.last_intent"
    assert record.scope == "io_iii"
    assert record.value == "explain deterministic routing"
    assert record.version == 1
    assert record.provenance == "human"
    assert record.sensitivity == SENSITIVITY_STANDARD


def test_record_is_frozen(record: MemoryRecord) -> None:
    with pytest.raises((AttributeError, TypeError)):
        record.key = "mutated"  # type: ignore[misc]


def test_record_identifier(record: MemoryRecord) -> None:
    assert record.identifier() == "io_iii/session.last_intent"


# ---------------------------------------------------------------------------
# MemoryRecord — to_log_safe()
# ---------------------------------------------------------------------------

def test_to_log_safe_excludes_value(record: MemoryRecord) -> None:
    safe = record.to_log_safe()
    assert "value" not in safe


def test_to_log_safe_includes_key(record: MemoryRecord) -> None:
    safe = record.to_log_safe()
    assert safe["key"] == record.key


def test_to_log_safe_includes_scope(record: MemoryRecord) -> None:
    safe = record.to_log_safe()
    assert safe["scope"] == record.scope


def test_to_log_safe_includes_version(record: MemoryRecord) -> None:
    safe = record.to_log_safe()
    assert safe["version"] == record.version


def test_to_log_safe_includes_sensitivity(record: MemoryRecord) -> None:
    safe = record.to_log_safe()
    assert safe["sensitivity"] == record.sensitivity


def test_to_log_safe_includes_provenance(record: MemoryRecord) -> None:
    safe = record.to_log_safe()
    assert safe["provenance"] == record.provenance


# ---------------------------------------------------------------------------
# MemoryRecord — validation: key / scope
# ---------------------------------------------------------------------------

def test_record_empty_key_rejected() -> None:
    with pytest.raises(ValueError, match="key"):
        MemoryRecord(
            key="",
            scope="io_iii",
            value="v",
            version=1,
            provenance="human",
            created_at="2026-04-12T00:00:00Z",
            updated_at="2026-04-12T00:00:00Z",
            sensitivity=SENSITIVITY_STANDARD,
        )


def test_record_empty_scope_rejected() -> None:
    with pytest.raises(ValueError, match="scope"):
        MemoryRecord(
            key="k",
            scope="",
            value="v",
            version=1,
            provenance="human",
            created_at="2026-04-12T00:00:00Z",
            updated_at="2026-04-12T00:00:00Z",
            sensitivity=SENSITIVITY_STANDARD,
        )


# ---------------------------------------------------------------------------
# MemoryRecord — validation: version
# ---------------------------------------------------------------------------

def test_record_version_zero_rejected() -> None:
    with pytest.raises(ValueError, match="version"):
        MemoryRecord(
            key="k",
            scope="s",
            value="v",
            version=0,
            provenance="human",
            created_at="2026-04-12T00:00:00Z",
            updated_at="2026-04-12T00:00:00Z",
            sensitivity=SENSITIVITY_STANDARD,
        )


def test_record_version_negative_rejected() -> None:
    with pytest.raises(ValueError, match="version"):
        MemoryRecord(
            key="k",
            scope="s",
            value="v",
            version=-1,
            provenance="human",
            created_at="2026-04-12T00:00:00Z",
            updated_at="2026-04-12T00:00:00Z",
            sensitivity=SENSITIVITY_STANDARD,
        )


def test_record_version_one_accepted() -> None:
    r = MemoryRecord(
        key="k",
        scope="s",
        value="v",
        version=1,
        provenance="human",
        created_at="2026-04-12T00:00:00Z",
        updated_at="2026-04-12T00:00:00Z",
        sensitivity=SENSITIVITY_STANDARD,
    )
    assert r.version == 1


# ---------------------------------------------------------------------------
# MemoryRecord — validation: sensitivity
# ---------------------------------------------------------------------------

def test_record_invalid_sensitivity_rejected() -> None:
    with pytest.raises(ValueError, match="sensitivity"):
        MemoryRecord(
            key="k",
            scope="s",
            value="v",
            version=1,
            provenance="human",
            created_at="2026-04-12T00:00:00Z",
            updated_at="2026-04-12T00:00:00Z",
            sensitivity="top_secret",
        )


@pytest.mark.parametrize("sensitivity", [
    SENSITIVITY_STANDARD,
    SENSITIVITY_ELEVATED,
    SENSITIVITY_RESTRICTED,
])
def test_record_valid_sensitivity_accepted(sensitivity: str) -> None:
    r = MemoryRecord(
        key="k",
        scope="s",
        value="v",
        version=1,
        provenance="human",
        created_at="2026-04-12T00:00:00Z",
        updated_at="2026-04-12T00:00:00Z",
        sensitivity=sensitivity,
    )
    assert r.sensitivity == sensitivity


# ---------------------------------------------------------------------------
# MemoryRecord — validation: provenance
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provenance", [
    "human",
    "mixed",
    "llm:llama3.2",
    "llm:model-name.v2",
    "llm:gpt-4o",
])
def test_record_valid_provenance_accepted(provenance: str) -> None:
    r = MemoryRecord(
        key="k",
        scope="s",
        value="v",
        version=1,
        provenance=provenance,
        created_at="2026-04-12T00:00:00Z",
        updated_at="2026-04-12T00:00:00Z",
        sensitivity=SENSITIVITY_STANDARD,
    )
    assert r.provenance == provenance


@pytest.mark.parametrize("bad_provenance", [
    "llm",        # missing slug
    "llm:",       # empty slug
    "model",      # unknown literal
    "auto",
    "",
])
def test_record_invalid_provenance_rejected(bad_provenance: str) -> None:
    with pytest.raises(ValueError, match="provenance"):
        MemoryRecord(
            key="k",
            scope="s",
            value="v",
            version=1,
            provenance=bad_provenance,
            created_at="2026-04-12T00:00:00Z",
            updated_at="2026-04-12T00:00:00Z",
            sensitivity=SENSITIVITY_STANDARD,
        )


# ---------------------------------------------------------------------------
# MemoryStore — put / get roundtrip
# ---------------------------------------------------------------------------

def test_store_put_get_roundtrip(store: MemoryStore, record: MemoryRecord) -> None:
    store.put(record)
    retrieved = store.get(record.scope, record.key)
    assert retrieved == record


def test_store_get_returns_none_for_missing(store: MemoryStore) -> None:
    result = store.get("io_iii", "nonexistent.key")
    assert result is None


def test_store_get_scope_isolated(store: MemoryStore, record: MemoryRecord) -> None:
    store.put(record)
    result = store.get("other_scope", record.key)
    assert result is None


def test_store_put_creates_directories(tmp_path: Path, record: MemoryRecord) -> None:
    nested_root = tmp_path / "deep" / "nested" / "store"
    s = MemoryStore(storage_root=nested_root)
    s.put(record)
    assert s.get(record.scope, record.key) == record


def test_store_put_no_tmp_file_left(store: MemoryStore, record: MemoryRecord) -> None:
    store.put(record)
    scope_dir = store._root / record.scope
    tmp_files = list(scope_dir.glob("*.tmp"))
    assert tmp_files == [], f"Unexpected .tmp files left: {tmp_files}"


def test_store_put_overwrites_without_error(store: MemoryStore, record: MemoryRecord) -> None:
    store.put(record)
    updated = MemoryRecord(
        key=record.key,
        scope=record.scope,
        value="updated value",
        version=2,
        provenance=record.provenance,
        created_at=record.created_at,
        updated_at="2026-04-12T11:00:00Z",
        sensitivity=record.sensitivity,
    )
    store.put(updated)
    retrieved = store.get(record.scope, record.key)
    assert retrieved == updated
    assert retrieved.version == 2


# ---------------------------------------------------------------------------
# MemoryStore — exists
# ---------------------------------------------------------------------------

def test_store_exists_true_for_present(store: MemoryStore, record: MemoryRecord) -> None:
    store.put(record)
    assert store.exists(record.scope, record.key) is True


def test_store_exists_false_for_missing(store: MemoryStore) -> None:
    assert store.exists("io_iii", "missing.key") is False


# ---------------------------------------------------------------------------
# MemoryStore — list_by_scope
# ---------------------------------------------------------------------------

def _make_record(key: str, scope: str = "io_iii") -> MemoryRecord:
    return MemoryRecord(
        key=key,
        scope=scope,
        value=f"value for {key}",
        version=1,
        provenance="human",
        created_at="2026-04-12T00:00:00Z",
        updated_at="2026-04-12T00:00:00Z",
        sensitivity=SENSITIVITY_STANDARD,
    )


def test_list_by_scope_returns_all_records(store: MemoryStore) -> None:
    r1 = _make_record("alpha")
    r2 = _make_record("beta")
    r3 = _make_record("gamma")
    for r in [r1, r2, r3]:
        store.put(r)
    result = store.list_by_scope("io_iii")
    assert len(result) == 3


def test_list_by_scope_deterministic_order(store: MemoryStore) -> None:
    r1 = _make_record("zebra")
    r2 = _make_record("alpha")
    r3 = _make_record("mango")
    for r in [r1, r2, r3]:
        store.put(r)
    result = store.list_by_scope("io_iii")
    keys = [r.key for r in result]
    assert keys == sorted(keys)


def test_list_by_scope_empty_for_missing_scope(store: MemoryStore) -> None:
    result = store.list_by_scope("nonexistent_scope")
    assert result == []


def test_list_by_scope_excludes_other_scopes(store: MemoryStore) -> None:
    r_a = _make_record("key1", scope="scope_a")
    r_b = _make_record("key1", scope="scope_b")
    store.put(r_a)
    store.put(r_b)
    result = store.list_by_scope("scope_a")
    assert len(result) == 1
    assert result[0].scope == "scope_a"


# ---------------------------------------------------------------------------
# MemoryStore — list_by_keys
# ---------------------------------------------------------------------------

def test_list_by_keys_returns_in_declaration_order(store: MemoryStore) -> None:
    for key in ["alpha", "beta", "gamma"]:
        store.put(_make_record(key))
    result = store.list_by_keys("io_iii", ["gamma", "alpha", "beta"])
    assert [r.key for r in result] == ["gamma", "alpha", "beta"]


def test_list_by_keys_skips_missing_silently(store: MemoryStore) -> None:
    store.put(_make_record("alpha"))
    result = store.list_by_keys("io_iii", ["alpha", "missing_key"])
    assert len(result) == 1
    assert result[0].key == "alpha"


def test_list_by_keys_empty_when_all_missing(store: MemoryStore) -> None:
    result = store.list_by_keys("io_iii", ["missing_a", "missing_b"])
    assert result == []


def test_list_by_keys_empty_key_list(store: MemoryStore) -> None:
    store.put(_make_record("alpha"))
    result = store.list_by_keys("io_iii", [])
    assert result == []


# ---------------------------------------------------------------------------
# MemoryStore — record_identifier
# ---------------------------------------------------------------------------

def test_record_identifier_static() -> None:
    assert MemoryStore.record_identifier("io_iii", "session.last_intent") == \
        "io_iii/session.last_intent"


# ---------------------------------------------------------------------------
# Failure model integration — MEMORY_ and SNAPSHOT_ codes
# ---------------------------------------------------------------------------

from io_iii.core.failure_model import RuntimeFailureKind, classify_exception


def test_memory_write_failed_causal_code_extracted() -> None:
    exc = ValueError("MEMORY_WRITE_FAILED: scope=io_iii key=some.key reason=permission denied")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.causal_code == "MEMORY_WRITE_FAILED"


def test_memory_write_failed_kind_is_contract_violation() -> None:
    exc = ValueError("MEMORY_WRITE_FAILED: scope=io_iii key=some.key")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.kind == RuntimeFailureKind.CONTRACT_VIOLATION


def test_memory_write_failed_not_retryable() -> None:
    exc = ValueError("MEMORY_WRITE_FAILED: scope=io_iii key=some.key")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.retryable is False


def test_snapshot_schema_invalid_causal_code_extracted() -> None:
    exc = ValueError("SNAPSHOT_SCHEMA_INVALID: missing field run_id")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.causal_code == "SNAPSHOT_SCHEMA_INVALID"


def test_snapshot_schema_invalid_kind_is_contract_violation() -> None:
    exc = ValueError("SNAPSHOT_SCHEMA_INVALID: schema_version mismatch")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.kind == RuntimeFailureKind.CONTRACT_VIOLATION


def test_snapshot_schema_invalid_not_retryable() -> None:
    exc = ValueError("SNAPSHOT_SCHEMA_INVALID: schema_version mismatch")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.retryable is False


# ---------------------------------------------------------------------------
# Content safety structural check
# ---------------------------------------------------------------------------

def test_to_log_safe_value_not_present_regardless_of_content(store: MemoryStore) -> None:
    """to_log_safe() must not expose value even when value matches a log field name."""
    sensitive_record = MemoryRecord(
        key="dangerous.key",
        scope="test",
        value="value",   # value field content equals the string "value"
        version=1,
        provenance="human",
        created_at="2026-04-12T00:00:00Z",
        updated_at="2026-04-12T00:00:00Z",
        sensitivity=SENSITIVITY_RESTRICTED,
    )
    safe = sensitive_record.to_log_safe()
    # The 'value' key must not appear in the log projection
    assert "value" not in safe


def test_store_json_file_contains_value_field(store: MemoryStore, record: MemoryRecord) -> None:
    """Verify the on-disk JSON contains the value (so roundtrip works correctly)."""
    store.put(record)
    path = store._root / record.scope / f"{record.key}.json"
    on_disk = json.loads(path.read_text())
    assert "value" in on_disk
    assert on_disk["value"] == record.value
