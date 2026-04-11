"""
test_memory_packs_m62.py — Phase 6 M6.2 memory pack system tests (ADR-022 §3).

Verifies:

  Unit — MemoryPack
  - construction and field access
  - is frozen
  - empty keys list is valid
  - empty include_packs defaults to empty tuple
  - id validation: empty id rejected
  - scope validation: empty scope rejected

  Unit — PackLoader (in-memory config via tmp_path)
  - get() returns None when config file absent
  - get() returns None for unknown pack id
  - get() returns correct MemoryPack for known id
  - all_pack_ids() returns declared ids in order
  - all_pack_ids() returns empty list when no config
  - storage_root defaults to './memory_store' when key absent
  - storage_root reads declared value from config
  - resolve_keys() returns keys in declaration order
  - resolve_keys() for empty pack returns empty list
  - resolve_keys() raises ValueError for unknown pack id
  - resolve_keys() expands include_packs (depth 1) correctly
  - resolve_keys() prepends included keys before own keys
  - resolve_keys() raises ValueError when included pack is missing
  - resolve_keys() raises ValueError when included pack has its own include_packs (depth > 1)
  - multiple include_packs are expanded in order
  - pack with only include_packs (no own keys) resolves correctly

  Integration — canonical config file
  - memory_packs.yaml is valid YAML and parseable by PackLoader
  - pack.default.starter is declared and resolvable
  - pack.io_iii.session_resume is declared and resolvable
  - storage_root is a non-empty string
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from io_iii.memory.packs import MemoryPack, PackLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_packs_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "memory_packs.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# MemoryPack — construction
# ---------------------------------------------------------------------------

def test_pack_field_access() -> None:
    pack = MemoryPack(
        id="pack.test.basic",
        version="1.0",
        description="A test pack",
        scope="test",
        keys=("alpha", "beta"),
    )
    assert pack.id == "pack.test.basic"
    assert pack.scope == "test"
    assert pack.keys == ("alpha", "beta")
    assert pack.include_packs == ()


def test_pack_is_frozen() -> None:
    pack = MemoryPack(
        id="pack.test.basic",
        version="1.0",
        description="",
        scope="test",
        keys=(),
    )
    with pytest.raises((AttributeError, TypeError)):
        pack.id = "mutated"  # type: ignore[misc]


def test_pack_empty_keys_valid() -> None:
    pack = MemoryPack(
        id="pack.test.empty",
        version="1.0",
        description="",
        scope="test",
        keys=(),
    )
    assert pack.keys == ()


def test_pack_include_packs_defaults_to_empty() -> None:
    pack = MemoryPack(
        id="pack.test.basic",
        version="1.0",
        description="",
        scope="test",
        keys=("k1",),
    )
    assert pack.include_packs == ()


def test_pack_empty_id_rejected() -> None:
    with pytest.raises(ValueError, match="id"):
        MemoryPack(id="", version="1.0", description="", scope="s", keys=())


def test_pack_empty_scope_rejected() -> None:
    with pytest.raises(ValueError, match="scope"):
        MemoryPack(id="p", version="1.0", description="", scope="", keys=())


# ---------------------------------------------------------------------------
# PackLoader — absent config
# ---------------------------------------------------------------------------

def test_loader_absent_config_get_returns_none(tmp_path: Path) -> None:
    loader = PackLoader(tmp_path / "nonexistent.yaml")
    assert loader.get("pack.any") is None


def test_loader_absent_config_all_ids_empty(tmp_path: Path) -> None:
    loader = PackLoader(tmp_path / "nonexistent.yaml")
    assert loader.all_pack_ids() == []


def test_loader_absent_config_storage_root_default(tmp_path: Path) -> None:
    loader = PackLoader(tmp_path / "nonexistent.yaml")
    assert loader.storage_root == "./memory_store"


# ---------------------------------------------------------------------------
# PackLoader — get / all_pack_ids / storage_root
# ---------------------------------------------------------------------------

def test_loader_get_unknown_id_returns_none(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.test.alpha
            version: "1.0"
            description: ""
            scope: test
            keys: [a, b]
    """)
    loader = PackLoader(cfg)
    assert loader.get("pack.unknown") is None


def test_loader_get_known_id_returns_pack(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.test.alpha
            version: "1.0"
            description: "A pack"
            scope: test
            keys: [a, b, c]
    """)
    loader = PackLoader(cfg)
    pack = loader.get("pack.test.alpha")
    assert pack is not None
    assert pack.id == "pack.test.alpha"
    assert pack.scope == "test"
    assert pack.keys == ("a", "b", "c")


def test_loader_all_pack_ids_in_order(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.one
            version: "1.0"
            description: ""
            scope: s
            keys: []
          - id: pack.two
            version: "1.0"
            description: ""
            scope: s
            keys: []
          - id: pack.three
            version: "1.0"
            description: ""
            scope: s
            keys: []
    """)
    loader = PackLoader(cfg)
    assert loader.all_pack_ids() == ["pack.one", "pack.two", "pack.three"]


def test_loader_storage_root_from_config(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: /data/my_store
        packs: []
    """)
    loader = PackLoader(cfg)
    assert loader.storage_root == "/data/my_store"


def test_loader_storage_root_default_when_key_absent(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        packs: []
    """)
    loader = PackLoader(cfg)
    assert loader.storage_root == "./memory_store"


# ---------------------------------------------------------------------------
# PackLoader — resolve_keys
# ---------------------------------------------------------------------------

def test_resolve_keys_returns_in_declaration_order(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.test.ordered
            version: "1.0"
            description: ""
            scope: test
            keys: [gamma, alpha, beta]
    """)
    loader = PackLoader(cfg)
    assert loader.resolve_keys("pack.test.ordered") == ["gamma", "alpha", "beta"]


def test_resolve_keys_empty_pack_returns_empty(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.test.empty
            version: "1.0"
            description: ""
            scope: test
            keys: []
    """)
    loader = PackLoader(cfg)
    assert loader.resolve_keys("pack.test.empty") == []


def test_resolve_keys_unknown_id_raises(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs: []
    """)
    loader = PackLoader(cfg)
    with pytest.raises(ValueError, match="not declared"):
        loader.resolve_keys("pack.unknown")


def test_resolve_keys_expands_include_packs(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.base
            version: "1.0"
            description: ""
            scope: test
            keys: [base_a, base_b]
          - id: pack.extended
            version: "1.0"
            description: ""
            scope: test
            keys: [own_c]
            include_packs: [pack.base]
    """)
    loader = PackLoader(cfg)
    result = loader.resolve_keys("pack.extended")
    assert result == ["base_a", "base_b", "own_c"]


def test_resolve_keys_included_keys_prepend_own_keys(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.first
            version: "1.0"
            description: ""
            scope: test
            keys: [first_key]
          - id: pack.main
            version: "1.0"
            description: ""
            scope: test
            keys: [main_key]
            include_packs: [pack.first]
    """)
    loader = PackLoader(cfg)
    result = loader.resolve_keys("pack.main")
    assert result.index("first_key") < result.index("main_key")


def test_resolve_keys_multiple_include_packs_in_order(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.a
            version: "1.0"
            description: ""
            scope: test
            keys: [a1, a2]
          - id: pack.b
            version: "1.0"
            description: ""
            scope: test
            keys: [b1]
          - id: pack.combined
            version: "1.0"
            description: ""
            scope: test
            keys: [own]
            include_packs: [pack.a, pack.b]
    """)
    loader = PackLoader(cfg)
    assert loader.resolve_keys("pack.combined") == ["a1", "a2", "b1", "own"]


def test_resolve_keys_only_include_packs_no_own_keys(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.base
            version: "1.0"
            description: ""
            scope: test
            keys: [x, y]
          - id: pack.proxy
            version: "1.0"
            description: ""
            scope: test
            keys: []
            include_packs: [pack.base]
    """)
    loader = PackLoader(cfg)
    assert loader.resolve_keys("pack.proxy") == ["x", "y"]


def test_resolve_keys_missing_included_pack_raises(tmp_path: Path) -> None:
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.main
            version: "1.0"
            description: ""
            scope: test
            keys: [own]
            include_packs: [pack.missing]
    """)
    loader = PackLoader(cfg)
    with pytest.raises(ValueError, match="not declared"):
        loader.resolve_keys("pack.main")


def test_resolve_keys_depth_2_raises(tmp_path: Path) -> None:
    """A pack that includes a pack that itself has include_packs must be rejected."""
    cfg = write_packs_yaml(tmp_path, """
        storage_root: ./store
        packs:
          - id: pack.leaf
            version: "1.0"
            description: ""
            scope: test
            keys: [leaf_key]
          - id: pack.middle
            version: "1.0"
            description: ""
            scope: test
            keys: [mid_key]
            include_packs: [pack.leaf]
          - id: pack.top
            version: "1.0"
            description: ""
            scope: test
            keys: [top_key]
            include_packs: [pack.middle]
    """)
    loader = PackLoader(cfg)
    with pytest.raises(ValueError, match="maximum nesting depth"):
        loader.resolve_keys("pack.top")


# ---------------------------------------------------------------------------
# Integration — canonical config file
# ---------------------------------------------------------------------------

CANONICAL_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "architecture" / "runtime" / "config" / "memory_packs.yaml"
)


def test_canonical_config_parseable() -> None:
    loader = PackLoader(CANONICAL_CONFIG)
    assert isinstance(loader.all_pack_ids(), list)


def test_canonical_config_storage_root_non_empty() -> None:
    loader = PackLoader(CANONICAL_CONFIG)
    assert loader.storage_root and isinstance(loader.storage_root, str)


def test_canonical_config_starter_pack_declared() -> None:
    loader = PackLoader(CANONICAL_CONFIG)
    pack = loader.get("pack.default.starter")
    assert pack is not None
    assert pack.scope == "default"


def test_canonical_config_starter_pack_resolvable() -> None:
    loader = PackLoader(CANONICAL_CONFIG)
    keys = loader.resolve_keys("pack.default.starter")
    assert isinstance(keys, list)


def test_canonical_config_session_resume_pack_declared() -> None:
    loader = PackLoader(CANONICAL_CONFIG)
    pack = loader.get("pack.io_iii.session_resume")
    assert pack is not None
    assert pack.scope == "io_iii"


def test_canonical_config_session_resume_resolvable() -> None:
    loader = PackLoader(CANONICAL_CONFIG)
    keys = loader.resolve_keys("pack.io_iii.session_resume")
    assert isinstance(keys, list)
    assert len(keys) > 0
