"""
test_engine_observability_m45.py — Phase 4 M4.5 engine observability tests.

Verifies structured per-stage timing fields in ExecutionTrace.to_dict():

  - stage_timings present and dict-typed
  - empty steps → empty stage_timings
  - single step → stage mapped to its duration_ms
  - multiple distinct stages → each stage keyed independently
  - repeated stage → durations summed (not overwritten)
  - stage_timings values are non-negative integers
  - stage_timings passes content-safety assert_no_forbidden_keys
  - stage_timings not present on non-terminal trace is consistent (computed at call time)
  - integration: engine null-route trace includes stage_timings
  - SessionState.latency_ms is unaffected (total-only contract preserved)
"""
from __future__ import annotations

import types

import pytest

from io_iii.core.content_safety import assert_no_forbidden_keys
from io_iii.core.execution_trace import TraceRecorder
from io_iii.core.session_state import AuditGateState, RouteInfo, SessionState


# ---------------------------------------------------------------------------
# Unit tests — ExecutionTrace.to_dict() stage_timings
# ---------------------------------------------------------------------------

def test_stage_timings_present_in_to_dict():
    """stage_timings must be a key in to_dict() output."""
    rec = TraceRecorder(trace_id="t-st-present")
    rec.start()
    rec.complete()
    d = rec.trace.to_dict()
    assert "stage_timings" in d


def test_stage_timings_is_dict():
    """stage_timings must be a dict instance."""
    rec = TraceRecorder(trace_id="t-st-type")
    rec.start()
    rec.complete()
    assert isinstance(rec.trace.to_dict()["stage_timings"], dict)


def test_stage_timings_empty_when_no_steps():
    """stage_timings must be an empty dict when no steps have been recorded."""
    rec = TraceRecorder(trace_id="t-st-empty")
    rec.start()
    rec.complete()
    assert rec.trace.to_dict()["stage_timings"] == {}


def test_stage_timings_single_step():
    """A single recorded step must appear in stage_timings with a non-negative int value."""
    rec = TraceRecorder(trace_id="t-st-single")
    with rec.step("provider_run"):
        pass
    rec.complete()

    st = rec.trace.to_dict()["stage_timings"]
    assert "provider_run" in st
    assert isinstance(st["provider_run"], int)
    assert st["provider_run"] >= 0


def test_stage_timings_multiple_distinct_stages():
    """Each distinct stage must appear as its own key in stage_timings."""
    rec = TraceRecorder(trace_id="t-st-multi")
    with rec.step("context_assembly"):
        pass
    with rec.step("provider_inference"):
        pass
    with rec.step("challenger_audit"):
        pass
    rec.complete()

    st = rec.trace.to_dict()["stage_timings"]
    assert set(st.keys()) == {"context_assembly", "provider_inference", "challenger_audit"}
    for v in st.values():
        assert isinstance(v, int)
        assert v >= 0


def test_stage_timings_repeated_stage_sums_durations():
    """
    If the same stage appears more than once in steps, its durations must be
    summed in stage_timings — not overwritten by the last occurrence.
    """
    rec = TraceRecorder(trace_id="t-st-repeat")
    with rec.step("provider_inference"):
        pass
    with rec.step("provider_inference"):
        pass
    rec.complete()

    steps = rec.trace.steps
    expected_total = steps[0].duration_ms + steps[1].duration_ms

    st = rec.trace.to_dict()["stage_timings"]
    assert "provider_inference" in st
    assert st["provider_inference"] == expected_total


def test_stage_timings_values_are_non_negative_integers():
    """All stage_timings values must be non-negative integers."""
    rec = TraceRecorder(trace_id="t-st-ints")
    with rec.step("capability_execution"):
        pass
    with rec.step("provider_run"):
        pass
    rec.complete()

    for v in rec.trace.to_dict()["stage_timings"].values():
        assert isinstance(v, int)
        assert v >= 0


def test_stage_timings_passes_content_safety():
    """stage_timings must pass assert_no_forbidden_keys — no content leakage."""
    rec = TraceRecorder(trace_id="t-st-safety")
    with rec.step("context_assembly", meta={"route_id": "executor"}):
        pass
    with rec.step("provider_inference", meta={"provider": "ollama", "model": "test"}):
        pass
    rec.complete()

    d = rec.trace.to_dict()
    # Must not raise — stage names and int durations are content-safe.
    assert_no_forbidden_keys(d)


def test_stage_timings_consistent_on_non_terminal_trace():
    """
    stage_timings is computed at to_dict() call time from current steps.
    A running trace with steps recorded mid-execution must reflect those steps.
    """
    rec = TraceRecorder(trace_id="t-st-running")
    with rec.step("context_assembly"):
        pass
    # Deliberately not calling complete() — trace is still 'running'.
    assert rec.status == "running"

    st = rec.trace.to_dict()["stage_timings"]
    assert "context_assembly" in st


def test_stage_timings_keys_match_step_stages():
    """
    The set of keys in stage_timings must exactly equal the set of stage names
    in steps (no phantom keys, no missing keys).
    """
    rec = TraceRecorder(trace_id="t-st-keys-match")
    stages = ["capability_execution", "provider_run"]
    for s in stages:
        with rec.step(s):
            pass
    rec.complete()

    expected_keys = set(stages)
    actual_keys = set(rec.trace.to_dict()["stage_timings"].keys())
    assert actual_keys == expected_keys


# ---------------------------------------------------------------------------
# Integration — engine null-route trace includes stage_timings
# ---------------------------------------------------------------------------

def _make_null_state() -> SessionState:
    route = RouteInfo(
        mode="executor",
        primary_target=None,
        secondary_target=None,
        selected_target=None,
        selected_provider="null",
        fallback_used=False,
        fallback_reason=None,
        boundaries={"single_voice_output": True},
    )
    return SessionState(
        request_id="m45-int-test",
        started_at_ms=0,
        mode="executor",
        config_dir="./architecture/runtime/config",
        route=route,
        audit=AuditGateState(audit_enabled=False),
        status="ok",
        provider="null",
        model=None,
        route_id="executor",
        persona_contract_version="0.2.0",
        persona_id=None,
        logging_policy={"content": "disabled"},
    )


def test_engine_null_route_trace_includes_stage_timings():
    """
    End-to-end: engine.run on null provider must return a trace with stage_timings.
    stage_timings must include 'provider_run' with a non-negative int duration.
    """
    import io_iii.core.engine as engine
    from io_iii.core.dependencies import RuntimeDependencies
    from io_iii.core.capabilities import CapabilityRegistry

    cfg = types.SimpleNamespace(
        providers={},
        routing={"routing_table": {}},
        logging={"schema": "test"},
        config_dir=".",
    )
    deps = RuntimeDependencies(
        ollama_provider_factory=lambda _cfg: None,
        challenger_fn=None,
        capability_registry=CapabilityRegistry([]),
    )
    state = _make_null_state()

    _s2, result = engine.run(
        cfg=cfg,
        session_state=state,
        user_prompt="observability check",
        audit=False,
        deps=deps,
    )

    trace = result.meta["trace"]
    assert "stage_timings" in trace
    st = trace["stage_timings"]
    assert isinstance(st, dict)
    assert "provider_run" in st
    assert isinstance(st["provider_run"], int)
    assert st["provider_run"] >= 0


def test_session_state_latency_ms_is_total_only_unaffected():
    """
    M4.5 must not change the SessionState.latency_ms contract.
    latency_ms must remain a single total integer after engine execution.
    stage_timings lives only in ExecutionTrace; SessionState must not gain timing fields.
    """
    import io_iii.core.engine as engine
    from io_iii.core.dependencies import RuntimeDependencies
    from io_iii.core.capabilities import CapabilityRegistry

    cfg = types.SimpleNamespace(
        providers={},
        routing={"routing_table": {}},
        logging={"schema": "test"},
        config_dir=".",
    )
    deps = RuntimeDependencies(
        ollama_provider_factory=lambda _cfg: None,
        challenger_fn=None,
        capability_registry=CapabilityRegistry([]),
    )
    state = _make_null_state()

    state2, _ = engine.run(
        cfg=cfg,
        session_state=state,
        user_prompt="latency check",
        audit=False,
        deps=deps,
    )

    # latency_ms must be set to a non-negative integer (total only)
    assert isinstance(state2.latency_ms, int)
    assert state2.latency_ms >= 0

    # SessionState must have no stage-level timing field
    assert not hasattr(state2, "stage_timings")
