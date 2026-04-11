"""
io_iii.memory.packs — Phase 6 M6.2 memory pack system (ADR-022 §3).

Provides:
    MemoryPack   — named, versioned collection of memory record keys
    PackLoader   — loads and resolves packs from memory_packs.yaml

Pack resolution contract (ADR-022 §3.2):
    - Packs are author-controlled; not runtime-generated
    - Resolution is deterministic from pack id
    - A pack may not reference keys from multiple scopes
    - Max nesting depth: 1 (include_packs expands one level; no recursion)
    - Empty pack (zero keys) is valid and resolves to an empty key list
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# MemoryPack dataclass (ADR-022 §3.1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryPack:
    """
    Named, versioned collection of memory record keys (ADR-022 §3.1).

    Fields:
        id            — stable pack identifier (e.g. pack.io_iii.session_resume)
        version       — semantic version string
        description   — human-readable purpose; never logged as a value
        scope         — scope identifier for all records in the pack
        keys          — ordered tuple of memory record keys
        include_packs — tuple of other pack ids whose keys are prepended (max depth 1)
    """
    id: str
    version: str
    description: str
    scope: str
    keys: tuple[str, ...]
    include_packs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValueError("MemoryPack.id must be a non-empty string")
        if not self.scope or not isinstance(self.scope, str):
            raise ValueError("MemoryPack.scope must be a non-empty string")
        if not isinstance(self.version, str):
            raise ValueError("MemoryPack.version must be a string")
        if not isinstance(self.keys, tuple):
            raise TypeError("MemoryPack.keys must be a tuple")
        if not isinstance(self.include_packs, tuple):
            raise TypeError("MemoryPack.include_packs must be a tuple")


def _pack_from_dict(data: dict) -> MemoryPack:
    """Deserialise a pack entry from a YAML-loaded dict."""
    return MemoryPack(
        id=data["id"],
        version=str(data.get("version", "1.0")),
        description=data.get("description", ""),
        scope=data["scope"],
        keys=tuple(data.get("keys") or []),
        include_packs=tuple(data.get("include_packs") or []),
    )


# ---------------------------------------------------------------------------
# PackLoader (ADR-022 §3.2)
# ---------------------------------------------------------------------------

class PackLoader:
    """
    Loads and resolves memory packs from memory_packs.yaml (ADR-022 §3).

    Resolve contract:
        resolve_keys(pack_id) expands include_packs at depth 1 only.
        If a referenced pack itself has include_packs entries, ValueError is raised.
        This enforces the max-nesting-depth-1 constraint from ADR-022 §3.2.

    Policy on absent config:
        If the config file does not exist, all lookups return None / empty list.
        This is not a failure — it is the safe default (mirrors M6.3 policy absence).
    """

    def __init__(self, config_path: str | Path) -> None:
        self._path = Path(config_path)
        self._packs: dict[str, MemoryPack] = {}
        self._storage_root: str = "./memory_store"
        self._loaded = False
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            self._loaded = True
            return
        with self._path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._storage_root = str(data.get("storage_root", "./memory_store"))
        for entry in data.get("packs") or []:
            pack = _pack_from_dict(entry)
            self._packs[pack.id] = pack
        self._loaded = True

    @property
    def storage_root(self) -> str:
        """Configurable storage root declared in memory_packs.yaml (ADR-022 §2.3)."""
        return self._storage_root

    def get(self, pack_id: str) -> Optional[MemoryPack]:
        """Return the MemoryPack for pack_id, or None if not declared."""
        return self._packs.get(pack_id)

    def all_pack_ids(self) -> list[str]:
        """Return all declared pack ids in insertion order."""
        return list(self._packs.keys())

    def resolve_keys(self, pack_id: str) -> list[str]:
        """
        Return the full, ordered key list for a pack, expanding include_packs.

        Resolution order: included pack keys first (in include_packs order),
        then the pack's own keys.

        Raises ValueError if:
            - pack_id is not declared
            - any included pack is itself missing from the config
            - any included pack has its own include_packs (depth > 1)
        """
        pack = self._packs.get(pack_id)
        if pack is None:
            raise ValueError(
                f"Pack '{pack_id}' is not declared in {self._path}"
            )

        result: list[str] = []

        for included_id in pack.include_packs:
            included = self._packs.get(included_id)
            if included is None:
                raise ValueError(
                    f"Pack '{pack_id}' includes '{included_id}', "
                    f"which is not declared in {self._path}"
                )
            if included.include_packs:
                raise ValueError(
                    f"Pack '{pack_id}' includes '{included_id}', "
                    f"which itself has include_packs — maximum nesting depth is 1 "
                    f"(ADR-022 §3.2)"
                )
            result.extend(included.keys)

        result.extend(pack.keys)
        return result
