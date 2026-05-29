---
id: ADR-009
title: Audit Gate Contract
type: adr
status: active
version: v1.0
canonical: true
scope: io-iii
audience: internal
created: "2026-02-27"
updated: "2026-05-29"
tags:
  - governance
  - adr
  - audit
  - challenger
roles_focus:
  - governance
provenance: human
---

# ADR-009 | Audit Gate Contract v1.0

## Status

Active

---

## 1. Context

IO-III v0.2 implements a one-pass audit gate using a Challenger model to review Executor output.

The audit system is currently:
- CLI controlled (`--audit`)
- Single-pass
- Returning `audit_meta` in structured JSON
- Producing unified final output only

As the system expands, the audit gate becomes the primary structural hinge where recursion, drift, and control-plane sprawl could emerge.

This ADR freezes the audit contract to prevent architectural instability.

### Rationale

The audit gate is the only structural re-entry point in the execution pipeline.

Freezing its behaviour:

- Prevents recursion loops
- Prevents runaway revision chains
- Preserves deterministic routing
- Stabilises the control plane before expansion

This establishes IO-III as governance-first and expansion-ready.

---

## 2. Decision

The Audit Gate Contract is formally defined and frozen as follows:

### §1 Pass limits (hard constraints)

- `max_audit_passes = 1`
- `max_revision_passes = 1`
- No additional chained review cycles allowed

These limits must be enforced at framework level, not by convention.

### §2 Audit input contract

Audit receives:
```
{
  prompt,
  executor_output,
  constraints,
  policies
}
```

Audit does NOT receive:
- Router configuration
- System state mutations
- Memory layer access
- Tool invocation permissions

### §3 Audit output contract

Audit must return:
```
{
  final_output,
  audit_meta
}
```

Where:

- `final_output` = single user-facing output (unified)
- `audit_meta` = structured JSON (machine-readable)

No additional output streams are allowed.

### §4 Explicit prohibitions

Audit is NOT permitted to:

- Trigger routing decisions
- Modify routing policies
- Invoke external tools
- Perform fact-verification calls
- Write to persistent memory
- Trigger additional audits
- Initiate recursive execution

Audit is strictly evaluative and bounded revision.

### §5 Determinism requirement

Audit behaviour must remain deterministic under identical inputs and policies.

No stochastic routing or multi-agent arbitration is allowed at this layer.

---

## 3. Consequences

### Positive

- Clear architectural boundary
- Reduced drift risk
- Safer future integration of:
  - Memory layer
  - Persona injection
  - Fact verification module

### Trade-offs

- No multi-pass self-improvement cycles
- No dynamic adaptive arbitration at audit layer

These trade-offs are intentional for v0.x stabilisation.

---

## 4. Non-goals

- Adjustable audit intensity levels
- Conditional auto-audit policy
- Verification gate module
- Steward-mode memory writes

These require separate ADRs.

---

## 6. Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-02-27 | Initial |