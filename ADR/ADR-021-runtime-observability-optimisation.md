---
id: ADR-021
title: Runtime Observability and Optimisation Contract
type: adr
status: accepted
version: v1.0
canonical: true
scope: io-iii-phase-5
audience:
  - developer
  - maintainer
created: "2026-04-11"
updated: "2026-04-11"
tags:
  - io-iii
  - adr
  - phase-5
  - observability
  - telemetry
  - token-estimation
  - constellation
roles_focus:
  - executor
  - challenger
  - governance
provenance: io-iii-runtime-development
milestone: M5.0
---

# ADR-021 — Runtime Observability and Optimisation Contract

## Status

Accepted

---

## Context

Phase 4 is complete. The replay/resume layer (ADR-020, M4.11) is implemented and
tested. The repository is tagged `v0.4.0`.

The execution stack is frozen at the M4.11 boundary. No modification to the routing
layer (ADR-002), the audit gate (ADR-009), the bounded runbook runner (ADR-014), the
context assembly layer (ADR-010), or the replay/resume layer (ADR-020) is permitted
by this ADR or any milestone it governs.

Phase 5 introduces measurement and governance signals that operate *alongside* the
frozen execution stack without expanding it. Three capabilities are introduced:

1. **Token pre-flight estimation** — a bounded check before every provider call that
   prevents oversized context from reaching the model. This is a prerequisite for Phase 6
   memory injection (M6.4).
2. **Execution telemetry metrics** — structured, content-safe performance fields attached
   to execution results and projected to `metadata.jsonl`.
3. **Constellation integrity guard** — a config-time validation pass that detects
   architecture drift before execution, ensuring distinct roles are not silently mapped
   to the same model and that call chain configurations respect bounded execution limits.

---

## Decision

IO-III introduces three governed observability capabilities under the Phase 5 freeze
boundary. All three operate within the existing execution path without extending it.
No new execution surfaces, no persistent session state, no autonomous behaviour, and
no dynamic routing are introduced by this ADR or any milestone it governs.

---

## 1. Governance Freeze Boundary

### 1.1 Frozen surface

The following components are frozen for the duration of Phase 5. No Phase 5 milestone
may modify them:

- `io_iii/routing.py` — routing resolution logic
- `io_iii/core/engine.py` — execution engine
- `io_iii/core/context_assembly.py` — context assembly layer
- `io_iii/core/runbook.py` — runbook definition
- `io_iii/core/runbook_runner.py` — bounded runner
- `io_iii/core/replay_resume.py` — replay/resume execution layer
- All ADR-002, ADR-008, ADR-009, ADR-014, ADR-016, ADR-017, ADR-020 contracts

### 1.2 Permissible surfaces

Phase 5 milestones may add to or read from:

- `io_iii/core/execution_context.py` — to attach telemetry and memory fields (read-only
  by observability; new fields may be added to the dataclass)
- `io_iii/core/session_state.py` — to attach telemetry projection fields (read-only by
  observability; new content-safe fields may be added)
- `io_iii/providers/ollama_provider.py` — to surface token usage fields already present
  in Ollama API responses (`prompt_eval_count`, `eval_count`)
- `io_iii/cli.py` — to invoke the constellation guard at startup; no new execution
  subcommands introduced
- `architecture/runtime/config/` — to introduce configurable limits and constellation
  validation rules

---

## 2. Token Pre-flight Estimator (M5.1)

### 2.1 Purpose

The estimator prevents oversized context calls from reaching the provider. It enforces
thin prompt discipline at the execution boundary and provides the token-budget mechanism
required by Phase 6 M6.4 (memory injection via context assembly).

### 2.2 Estimation method

Estimation is heuristic-based: character count divided by a configurable characters-per-token
approximation. No tokenizer library dependency is introduced. The estimator is deliberately
approximate — its purpose is to enforce a pre-execution budget bound, not to produce an
exact token count.

### 2.3 Invocation point

The estimator runs after context assembly and before the provider call. It is not invoked
during replay/resume checkpoint resolution or during challenger audit steps.

### 2.4 Configuration

The context limit ceiling is declared in runtime configuration. No hardcoded ceiling is
permitted. The configuration key is:

```text
runtime.context_limit_chars
```

If absent, the estimator falls back to a documented safe default. The default must be
declared in the config schema documentation, not embedded in code as a magic number.

### 2.5 Failure contract

If the estimated context size exceeds the configured limit, the estimator raises a
`RuntimeFailure` under `ADR-013`:

| Field | Value |
|---|---|
| `kind` | `contract_violation` |
| `code` | `CONTEXT_LIMIT_EXCEEDED` |
| `retryable` | `False` |
| `summary` | estimated character count and configured limit — no prompt content |

No prompt text, model output, or context content appears in any failure field. The
failure surfaces at the CLI as a stable JSON object with exit code `1`.

### 2.6 Cross-phase dependency

This milestone is a **prerequisite for Phase 6 M6.4** (memory injection via context
assembly). Memory injection adds tokens to the context window. Without a pre-flight
bound, injected memory subsets cannot be safely constrained to the available context
budget. Phase 6 M6.4 must not begin until M5.1 is implemented and tested.

---

## 3. Execution Telemetry Metrics (M5.2)

### 3.1 Structure

Telemetry fields are attached to `ExecutionResult.meta` under the key `"telemetry"`.
The value is an `ExecutionMetrics` dataclass. This follows the existing pattern of
`ExecutionResult.meta["capability"]`.

`SessionState` remains a control-plane state container. Telemetry fields are not added
to `SessionState` directly — they are projected from `ExecutionMetrics` to the
`metadata.jsonl` log sink.

### 3.2 Fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `call_count` | `int` | engine | number of provider calls in the execution |
| `input_tokens` | `int` | estimator (M5.1) | estimated input token count |
| `output_tokens` | `int \| None` | provider response | populated if provider returns it; `None` otherwise |
| `latency_ms` | `int` | engine timing | total execution duration in milliseconds |
| `model_used` | `str` | routing | resolved model identifier |

### 3.3 Ollama token fields

The Ollama `/api/generate` response body includes `prompt_eval_count` (input tokens) and
`eval_count` (output tokens). The current `OllamaProvider.generate()` method discards
these fields. M5.2 surfaces them: `prompt_eval_count` maps to `output_tokens`
(post-generation eval count) and `eval_count` maps to the generation output token count.

The canonical mapping is:

```text
ollama response.prompt_eval_count → ExecutionMetrics.input_tokens (provider-confirmed)
ollama response.eval_count        → ExecutionMetrics.output_tokens
```

Where Ollama confirms an input token count, it takes precedence over the M5.1 heuristic
estimate within the telemetry record. The M5.1 estimator still runs as a pre-flight
check regardless — the provider-confirmed count is a post-hoc telemetry field, not a
gating mechanism.

### 3.4 Content safety

All telemetry fields are counts or durations. No prompt text, model output, context
content, or memory values appear in any field. The `ExecutionMetrics` object is
content-safe by construction: it carries only numeric and identifier fields.

Projection to `metadata.jsonl` follows the ADR-003 content safety policy. The
`"telemetry"` key is whitelisted as a safe metadata namespace.

### 3.5 Best-effort fields

`output_tokens` is `None` when the provider does not return a token count (e.g., when
using the null provider or a provider that does not surface usage). Missing fields do
not constitute failures.

---

## 4. Constellation Integrity Guard (M5.3)

### 4.1 Purpose

The constellation guard detects architecture drift in the model constellation at
config-time. It enforces that distinct roles are not silently mapped to the same model,
and that call chain configurations respect the bounded execution limits established by
ADR-009 and ADR-014.

The model constellation for IO-III is:

```text
Executor (user-facing)
  → Specialist LLMs (delegated tasks, where declared)
  → Challenger (adversarial review)
  → Executor (final output decision)
  → User
```

Collapsing Executor and Challenger onto the same model defeats the adversarial review
guarantee. The guard makes this collapse a hard, detectable failure rather than a
silent misconfiguration.

### 4.2 Invocation point

The guard runs at CLI startup after config load and before routing resolution. It does
not run during individual execution steps. It consumes the config layer only — no
runtime state, no provider calls, no model inference.

### 4.3 Checks

The following checks are performed:

1. **Role-model collapse** — executor and challenger must not resolve to the same model
   identifier. If they do, raise `CONSTELLATION_DRIFT`.
2. **Required role bindings** — any role declared in the runtime config must have a
   non-empty model binding. Missing or empty bindings raise `CONSTELLATION_DRIFT`.
3. **Call chain bounds** — if a runbook step count is statically knowable from config,
   validate it does not exceed `RUNBOOK_MAX_STEPS` (ADR-014). Raise
   `CONSTELLATION_DRIFT` if violated.

Additional checks may be introduced in subsequent milestones via configuration schema
extensions. New checks must not modify this ADR — they extend the guard implementation
only.

### 4.4 Failure contract

Guard failures raise a `RuntimeFailure` under ADR-013:

| Field | Value |
|---|---|
| `kind` | `contract_violation` |
| `code` | `CONSTELLATION_DRIFT` |
| `retryable` | `False` |
| `summary` | human-readable description of the specific drift detected — no model output |

The failure surfaces at the CLI as a stable JSON object with exit code `1`.

### 4.5 Bypass flag

The guard is bypassable via `--no-constellation-check` for offline or CI use cases
where config is intentionally incomplete. The bypass must be explicitly declared in the
CLI invocation. It is not a persistent config option.

When bypassed, the CLI emits a structured warning to stderr (not to `metadata.jsonl`):

```text
WARN: constellation integrity check bypassed via --no-constellation-check
```

No silent bypass is permitted.

---

## 5. New Failure Codes

This ADR extends the ADR-013 failure taxonomy with two new codes under the
`contract_violation` kind:

| Code | Condition |
|---|---|
| `CONTEXT_LIMIT_EXCEEDED` | Estimated context size exceeds configured limit (M5.1) |
| `CONSTELLATION_DRIFT` | Model constellation integrity check failed (M5.3) |

Both codes are `retryable = False`. Both are content-safe: no prompt, output, or
context content appears in any failure field.

---

## 6. Explicit Non-Goals

### Not in scope for this ADR

- Python implementation of M5.1, M5.2, or M5.3
- Tests
- New CLI subcommands beyond `--no-constellation-check`
- Output-driven routing or branching based on telemetry signals
- Autonomous retry or remediation behaviour
- Persistent session state or cross-run history
- Memory systems or retrieval mechanisms
- Dynamic routing based on telemetry signals
- Adaptive execution or self-tuning behaviour

### Out of scope permanently for Phase 5

- Phase 6 memory injection (M6.4) — dependent on M5.1 but not introduced in Phase 5
- Phase 7 portability layer
- Any modification to ADR-002, ADR-008, ADR-009, ADR-014, or ADR-020

---

## 7. Scope Boundary

This ADR covers:

- the Phase 5 governance freeze boundary and permissible surfaces (§1)
- the token pre-flight estimator contract: method, invocation, config, failure codes,
  and cross-phase dependency (§2)
- the execution telemetry metrics contract: structure, fields, Ollama mapping, and
  content safety (§3)
- the constellation integrity guard contract: purpose, invocation, checks, failure
  codes, and bypass (§4)
- new failure codes extending ADR-013 (§5)

This ADR does **not** cover:

- implementation of any milestone
- Phase 6 or Phase 7 contracts
- any modification to the frozen execution stack

---

## 8. Relationship to Other ADRs

- **ADR-002** — routing. Frozen. Constellation guard reads routing config but does not
  modify routing logic.
- **ADR-003** — content safety. Telemetry fields and failure summaries must comply in
  full. No prompt, output, or context content in any field.
- **ADR-009** — audit gate contract. Frozen. Bounded execution constraints are validated
  by the constellation guard, not modified.
- **ADR-010** — context assembly layer. Frozen. The token estimator runs after context
  assembly completes — it reads the assembled context size, does not modify assembly.
- **ADR-013** — failure semantics. Extended by §5 with two new `contract_violation`
  codes. All existing failure contracts unchanged.
- **ADR-014** — bounded runbook layer contract. Frozen. `RUNBOOK_MAX_STEPS` is consumed
  by the constellation guard as a read-only bound.
- **ADR-020** — replay/resume execution contract. Frozen. Phase 5 observability applies
  to replay/resume runs identically to first-run executions.

---

## 9. Consequences

### Positive

- M5.1 is now implementation-safe and unblocks Phase 6 M6.4.
- M5.2 surfaces Ollama token counts already present in API responses but previously
  discarded, at no additional provider cost.
- M5.3 converts silent model constellation misconfiguration into a hard, detectable
  failure at startup — before any execution occurs.
- All three capabilities operate alongside the frozen execution stack without modifying
  it. Phase 1–4 invariants are preserved in full.
- The new failure codes (`CONTEXT_LIMIT_EXCEEDED`, `CONSTELLATION_DRIFT`) extend
  ADR-013 without modifying existing codes.

### Negative

- The M5.1 heuristic estimator will occasionally over-estimate token counts (character
  count is conservative). This is acceptable: the estimator's purpose is to prevent
  genuine overruns, not to maximise context utilisation.
- The bypass flag (`--no-constellation-check`) is a safety valve that could be misused
  to suppress legitimate drift warnings. It is explicitly a CLI-only, per-invocation
  mechanism — not a persistent config option.

### Neutral

- This ADR produces no code, no tests, and no changes to any existing runtime surface.

---

## Decision Summary

IO-III introduces three governed observability capabilities under Phase 5. A heuristic
token pre-flight estimator enforces context limits before every provider call and blocks
Phase 6 memory injection until it is active. Structured execution telemetry fields are
attached to `ExecutionResult.meta["telemetry"]` as an `ExecutionMetrics` dataclass and
projected content-safely to `metadata.jsonl`; Ollama's native token counts
(`prompt_eval_count`, `eval_count`) are surfaced where available. A constellation
integrity guard runs at CLI startup to detect role-model collapse and call chain
violations before execution begins. Two new failure codes (`CONTEXT_LIMIT_EXCEEDED`,
`CONSTELLATION_DRIFT`) extend the ADR-013 taxonomy under `contract_violation`. The
frozen Phase 1–4 execution stack is not modified.