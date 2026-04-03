---
id: DOC-RUN-006
title: IO-III Engine Observability Model (M4.5)
type: runtime
status: active
version: v1.0
canonical: true
scope: io-iii
audience: engineers
created: "2026-04-03"
updated: "2026-04-03"
tags:
  - runtime
  - observability
  - engine
  - events
  - m4.5
roles_focus:
  - executor
provenance: human
---

# IO-III Engine Observability Model (M4.5)

---

## Purpose

This document defines the **engine lifecycle event model** introduced in Phase 4 M4.5.

Engine events provide structured, content-safe observability at coarser lifecycle
boundaries than the per-step `ExecutionTrace`. They are the primary mechanism for
inspecting which engine path executed and for linking engine runs back to the
upstream `TaskSpec` or CLI invocation.

---

## Scope

Covers:

- `io_iii/core/engine_observability.py` — event types and accumulator
- `io_iii/core/engine.py` — emission points
- `ExecutionResult.meta["engine_events"]` — serialised output

Does not cover:

- `ExecutionTrace` / `stage_timings` (see DOC-RUN-005)
- metadata JSONL logging (see DOC-RUN-003)
- capability meta (see DOC-RUN-004)

---

## Design Principles

1. **Content-safe** — event meta must never contain prompt text, completion text, or
   model output. Enforced by `assert_no_forbidden_keys` at emit time.

2. **Bounded** — at most 16 events per engine run. Overflow raises `RuntimeError`
   with code `OBSERVABILITY_LOG_CAPACITY`.

3. **Engine-internal** — `EngineObservabilityLog` is created inside `engine.run()`,
   following the same pattern as `TraceRecorder`. Not injected via `RuntimeDependencies`.

4. **Lifecycle-ordered** — events are stored and serialised in emission order
   (insertion order = lifecycle order). Consumers must not sort or reorder.

5. **Optional-event discipline** — only events on the active execution path are emitted.
   `challenger_audit_complete` and `revision_complete` are absent, not null, when not
   applicable.

---

## Event Record: EngineEvent

```
kind          : str        — EngineEventKind value (stable string identifier)
timestamp_ms  : int        — epoch ms at emission
request_id    : str        — session linkage (equals SessionState.request_id)
task_spec_id  : str | null — upstream TaskSpec binding; null for CLI paths
meta          : object     — small structural dict (see per-kind fields below)
```

---

## Event Kinds

| Kind | Constant | Emitted when |
|---|---|---|
| `engine_run_started` | `RUN_STARTED` | Entry into `engine.run()` |
| `route_resolved` | `ROUTE_RESOLVED` | Routing snapshot confirmed from `SessionState` |
| `provider_execution_complete` | `PROVIDER_EXECUTION_COMPLETE` | Provider delivered its result |
| `challenger_audit_complete` | `CHALLENGER_AUDIT_COMPLETE` | Challenger verdict received (`audit=True` only) |
| `revision_complete` | `REVISION_COMPLETE` | Controlled revision applied (`needs_work` path only) |
| `output_emitted` | `OUTPUT_EMITTED` | `ExecutionResult` constructed; about to return |
| `engine_run_complete` | `RUN_COMPLETE` | `engine.run()` returning; trace terminal |

---

## Per-kind meta fields

### engine_run_started

| Field | Type | Description |
|---|---|---|
| `mode` | string | Execution mode from `SessionState.mode` |
| `provider` | string | Provider from `SessionState.provider` |
| `caller` | string | `"orchestrator"` if `task_spec_id` is set; `"cli"` otherwise |

### route_resolved

| Field | Type | Description |
|---|---|---|
| `selected_provider` | string | Confirmed provider |
| `route_id` | string | Resolved route identifier |
| `fallback_used` | boolean | Whether fallback routing was applied |

### provider_execution_complete

| Field | Type | Description |
|---|---|---|
| `provider` | string | Provider that executed (`"null"` or `"ollama"`) |
| `model` | string or null | Resolved model; null for null provider |

### challenger_audit_complete

| Field | Type | Description |
|---|---|---|
| `verdict` | string or null | Challenger verdict (`"pass"`, `"needs_work"`, or null) |
| `audit_passes` | integer | Audit pass counter at completion |

### revision_complete

| Field | Type | Description |
|---|---|---|
| `revision_passes` | integer | Revision pass counter at completion |

### output_emitted

| Field | Type | Description |
|---|---|---|
| `provider` | string | Provider on the result path |
| `model` | string or null | Model on the result path; null for null provider |

### engine_run_complete

| Field | Type | Description |
|---|---|---|
| `trace_step_count` | integer | Number of steps in the completed `ExecutionTrace` |

---

## Canonical event sequences

### Null provider, no audit (5 events)

```
engine_run_started
route_resolved
provider_execution_complete
output_emitted
engine_run_complete
```

### Ollama provider, no audit (5 events)

```
engine_run_started
route_resolved
provider_execution_complete
output_emitted
engine_run_complete
```

### Ollama provider, audit=True, verdict=pass (6 events)

```
engine_run_started
route_resolved
provider_execution_complete
challenger_audit_complete
output_emitted
engine_run_complete
```

### Ollama provider, audit=True, verdict=needs_work (7 events)

```
engine_run_started
route_resolved
provider_execution_complete
challenger_audit_complete
revision_complete
output_emitted
engine_run_complete
```

---

## Serialised output

Engine events are attached to `ExecutionResult.meta["engine_events"]` as a JSON array.

```json
{
  "engine_events": [
    {
      "kind": "engine_run_started",
      "timestamp_ms": 1743678000000,
      "request_id": "1743678000000000-12345",
      "task_spec_id": null,
      "meta": {
        "mode": "executor",
        "provider": "null",
        "caller": "cli"
      }
    },
    {
      "kind": "route_resolved",
      "timestamp_ms": 1743678000001,
      "request_id": "1743678000000000-12345",
      "task_spec_id": null,
      "meta": {
        "selected_provider": "null",
        "route_id": "executor",
        "fallback_used": false
      }
    },
    {
      "kind": "provider_execution_complete",
      "timestamp_ms": 1743678000002,
      "request_id": "1743678000000000-12345",
      "task_spec_id": null,
      "meta": {"provider": "null", "model": null}
    },
    {
      "kind": "output_emitted",
      "timestamp_ms": 1743678000003,
      "request_id": "1743678000000000-12345",
      "task_spec_id": null,
      "meta": {"provider": "null", "model": null}
    },
    {
      "kind": "engine_run_complete",
      "timestamp_ms": 1743678000004,
      "request_id": "1743678000000000-12345",
      "task_spec_id": null,
      "meta": {"trace_step_count": 1}
    }
  ]
}
```

---

## task_spec_id propagation

`task_spec_id` is the binding reference from `SessionState.task_spec_id`.

- When `engine.run()` is called from the orchestrator, `task_spec_id` carries the
  `TaskSpec.task_spec_id` of the upstream spec.
- When called from the CLI directly, `task_spec_id` is `null`.
- The value is the identifier only — the TaskSpec payload is never stored in events.

---

## Relationship to ExecutionTrace

| Concern | ExecutionTrace / stage_timings | Engine events |
|---|---|---|
| Granularity | Per execution step (fine) | Per lifecycle boundary (coarse) |
| Timing | `perf_counter_ns` duration per step | Epoch ms timestamp at emission |
| Location | `meta["trace"]` | `meta["engine_events"]` |
| Session linkage | `trace_id` (equals `request_id`) | `request_id` + `task_spec_id` |
| Conditional events | No (all stages recorded) | Yes (audit/revision absent when inactive) |

---

## CLI metadata log integration

`cli.py` reads `len(meta["engine_events"])` and logs it as `engine_event_count` in the
metadata JSONL record. This is a structural count only — no event content is logged.

---

## Bounds contract

- Maximum events per run: `_MAX_EVENTS = 16` (defined in `engine_observability.py`).
- Overflow raises `RuntimeError("OBSERVABILITY_LOG_CAPACITY: ...")`.
- Current maximum canonical path is 7 events (full audit + revision).
- Remaining headroom: 9 events for future single-milestone additions.

---

## Acceptance Criteria

M4.5 is complete when:

1. `engine_events` is present in `ExecutionResult.meta` for all execution paths.
2. Event ordering is deterministic and matches canonical sequences above.
3. `task_spec_id` propagates correctly from orchestrator path; is `null` on CLI path.
4. No forbidden content key appears in any event or its `meta`.
5. `engine_event_count` is logged in CLI metadata JSONL.
6. Existing `ExecutionTrace` / `stage_timings` contracts are unaffected.
7. `SessionState.latency_ms` remains total-only; no per-stage timing added to state.