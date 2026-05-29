---
id: DOC-ARCH-019
title: Phase 11 Guide | Cloud Adapters, OpenAI Compatibility, and RAG Boundary
type: architecture
status: draft
version: v0.1
canonical: true
scope: phase-11
audience:
  - developer
  - maintainer
  - operator
created: "2026-05-29"
updated: "2026-05-29"
tags:
  - io-iii
  - phase-11
  - architecture
  - cloud-providers
  - openai-compat
  - rag
  - file-upload
roles_focus:
  - executor
  - governance
provenance: io-iii-runtime-development
---

# Phase 11 Guide | Cloud Adapters, OpenAI Compatibility, and RAG Boundary

## Status

Draft

---

## Purpose

This document is the governing stub for Phase 11. It records the scope inherited
from Phase 10 gate ADRs and establishes the prerequisite conditions for Phase 11
planning to begin. It is not a milestone plan. That plan is written when Phase 11
opens, under the ADR-first rule.

No Phase 11 work begins without this document being promoted from `draft` to
`accepted` and all governing ADRs confirmed as accepted.

---

## Phase Prerequisite

Phase 11 depends on Phase 10 being complete and tagged `v1.0.0`.

Before Phase 11 planning begins, the following must be confirmed:

- `v1.0.0` tagged and repository public.
- All Phase 10 ADRs (ADR-027 through ADR-034) in `accepted` or `amended` status.
- This document promoted to `accepted` with a milestone plan replacing the scope
  section below.
- At minimum one new ADR accepted before any implementation begins (ADR-first rule).

---

## Invariants That Must Remain True

All Phase 1–10 invariants are preserved throughout Phase 11 without exception.

- Deterministic routing (ADR-002)
- Bounded execution: max 1 audit pass, max 1 revision pass (ADR-009)
- Content-safe output across all surfaces (ADR-003, ADR-025, ADR-026)
- No autonomous behaviour, no dynamic routing, no recursive execution
- ADR-first development for all structural additions
- `engine.py`, `routing.py`, and `telemetry.py` unchanged

---

## Scope Inherited from Phase 10

The following items were explicitly deferred to Phase 11 by accepted Phase 10 ADRs.
Each entry names the governing ADR and the relevant section.

### Cloud provider adapter implementations

**Gate ADR:** ADR-028 §3

Phase 10 introduced stub adapters for OpenAI and Anthropic that raise
`NotImplementedError` with a roadmap message. Phase 11 implements real adapter
modules for OpenAI and Anthropic (Option C as defined in ADR-028). Google is
explicitly out of scope for Phase 10 and Phase 11 (ADR-028 §3). The stub modules
introduced in Phase 10 satisfy the provider protocol contract; Phase 11 replaces
their bodies with working implementations.

A dedicated ADR is required before any cloud adapter implementation begins
(ADR-028 §3 explicit requirement).

### OpenAI-compatible transport endpoint

**Gate ADR:** ADR-030 §1

Phase 11 introduces `POST /v1/chat/completions` as a transport adapter endpoint
mapping the OpenAI Chat Completions request shape to the existing IO-III session
and engine layer. This is a transport adapter only, following ADR-025 and ADR-030.
It does not introduce new execution semantics or bypass governance.

Minimum supported fields: `model`, `messages`, `stream`. The `model` field maps
to IO-III routing modes via a configurable translation table in `runtime.yaml`.
Unsupported fields return a structured error. `content_release: true` must be set
in `runtime.yaml` for the endpoint to surface model output (ADR-026).

Implementation is paired with cloud adapter delivery (ADR-028): shipping the
compatibility endpoint with a working cloud provider backend maximises adoption
value. The Phase 11 plan must address this dependency explicitly.

### Server-side file upload extensions

**Gate ADR:** ADR-029 §8

Phase 10 delivers the core server-side file upload pipeline (Option B: `POST /upload`,
`file_store.py`, `file_ref` context injection). Phase 11 may extend this contract to
support additional file types, persistent file storage across server restarts (which
would require amending ADR-033 §5 and §7), and integration with the RAG retrieval
layer if introduced.

OCR is explicitly out of scope for Phase 10 and Phase 11 (ADR-029 §8).

Any extension to the file upload contract requires an ADR amending ADR-029 and,
where the context assembly contract changes, ADR-033.

### Knowledge extension via RAG

**Gate ADR:** ADR-031

ADR-031 is accepted with implementation deferred to Phase 11. It establishes the
architecture boundary for retrieval-augmented generation: a fifth context assembly
input lane (corpus-indexed, cross-session retrieval content), distinct from the
file content lane (session-scoped, user-uploaded) introduced in ADR-033.

Phase 11 RAG implementation requires a new ADR governing the retrieval adapter
interface, the new context assembly lane, and new invariant contracts. ADR-031
is the gate document; the implementation ADR is written in Phase 11 planning.

Memory packs (ADR-022) remain the primary knowledge injection mechanism. Retrieval
is an additional lane, not a replacement.

---

## What Phase 11 Must Not Do

- Modify `engine.py`, `routing.py`, or `telemetry.py`.
- Introduce autonomous behaviour, dynamic routing, or recursive execution.
- Begin implementation before this document is promoted from `draft` to `accepted`.
- Begin any workstream without a corresponding accepted ADR.

---

## Relationship to Phase 10 ADRs

| ADR | Title | Phase 11 role |
|-----|-------|---------------|
| ADR-028 | Provider Adapter Completion and Cloud Opt-In | Gate for cloud adapter implementation |
| ADR-029 | File Upload Input Surface Contract | Gate for file upload extensions |
| ADR-030 | Cloud LLM API Transport Adapter | Gate for OpenAI-compat endpoint |
| ADR-031 | Knowledge Extension and RAG Architecture Boundary | Gate for RAG implementation |

---

*Phase 11 governing stub. Promoted to accepted when Phase 11 planning begins.*