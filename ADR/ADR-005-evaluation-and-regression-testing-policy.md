---
id: ADR-005
title: Evaluation and Regression Testing Policy
type: adr
status: accepted
version: v1.0
canonical: true
scope: io-iii
audience: internal
created: "2026-01-09"
updated: "2026-05-29"
tags:
  - evaluation
  - regression-tests
  - quality
  - routing
  - governance
  - safety
roles_focus:
  - challenger
  - executor
  - governance
provenance: human
---

# ADR-005 | Evaluation and Regression Testing Policy

## Status

Accepted

---

## 1. Context

IO-III is a multi-mode, multi-model system whose quality depends on:
- deterministic routing (ADR-002),
- strict boundaries (ADR-004),
- observable behaviour (ADR-003),
- stable persona behaviour over time.

Because model outputs vary naturally, the repo requires a testing strategy that:
- detects **behaviour drift** without demanding identical text,
- enforces **invariants** (routing, safety, formatting rules),
- supports **local-first** workflows.

### Decision drivers

- Multi-model systems drift; invariants must remain stable.
- Quality varies; policies should detect degradation without blocking iteration.
- Portfolio-grade engineering favours explicit tests and traceable behaviour.

---

## 2. Decision

### §1 Two-layer evaluation: invariants + quality

IO-III evaluation is split into:

**Layer A — Invariant Regression Tests (must always pass)**
These tests assert rules that must not drift:
- routing selection and fallback triggers (ADR-002)
- cloud disablement / opt-in boundaries (ADR-004)
- logging defaults and retention configuration flags (ADR-003)
- "single-voice guarantee" (only one user-facing final output per cycle)
- role boundaries (e.g., Challenger is internal-only unless explicitly surfaced)

**Layer B — Quality Evaluation (monitored, not gatekeeping by default)**
These tests measure quality signals that may fluctuate:
- reasoning completeness
- factuality verification behaviour (when required)
- structure adherence
- tone/verbosity discipline
- refusal correctness and safety compliance

Layer B produces metrics and notes; it does not block commits unless explicitly configured as a release gate.

### §2 Test outputs are scored, not matched

Regression tests must avoid exact string matching except where required.
Prefer:
- schema validation (YAML, JSON)
- section presence checks
- regex-based constraints (e.g., headings, required fields)
- routing log inspection
- "must include citations" checks where policy requires

### §3 Test corpus is versioned and minimal

Maintain a small, curated test corpus:
- representative prompts per mode
- edge cases for safety and routing
- doc-generation prompts for YAML compliance

Add new tests when:
- a bug is found (test reproduces it),
- a policy is added (ADR introduces new invariant),
- a drift event occurs (lock in prevention).

### §4 Challenger as evaluator, not author

Challenger mode is designated as the primary evaluator:
- generates critiques, scores, and failure reasons
- does not directly publish user-facing responses
- feeds Synthesizer/Executor for final output

This preserves governance boundaries: evaluation ≠ delivery.

### §5 Gating policy (simple and enforceable)

- **Pre-commit / CI gate:** Layer A (invariants) only
- **Release gate (optional):** Layer A + selected Layer B thresholds

Default for solo work:
- gate only Layer A
- review Layer B periodically (weekly or per milestone)

### Implementation notes

Recommended structure (paths are suggestions, not mandated):
- Test cases: `./IO-III/tests/corpus/`
- Invariant tests: `./IO-III/tests/invariants/`
- Quality eval scripts: `./IO-III/tests/quality/`
- Results/logs (local-only): `./IO-III/runtime/logs/` (per ADR-003)

Recommended minimum invariant tests:
- ADR-002 routing table validation (mode → primary/secondary)
- fallback trigger simulation (timeout, 5xx, not found)
- cloud disabled unless explicit enable flag set
- "internal audience cannot route to cloud" check
- metadata logging schema presence

---

## 3. Consequences

### Positive

- Fast iteration without sacrificing core guarantees.
- Clear separation between "must not drift" and "should improve".
- Tests become living documentation of system behaviour.

### Trade-offs

- Requires deliberate selection of invariants.
- Some subjective quality regressions may slip through between reviews.
- Maintaining a corpus takes discipline (but stays small by design).

### Related

- `./ADR/ADR-002-model-routing-and-fallback-policy.md`
- `./ADR/ADR-003-telemetry-logging-and-retention-policy.md`
- `./ADR/ADR-004-cloud-provider-enablement-and-key-security.md`
- `./docs/governance/adr-policy.md`

---

## 4. Non-goals

None declared.

---

## 5. Options considered

### Option A — Exact-output snapshot testing
Rejected:
- brittle under model variability,
- produces noise,
- discourages iteration.

### Option B — No testing; rely on manual review
Rejected:
- increases drift risk,
- lowers confidence in ADR guarantees,
- not portfolio-grade.

### Option C — Invariant gating + quality monitoring (selected)
Accepted:
- stable guarantees,
- realistic under LLM variability,
- scalable as the repo grows.

---

## 6. Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-01-09 | Initial |