---
id: ADR-008
title: Challenger Enforcement Layer
type: adr
status: active
version: v1.0
canonical: true
scope: io-iii
audience: internal
created: "2026-02-26"
updated: "2026-05-29"
tags:
  - governance
  - adr
  - challenger
  - audit
roles_focus:
  - governance
provenance: human
---

# ADR-008 | Challenger Enforcement Layer (Audit + Gate)

Related: ADR-009 — Audit Gate Contract v1.0
Scope: IO-III Runtime Execution Path (`run` command)

## Status

Active

---

## 1. Context

IO-III currently performs deterministic single-pass execution:

User Prompt → Executor (LLM) → Structured Output

This architecture produces functional results but lacks:

- Systematic compliance verification
- Structured factual risk detection
- Drift detection
- Boundary enforcement

To increase reliability and production readiness, a Challenger Enforcement Layer is introduced.

### Rationale

- Improves reliability without architectural explosion.
- Preserves deterministic bounded execution.
- Maintains clear separation of roles:
  - Executor = generative
  - Challenger = compliance enforcement
- Avoids uncontrolled self-refinement loops.

---

## 2. Decision

IO-III will implement a two-stage execution model:

Executor → Challenger → (Optional Revision) → Final Output

### §1 Challenger role

The Challenger:

- Audits executor output
- Checks for:
  - Policy compliance
  - Boundary violations
  - Factual risk
  - Unverifiable claims
  - Internal contradictions
  - Missing verification steps
- MUST NOT introduce new facts
- MUST NOT rewrite the draft
- MUST produce structured JSON audit output

### §2 Enforcement model

If Challenger verdict == "pass":
    → Executor draft is returned unchanged.

If Challenger verdict == "needs_work":
    → Executor receives:
        - Original prompt
        - Original draft
        - Challenger structured audit
    → Executor performs one revision pass.
    → Revised output becomes final output.

### §3 Loop policy

- Maximum: 1 revision pass.
- No recursive critique loops.
- Deterministic bounded execution.

### §4 Activation policy

Initial implementation:
- Enabled via CLI flag: `--audit`

Future possibility:
- Default enabled in production mode.

### §5 Determinism and governance

- No new facts may be introduced during revision.
- Challenger must reference executor draft only.
- Revision must preserve original user intent.
- If Challenger fails (error/unavailable), executor result is returned unchanged.

---

## 3. Consequences

### Positive
- Higher output integrity
- Reduced hallucination risk
- Clear enforcement boundary

### Trade-offs
- Increased latency
- Higher compute cost
- Additional implementation complexity

### Performance impact

Adds:
- +1 LLM call (audit)
- +1 optional LLM call (revision)

Worst case: 3 total model invocations per run.

---

## 4. Non-goals

- Multi-stage challenger scoring
- Cross-model adversarial audit
- Memory-aware challenger
- Auto-citation insertion

---

## 6. Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-02-26 | Initial |