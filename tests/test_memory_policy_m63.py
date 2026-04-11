"""
test_memory_policy_m63.py — Phase 6 M6.3 memory retrieval policy tests (ADR-022 §4).

Verifies:

  Unit — RetrievalPolicy
  - is_route_allowed: allowed route returns True
  - is_route_allowed: unknown route returns False
  - is_capability_allowed: allowed capability returns True
  - is_capability_allowed: unknown capability returns False
  - can_access: route not in allowlist → False regardless of sensitivity
  - can_access: standard sensitivity + allowed route → True
  - can_access: elevated sensitivity + allowed route + not in elevated list → False
  - can_access: elevated sensitivity + allowed route + in elevated list → True
  - can_access: restricted sensitivity + allowed route + not in restricted list → False
  - can_access: restricted sensitivity + allowed route + in restricted list → True
  - can_access: unknown sensitivity tier → False (safe default)
  - filter_records: returns only accessible records for route
  - filter_records: preserves order of accessible records
  - filter_records: returns empty list when no records accessible

  Unit — NULL_POLICY
  - is_route_allowed always returns False
  - is_capability_allowed always returns False
  - can_access always returns False for any sensitivity

  Unit — load_retrieval_policy
  - absent file returns NULL_POLICY
  - loads route_allowlist correctly
  - loads capability_allowlist correctly
  - loads sensitivity_allowlist.elevated correctly
  - loads sensitivity_allowlist.restricted correctly
  - empty allowlists are valid (no error)
  - absent sensitivity_allowlist key defaults to empty

  Integration — canonical config file
  - memory_retrieval_policy.yaml is valid YAML and parseable
  - executor is in route_allowlist
  - synthesizer is in route_allowlist
  - executor is in sensitivity_allowlist.elevated
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from io_iii.memory.policy import (
    NULL_POLICY,
    RetrievalPolicy,
    load_retrieval_policy,
)
from io_iii.memory.store import (
    SENSITIVITY_ELEVATED,
    SENSITIVITY_RESTRICTED,
    SENSITIVITY_STANDARD,
    MemoryRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_policy_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "memory_retrieval_policy.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def make_policy(
    routes: list[str] | None = None,
    capabilities: list[str] | None = None,
    elevated: list[str] | None = None,
    restricted: list[str] | None = None,
) -> RetrievalPolicy:
    return RetrievalPolicy(
        route_allowlist=frozenset(routes or []),
        capability_allowlist=frozenset(capabilities or []),
        sensitivity_elevated=frozenset(elevated or []),
        sensitivity_restricted=frozenset(restricted or []),
    )


def make_record(key: str, sensitivity: str = SENSITIVITY_STANDARD) -> MemoryRecord:
    return MemoryRecord(
        key=key,
        scope="test",
        value="v",
        version=1,
        provenance="human",
        created_at="2026-04-12T00:00:00Z",
        updated_at="2026-04-12T00:00:00Z",
        sensitivity=sensitivity,
    )


# ---------------------------------------------------------------------------
# RetrievalPolicy — is_route_allowed
# ---------------------------------------------------------------------------

def test_route_allowed_returns_true() -> None:
    policy = make_policy(routes=["executor"])
    assert policy.is_route_allowed("executor") is True


def test_route_not_allowed_returns_false() -> None:
    policy = make_policy(routes=["executor"])
    assert policy.is_route_allowed("challenger") is False


def test_route_allowed_empty_allowlist() -> None:
    policy = make_policy(routes=[])
    assert policy.is_route_allowed("executor") is False


# ---------------------------------------------------------------------------
# RetrievalPolicy — is_capability_allowed
# ---------------------------------------------------------------------------

def test_capability_allowed_returns_true() -> None:
    policy = make_policy(capabilities=["summarise"])
    assert policy.is_capability_allowed("summarise") is True


def test_capability_not_allowed_returns_false() -> None:
    policy = make_policy(capabilities=["summarise"])
    assert policy.is_capability_allowed("unknown_cap") is False


def test_capability_allowed_empty_list() -> None:
    policy = make_policy(capabilities=[])
    assert policy.is_capability_allowed("summarise") is False


# ---------------------------------------------------------------------------
# RetrievalPolicy — can_access
# ---------------------------------------------------------------------------

def test_can_access_route_not_allowed_returns_false() -> None:
    policy = make_policy(routes=["executor"])
    assert policy.can_access("challenger", SENSITIVITY_STANDARD) is False


def test_can_access_standard_allowed_route_returns_true() -> None:
    policy = make_policy(routes=["executor"])
    assert policy.can_access("executor", SENSITIVITY_STANDARD) is True


def test_can_access_elevated_allowed_route_not_in_elevated_list() -> None:
    policy = make_policy(routes=["executor"], elevated=[])
    assert policy.can_access("executor", SENSITIVITY_ELEVATED) is False


def test_can_access_elevated_route_in_elevated_list() -> None:
    policy = make_policy(routes=["executor"], elevated=["executor"])
    assert policy.can_access("executor", SENSITIVITY_ELEVATED) is True


def test_can_access_elevated_different_route_not_in_elevated_list() -> None:
    policy = make_policy(routes=["executor", "synthesizer"], elevated=["executor"])
    assert policy.can_access("synthesizer", SENSITIVITY_ELEVATED) is False


def test_can_access_restricted_allowed_route_not_in_restricted_list() -> None:
    policy = make_policy(routes=["executor"], restricted=[])
    assert policy.can_access("executor", SENSITIVITY_RESTRICTED) is False


def test_can_access_restricted_route_in_restricted_list() -> None:
    policy = make_policy(routes=["executor"], restricted=["executor"])
    assert policy.can_access("executor", SENSITIVITY_RESTRICTED) is True


def test_can_access_unknown_sensitivity_returns_false() -> None:
    policy = make_policy(routes=["executor"])
    assert policy.can_access("executor", "top_secret") is False


def test_can_access_standard_route_not_in_elevated_still_allowed() -> None:
    """Standard sensitivity doesn't require sensitivity_allowlist entries."""
    policy = make_policy(routes=["synthesizer"], elevated=["executor"])
    assert policy.can_access("synthesizer", SENSITIVITY_STANDARD) is True


# ---------------------------------------------------------------------------
# RetrievalPolicy — filter_records
# ---------------------------------------------------------------------------

def test_filter_records_returns_accessible_only() -> None:
    policy = make_policy(routes=["executor"], elevated=["executor"])
    records = [
        make_record("std", SENSITIVITY_STANDARD),
        make_record("elv", SENSITIVITY_ELEVATED),
        make_record("rst", SENSITIVITY_RESTRICTED),
    ]
    result = policy.filter_records("executor", records)
    keys = [r.key for r in result]
    assert "std" in keys
    assert "elv" in keys
    assert "rst" not in keys


def test_filter_records_preserves_order() -> None:
    policy = make_policy(routes=["executor"])
    records = [
        make_record("gamma"),
        make_record("alpha"),
        make_record("beta"),
    ]
    result = policy.filter_records("executor", records)
    assert [r.key for r in result] == ["gamma", "alpha", "beta"]


def test_filter_records_empty_when_route_not_allowed() -> None:
    policy = make_policy(routes=["executor"])
    records = [make_record("k1"), make_record("k2")]
    result = policy.filter_records("challenger", records)
    assert result == []


def test_filter_records_empty_input_returns_empty() -> None:
    policy = make_policy(routes=["executor"])
    assert policy.filter_records("executor", []) == []


# ---------------------------------------------------------------------------
# NULL_POLICY
# ---------------------------------------------------------------------------

def test_null_policy_route_always_denied() -> None:
    assert NULL_POLICY.is_route_allowed("executor") is False


def test_null_policy_capability_always_denied() -> None:
    assert NULL_POLICY.is_capability_allowed("summarise") is False


@pytest.mark.parametrize("sensitivity", [
    SENSITIVITY_STANDARD,
    SENSITIVITY_ELEVATED,
    SENSITIVITY_RESTRICTED,
])
def test_null_policy_can_access_always_false(sensitivity: str) -> None:
    assert NULL_POLICY.can_access("executor", sensitivity) is False


# ---------------------------------------------------------------------------
# load_retrieval_policy — absent file
# ---------------------------------------------------------------------------

def test_load_absent_file_returns_null_policy(tmp_path: Path) -> None:
    policy = load_retrieval_policy(tmp_path / "nonexistent.yaml")
    assert policy is NULL_POLICY


# ---------------------------------------------------------------------------
# load_retrieval_policy — from YAML
# ---------------------------------------------------------------------------

def test_load_route_allowlist(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: [executor, synthesizer]
        capability_allowlist: []
        sensitivity_allowlist:
          elevated: []
          restricted: []
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.is_route_allowed("executor") is True
    assert policy.is_route_allowed("synthesizer") is True
    assert policy.is_route_allowed("challenger") is False


def test_load_capability_allowlist(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: []
        capability_allowlist: [summarise, context_inject]
        sensitivity_allowlist:
          elevated: []
          restricted: []
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.is_capability_allowed("summarise") is True
    assert policy.is_capability_allowed("context_inject") is True
    assert policy.is_capability_allowed("other") is False


def test_load_sensitivity_elevated(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: [executor]
        capability_allowlist: []
        sensitivity_allowlist:
          elevated: [executor]
          restricted: []
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.can_access("executor", SENSITIVITY_ELEVATED) is True


def test_load_sensitivity_restricted(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: [admin]
        capability_allowlist: []
        sensitivity_allowlist:
          elevated: []
          restricted: [admin]
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.can_access("admin", SENSITIVITY_RESTRICTED) is True


def test_load_empty_allowlists_valid(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: []
        capability_allowlist: []
        sensitivity_allowlist:
          elevated: []
          restricted: []
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.is_route_allowed("executor") is False


def test_load_absent_sensitivity_allowlist_defaults_empty(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: [executor]
        capability_allowlist: []
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.can_access("executor", SENSITIVITY_ELEVATED) is False
    assert policy.can_access("executor", SENSITIVITY_RESTRICTED) is False


def test_load_absent_capability_allowlist_defaults_empty(tmp_path: Path) -> None:
    cfg = write_policy_yaml(tmp_path, """
        route_allowlist: [executor]
    """)
    policy = load_retrieval_policy(cfg)
    assert policy.is_capability_allowed("any") is False


# ---------------------------------------------------------------------------
# Integration — canonical config file
# ---------------------------------------------------------------------------

CANONICAL_POLICY = (
    Path(__file__).resolve().parents[1]
    / "architecture" / "runtime" / "config" / "memory_retrieval_policy.yaml"
)


def test_canonical_policy_parseable() -> None:
    policy = load_retrieval_policy(CANONICAL_POLICY)
    assert isinstance(policy, RetrievalPolicy)


def test_canonical_policy_executor_in_route_allowlist() -> None:
    policy = load_retrieval_policy(CANONICAL_POLICY)
    assert policy.is_route_allowed("executor") is True


def test_canonical_policy_synthesizer_in_route_allowlist() -> None:
    policy = load_retrieval_policy(CANONICAL_POLICY)
    assert policy.is_route_allowed("synthesizer") is True


def test_canonical_policy_executor_in_elevated_allowlist() -> None:
    policy = load_retrieval_policy(CANONICAL_POLICY)
    assert policy.can_access("executor", SENSITIVITY_ELEVATED) is True
