"""
io_iii.memory.policy — Phase 6 M6.3 memory retrieval policy (ADR-022 §4).

Provides:
    RetrievalPolicy  — evaluates whether a route or capability may access a
                       memory record at a given sensitivity tier

Policy contract (ADR-022 §4):
    - Default stance: no access. All access is opt-in via allowlists.
    - route_allowlist     — routes permitted to access memory at all
    - capability_allowlist — capabilities permitted to trigger memory access
    - sensitivity_allowlist — per-tier route subsets for elevated/restricted records
      * 'standard'    — accessible to any allowlisted route
      * 'elevated'    — route must also appear in sensitivity_allowlist["elevated"]
      * 'restricted'  — route must also appear in sensitivity_allowlist["restricted"]

Policy absence (ADR-022 §4.4):
    If the config file does not exist, all access checks return False.
    This is not a failure — it is the safe default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from io_iii.memory.store import (
    SENSITIVITY_ELEVATED,
    SENSITIVITY_RESTRICTED,
    SENSITIVITY_STANDARD,
)


# ---------------------------------------------------------------------------
# RetrievalPolicy dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetrievalPolicy:
    """
    Immutable snapshot of the memory retrieval policy (ADR-022 §4.2).

    Fields:
        route_allowlist       — frozenset of route identifiers permitted to access memory
        capability_allowlist  — frozenset of capability ids permitted to access memory
        sensitivity_elevated  — frozenset of routes permitted to access elevated records
        sensitivity_restricted — frozenset of routes permitted to access restricted records
    """
    route_allowlist: frozenset[str]
    capability_allowlist: frozenset[str]
    sensitivity_elevated: frozenset[str]
    sensitivity_restricted: frozenset[str]

    def is_route_allowed(self, route: str) -> bool:
        """
        Return True if the route may access any memory record.

        A False result means the route receives an empty memory subset (no error).
        """
        return route in self.route_allowlist

    def is_capability_allowed(self, capability_id: str) -> bool:
        """
        Return True if the capability may trigger memory access.

        A False result means the capability receives no memory context (no error).
        """
        return capability_id in self.capability_allowlist

    def can_access(self, route: str, sensitivity: str) -> bool:
        """
        Return True if the route may access a record at the given sensitivity tier.

        Evaluation order (ADR-022 §4.3):
            1. Route not in route_allowlist → False
            2. sensitivity == 'standard'    → True
            3. sensitivity == 'elevated'    → route in sensitivity_elevated
            4. sensitivity == 'restricted'  → route in sensitivity_restricted
            5. Unknown sensitivity tier     → False (safe default)
        """
        if route not in self.route_allowlist:
            return False
        if sensitivity == SENSITIVITY_STANDARD:
            return True
        if sensitivity == SENSITIVITY_ELEVATED:
            return route in self.sensitivity_elevated
        if sensitivity == SENSITIVITY_RESTRICTED:
            return route in self.sensitivity_restricted
        return False  # unknown tier: deny by default

    def filter_records(self, route: str, records: list) -> list:
        """
        Return the subset of records accessible to route at their declared sensitivity.

        Records for which can_access() returns False are dropped silently.
        Input list order is preserved.
        """
        return [r for r in records if self.can_access(route, r.sensitivity)]


# ---------------------------------------------------------------------------
# Null policy (ADR-022 §4.4 — policy absence)
# ---------------------------------------------------------------------------

NULL_POLICY = RetrievalPolicy(
    route_allowlist=frozenset(),
    capability_allowlist=frozenset(),
    sensitivity_elevated=frozenset(),
    sensitivity_restricted=frozenset(),
)
"""
Safe-default policy used when no config file is present.
All access checks return False. Injection is skipped for all routes.
"""


# ---------------------------------------------------------------------------
# Policy loader
# ---------------------------------------------------------------------------

def load_retrieval_policy(config_path: str | Path) -> RetrievalPolicy:
    """
    Load a RetrievalPolicy from memory_retrieval_policy.yaml.

    Returns NULL_POLICY if the file does not exist (ADR-022 §4.4).
    Raises ValueError if the file is present but malformed.
    """
    path = Path(config_path)
    if not path.is_file():
        return NULL_POLICY

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(
            f"Memory retrieval policy must be a YAML mapping: {path}"
        )

    route_allowlist = frozenset(data.get("route_allowlist") or [])
    capability_allowlist = frozenset(data.get("capability_allowlist") or [])

    sensitivity = data.get("sensitivity_allowlist") or {}
    sensitivity_elevated = frozenset(sensitivity.get("elevated") or [])
    sensitivity_restricted = frozenset(sensitivity.get("restricted") or [])

    return RetrievalPolicy(
        route_allowlist=route_allowlist,
        capability_allowlist=capability_allowlist,
        sensitivity_elevated=sensitivity_elevated,
        sensitivity_restricted=sensitivity_restricted,
    )
