---
id: DOC-ARCH-012
title: Phase 4 Guide — Post-Capability Architecture Layer
type: architecture
status: active
version: v0.2
canonical: true
scope: phase-4
audience: developer
created: "2026-03-06"
updated: "2026-04-03"
tags:
- io-iii
- phase-4
- architecture
roles_focus:
- executor
- challenger
provenance: io-iii-runtime-development
---

# Phase 4 Guide — Post-Capability Architecture Layer

## Purpose

Phase 4 introduces the architectural layer above capabilities while preserving all IO-III invariants.

The runtime kernel (routing, engine, context assembly, capability registry) is **frozen**. Phase 4 builds a layer *above* it, not inside it.

---

## Invariants that must remain true

- deterministic routing (ADR-002)
- bounded execution (ADR-009: max 1 audit pass, max 1 revision pass)
- explicit capability invocation only
- content-safe logging (no prompts or model outputs)
- no agent behaviour
- no recursion
- no dynamic routing

---

## What Phase 4 may add

- a bounded orchestration layer that composes a single execution path
- explicit task specs or runbooks that compile to one bounded run
- stricter lifecycle contracts for execution traces and session state
- per-stage execution timing in the trace
- a CLI surface for task and runbook execution

---

## What Phase 4 must not add

- autonomous tool selection
- multi-step loops without an explicit ceiling
- planner or heuristic-driven routing
- self-directed recursion
- dynamic routing based on output content
- uncontrolled multi-step orchestration

---

## Milestones

### M4.0 — Phase 4 ADR and Milestone Definition

Author ADR-012: Bounded Orchestration Layer contract.
Define all Phase 4 milestones formally in SESSION_STATE.md.
Update this document from draft v0.1 to active v0.2 with milestone list.
Define Definition of Done criteria for Phase 4 completion.

---

### M4.1 — Task Specification Schema

Define a `TaskSpec` data structure with explicit inputs, mode, and optional capability list.

Properties:

- `TaskSpec` compiles to exactly one `SessionState` and route — no branching
- Must not encode loops, conditions, or planner logic
- Document schema in DOC-RUN-006

---

### M4.2 — Bounded Orchestration Layer

Introduce an `Orchestrator` that accepts a `TaskSpec` and executes exactly one bounded run.

Execution path:

TaskSpec  
→ routing  
→ engine  
→ context assembly / capability registry  
→ bounded execution  
→ execution trace  
→ content-safe metadata logging

Hard bound: one executor pass, one optional challenger pass (ADR-009 contract preserved).

Must not introduce: multi-step loops, recursion, autonomous tool selection.

---

### M4.3 — Execution Trace Lifecycle Contracts

Define explicit lifecycle states for `ExecutionTrace`:

created → running → completed | failed

Constraints:

- Cannot transition backwards
- Cannot skip terminal states
- Add invariant covering trace lifecycle completeness

File  
`io_iii/core/execution_trace.py`

Documentation  
DOC-RUN-005 (Execution Trace Schema) updated.

---

### M4.4 — SessionState v1 Contract

Promote `SessionState` from v0 to v1 with stricter lifecycle semantics.

Changes:

- Define which fields are write-once vs mutable
- Add `task_spec_id` field to link session state to originating task spec (if applicable)
- Write migration note from v0 to v1

Documentation  
DOC-RUN-002 (SessionState Contract) updated.

---

### M4.5 — Engine Observability Groundwork

Expose structured per-stage timing in `ExecutionTrace`:

- routing_ms
- assembly_ms
- provider_ms
- capability_ms

`SessionState.latency_ms` remains the total. Trace carries the per-stage breakdown.

No external tooling required. Structured data only, stays in `metadata.jsonl`.

Documentation  
DOC-ARCH-006 (Execution Observability) updated.

---

### M4.6 — Runbook Support (Bounded Multi-Capability)

Define `Runbook` as an ordered, finite list of `TaskSpec` steps with no branching.

Properties:

- Explicit step count ceiling (maximum defined by ADR-013)
- Each step is a single engine execution (ADR-009 preserved per step)
- No conditional branching between steps
- Termination is unconditional at step ceiling

Author ADR-013: Runbook Execution Policy covering step ceiling and termination contract.

This is the ceiling for orchestration complexity in IO-III.

---

### M4.7 — CLI Runbook Execution Command

Introduce CLI commands for task and runbook execution:

python -m io_iii run --task <task_spec.yaml>  
python -m io_iii runbook <runbook.yaml>

Properties:

- Expose execution trace and metadata output per step
- `--dry-run` flag validates and prints resolved steps without executing
- `--no-health-check` flag preserved for offline and CI use

---

### M4.8 — Invariant Updates

Add Phase 4 invariants to `validate_invariants.py`:

- Orchestrator never executes more steps than declared in the runbook
- `TaskSpec` always resolves to exactly one route
- No step in a runbook may modify the routing table

Add corresponding invariant YAML files in `architecture/runtime/tests/invariants/`.

---

### M4.9 — Test Coverage

Tests to be added:

- `test_task_spec_resolution.py` — TaskSpec compiles to correct SessionState and route
- `test_orchestrator_bounds.py` — Orchestrator respects step ceiling, does not recurse
- `test_execution_trace_lifecycle.py` — Lifecycle state machine transitions
- `test_runbook_execution.py` — End-to-end bounded runbook execution

---

### M4.10 — Phase 4 Polish and Readiness Docs

- Update ARCHITECTURE.md with orchestration layer description
- Update SESSION_STATE.md for Phase 4 completion
- Update DOC-ARCH-003 (Master Roadmap) to mark Phase 4 complete
- Tag v0.4.0

---

## Definition of done for Phase 4

- Runtime kernel remains stable and unchanged
- All Phase 4 milestones delivered
- ADR-012 and ADR-013 authored and indexed
- Invariant tests updated with Phase 4 invariants
- All tests passing
- All documentation current
- SESSION_STATE.md reflects Phase 4 completion
- v0.4.0 tagged