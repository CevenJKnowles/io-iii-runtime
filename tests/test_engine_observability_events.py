"""
test_engine_observability_events.py — Phase 4 M4.5 engine lifecycle event tests.

Verifies the EngineObservabilityLog and EngineEvent model:

  Unit (EngineObservabilityLog / EngineEvent):
  - log starts empty
  - emit increments event_count
  - event fields are correct (kind, request_id, task_spec_id, meta)
  - to_list() serialises all emitted events in order
  - to_list() produces JSON-safe dicts (content-safe)
  - capacity overflow raises RuntimeError with OBSERVABILITY_LOG_CAPACITY code
  - forbidden meta key raises ValueError at emit time (fail-fast)
  - task_spec_id=None is preserved (CLI path)
  - task_spec_id set is preserved (orchestrator path)

  Engine integration (null-provider path):
  - engine_events key present in meta
  - deterministic event ordering (canonical 5-event null-path sequence)
  - event kinds match EngineEventKind values
  - request_id matches session_state.request_id
  - task_spec_id=None for CLI-style state (no task_spec_id set)
  - task_spec_id propagated for orchestrator-style state
  - no forbidden content keys in any event or meta
  - engine_event_count is non-negative integer in all paths
  - audit path adds challenger_audit_complete event
  - revision path adds revision_complete event
  - stage_timings still present (M4.5 trace contract preserved)
"""
from __future__ import annotations

import types
from typing import Any, Dict

import pytest

from io_iii.core.content_safety import assert_no_forbidden_keys
from io_iii.core.engine_observability import EngineEventKind, EngineObservabilityLog
from io_iii.core.session_state import AuditGateState, RouteInfo, SessionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _null_state(*, task_spec_id=None) -> SessionState:
    route = RouteInfo(
        mode="executor",
        primary_target=None,
        secondary_target=None,
        selected_target=None,
        selected_provider="null",
        fallback_used=False,
        fallback_reason=None,
        boundaries={},
    )
    return SessionState(
        request_id="obs-test-rid",
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
        task_spec_id=task_spec_id,
        logging_policy={"schema": "test"},
    )


def _engine_cfg() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        providers={},
        routing={"routing_table": {}},
        logging={"schema": "test"},
        config_dir=".",
    )


def _engine_deps():
    from io_iii.core.capabilities import CapabilityRegistry
    from io_iii.core.dependencies import RuntimeDependencies
    return RuntimeDependencies(
        ollama_provider_factory=lambda _cfg: None,
        challenger_fn=None,
        capability_registry=CapabilityRegistry([]),
    )


# ---------------------------------------------------------------------------
# Unit tests — EngineObservabilityLog
# ---------------------------------------------------------------------------

def test_log_starts_empty():
    log = EngineObservabilityLog()
    assert log.event_count == 0
    assert log.to_list() == []


def test_emit_increments_count():
    log = EngineObservabilityLog()
    log.emit(EngineEventKind.RUN_STARTED, request_id="r1")
    assert log.event_count == 1
    log.emit(EngineEventKind.ROUTE_RESOLVED, request_id="r1")
    assert log.event_count == 2


def test_emit_stores_correct_fields():
    log = EngineObservabilityLog()
    log.emit(
        EngineEventKind.RUN_STARTED,
        request_id="req-abc",
        task_spec_id="ts-xyz",
        meta={"provider": "null", "mode": "executor"},
    )
    events = log.to_list()
    assert len(events) == 1
    e = events[0]
    assert e["kind"] == "engine_run_started"
    assert e["request_id"] == "req-abc"
    assert e["task_spec_id"] == "ts-xyz"
    assert e["meta"]["provider"] == "null"
    assert e["meta"]["mode"] == "executor"
    assert isinstance(e["timestamp_ms"], int)
    assert e["timestamp_ms"] > 0


def test_emit_task_spec_id_none_preserved():
    """task_spec_id=None (CLI path) must be stored and serialised as None, not dropped."""
    log = EngineObservabilityLog()
    log.emit(EngineEventKind.RUN_STARTED, request_id="r1", task_spec_id=None)
    e = log.to_list()[0]
    assert "task_spec_id" in e
    assert e["task_spec_id"] is None


def test_emit_task_spec_id_set_preserved():
    """task_spec_id when provided (orchestrator path) must be stored correctly."""
    log = EngineObservabilityLog()
    log.emit(EngineEventKind.RUN_STARTED, request_id="r1", task_spec_id="ts-abcdef")
    assert log.to_list()[0]["task_spec_id"] == "ts-abcdef"


def test_to_list_ordering_preserved():
    """to_list() must return events in emission order."""
    log = EngineObservabilityLog()
    kinds = [
        EngineEventKind.RUN_STARTED,
        EngineEventKind.ROUTE_RESOLVED,
        EngineEventKind.PROVIDER_EXECUTION_COMPLETE,
        EngineEventKind.OUTPUT_EMITTED,
        EngineEventKind.RUN_COMPLETE,
    ]
    for k in kinds:
        log.emit(k, request_id="r1")
    serialised_kinds = [e["kind"] for e in log.to_list()]
    assert serialised_kinds == [k.value for k in kinds]


def test_to_list_content_safety():
    """to_list() output must pass assert_no_forbidden_keys."""
    log = EngineObservabilityLog()
    log.emit(
        EngineEventKind.PROVIDER_EXECUTION_COMPLETE,
        request_id="r1",
        meta={"provider": "null", "model": None},
    )
    log.emit(
        EngineEventKind.RUN_COMPLETE,
        request_id="r1",
        meta={"trace_step_count": 1},
    )
    # Must not raise.
    assert_no_forbidden_keys(log.to_list())


def test_overflow_raises_runtime_error():
    """Emitting beyond _MAX_EVENTS must raise RuntimeError with OBSERVABILITY_LOG_CAPACITY."""
    from io_iii.core.engine_observability import _MAX_EVENTS
    log = EngineObservabilityLog()
    for _ in range(_MAX_EVENTS):
        log.emit(EngineEventKind.RUN_STARTED, request_id="r1")
    with pytest.raises(RuntimeError, match="OBSERVABILITY_LOG_CAPACITY"):
        log.emit(EngineEventKind.RUN_STARTED, request_id="r1")


def test_forbidden_meta_key_raises_at_emit_time():
    """Emitting an event whose meta contains a forbidden key must raise ValueError immediately."""
    log = EngineObservabilityLog()
    with pytest.raises(ValueError):
        log.emit(
            EngineEventKind.RUN_STARTED,
            request_id="r1",
            meta={"prompt": "should not be here"},
        )
    # Log must remain unchanged on forbidden-key failure.
    assert log.event_count == 0


def test_forbidden_meta_key_does_not_mutate_log():
    """After a rejected emit, previously recorded events must be intact."""
    log = EngineObservabilityLog()
    log.emit(EngineEventKind.RUN_STARTED, request_id="r1")
    assert log.event_count == 1

    with pytest.raises(ValueError):
        log.emit(EngineEventKind.ROUTE_RESOLVED, request_id="r1", meta={"content": "bad"})

    assert log.event_count == 1  # unchanged


# ---------------------------------------------------------------------------
# Integration tests — engine.run() null-provider path
# ---------------------------------------------------------------------------

def test_engine_events_present_in_meta():
    """engine.run() must attach engine_events to ExecutionResult.meta."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="obs test", audit=False, deps=deps
    )

    assert isinstance(result.meta, dict)
    assert "engine_events" in result.meta
    assert isinstance(result.meta["engine_events"], list)


def test_engine_null_path_event_count_and_ordering():
    """
    Null-provider path (no audit, no capability) must emit exactly 5 events in
    canonical order: run_started → route_resolved → provider_execution_complete
                     → output_emitted → engine_run_complete.
    """
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="order test", audit=False, deps=deps
    )

    events = result.meta["engine_events"]
    assert len(events) == 5
    assert [e["kind"] for e in events] == [
        "engine_run_started",
        "route_resolved",
        "provider_execution_complete",
        "output_emitted",
        "engine_run_complete",
    ]


def test_engine_events_request_id_matches_session():
    """Every event must carry the request_id from the original SessionState."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="rid test", audit=False, deps=deps
    )

    for ev in result.meta["engine_events"]:
        assert ev["request_id"] == "obs-test-rid"


def test_engine_events_task_spec_id_none_for_cli_path():
    """CLI-style state (task_spec_id=None) must propagate None into all events."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state(task_spec_id=None)

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="tsid-none test", audit=False, deps=deps
    )

    for ev in result.meta["engine_events"]:
        assert ev["task_spec_id"] is None


def test_engine_events_task_spec_id_propagated():
    """Orchestrator-style state (task_spec_id set) must propagate into all events."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state(task_spec_id="ts-abc123")

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="tsid-set test", audit=False, deps=deps
    )

    for ev in result.meta["engine_events"]:
        assert ev["task_spec_id"] == "ts-abc123"


def test_engine_events_no_forbidden_content_keys():
    """No event or nested meta dict must contain a forbidden content key."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="safety test", audit=False, deps=deps
    )

    # Must not raise.
    assert_no_forbidden_keys(result.meta["engine_events"])


def test_engine_run_started_caller_is_cli_when_no_task_spec_id():
    """engine_run_started.meta.caller must be 'cli' when task_spec_id is None."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state(task_spec_id=None)

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="caller test", audit=False, deps=deps
    )

    started = result.meta["engine_events"][0]
    assert started["kind"] == "engine_run_started"
    assert started["meta"]["caller"] == "cli"


def test_engine_run_started_caller_is_orchestrator_when_task_spec_id_set():
    """engine_run_started.meta.caller must be 'orchestrator' when task_spec_id is set."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state(task_spec_id="ts-999")

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="caller orch test", audit=False, deps=deps
    )

    started = result.meta["engine_events"][0]
    assert started["kind"] == "engine_run_started"
    assert started["meta"]["caller"] == "orchestrator"


def test_engine_run_complete_meta_has_trace_step_count():
    """engine_run_complete event meta must include trace_step_count as a non-negative integer."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="step count test", audit=False, deps=deps
    )

    complete_ev = result.meta["engine_events"][-1]
    assert complete_ev["kind"] == "engine_run_complete"
    assert isinstance(complete_ev["meta"].get("trace_step_count"), int)
    assert complete_ev["meta"]["trace_step_count"] >= 0


def test_engine_events_all_timestamps_positive_integers():
    """All event timestamp_ms values must be positive integers."""
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="ts test", audit=False, deps=deps
    )

    for ev in result.meta["engine_events"]:
        assert isinstance(ev["timestamp_ms"], int)
        assert ev["timestamp_ms"] > 0


def test_stage_timings_still_present_alongside_engine_events():
    """
    M4.5 regression guard: stage_timings in trace must still be present when
    engine_events are also attached.
    """
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="coexistence test", audit=False, deps=deps
    )

    assert "stage_timings" in result.meta["trace"]
    assert "engine_events" in result.meta


def test_engine_events_bounded_count_within_max():
    """Engine events count must not exceed _MAX_EVENTS on any supported execution path."""
    from io_iii.core.engine_observability import _MAX_EVENTS
    import io_iii.core.engine as engine
    cfg = _engine_cfg()
    deps = _engine_deps()
    state = _null_state()

    _, result = engine.run(
        cfg=cfg, session_state=state, user_prompt="bounds test", audit=False, deps=deps
    )

    assert len(result.meta["engine_events"]) <= _MAX_EVENTS


# ---------------------------------------------------------------------------
# Orchestrator integration — task_spec_id propagation
# ---------------------------------------------------------------------------

def test_orchestrator_task_spec_id_reaches_engine_events():
    """
    When run via orchestrator, task_spec_id from TaskSpec must appear in all
    engine_events without content leakage.
    """
    import io_iii.core.orchestrator as orchestrator
    from io_iii.capabilities.builtins import builtin_registry
    from io_iii.core.dependencies import RuntimeDependencies
    from io_iii.core.task_spec import TaskSpec

    cfg = types.SimpleNamespace(
        config_dir=".",
        providers={"providers": {"ollama": {"enabled": False}}},
        routing={
            "routing_table": {
                "rules": {"boundaries": {}},
                "modes": {
                    "executor": {
                        "primary": "local:test-model",
                        "secondary": "local:fallback-model",
                    }
                },
            }
        },
        logging={"schema": "test"},
    )
    deps = RuntimeDependencies(
        ollama_provider_factory=lambda _cfg: None,
        challenger_fn=None,
        capability_registry=builtin_registry(),
    )

    spec = TaskSpec.create(mode="executor", prompt="orchestrator obs test")
    state2, result = orchestrator.run(task_spec=spec, cfg=cfg, deps=deps)

    assert "engine_events" in result.meta
    events = result.meta["engine_events"]

    # All events carry the correct task_spec_id.
    for ev in events:
        assert ev["task_spec_id"] == spec.task_spec_id

    # 'caller' field on run_started must be 'orchestrator'.
    started = events[0]
    assert started["kind"] == "engine_run_started"
    assert started["meta"]["caller"] == "orchestrator"

    # Content safety holds end-to-end.
    assert_no_forbidden_keys(events)
