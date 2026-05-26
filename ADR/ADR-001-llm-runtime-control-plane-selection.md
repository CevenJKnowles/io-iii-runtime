---
id: "ADR-001"
title: "LLM Runtime Control Plane Selection"
type: "adr"
status: "ammended"
version: "v1.1"
canonical: true
scope: "io-iii"
audience: "internal"
created: "2026-01-09"
updated: "2026-05-26"
tags:
  - "llm-runtime"
  - "control-plane"
  - "routing"
  - "local-llm"
  - "api-compatibility"
roles_focus:
  - "executor"
  - "synthesizer"
  - "governance"
provenance: "human" 
amendment date: "2026-05-26" 
reason: "LiteLLM was not implemented. Provider adapter layer supersedes the two-layer model." 
superseded_by:
  - "ADR-002"
  - "ADR-012"
  - "ADR-028"

---

# ADR-001 | LLM Runtime Control Plane Selection

**⚠ Amendment notice — v1.1 — 2026-05-26** This ADR has been amended. The decision recorded below (LiteLLM as control plane) was not implemented. The original decision is preserved as a historical record. See the **Amendment** section at the end of this document for the full account of what was built instead and why.

## Context

IO‑III requires a **single, stable control plane** to route prompts across multiple model backends while keeping:
- **portable interfaces** (OpenAI-compatible where possible),
- **swap‑ability** (models/providers can change without rewriting app logic),
- **local-first execution** (run on laptop hardware by default),
- **observable behavior** (logging, rate limits, routing rules),
- **future expansion** (cloud models, eval harnesses, guardrails).

The repo already separates **architecture**, **implementation**, and **governance** documents, and ADRs are treated as canonical decisions that prevent silent divergence.

## Decision

Adopt a **two-layer runtime**:

1. **Ollama** as the **local model runtime** (model hosting + local inference).
2. **LiteLLM** as the **control plane / router** (single API endpoint, provider abstraction, routing, retries, logging hooks).

The IO‑III application targets **LiteLLM’s OpenAI‑compatible endpoint** as the primary integration surface.

## Decision Drivers

- **Interface stability:** OpenAI-compatible surface minimizes integration churn.
- **Provider abstraction:** Easy to add/remove local + cloud providers.
- **Routing support:** Central place for “mode → model” mapping and fallbacks.
- **Operational clarity:** One endpoint for clients; one place for logs + policies.
- **Local-first:** Ollama supports laptop-friendly local inference.

## Options Considered

### A) Direct-to-Ollama (no control plane)
**Pros**
- Minimal moving parts
- Fast to start

**Cons**
- Harder multi-provider routing
- App becomes tightly coupled to a single runtime API
- No clean, central policy layer

### B) LiteLLM-only (without Ollama)
**Pros**
- Strong abstraction + routing
- Clean endpoint for IO‑III

**Cons**
- Still needs actual local runtime for local inference
- You end up choosing a runtime anyway

### C) vLLM / TGI / llama.cpp as runtime (instead of Ollama)
**Pros**
- Potentially higher throughput / advanced serving options

**Cons**
- Higher setup complexity on a laptop
- More ops overhead than necessary for current phase

### D) LangChain/LangGraph as “control plane”
**Pros**
- Rich agent/tooling ecosystem

**Cons**
- Not a control plane per se; still need runtime + provider abstraction
- Risk of framework lock-in at this stage

## Consequences

### Positive
- IO‑III can standardize on **one client interface** (OpenAI-like).
- Routing rules become a **config-level concern** (not app rewrites).
- Easier to integrate:
  - evaluation harnesses,
  - usage logging,
  - fallback logic,
  - guardrails/policies.

### Negative / Tradeoffs
- More components to maintain (Ollama + LiteLLM).
- Debugging spans layers (client → LiteLLM → Ollama/provider).
- Needs a disciplined config strategy to avoid “routing drift”.

## Implementation Notes

### Baseline contract
- **Client code** calls LiteLLM (OpenAI-compatible).
- LiteLLM routes to:
  - **Ollama** for local models by default,
  - optional cloud providers when explicitly enabled.

### Configuration strategy (recommended)
- Keep a single routing config file (e.g., `IO-III/runtime/litellm.yaml`)
- Store mode routing table in the same config or an adjacent canonical file.
- Add a lightweight health check:
  - `GET /health` for LiteLLM
  - verify Ollama is reachable and at least one model is loaded

### Logging & privacy
- Default to **local logs only**.
- If cloud models are enabled, ensure prompts marked “internal” remain local unless explicitly overridden.

## Related

- `docs/architecture/io-iii-llm-architecture.md`
- `IO-III/strategy/` (routing & persona binding notes)
- Future ADRs:
  - ADR-002: Model routing table & fallback policy
  - ADR-003: Telemetry/logging policy and retention
  - ADR-004: Security posture for cloud provider keys

---
## Amendment — v1.1 — 2026-05-26

### What happened

LiteLLM was not implemented. The two-layer runtime (Ollama + LiteLLM) described in the decision above was the intended architecture at the time ADR-001 was written. As implementation progressed through Phases 1–10, the control plane and routing functions that LiteLLM was intended to supply were absorbed directly into the engine layer of IO-III. No LiteLLM dependency was introduced. No LiteLLM configuration file was created. The codebase contains no reference to LiteLLM outside this ADR and one early architecture document (DOC-ARCH-001, updated 2026-03-03).

### What was built instead

The runtime is governed by a direct provider adapter layer:

* **`ollama_provider.py`** — the live local model adapter; the only fully implemented provider in the Phase 10 release.
* **`openai_provider.py`** and **`anthropic_provider.py`** — stub adapters introduced in Phase 10 (ADR-028), implementing the provider protocol at the interface level only. Both raise `NotImplementedError` at instantiation. Cloud provider implementation is deferred to Phase 11.
* **`null_provider.py`** — test and fallback surface.

Routing logic, fallback policy, and mode-to-model mapping are governed directly by ADR-002 (model routing and fallback policy) and enforced through the engine layer (ADR-012, bounded orchestration layer contract). There is no intermediate routing middleware.

### Why this was not recorded sooner

The divergence from the ADR-001 decision accumulated silently across Phases 1–10 as the architecture evolved toward a leaner, more direct provider abstraction. No phase checkpoint triggered a formal review of ADR-001's status. This amendment constitutes that review and closes the gap between the written record and the implemented architecture.

### Governing ADRs for the implemented design

|  Concern |  ADR |
|---|---|
|  Mode-driven routing and fallback policy |  ADR-002 |
|  Bounded orchestration layer contract |  ADR-012 |
|  Provider adapter completion and cloud opt-in |  ADR-028 |
|  Cloud provider enablement and key security |  ADR-004 |

### Status of the original decision

The original decision (LiteLLM as control plane) is preserved as a historical record. It reflects the architectural reasoning at Phase 1 and the options considered at that time. The reasoning remains sound; the implementation took a different path. This ADR's status is amended, not superseded: the context and decision drivers remain valid reference material for any future contributor evaluating control plane options.