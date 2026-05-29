---
id: DOC-GOV-001
title: ADR Policy
type: governance
status: active
version: v1.1
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
  - executor
provenance: human
---

# ADR Policy

## Purpose

ADRs (Architecture Decision Records) capture decisions that would otherwise cause silent divergence between architecture, implementation, and documentation. No structural change may be implemented without a corresponding accepted ADR. This is the ADR-first rule.

---

## Rules

**Rule 1 — ADR before implementation.** Create and accept an ADR before implementing or documenting any change that affects the following: LLM runtime stack, serving, or control plane; routing rules (mode → model), fallbacks, or retry strategy; safety posture, logging, telemetry, or privacy boundaries; persona binding, mode governance, or regression test policy; any change that alters the meaning of a canonical architecture document or modifies a frozen module.

**Rule 2 — Frozen core.** The following modules must never be modified: `routing.py`, `engine.py`, `telemetry.py`. Any ADR that appears to require modification of these modules must find an alternative implementation path and document it explicitly.

**Rule 3 — No silent edits.** Once an ADR reaches `accepted` status, its decisions may not be quietly reworded. If a decision changes, increment the version, add an amendment record entry, and document the change in the body.

**Rule 4 — Supersession requires a new ADR.** If an accepted ADR is fully replaced, create a new ADR, mark the old one `superseded`, and add a reference to the new ADR in the old file's body.

---

## Status lifecycle

| Status | Meaning |
|--------|---------|
| `draft` | Being written; not yet in force |
| `accepted` | Adopted and currently governing behaviour |
| `amended` | Governing current behaviour; one or more decisions revised — see Amendment record |
| `superseded` | Replaced entirely by a later ADR; no longer governing |

---

## File naming and location

ADRs live in `./ADR/`. Filename pattern: `ADR-NNN-kebab-case-title.md` where NNN is a three-digit zero-padded incrementing number. Version strings must not appear in filenames.

---

## Canonical ADR structure

Every ADR must follow this section structure exactly. Sections marked optional may be omitted if not applicable; all others are required.

```
---
id: ADR-NNN
title: Short Descriptive Title
type: adr
status: accepted
version: v1.0
canonical: true
scope: io-iii-phase-N
audience:
  - developer
  - maintainer
  - operator
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
tags:
  - io-iii
  - adr
  - phase-N
  - relevant-tag
milestone: MN.N              (optional)
subordinate_to: ADR-NNN      (optional)
amends: ADR-NNN              (optional)
provenance: io-iii-runtime-development
---

# ADR-NNN — Short Descriptive Title

## Status

Accepted

---

## 1. Context

## 2. Decision

### §1 First decision clause
### §2 Second decision clause

---

## 3. Consequences

---

## 4. Non-goals

---

## 5. Options considered    (optional)

### Option A — Name
### Option B — Name

---

## 6. Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | YYYY-MM-DD | Initial |
```

**Frontmatter rules:**

All scalar values are unquoted. Date strings (`created`, `updated`) are quoted. Audience, tags, and roles_focus are always lists. `subordinate_to` and `amends` are omitted when not applicable — do not leave them empty. `milestone` is omitted for cross-phase ADRs.

**Section rules:**

`### Decision drivers` is a subsection under `## 1. Context`, not a top-level section. `### Rationale` is likewise a subsection under `## 1. Context`. Decision subsections use `§` notation (`### §1`, `### §2`). `### Implementation notes` and `### Related` are subsections under `## 3. Consequences`. `## 5. Options considered` is optional and present only when the choice was non-obvious or contested.

---

## Enforcement

Compliance is verified by the ADR README index (`ADR/README.md`), which must be updated whenever a new ADR is added or an existing ADR changes status. The index is the authoritative list of all ADRs and their current status.

---

## Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-01-09 | Initial |
| v1.1 | 2026-05-29 | Added canonical ADR structure template, frontmatter rules, section rules, frozen core rule, status vocabulary table. Aligned to H0 hardening standards. |