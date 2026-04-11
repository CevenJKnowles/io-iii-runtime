# io_iii/core/constellation.py
from __future__ import annotations

from typing import Any, Dict, Optional

from io_iii.core.runbook import RUNBOOK_MAX_STEPS


def _extract_model(target: str) -> str:
    """
    Extract the model identifier from a '<namespace>:<model>' target string.

    Examples:
        'local:qwen3:8b'          → 'qwen3:8b'
        'local:deepseek-r1:latest' → 'deepseek-r1:latest'
        'qwen3:8b'                 → 'qwen3:8b'  (no namespace prefix)
    """
    parts = target.split(":", 1)
    # If there is only one segment, treat the whole string as the model name.
    return parts[1] if len(parts) == 2 else parts[0]


def check_constellation(routing_cfg: Dict[str, Any]) -> None:
    """
    Validate model constellation integrity at config-time (ADR-021 §4).

    Checks (ADR-021 §4.3):
      1. Role-model collapse — executor and challenger must not resolve to the
         same model identifier.
      2. Required role bindings — every declared role must have a non-empty
         primary model binding.
      3. Call chain bounds — if a role declares a static 'max_steps' field,
         it must not exceed RUNBOOK_MAX_STEPS (ADR-014).

    Raises:
        ValueError: message begins with 'CONSTELLATION_DRIFT:' — content-safe
            (no model output, no prompt text).

    Does nothing when routing_cfg is empty or contains no modes.
    """
    if not isinstance(routing_cfg, dict):
        return

    routing_table: Dict[str, Any] = routing_cfg.get("routing_table") or {}
    modes: Dict[str, Any] = routing_table.get("modes") or {}

    if not modes:
        return

    # -----------------------------------------------------------------------
    # Check 1: Role-model collapse (executor vs challenger)
    # -----------------------------------------------------------------------
    executor_cfg: Optional[Dict[str, Any]] = modes.get("executor")
    challenger_cfg: Optional[Dict[str, Any]] = modes.get("challenger")

    if executor_cfg and challenger_cfg:
        executor_primary = (executor_cfg.get("primary") or "").strip()
        challenger_primary = (challenger_cfg.get("primary") or "").strip()

        if executor_primary and challenger_primary:
            exec_model = _extract_model(executor_primary)
            chall_model = _extract_model(challenger_primary)
            if exec_model == chall_model:
                raise ValueError(
                    f"CONSTELLATION_DRIFT: executor and challenger resolve to the same "
                    f"model ({exec_model!r}) — adversarial review guarantee is defeated"
                )

    # -----------------------------------------------------------------------
    # Check 2: Required role bindings — non-empty primary
    # -----------------------------------------------------------------------
    for role, role_cfg in modes.items():
        if not isinstance(role_cfg, dict):
            raise ValueError(
                f"CONSTELLATION_DRIFT: role {role!r} has invalid binding "
                f"(expected a mapping, got {type(role_cfg).__name__!r})"
            )
        primary = (role_cfg.get("primary") or "").strip()
        if not primary:
            raise ValueError(
                f"CONSTELLATION_DRIFT: role {role!r} has an empty or missing "
                f"primary model binding"
            )

    # -----------------------------------------------------------------------
    # Check 3: Call chain bounds — static max_steps vs RUNBOOK_MAX_STEPS
    # -----------------------------------------------------------------------
    for role, role_cfg in modes.items():
        if not isinstance(role_cfg, dict):
            continue
        raw_steps = role_cfg.get("max_steps")
        if raw_steps is None:
            continue
        try:
            steps = int(raw_steps)
        except (TypeError, ValueError):
            continue
        if steps > RUNBOOK_MAX_STEPS:
            raise ValueError(
                f"CONSTELLATION_DRIFT: role {role!r} declares max_steps={steps} "
                f"which exceeds RUNBOOK_MAX_STEPS={RUNBOOK_MAX_STEPS}"
            )
