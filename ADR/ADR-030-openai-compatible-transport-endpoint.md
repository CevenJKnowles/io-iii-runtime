---
id: ADR-030
title: OpenAI-Compatible Transport Endpoint
type: adr
status: accepted
version: v1.0
canonical: true
scope: io-iii-phase-10
audience:
  - developer
  - maintainer
  - operator
created: "2026-05-01"
updated: "2026-05-01"
tags:
  - io-iii
  - adr
  - phase-10
  - phase-11
  - api
  - openai-compat
  - transport
  - governance
roles_focus:
  - executor
  - governance
provenance: io-iii-runtime-development
milestone: M10.0
---

# ADR-030 — OpenAI-Compatible Transport Endpoint

## Status

Accepted — implementation deferred to Phase 11. This ADR is a gate document written
in Phase 10 to govern Phase 11 implementation. No code is produced under this ADR
in Phase 10.

---

## 1. Context

The Phase 9 HTTP API exposes Io³-native endpoints (`POST /run`, `POST /session/start`,
etc.). Users and organisations already using the OpenAI Python SDK or any OpenAI-API-
compatible client cannot point their existing code at Io³ without rewriting their API
calls to the Io³ request shape.

A `POST /v1/chat/completions` endpoint that mimics the OpenAI Chat Completions API
surface would allow drop-in adoption: existing client code, tooling, and integrations
can target Io³ without modification. This is the most direct path to broad adoption
for teams already invested in the OpenAI ecosystem.

The endpoint is architecturally viable as a transport adapter only. The execution
semantics, governance invariants, and content safety rules established in Phases 1–9
are not affected by the shape of the incoming request. The OpenAI request format is
translated into the existing Io³ session and engine pipeline at the API boundary.

The implementation is deferred to Phase 11 because it pairs naturally with cloud
provider adapter delivery (ADR-028 Phase 11, Option C). Shipping the compatibility
endpoint in Phase 10 without a real cloud provider backend would require users to
already have Ollama configured — limiting the adoption benefit. Phase 11 delivers
both simultaneously: an operator can point an OpenAI client at Io³ backed by either
Ollama or a real OpenAI adapter.

---

## 2. Decision

### §1 Phase 11 implementation scope

Phase 11 introduces `POST /v1/chat/completions` as a transport adapter endpoint in
the Phase 9 API layer. The endpoint:

- Translates the OpenAI `messages` array into an assembled prompt string
- Maps the `model` field to an Io³ routing mode via `openai_compat_model_map` in
  `runtime.yaml`
- Routes the request through the existing session and engine layer
- Returns a response in OpenAI Chat Completions response shape

The endpoint is a transport adapter only. It does not introduce new execution
semantics, bypass governance invariants, or duplicate engine logic at the HTTP layer.
ADR-025 (API-as-Transport-Adapter Contract) governs this endpoint in full.

### §2 Supported OpenAI fields

The following fields are supported in Phase 11:

- `model` — mapped to routing mode via `openai_compat_model_map`
- `messages` — assembled into a structured prompt string
- `stream` — boolean; when true, response is streamed via the existing SSE layer

All other OpenAI request fields are rejected with a structured error:
`{"error": {"type": "unsupported_field", "message": "..."}}`

Silent ignore of unsupported fields is explicitly prohibited.

### §3 Model mapping

A new `openai_compat_model_map` key in `runtime.yaml` maps OpenAI model strings to
Io³ routing modes. Example:

```yaml
openai_compat_model_map:
  gpt-4o: executor
  gpt-3.5-turbo: fast
  default: executor
```

If no mapping is found and no `default` is set, the request is rejected with:
`{"error": {"type": "model_not_mapped", "message": "..."}}`.

### §4 Content release requirement

`content_release: true` must be set in `runtime.yaml` for the endpoint to surface
model output in the response body. ADR-026 governs content release. The operator
accepts responsibility for API access control and log retention when enabling this.

### §5 Phase 10 posture

No implementation occurs in Phase 10. The Phase 9 API is not modified. No stub
endpoint is added. The `openai_compat_model_map` key is not added to `runtime.yaml`
in Phase 10.

### §6 Phase 11 gate conditions

Phase 11 implementation of this endpoint may not begin until:

- Phase 10 is complete and tagged `v1.0.0`
- ADR-028 Phase 11 cloud provider adapters are in progress or complete
- A Phase 11 ADR supplements this record with streaming contract details if the
  SSE response shape for OpenAI-format streaming diverges from the existing M9.2
  SSE contract

---

## 3. Consequences

- No code change in Phase 10.
- Phase 11 planning has a clear contract to implement against.
- The transport adapter constraint (ADR-025) is explicitly extended to cover this
  endpoint, preventing future drift toward execution semantics at the HTTP layer.

---

## 4. Non-goals

- This ADR does not implement function calling, tool use, or assistants API compatibility.
- This ADR does not implement the OpenAI embeddings, fine-tuning, or completions
  (legacy) endpoints.
- This ADR does not implement vision or multimodal input.
- This ADR does not modify the execution engine, routing layer, or telemetry.