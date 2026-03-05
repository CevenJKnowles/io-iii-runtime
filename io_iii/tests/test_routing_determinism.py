from __future__ import annotations

from pathlib import Path

from io_iii.config import load_io3_config
from io_iii.routing import resolve_route


def test_routing_is_deterministic_for_same_inputs() -> None:
    """Same inputs must yield identical RouteSelection (deterministic contract)."""

    cfg_dir = Path("architecture/runtime/config")
    cfg = load_io3_config(cfg_dir)

    routing_cfg = cfg.routing["routing_table"]
    providers_cfg = cfg.providers

    sel1 = resolve_route(
        routing_cfg=routing_cfg,
        mode="executor",
        providers_cfg=providers_cfg,
        supported_providers={"null", "ollama"},
    )

    for _ in range(10):
        selN = resolve_route(
            routing_cfg=routing_cfg,
            mode="executor",
            providers_cfg=providers_cfg,
            supported_providers={"null", "ollama"},
        )
        assert selN == sel1
