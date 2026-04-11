"""
test_constellation_m53.py — Phase 5 M5.3 constellation integrity guard tests.

Verifies:

  Unit — check_constellation()
  - passes with valid config (executor != challenger)
  - raises CONSTELLATION_DRIFT when executor and challenger share the same model
  - raises CONSTELLATION_DRIFT when a role has an empty primary binding
  - raises CONSTELLATION_DRIFT when a role has a missing primary binding
  - passes when modes dict is empty
  - passes when routing_cfg is empty dict
  - passes with non-dict routing_cfg (no-op, no crash)
  - raises CONSTELLATION_DRIFT when role declares max_steps > RUNBOOK_MAX_STEPS
  - passes when role declares max_steps == RUNBOOK_MAX_STEPS
  - raises CONSTELLATION_DRIFT for invalid role binding (non-dict)
  - handles executor missing from modes (no collapse check)
  - handles challenger missing from modes (no collapse check)

  Failure model
  - CONSTELLATION_DRIFT raises ValueError (content-safe prefix)
  - classify_exception maps to CONTRACT_VIOLATION kind
  - causal_code is CONSTELLATION_DRIFT
  - retryable is False

  CLI integration — cmd_run
  - constellation guard is invoked on normal run
  - CONSTELLATION_DRIFT raises at CLI boundary (error surfaced)
  - --no-constellation-check bypasses the guard (no exception)
  - --no-constellation-check emits warning to stderr
"""
from __future__ import annotations

import io
import types
import sys
from unittest.mock import patch

import pytest

from io_iii.core.constellation import check_constellation, _extract_model
from io_iii.core.runbook import RUNBOOK_MAX_STEPS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(modes: dict) -> dict:
    """Wrap modes in a minimal routing_cfg shape."""
    return {"routing_table": {"modes": modes}}


def _valid_modes() -> dict:
    return {
        "executor": {"primary": "local:qwen3:8b", "secondary": "local:mistral:latest"},
        "challenger": {"primary": "local:deepseek-r1:latest", "secondary": "local:deepseek-r1:latest"},
    }


# ---------------------------------------------------------------------------
# Unit: _extract_model helper
# ---------------------------------------------------------------------------

def test_extract_model_with_namespace():
    assert _extract_model("local:qwen3:8b") == "qwen3:8b"


def test_extract_model_nested_colon():
    assert _extract_model("local:deepseek-r1:latest") == "deepseek-r1:latest"


def test_extract_model_no_namespace():
    # "qwen3:8b" has no explicit namespace — split on first colon yields "8b".
    # Consistent with _parse_target() behaviour in routing.py.
    assert _extract_model("qwen3:8b") == "8b"


# ---------------------------------------------------------------------------
# Unit: check_constellation — valid configs
# ---------------------------------------------------------------------------

def test_valid_config_passes():
    """Standard valid routing config must not raise."""
    check_constellation(_cfg(_valid_modes()))


def test_empty_modes_passes():
    """Empty modes dict — no checks to run."""
    check_constellation(_cfg({}))


def test_empty_routing_cfg_passes():
    """Empty routing_cfg — nothing to validate."""
    check_constellation({})


def test_non_dict_routing_cfg_passes():
    """Non-dict routing_cfg — guard is a no-op (never crashes)."""
    check_constellation(None)   # type: ignore
    check_constellation("bad")  # type: ignore


def test_executor_absent_passes():
    """If executor mode is absent, no collapse check is performed."""
    modes = {"challenger": {"primary": "local:deepseek-r1:latest"}}
    check_constellation(_cfg(modes))


def test_challenger_absent_passes():
    """If challenger mode is absent, no collapse check is performed."""
    modes = {"executor": {"primary": "local:qwen3:8b"}}
    check_constellation(_cfg(modes))


# ---------------------------------------------------------------------------
# Unit: check_constellation — Check 1: role-model collapse
# ---------------------------------------------------------------------------

def test_executor_challenger_same_model_raises():
    """Same model for executor and challenger must raise CONSTELLATION_DRIFT."""
    modes = {
        "executor": {"primary": "local:qwen3:8b"},
        "challenger": {"primary": "local:qwen3:8b"},
    }
    with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
        check_constellation(_cfg(modes))


def test_executor_challenger_same_model_error_message():
    """Error message must name the model and not include prompt content."""
    modes = {
        "executor": {"primary": "local:qwen3:8b"},
        "challenger": {"primary": "local:qwen3:8b"},
    }
    with pytest.raises(ValueError) as exc_info:
        check_constellation(_cfg(modes))
    msg = str(exc_info.value)
    assert "qwen3:8b" in msg
    assert "adversarial review" in msg


def test_executor_challenger_different_models_passes():
    """Distinct models — no collapse."""
    modes = {
        "executor": {"primary": "local:qwen3:8b"},
        "challenger": {"primary": "local:deepseek-r1:latest"},
    }
    check_constellation(_cfg(modes))


# ---------------------------------------------------------------------------
# Unit: check_constellation — Check 2: required role bindings
# ---------------------------------------------------------------------------

def test_empty_primary_binding_raises():
    """Empty primary string must raise CONSTELLATION_DRIFT."""
    modes = {
        "executor": {"primary": ""},
    }
    with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
        check_constellation(_cfg(modes))


def test_missing_primary_binding_raises():
    """Missing primary key must raise CONSTELLATION_DRIFT."""
    modes = {
        "executor": {"secondary": "local:mistral:latest"},
    }
    with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
        check_constellation(_cfg(modes))


def test_none_primary_binding_raises():
    """None primary must raise CONSTELLATION_DRIFT."""
    modes = {
        "executor": {"primary": None},
    }
    with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
        check_constellation(_cfg(modes))


def test_invalid_role_binding_non_dict_raises():
    """Non-dict role binding must raise CONSTELLATION_DRIFT."""
    modes = {
        "executor": "local:qwen3:8b",  # should be a dict
    }
    with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
        check_constellation(_cfg(modes))


# ---------------------------------------------------------------------------
# Unit: check_constellation — Check 3: call chain bounds
# ---------------------------------------------------------------------------

def test_max_steps_within_limit_passes():
    """max_steps == RUNBOOK_MAX_STEPS must pass."""
    modes = {
        "executor": {"primary": "local:qwen3:8b", "max_steps": RUNBOOK_MAX_STEPS},
    }
    check_constellation(_cfg(modes))


def test_max_steps_exceeded_raises():
    """max_steps > RUNBOOK_MAX_STEPS must raise CONSTELLATION_DRIFT."""
    modes = {
        "executor": {"primary": "local:qwen3:8b", "max_steps": RUNBOOK_MAX_STEPS + 1},
    }
    with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
        check_constellation(_cfg(modes))


def test_max_steps_exceeded_error_mentions_limit():
    """Error message must include the declared steps and the hard limit."""
    exceeded = RUNBOOK_MAX_STEPS + 5
    modes = {
        "executor": {"primary": "local:qwen3:8b", "max_steps": exceeded},
    }
    with pytest.raises(ValueError) as exc_info:
        check_constellation(_cfg(modes))
    msg = str(exc_info.value)
    assert str(exceeded) in msg
    assert str(RUNBOOK_MAX_STEPS) in msg


def test_max_steps_absent_passes():
    """Mode without max_steps is unaffected by bound check."""
    modes = {
        "executor": {"primary": "local:qwen3:8b"},
    }
    check_constellation(_cfg(modes))


def test_max_steps_non_numeric_ignored():
    """Non-numeric max_steps value is silently skipped — no crash."""
    modes = {
        "executor": {"primary": "local:qwen3:8b", "max_steps": "unlimited"},
    }
    check_constellation(_cfg(modes))


# ---------------------------------------------------------------------------
# Failure model
# ---------------------------------------------------------------------------

def test_constellation_drift_is_value_error():
    """CONSTELLATION_DRIFT must be raised as ValueError."""
    with pytest.raises(ValueError):
        check_constellation(_cfg({
            "executor": {"primary": "local:x"},
            "challenger": {"primary": "local:x"},
        }))


def test_classify_exception_maps_to_contract_violation():
    """classify_exception maps CONSTELLATION_DRIFT to CONTRACT_VIOLATION."""
    from io_iii.core.failure_model import classify_exception, RuntimeFailureKind
    exc = ValueError("CONSTELLATION_DRIFT: executor and challenger share model 'x'")
    failure = classify_exception(exc, request_id="test-id")
    assert failure.kind == RuntimeFailureKind.CONTRACT_VIOLATION


def test_classify_exception_causal_code_is_constellation_drift():
    """causal_code must be extracted as CONSTELLATION_DRIFT."""
    from io_iii.core.failure_model import classify_exception
    exc = ValueError("CONSTELLATION_DRIFT: role 'executor' has empty binding")
    failure = classify_exception(exc, request_id="test-id")
    assert failure.causal_code == "CONSTELLATION_DRIFT"


def test_classify_exception_not_retryable():
    """CONSTELLATION_DRIFT must be retryable=False."""
    from io_iii.core.failure_model import classify_exception
    exc = ValueError("CONSTELLATION_DRIFT: role collapse detected")
    failure = classify_exception(exc, request_id="test-id")
    assert failure.retryable is False


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def _make_args(no_constellation_check: bool = False, no_health_check: bool = True) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        mode="executor",
        prompt="hello",
        audit=False,
        capability_id=None,
        capability_payload_json=None,
        no_health_check=no_health_check,
        no_constellation_check=no_constellation_check,
        config_dir=None,
    )


def _make_null_cfg():
    """Minimal cfg that routes to null provider (no Ollama needed)."""
    return types.SimpleNamespace(
        config_dir="./architecture/runtime/config",
        providers={},
        logging={},
        routing={"routing_table": {}},
        runtime={"context_limit_chars": 32000},
    )


def test_cmd_run_constellation_guard_called():
    """check_constellation is invoked during cmd_run."""
    from io_iii.cli import cmd_run
    guard_called = []

    def mock_guard(routing_cfg):
        guard_called.append(routing_cfg)

    with patch("io_iii.cli.load_io3_config", return_value=_make_null_cfg()), \
         patch("io_iii.cli.make_request_id", return_value="test-id"), \
         patch("io_iii.cli.resolve_route") as mock_route, \
         patch("io_iii.core.constellation.check_constellation", side_effect=mock_guard), \
         patch("io_iii.cli.validate_session_state"), \
         patch("io_iii.cli.engine_run") as mock_engine:

        from io_iii.core.session_state import RouteInfo
        mock_route.return_value = types.SimpleNamespace(
            mode="executor",
            selected_provider="null",
            selected_target=None,
            primary_target=None,
            secondary_target=None,
            fallback_used=False,
            fallback_reason=None,
            boundaries={},
        )

        from io_iii.core.engine import ExecutionResult
        mock_engine.return_value = (
            types.SimpleNamespace(
                mode="executor", route_id="executor",
                request_id="test-id", started_at_ms=0,
                config_dir=".", route=None, audit=None,
                status="ok", provider="null", model=None,
                persona_contract_version="v1.0", persona_id=None,
                logging_policy={}, latency_ms=0, task_spec_id=None,
            ),
            ExecutionResult(
                message="ok",
                meta={"trace": {"steps": []}, "engine_events": []},
                provider="null",
                model=None,
                route_id="executor",
                audit_meta=None,
                prompt_hash=None,
            ),
        )

        cmd_run(_make_args())

    assert len(guard_called) == 1


def test_cmd_run_constellation_drift_surfaces():
    """CONSTELLATION_DRIFT from check_constellation raises at CLI boundary."""
    from io_iii.cli import cmd_run

    with patch("io_iii.cli.load_io3_config", return_value=_make_null_cfg()), \
         patch("io_iii.cli.make_request_id", return_value="test-id"), \
         patch("io_iii.core.constellation.check_constellation",
               side_effect=ValueError("CONSTELLATION_DRIFT: collapse")):

        with pytest.raises(ValueError, match="CONSTELLATION_DRIFT"):
            cmd_run(_make_args(no_constellation_check=False))


def test_cmd_run_no_constellation_check_bypasses_guard():
    """--no-constellation-check skips the guard — no CONSTELLATION_DRIFT raised."""
    from io_iii.cli import cmd_run

    guard_called = []

    def mock_guard(routing_cfg):
        guard_called.append(True)
        raise ValueError("CONSTELLATION_DRIFT: should not be reached")

    with patch("io_iii.cli.load_io3_config", return_value=_make_null_cfg()), \
         patch("io_iii.cli.make_request_id", return_value="test-id"), \
         patch("io_iii.cli.resolve_route") as mock_route, \
         patch("io_iii.core.constellation.check_constellation", side_effect=mock_guard), \
         patch("io_iii.cli.validate_session_state"), \
         patch("io_iii.cli.engine_run") as mock_engine:

        mock_route.return_value = types.SimpleNamespace(
            mode="executor",
            selected_provider="null",
            selected_target=None,
            primary_target=None,
            secondary_target=None,
            fallback_used=False,
            fallback_reason=None,
            boundaries={},
        )

        from io_iii.core.engine import ExecutionResult
        mock_engine.return_value = (
            types.SimpleNamespace(
                mode="executor", route_id="executor",
                request_id="test-id", started_at_ms=0,
                config_dir=".", route=None, audit=None,
                status="ok", provider="null", model=None,
                persona_contract_version="v1.0", persona_id=None,
                logging_policy={}, latency_ms=0, task_spec_id=None,
            ),
            ExecutionResult(
                message="ok",
                meta={"trace": {"steps": []}, "engine_events": []},
                provider="null",
                model=None,
                route_id="executor",
                audit_meta=None,
                prompt_hash=None,
            ),
        )

        # Should not raise
        cmd_run(_make_args(no_constellation_check=True))

    # Guard function was NOT called (short-circuit before it)
    assert len(guard_called) == 0


def test_cmd_run_no_constellation_check_warns_to_stderr(capsys):
    """--no-constellation-check emits the mandatory warning to stderr."""
    from io_iii.cli import cmd_run

    with patch("io_iii.cli.load_io3_config", return_value=_make_null_cfg()), \
         patch("io_iii.cli.make_request_id", return_value="test-id"), \
         patch("io_iii.cli.resolve_route") as mock_route, \
         patch("io_iii.cli.validate_session_state"), \
         patch("io_iii.cli.engine_run") as mock_engine:

        mock_route.return_value = types.SimpleNamespace(
            mode="executor",
            selected_provider="null",
            selected_target=None,
            primary_target=None,
            secondary_target=None,
            fallback_used=False,
            fallback_reason=None,
            boundaries={},
        )

        from io_iii.core.engine import ExecutionResult
        mock_engine.return_value = (
            types.SimpleNamespace(
                mode="executor", route_id="executor",
                request_id="test-id", started_at_ms=0,
                config_dir=".", route=None, audit=None,
                status="ok", provider="null", model=None,
                persona_contract_version="v1.0", persona_id=None,
                logging_policy={}, latency_ms=0, task_spec_id=None,
            ),
            ExecutionResult(
                message="ok",
                meta={"trace": {"steps": []}, "engine_events": []},
                provider="null",
                model=None,
                route_id="executor",
                audit_meta=None,
                prompt_hash=None,
            ),
        )

        cmd_run(_make_args(no_constellation_check=True))

    captured = capsys.readouterr()
    assert "WARN: constellation integrity check bypassed via --no-constellation-check" in captured.err
