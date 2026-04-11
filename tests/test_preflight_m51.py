"""
test_preflight_m51.py — Phase 5 M5.1 token pre-flight estimator tests.

Verifies:

  Unit — preflight module
  - estimate_chars returns len(text)
  - estimate_chars on empty string returns 0
  - check_context_limit passes when count <= limit
  - check_context_limit raises ValueError exactly at count == limit + 1
  - check_context_limit raises ValueError with CONTEXT_LIMIT_EXCEEDED prefix
  - ValueError message contains estimated_chars and limit_chars counts
  - ValueError message contains no prompt content

  Unit — failure classification
  - CONTEXT_LIMIT_EXCEEDED is extracted as causal_code by failure_model
  - classify_exception produces CONTRACT_VIOLATION kind for preflight ValueError

  Integration — engine
  - engine raises on oversized prompt (below provider call)
  - engine passes for prompt within limit
  - engine respects limit_chars=0 (disabled — no raise)
  - RuntimeFailure attached to exception has CONTRACT_VIOLATION kind and
    CONTEXT_LIMIT_EXCEEDED code
  - config-sourced limit is respected over default
"""
from __future__ import annotations

import types
from unittest.mock import patch

import pytest

from io_iii.core.preflight import (
    _DEFAULT_CONTEXT_LIMIT_CHARS,
    check_context_limit,
    estimate_chars,
)
from io_iii.core.failure_model import RuntimeFailureKind, classify_exception


# ---------------------------------------------------------------------------
# Unit: preflight module
# ---------------------------------------------------------------------------

def test_estimate_chars_returns_length():
    text = "hello world"
    assert estimate_chars(text) == len(text)


def test_estimate_chars_empty_string():
    assert estimate_chars("") == 0


def test_check_context_limit_passes_at_limit():
    prompt = "x" * 100
    check_context_limit(prompt, limit_chars=100)  # must not raise


def test_check_context_limit_passes_below_limit():
    prompt = "x" * 50
    check_context_limit(prompt, limit_chars=100)  # must not raise


def test_check_context_limit_raises_one_over():
    prompt = "x" * 101
    with pytest.raises(ValueError):
        check_context_limit(prompt, limit_chars=100)


def test_check_context_limit_raises_with_correct_prefix():
    prompt = "x" * 200
    with pytest.raises(ValueError, match="CONTEXT_LIMIT_EXCEEDED"):
        check_context_limit(prompt, limit_chars=100)


def test_check_context_limit_message_contains_counts():
    prompt = "x" * 150
    with pytest.raises(ValueError) as exc_info:
        check_context_limit(prompt, limit_chars=100)
    msg = str(exc_info.value)
    assert "150" in msg
    assert "100" in msg


def test_check_context_limit_message_no_prompt_content():
    """Failure message must not echo back any portion of the prompt text."""
    prompt = "SENSITIVE_CONTENT_DO_NOT_LOG" * 5
    with pytest.raises(ValueError) as exc_info:
        check_context_limit(prompt, limit_chars=10)
    assert "SENSITIVE_CONTENT_DO_NOT_LOG" not in str(exc_info.value)


def test_default_context_limit_is_positive():
    assert _DEFAULT_CONTEXT_LIMIT_CHARS > 0


# ---------------------------------------------------------------------------
# Unit: failure classification
# ---------------------------------------------------------------------------

def test_context_limit_causal_code_extracted():
    exc = ValueError("CONTEXT_LIMIT_EXCEEDED: estimated_chars=500 limit_chars=100")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.causal_code == "CONTEXT_LIMIT_EXCEEDED"


def test_context_limit_failure_kind_is_contract_violation():
    exc = ValueError("CONTEXT_LIMIT_EXCEEDED: estimated_chars=500 limit_chars=100")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.kind == RuntimeFailureKind.CONTRACT_VIOLATION


def test_context_limit_failure_code_matches_causal():
    exc = ValueError("CONTEXT_LIMIT_EXCEEDED: estimated_chars=500 limit_chars=100")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.code == "CONTEXT_LIMIT_EXCEEDED"


def test_context_limit_failure_not_retryable():
    exc = ValueError("CONTEXT_LIMIT_EXCEEDED: estimated_chars=500 limit_chars=100")
    failure = classify_exception(exc, request_id="test-req")
    assert failure.retryable is False


# ---------------------------------------------------------------------------
# Integration: engine raises on oversized prompt
# ---------------------------------------------------------------------------

def _make_cfg(context_limit_chars=None):
    """Minimal cfg object with runtime config."""
    runtime = {}
    if context_limit_chars is not None:
        runtime["context_limit_chars"] = context_limit_chars
    cfg = types.SimpleNamespace(
        providers={"ollama": {"base_url": "http://127.0.0.1:11434"}},
        logging={},
        routing={"routing_table": {}},
        runtime=runtime,
    )
    return cfg


def _make_session_state(*, provider="null"):
    from io_iii.core.session_state import AuditGateState, RouteInfo, SessionState
    import time

    route = RouteInfo(
        mode=provider,
        selected_provider=provider,
        selected_target=None,
        fallback_used=False,
    ) if provider != "null" else None

    return SessionState(
        request_id="test-preflight",
        started_at_ms=int(time.time() * 1000),
        mode=provider,
        config_dir="./architecture/runtime/config",
        route=route,
        audit=AuditGateState(audit_enabled=False),
        status="ok",
        provider=provider,
        model=None,
        route_id=provider,
        persona_contract_version="v1.0",
        logging_policy={"content": "disabled"},
    )


def test_engine_raises_context_limit_exceeded():
    """Engine must raise ValueError with CONTEXT_LIMIT_EXCEEDED for oversized prompt."""
    from io_iii.core.engine import run
    from io_iii.core.session_state import SessionState, AuditGateState, RouteInfo
    import time

    cfg = _make_cfg(context_limit_chars=10)
    ollama_route = RouteInfo(
        mode="executor",
        primary_target="ollama:llama3.2",
        secondary_target=None,
        selected_target="ollama:llama3.2",
        selected_provider="ollama",
        fallback_used=False,
        fallback_reason=None,
    )
    state = SessionState(
        request_id="test-preflight-ollama",
        started_at_ms=int(time.time() * 1000),
        mode="executor",
        config_dir="./architecture/runtime/config",
        route=ollama_route,
        audit=AuditGateState(audit_enabled=False),
        status="ok",
        provider="ollama",
        model="llama3.2",
        route_id="executor",
        persona_contract_version="v1.0",
        logging_policy={"content": "disabled"},
    )

    # Factory creates a provider object; generate() must never be invoked.
    class _NeverGenerate:
        def generate(self, *, model, prompt):
            raise AssertionError("generate() must not be called when preflight fails")

    with pytest.raises(ValueError, match="CONTEXT_LIMIT_EXCEEDED"):
        run(
            cfg=cfg,
            session_state=state,
            user_prompt="this prompt is definitely longer than ten characters",
            audit=False,
            ollama_provider_factory=lambda _: _NeverGenerate(),
        )


def test_engine_preflight_attaches_runtime_failure():
    """RuntimeFailure envelope must be attached to the preflight ValueError."""
    from io_iii.core.engine import run
    from io_iii.core.session_state import SessionState, AuditGateState, RouteInfo
    import time

    cfg = _make_cfg(context_limit_chars=10)
    ollama_route = RouteInfo(
        mode="executor",
        primary_target="ollama:llama3.2",
        secondary_target=None,
        selected_target="ollama:llama3.2",
        selected_provider="ollama",
        fallback_used=False,
        fallback_reason=None,
    )
    state = SessionState(
        request_id="test-preflight-failure",
        started_at_ms=int(time.time() * 1000),
        mode="executor",
        config_dir="./architecture/runtime/config",
        route=ollama_route,
        audit=AuditGateState(audit_enabled=False),
        status="ok",
        provider="ollama",
        model="llama3.2",
        route_id="executor",
        persona_contract_version="v1.0",
        logging_policy={"content": "disabled"},
    )

    class _NeverGenerate:
        def generate(self, *, model, prompt):
            raise AssertionError("generate() must not be called when preflight fails")

    with pytest.raises(ValueError) as exc_info:
        run(
            cfg=cfg,
            session_state=state,
            user_prompt="this prompt is definitely longer than ten characters",
            audit=False,
            ollama_provider_factory=lambda _: _NeverGenerate(),
        )

    exc = exc_info.value
    assert hasattr(exc, "runtime_failure")
    failure = exc.runtime_failure
    assert failure.kind == RuntimeFailureKind.CONTRACT_VIOLATION
    assert failure.code == "CONTEXT_LIMIT_EXCEEDED"
    assert failure.retryable is False


def test_engine_disabled_limit_does_not_raise():
    """limit_chars=0 must disable the check — no raise even for large prompts."""
    from io_iii.core.engine import run
    from io_iii.core.session_state import SessionState, AuditGateState, RouteInfo
    import time

    cfg = _make_cfg(context_limit_chars=0)
    ollama_route = RouteInfo(
        mode="executor",
        primary_target="ollama:llama3.2",
        secondary_target=None,
        selected_target="ollama:llama3.2",
        selected_provider="ollama",
        fallback_used=False,
        fallback_reason=None,
    )
    state = SessionState(
        request_id="test-preflight-disabled",
        started_at_ms=int(time.time() * 1000),
        mode="executor",
        config_dir="./architecture/runtime/config",
        route=ollama_route,
        audit=AuditGateState(audit_enabled=False),
        status="ok",
        provider="ollama",
        model="llama3.2",
        route_id="executor",
        persona_contract_version="v1.0",
        logging_policy={"content": "disabled"},
    )

    provider_called = []

    def mock_provider_factory(_):
        from io_iii.providers.null_provider import NullProvider

        class _MockOllama:
            def generate(self, *, model, prompt):
                provider_called.append(True)
                return "mock response"

        return _MockOllama()

    # Should not raise — limit is disabled
    run(
        cfg=cfg,
        session_state=state,
        user_prompt="x" * 50_000,
        audit=False,
        ollama_provider_factory=mock_provider_factory,
    )
    assert provider_called, "provider must have been called when limit is disabled"


def test_engine_config_limit_respected():
    """Engine must read context_limit_chars from cfg.runtime, not use the default."""
    from io_iii.core.engine import run
    from io_iii.core.session_state import SessionState, AuditGateState, RouteInfo
    import time

    # Set a very tight limit in config
    cfg = _make_cfg(context_limit_chars=5)
    ollama_route = RouteInfo(
        mode="executor",
        primary_target="ollama:llama3.2",
        secondary_target=None,
        selected_target="ollama:llama3.2",
        selected_provider="ollama",
        fallback_used=False,
        fallback_reason=None,
    )
    state = SessionState(
        request_id="test-preflight-cfg",
        started_at_ms=int(time.time() * 1000),
        mode="executor",
        config_dir="./architecture/runtime/config",
        route=ollama_route,
        audit=AuditGateState(audit_enabled=False),
        status="ok",
        provider="ollama",
        model="llama3.2",
        route_id="executor",
        persona_contract_version="v1.0",
        logging_policy={"content": "disabled"},
    )

    with pytest.raises(ValueError, match="CONTEXT_LIMIT_EXCEEDED"):
        run(
            cfg=cfg,
            session_state=state,
            user_prompt="six chars",  # well within 32k default but over 5
            audit=False,
            ollama_provider_factory=lambda _: None,
        )
