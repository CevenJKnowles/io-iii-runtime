---
id: ADR-010
title: Context Assembly Layer Definition
type: adr
status: amended
version: v1.1
canonical: true
scope: io-iii
audience: internal
created: "2026-03-03"
updated: "2026-05-29"
tags:
  - architecture
  - context
  - assembly
  - determinism
roles_focus:
  - synthesizer
  - executor
  - governance
provenance: human
---

# ADR-010 — Context Assembly Layer Definition

## Status

Amended

---

## 1. Context

IO-III currently operates under a deterministic control plane:

CLI → routing resolution → provider execution → optional audit gate → unified output.

Prompt construction is implicitly distributed across routing, persona contract injection, and execution logic. As structural complexity increases, this implicit composition risks:

- Boundary ambiguity
- Tight coupling between routing and prompt logic
- Premature feature inflation (memory, tools, arbitration)

To preserve determinism and governance clarity, a formal structural boundary is required.

### Rationale

Formalising context assembly:

- Preserves deterministic execution guarantees.
- Creates a clean abstraction seam before future envelope sophistication.
- Prevents premature integration of memory or tool surfaces.
- Improves testability by isolating prompt construction logic.

This aligns with IO-III's governance-first evolution model.

---

## 2. Decision

Introduce a **Context Assembly Layer** as a thin, deterministic module responsible solely for constructing the final prompt envelope prior to provider execution.

The Context Assembly Layer will:

1. Accept immutable inputs:
   - SessionState (v0)
   - Route resolution metadata
   - Persona contract payload
   - Explicit user prompt
2. Compose a single structured prompt envelope.
3. Return a final prompt payload for execution.

**Amendment — v1.1:** ADR-033 formally amends this record by introducing a fourth
input lane: file-derived content. The assembly order becomes:

1. Persona contract
2. Memory pack content
3. File content (ADR-033)
4. Direct prompt text

See ADR-033 for the full contract governing the file content lane, including token
budget, INV-006, and server restart coherence.

The layer will NOT:

- Perform retrieval
- Access persistent memory
- Invoke tools
- Modify routing decisions
- Introduce dynamic arbitration
- Execute recursive calls

It is a composition boundary, not a capability layer.

### Implementation sequence

1. Define SessionState v0 (structural only).
2. Extract execution engine from CLI.
3. Introduce Context Assembly Layer (definition and wiring).
4. Freeze.
5. Only then consider envelope sophistication.

This ADR defines the boundary only. It does not introduce behavioural changes.

---

## 3. Consequences

### Positive

- Clear separation of concerns.
- Reduced coupling between CLI, routing, and prompt logic.
- Foundation for structured envelope expansion (future phase).

### Neutral

- No behavioural change at introduction.
- No runtime surface expansion.

### Scope boundary

The following are deferred to later phases:

- Persistent memory systems
- Retrieval mechanisms
- Token pre-flight enforcement
- Capability gating logic
- Autonomous orchestration
- Multi-model arbitration

---

## 4. Non-goals

None declared.

---

## 6. Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-03-03 | Initial |
| v1.1 | 2026-05-29 | Cross-reference to ADR-033 added; ADR-033 amends this record by introducing a fourth context assembly input lane (file content) |