---
id: ADR-003
title: Telemetry, Logging, and Retention Policy
type: adr
status: amended
version: v1.1
canonical: true
scope: io-iii
audience: internal
created: "2026-01-09"
updated: "2026-05-29"
tags:
  - telemetry
  - logging
  - retention
  - privacy
  - observability
roles_focus:
  - governance
  - executor
  - challenger
provenance: human
---

# ADR-003 | Telemetry, Logging, and Retention Policy

## Status

Amended

---

## 1. Context

IO-III routes requests across multiple model backends via a control plane.
Routing and fallback are only trustworthy if the system is observable.
At the same time, IO-III is local-first and must minimise data exposure.

This ADR defines what is logged, where it is stored, how long it is retained,
and what must never be logged by default.

### Decision drivers

- Observability is required for routing determinism and regression tests.
- Local-first posture reduces privacy risk and accidental leakage.
- Content logs create disproportionate risk vs benefit in steady-state.

---

## 2. Decision

### §1 Local-first logging only (default)

By default, IO-III logs are stored **locally on disk** only.
No external telemetry is enabled unless explicitly configured.

### §2 Two-tier logging: metadata vs content

**Tier A — Metadata logs (default ON)**
Log operational metadata needed for debugging and regression testing:
- timestamp
- request id
- mode
- selected primary model
- fallback used (yes/no)
- fallback reason (enum)
- latency (ms)
- token counts (if available)
- error codes (if any)

**Tier B — Content logs (default OFF)**
Prompt/response content logging is OFF by default.
It can be enabled only for targeted debugging sessions.

### §3 Redaction and secret hygiene

When any content logging is enabled:
- redact API keys / secrets
- redact filesystem paths that contain usernames (optional but recommended)
- redact environment variables by default

### §4 Retention policy (default)

- Metadata logs retained for: **30 days**
- Content logs retained for: **7 days** (only if enabled)
- Manual "debug sessions" should be time-boxed and disabled immediately after use

### §5 Cloud boundary rule

If cloud providers are enabled:
- internal docs and "internal" audience prompts stay local unless explicitly overridden
- cloud calls must be opt-in per provider and auditable in logs (metadata tier)

---

## 3. Consequences

### Positive
- Debuggability without content exposure
- Clear privacy defaults
- Supports regression testing and routing audits

### Trade-offs
- Harder to diagnose "quality" issues without temporary content logging
- Requires discipline to avoid leaving debug content logging on

### Implementation notes

Implemented in Phase 3 (M3.8, M3.12):

- Log schema version: `io-iii-metadata-jsonl v1.0` (set as default in `metadata_logging.py`)
- Metadata log location: `./architecture/runtime/logs/metadata.jsonl` (JSONL format)
- Content-safe guard: recursive forbidden-key scan via `assert_no_forbidden_keys()` in `core/content_safety.py`
- Configuration: `architecture/runtime/config/logging.yaml` (canonical, references this ADR)
- Retention enforcement is policy-only at this stage; log rotation is not automated

### Related

- `./ADR/ADR-001-llm-runtime-control-plane-selection.md`
- `./ADR/ADR-002-model-routing-and-fallback-policy.md`
- `./docs/architecture/io-iii-llm-architecture.md`
- `./docs/governance/adr-policy.md`

---

## 4. Non-goals

None declared.

---

## 5. Options considered

### Option A — Log everything by default
Rejected (privacy and noise).

### Option B — No logging by default
Rejected (breaks debuggability and undermines routing/ADR guarantees).

### Option C — Metadata logging by default + content logging opt-in (selected)
Accepted (balanced, testable, low-risk).

---

## 6. Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-01-09 | Initial |
| v1.1 | 2026-05-29 | Cross-reference to ADR-034 added; ADR-034 §4 extends content-safety invariants to all HTTP response bodies and webhook payloads |