from __future__ import annotations

from io_iii.core.context_assembly import assemble_context
from io_iii.core.session_state import AuditGateState, RouteInfo, SessionState


def _make_state(*, audit_enabled: bool) -> SessionState:
    return SessionState(
        request_id="20260303T000000Z-aaaa",
        started_at_ms=0,
        mode="executor",
        config_dir="./architecture/runtime/config",
        route=RouteInfo(
            mode="executor",
            primary_target="executor",
            secondary_target=None,
            selected_target="executor",
            selected_provider="null",
            fallback_used=False,
            fallback_reason=None,
            boundaries={"single_voice_output": True},
        ),
        audit=AuditGateState(audit_enabled=audit_enabled, audit_passes=0, revision_passes=0),
        status="ok",
        provider="null",
        model=None,
        route_id="executor",
        persona_contract_version="0.2.0",
        persona_id="io-ii:v1.4.2",
        logging_policy={"content": "disabled"},
    )


def test_assembly_is_deterministic_same_inputs_same_hash():
    state = _make_state(audit_enabled=False)
    persona = "Be precise. Be deterministic."
    prompt = "Return one word."

    a1 = assemble_context(session_state=state, user_prompt=prompt, persona_contract=persona, route_metadata={"route_id": "executor"})
    a2 = assemble_context(session_state=state, user_prompt=prompt, persona_contract=persona, route_metadata={"route_id": "executor"})

    assert a1.prompt_hash == a2.prompt_hash
    assert a1.messages == a2.messages


def test_assembly_hash_changes_when_persona_changes():
    state = _make_state(audit_enabled=False)
    prompt = "Return one word."

    a1 = assemble_context(session_state=state, user_prompt=prompt, persona_contract="Persona A", route_metadata=None)
    a2 = assemble_context(session_state=state, user_prompt=prompt, persona_contract="Persona B", route_metadata=None)

    assert a1.prompt_hash != a2.prompt_hash


def test_assembly_envelope_reflects_audit_toggle_deterministically():
    persona = "Be precise."
    prompt = "Return one word."

    s_off = _make_state(audit_enabled=False)
    s_on = _make_state(audit_enabled=True)

    a_off = assemble_context(session_state=s_off, user_prompt=prompt, persona_contract=persona, route_metadata=None)
    a_on = assemble_context(session_state=s_on, user_prompt=prompt, persona_contract=persona, route_metadata=None)

    assert a_off.prompt_hash != a_on.prompt_hash
    assert "audit_enabled: False" in a_off.system_prompt
    assert "audit_enabled: True" in a_on.system_prompt