---
id: DOC-RUN-007
title: Example Run Output
type: runtime
status: draft
version: v1.0
canonical: pending
scope: io-iii
audience:
  - developer
  - maintainer
  - operator
created: "2026-10-29"
updated: "2026-10-29"
tags:
  - runtime
  - example
  - output
  - ollama
provenance:
  - human
  - Claude Sonnet 5.5
---

# Example Run Output

## Purpose

This document records two complete runs of the single-run command, exactly as the CLI printed them. The README shows a shortened copy of the second run. Nothing here has been edited, so the model's wording, including its mistakes, is the model's own.

---

## Setup

- Date: 2026-10-29.
- Provider and model: Ollama, `mistral:latest`, which is the model the `executor` mode routes to in `architecture/runtime/config/routing_table.yaml`. Ollama version 0.35.1, freshly installed on the day of the runs.
- Machine: a laptop with an NVIDIA GeForce RTX 2060 (6 GB). Inference ran on the GPU, as reported by the maintainer.
- Working directory: the repository root, using the project's virtual environment.
- One run of each prompt. Timings come from one machine and will vary.

---

## Run 1

```bash
python -m io_iii run executor --prompt "Explain deterministic routing in one sentence."
```

```json
{
  "logging_policy": {
    "schema": "io-iii-logging",
    "version": "v1.0",
    "storage": {
      "local_only": true,
      "metadata_log_dir": "./architecture/runtime/logs",
      "content_log_dir": "./architecture/runtime/logs/content"
    },
    "logging": {
      "metadata": {
        "enabled": true,
        "fields": [
          "timestamp",
          "request_id",
          "mode",
          "selected_primary",
          "fallback_used",
          "fallback_reason",
          "latency_ms",
          "token_counts",
          "error_code",
          "provider",
          "model",
          "routing_source"
        ],
        "retention_days": 30
      },
      "content": {
        "enabled": false,
        "retention_days": 7,
        "redaction": {
          "enabled": true,
          "patterns": [
            "api_keys",
            "env_vars",
            "secrets"
          ]
        }
      }
    },
    "safety": {
      "never_log": [
        "api_keys",
        "auth_headers",
        "env_vars"
      ]
    }
  },
  "result": {
    "message": "Deterministic routing refers to the process where the flow of data or instructions is controlled in a consistent and predictable manner, without self-routing or recursion loops.",
    "meta": {
      "persona_contract_version": "v0.1",
      "trace": {
        "schema": "io-iii-execution-trace",
        "schema_version": "v1.0",
        "trace_id": "1793294148951344074-141354",
        "started_at_ms": 1793294148963,
        "status": "completed",
        "stage_timings": {
          "context_assembly": 11,
          "provider_inference": 4675
        },
        "steps": [
          {
            "stage": "context_assembly",
            "started_at_ms": 1793294148963,
            "duration_ms": 11,
            "meta": {
              "persona_contract_version": "v0.1",
              "route_id": "executor"
            }
          },
          {
            "stage": "provider_inference",
            "started_at_ms": 1793294148975,
            "duration_ms": 4675,
            "meta": {
              "provider": "ollama",
              "model": "mistral:latest"
            }
          }
        ]
      },
      "telemetry": {
        "call_count": 1,
        "input_tokens": 609,
        "output_tokens": 37,
        "latency_ms": 4687,
        "model_used": "mistral:latest"
      },
      "engine_events": [
        {
          "kind": "engine_run_started",
          "timestamp_ms": 1793294148963,
          "request_id": "1793294148951344074-141354",
          "task_spec_id": null,
          "meta": {
            "mode": "executor",
            "provider": "ollama",
            "caller": "cli"
          }
        },
        {
          "kind": "route_resolved",
          "timestamp_ms": 1793294148963,
          "request_id": "1793294148951344074-141354",
          "task_spec_id": null,
          "meta": {
            "selected_provider": "ollama",
            "route_id": "executor",
            "fallback_used": false
          }
        },
        {
          "kind": "provider_execution_complete",
          "timestamp_ms": 1793294153650,
          "request_id": "1793294148951344074-141354",
          "task_spec_id": null,
          "meta": {
            "provider": "ollama",
            "model": "mistral:latest"
          }
        },
        {
          "kind": "output_emitted",
          "timestamp_ms": 1793294153650,
          "request_id": "1793294148951344074-141354",
          "task_spec_id": null,
          "meta": {
            "provider": "ollama",
            "model": "mistral:latest"
          }
        },
        {
          "kind": "engine_run_complete",
          "timestamp_ms": 1793294153650,
          "request_id": "1793294148951344074-141354",
          "task_spec_id": null,
          "meta": {
            "trace_step_count": 2
          }
        }
      ]
    },
    "mode": "executor",
    "provider": "ollama",
    "model": "mistral:latest",
    "route_id": "executor"
  },
  "audit_meta": null
}
```

---

## Run 2

```bash
python -m io_iii run executor --prompt "Summarise what a routing table does in one sentence."
```

```json
{
  "logging_policy": {
    "schema": "io-iii-logging",
    "version": "v1.0",
    "storage": {
      "local_only": true,
      "metadata_log_dir": "./architecture/runtime/logs",
      "content_log_dir": "./architecture/runtime/logs/content"
    },
    "logging": {
      "metadata": {
        "enabled": true,
        "fields": [
          "timestamp",
          "request_id",
          "mode",
          "selected_primary",
          "fallback_used",
          "fallback_reason",
          "latency_ms",
          "token_counts",
          "error_code",
          "provider",
          "model",
          "routing_source"
        ],
        "retention_days": 30
      },
      "content": {
        "enabled": false,
        "retention_days": 7,
        "redaction": {
          "enabled": true,
          "patterns": [
            "api_keys",
            "env_vars",
            "secrets"
          ]
        }
      }
    },
    "safety": {
      "never_log": [
        "api_keys",
        "auth_headers",
        "env_vars"
      ]
    }
  },
  "result": {
    "message": "A routing table is a data structure that outlines the pathwaysor routes for data traffic in a network or a program, detailing where information should be sent to reach its intended destination.",
    "meta": {
      "persona_contract_version": "v0.1",
      "trace": {
        "schema": "io-iii-execution-trace",
        "schema_version": "v1.0",
        "trace_id": "1793294294862724153-142964",
        "started_at_ms": 1793294294875,
        "status": "completed",
        "stage_timings": {
          "context_assembly": 19,
          "provider_inference": 1725
        },
        "steps": [
          {
            "stage": "context_assembly",
            "started_at_ms": 1793294294875,
            "duration_ms": 19,
            "meta": {
              "persona_contract_version": "v0.1",
              "route_id": "executor"
            }
          },
          {
            "stage": "provider_inference",
            "started_at_ms": 1793294294895,
            "duration_ms": 1725,
            "meta": {
              "provider": "ollama",
              "model": "mistral:latest"
            }
          }
        ]
      },
      "telemetry": {
        "call_count": 1,
        "input_tokens": 612,
        "output_tokens": 40,
        "latency_ms": 1746,
        "model_used": "mistral:latest"
      },
      "engine_events": [
        {
          "kind": "engine_run_started",
          "timestamp_ms": 1793294294875,
          "request_id": "1793294294862724153-142964",
          "task_spec_id": null,
          "meta": {
            "mode": "executor",
            "provider": "ollama",
            "caller": "cli"
          }
        },
        {
          "kind": "route_resolved",
          "timestamp_ms": 1793294294875,
          "request_id": "1793294294862724153-142964",
          "task_spec_id": null,
          "meta": {
            "selected_provider": "ollama",
            "route_id": "executor",
            "fallback_used": false
          }
        },
        {
          "kind": "provider_execution_complete",
          "timestamp_ms": 1793294296621,
          "request_id": "1793294294862724153-142964",
          "task_spec_id": null,
          "meta": {
            "provider": "ollama",
            "model": "mistral:latest"
          }
        },
        {
          "kind": "output_emitted",
          "timestamp_ms": 1793294296621,
          "request_id": "1793294294862724153-142964",
          "task_spec_id": null,
          "meta": {
            "provider": "ollama",
            "model": "mistral:latest"
          }
        },
        {
          "kind": "engine_run_complete",
          "timestamp_ms": 1793294296621,
          "request_id": "1793294294862724153-142964",
          "task_spec_id": null,
          "meta": {
            "trace_step_count": 2
          }
        }
      ]
    },
    "mode": "executor",
    "provider": "ollama",
    "model": "mistral:latest",
    "route_id": "executor"
  },
  "audit_meta": null
}
```

---

## Notes

- The `message` fields are the model's own text. Run 2 contains a missing space ("pathwaysor"), which is how the model wrote it.
- `input_tokens` is 609 and 612 although the prompts are one sentence. The rest is the system prompt the runtime assembles before the user's text.
- The logging policy block is printed before the result and is identical in both runs.
- Content logging is disabled in the policy (`content.enabled: false`), so prompts and completions are not written to the content log.

---

## Amendment record

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-10-29 | Initial |
