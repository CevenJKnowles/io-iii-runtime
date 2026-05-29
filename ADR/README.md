---
id: ADR-000
title: README | ADR
type: adr
status: accepted
version: v1.0
canonical: true
scope: io-iii
audience:
  - developer
  - maintainer
  - operator
created: "2026-01-09"
updated: "2026-05-29"
tags:
  - governance
  - adr
roles_focus:
  - governance
provenance: human
---

# Architecture Decision Records (ADR)

This directory contains **canonical architecture and governance decisions**
for the I0³ runtime repository.

ADRs capture decisions that would otherwise cause silent divergence between
architecture, implementation, and documentation. No structural change may be
implemented without a corresponding accepted ADR.

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `draft` | Being written; not yet in force |
| `accepted` | Adopted and currently governing behaviour |
| `amended` | Governing current behaviour; one or more decisions revised — see Amendment record |
| `superseded` | Replaced entirely by a later ADR; no longer governing |

## Index

- **ADR-001 — LLM Runtime Control Plane Selection**
  Path: `./ADR/ADR-001-llm-runtime-control-plane-selection.md`
  Status: amended (v1.1 — LiteLLM not implemented; provider adapter layer built instead)

- **ADR-002 — Model Routing and Fallback Policy**
  Path: `./ADR/ADR-002-model-routing-and-fallback-policy.md`

- **ADR-003 — Telemetry, Logging, and Retention Policy**
  Path: `./ADR/ADR-003-telemetry-logging-and-retention-policy.md`

- **ADR-004 — Cloud Provider Enablement and Key Security**
  Path: `./ADR/ADR-004-cloud-provider-enablement-and-key-security.md`

- **ADR-005 — Evaluation and Regression Testing Policy**
  Path: `./ADR/ADR-005-evaluation-and-regression-testing-policy.md`

- **ADR-006 — Persona Binding and Mode Governance**
  Path: `./ADR/ADR-006-persona-binding-and-mode-governance.md`
  Status: amended (v1.1 — identity and user profile surfaces added, Phase 10)

- **ADR-007 — Memory, Persistence, and Drift Control**
  Path: `./ADR/ADR-007-memory-persistence-and-drift-control.md`

- **ADR-008 — Challenger Enforcement Layer**
  Path: `./ADR/ADR-008-challenger-enforcement-layer.md`

- **ADR-009 — Audit Gate Contract**
  Path: `./ADR/ADR-009-audit-gate-contract-v1.0.md`

- **ADR-010 — Context Assembly Layer Definition**
  Path: `./ADR/ADR-010-context-assembly-layer-definition.md`

- **ADR-011 — Provider Health Check Policy**
  Path: `./ADR/ADR-011-provider-health-check-policy.md`

- **ADR-012 — Bounded Orchestration Layer Contract**
  Path: `./ADR/ADR-012-bounded-orchestration-layer-contract.md`

- **ADR-013 — Deterministic Failure Semantics**
  Path: `./ADR/ADR-013-deterministic-failure-semantics.md`

- **ADR-014 — Bounded Runbook Layer Contract**
  Path: `./ADR/ADR-014-bounded-runbook-layer-contract.md`

- **ADR-015 — Runbook Traceability and Metadata Correlation**
  Path: `./ADR/ADR-015-runbook-traceability-and-metadata-correlation.md`

- **ADR-016 — CLI Runbook Execution Surface**
  Path: `./ADR/ADR-016-cli-runbook-execution-surface.md`

- **ADR-017 — Replay/Resume Boundary Definition**
  Path: `./ADR/ADR-017-replay-resume-boundary-definition.md`

- **ADR-018 — Run Identity Contract**
  Path: `./ADR/ADR-018-run-identity-contract.md`

- **ADR-019 — Checkpoint Persistence Contract**
  Path: `./ADR/ADR-019-checkpoint-persistence-contract.md`

- **ADR-020 — Replay/Resume Execution Contract**
  Path: `./ADR/ADR-020-replay-resume-execution-contract.md`

- **ADR-021 — Runtime Observability and Optimisation Contract**
  Path: `./ADR/ADR-021-runtime-observability-optimisation.md`

- **ADR-022 — Memory Architecture Contract**
  Path: `./ADR/ADR-022-memory-architecture-contract.md`

- **ADR-023 — Open-Source Initialisation Contract**
  Path: `./ADR/ADR-023-open-source-initialisation-contract.md`
  Status: amended (v1.1 — user_profile.yaml added to config surface, Phase 10)

- **ADR-024 — Work Mode / Steward Mode Contract**
  Path: `./ADR/ADR-024-work-mode-steward-mode-contract.md`

- **ADR-025 — API-as-Transport-Adapter Contract**
  Path: `./ADR/ADR-025-api-transport-adapter-contract.md`

- **ADR-026 — Governed Content Release Gate**
  Path: `./ADR/ADR-026-governed-content-release-gate.md`

- **ADR-027 — Project Identity and Rename Contract**
  Path: `./ADR/ADR-027-project-identity-rename-contract.md`

- **ADR-028 — Provider Adapter Completion and Cloud Opt-In Contract**
  Path: `./ADR/ADR-028-provider-adapter-completion-cloud-opt-in.md`

- **ADR-029 — File Upload Input Surface Contract**
  Path: `./ADR/ADR-029-file-upload-input-surface-contract.md`

- **ADR-030 — Cloud LLM API Transport Adapter**
  Path: `./ADR/ADR-030-cloud-llm-api-transport-adapter.md`
  Status: amended (v1.1 — generalised from OpenAI-specific to all cloud LLMs, Phase 10)

- **ADR-031 — Knowledge Extension and RAG Architecture Boundary**
  Path: `./ADR/ADR-031-knowledge-extension-rag-architecture-boundary.md`

- **ADR-032 — Container Deployment Surface Contract**
  Path: `./ADR/ADR-032-container-deployment-surface-contract.md`

- **ADR-033 — Context Assembly Extension — File Input Lane**
  Path: `./ADR/ADR-033-context-assembly-extension-file-input-lane.md`
  Status: amended (v1.1 — file injection point is dialogue_session.py:run_turn(), not context_assembly.py — frozen core constraint)

- **ADR-034 — API and Integration Surface — Transport Adapter Contract**
  Path: `./ADR/ADR-034-api-integration-surface.md`