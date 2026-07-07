# Delibra Core Model v0.1

```text
Delibra never reasons. Models reason.
Delibra orchestrates the production, transformation, and composition of artifacts.

A Protocol is an ordered set of artifact derivations.
Each StepDefinition declares which artifact outputs it consumes and which typed artifact output it produces.

Every step produces one or more typed artifacts.
Artifacts are the only durable outputs of deliberation steps.

Delibra is artifact-first.
Steps are derivation functions.
Runs are durable records of artifact derivation.
Trace is the event stream of derivation.
```

## 1. Scope

This document defines the durable MVP core model only.

Core durable:

```text
Protocol
Role
StepDefinition
Produces
Run
Artifact
Trace
TraceEvent
```

Engine ephemeral:

```text
ExecutionContext
StepExecution
Message
```

Out of core v0.1:

```text
Claim
Evidence
Critique
Decision
Message
```

`critique`, `review`, `synthesis`, and `framing` may exist as artifact `kind` values, but they are not core entities.

## 2. Core Entities

### Protocol

A static definition of artifact derivations.

Fields:

```text
id
version
description
roles
steps
```

Reasons:

- `id`: stable protocol identifier.
- `version`: records which protocol version a run used.
- `description`: human-readable inspection text.
- `roles`: named lenses used by steps.
- `steps`: ordered derivation definitions.

### Role

A declarative analysis lens.

Fields:

```text
id
name
instruction
```

Reasons:

- `id`: referenced by steps and artifacts.
- `name`: readable label.
- `instruction`: role-level instruction, not a provider-ready prompt.

### StepDefinition

A static derivation operation.

Fields:

```text
id
kind
role
roles
instruction
inputs
produces
```

Reasons:

- `id`: identifies the operation.
- `kind`: selects one MVP primitive.
- `role`: single role for `prompt` and `synthesize`.
- `roles`: multiple roles for `fanout` and `criticize`.
- `instruction`: step-level instruction.
- `inputs`: logical artifact outputs consumed by the step.
- `produces`: logical artifact output and structural artifact kind.

### Produces

Declares the logical value produced by a step.

Fields:

```text
output
kind
```

Reasons:

- `output`: logical value name, referenced by later `inputs`.
- `kind`: structural artifact kind produced under that output.

Important distinction:

```text
step.id = operation identity
produces.output = logical value identity
```

Example:

```yaml
- id: role_reviews
  kind: fanout
  roles: [maintainer, tester, security]
  inputs: [framing]
  produces:
    output: reviews
    kind: review
```

`kind` is structural, not business-domain specific.

Good MVP kinds:

```text
framing
review
critique
synthesis
```

Avoid:

```text
architecture_review
security_review
legal_review
```

Those belong in roles, instructions, and presets.

### Run

A durable record of one protocol execution.

Fields:

```text
id
protocol
status
input
artifacts
trace_id
started_at
completed_at
```

`completed_at` is optional because a run may still be running.

### Artifact

The durable output of a step.

Fields:

```text
id
kind
output
producer_step_id
producer_role_id
payload
metadata
created_at
```

Reasons:

- `id`: unique artifact id in the run.
- `kind`: structural type from `produces.kind`.
- `output`: logical output bucket from `produces.output`.
- `producer_step_id`: operation that created it.
- `producer_role_id`: role that created it.
- `payload`: opaque JSON object.
- `metadata`: non-semantic execution metadata.
- `created_at`: creation timestamp.

The core validates shape and references. It does not interpret `payload`.

### Trace

An event stream for a run.

Fields:

```text
id
run_id
events
```

### TraceEvent

A typed fact emitted during execution.

Fields:

```text
id
type
timestamp
run_id
step_id
payload
```

`step_id` is optional because run-level events do not belong to a step.

## 3. Enums

### StepKind

```text
prompt
fanout
criticize
synthesize
```

No other primitives in v0.1.

### RunStatus

```text
created
validated
running
completed
failed
cancelled
```

### TraceEventType

```text
RunCreated
RunValidated
RunStarted
StepStarted
MessageSent
MessageReceived
ArtifactCreated
StepCompleted
StepFailed
RunCompleted
RunFailed
RunCancelled
```

`MessageSent` and `MessageReceived` may reference `message_id` in payload, but `Message` is not a core durable entity.

## 4. Validation Rules

Protocol validation:

- `id` is required and non-empty.
- `version` is required and non-empty.
- `roles` is non-empty.
- `steps` is non-empty.
- role ids are unique.
- step ids are unique.
- `produces.output` values are unique.
- every `kind` is one of `prompt`, `fanout`, `criticize`, `synthesize`.
- every role reference exists.
- every `inputs` entry is either `user_input` or a previous `produces.output`.
- an input cannot reference a future output.
- every step has `instruction`.
- every step has `produces.output`.
- every step has `produces.kind`.
- unknown fields are rejected in v0.1.

Primitive validation:

`prompt`

- requires `role`;
- forbids `roles`;
- produces exactly one artifact.

`fanout`

- requires non-empty `roles`;
- forbids `role`;
- produces one artifact per role under the same output.

`criticize`

- requires non-empty `roles`;
- forbids `role`;
- produces one artifact per role under the same output.

`synthesize`

- requires `role`;
- forbids `roles`;
- should be the final step in v0.1;
- produces exactly one artifact.

Artifact validation:

- `id` unique within run.
- `kind` equals producer step `produces.kind`.
- `output` equals producer step `produces.output`.
- `producer_step_id` references an existing step.
- `producer_role_id` references an existing role.
- `payload` is a JSON object.
- `created_at` is present.

Trace validation:

- event ids are unique.
- event types are known.
- event `run_id` matches trace `run_id`.
- event `step_id`, when present, references an existing step.
- event payload is a JSON object.

## 5. Immutability

- A validated `Protocol` does not change during a run.
- `StepDefinition` objects are immutable during a run.
- `Artifact` objects are immutable after creation.
- `TraceEvent` is append-only.
- Existing trace events are never modified.
- Existing artifacts are never modified.
- Terminal runs cannot return to `running`.
- Failure does not create a failure artifact; failure creates trace events.

## 6. JSON Schemas

Canonical `Protocol` JSON:

```json
{
  "id": "code_review",
  "version": "0.1.0",
  "description": "Structured code review protocol.",
  "roles": {
    "framer": {
      "id": "framer",
      "name": "Framer",
      "instruction": "Restate scope and missing context."
    }
  },
  "steps": [
    {
      "id": "frame",
      "kind": "prompt",
      "role": "framer",
      "roles": null,
      "instruction": "Frame the input.",
      "inputs": ["user_input"],
      "produces": {
        "output": "framing",
        "kind": "framing"
      }
    }
  ]
}
```

Canonical `Run` JSON:

```json
{
  "id": "run_0001",
  "protocol": {
    "id": "code_review",
    "version": "0.1.0"
  },
  "status": "completed",
  "input": {
    "kind": "file",
    "source": "pr.diff",
    "hash": "sha256:abc123"
  },
  "artifacts": [],
  "trace_id": "trace_0001",
  "started_at": "2026-07-07T10:00:00Z",
  "completed_at": "2026-07-07T10:00:21Z"
}
```

Canonical `Artifact` JSON:

```json
{
  "id": "artifact_0001",
  "kind": "framing",
  "output": "framing",
  "producer_step_id": "frame",
  "producer_role_id": "framer",
  "payload": {
    "content": "The input describes a request validation change."
  },
  "metadata": {
    "model": "gpt-5-mini",
    "finish_reason": "stop"
  },
  "created_at": "2026-07-07T10:00:05Z"
}
```

Canonical `Trace` JSON:

```json
{
  "id": "trace_0001",
  "run_id": "run_0001",
  "events": []
}
```

Canonical `TraceEvent` JSON:

```json
{
  "id": "evt_0001",
  "type": "ArtifactCreated",
  "timestamp": "2026-07-07T10:00:05Z",
  "run_id": "run_0001",
  "step_id": "frame",
  "payload": {
    "artifact_id": "artifact_0001",
    "output": "framing",
    "kind": "framing",
    "producer_role_id": "framer"
  }
}
```

## 7. Complete Protocol YAML

```yaml
id: code_review
version: 0.1.0
description: Structured code review protocol.

roles:
  framer:
    name: Framer
    instruction: >
      Restate the input, identify scope, assumptions, and missing context.

  maintainer:
    name: Maintainer
    instruction: >
      Review maintainability, readability, API shape, and consistency.

  tester:
    name: Tester
    instruction: >
      Review test coverage, edge cases, regressions, and observability.

  security:
    name: Security Reviewer
    instruction: >
      Review security risks, permissions, data exposure, and unsafe behavior.

  synthesizer:
    name: Synthesizer
    instruction: >
      Produce a concise final synthesis from the artifacts.

steps:
  - id: frame
    kind: prompt
    role: framer
    instruction: >
      Frame the input. Do not invent missing context.
    inputs:
      - user_input
    produces:
      output: framing
      kind: framing

  - id: role_reviews
    kind: fanout
    roles:
      - maintainer
      - tester
      - security
    instruction: >
      Review the framed input from your role. Be concise and actionable.
    inputs:
      - framing
    produces:
      output: reviews
      kind: review

  - id: cross_critique
    kind: criticize
    roles:
      - maintainer
      - tester
      - security
    instruction: >
      Critique the review artifacts. Identify weak claims, missed risks,
      contradictions, or unsupported recommendations.
    inputs:
      - reviews
    produces:
      output: critiques
      kind: critique

  - id: final
    kind: synthesize
    role: synthesizer
    instruction: >
      Synthesize prior artifacts into a final review.
      Preserve important uncertainty.
    inputs:
      - framing
      - reviews
      - critiques
    produces:
      output: final_synthesis
      kind: synthesis
```

## 8. Successful Run JSON

```json
{
  "id": "run_0001",
  "protocol": {
    "id": "code_review",
    "version": "0.1.0"
  },
  "status": "completed",
  "input": {
    "kind": "file",
    "source": "pr.diff",
    "hash": "sha256:abc123"
  },
  "artifacts": [
    {
      "id": "artifact_0001",
      "kind": "framing",
      "output": "framing",
      "producer_step_id": "frame",
      "producer_role_id": "framer",
      "payload": {
        "content": "The input appears to describe a request validation change."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:05Z"
    },
    {
      "id": "artifact_0002",
      "kind": "review",
      "output": "reviews",
      "producer_step_id": "role_reviews",
      "producer_role_id": "maintainer",
      "payload": {
        "content": "The change is readable, but validation behavior should be documented if externally visible."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:08Z"
    },
    {
      "id": "artifact_0003",
      "kind": "review",
      "output": "reviews",
      "producer_step_id": "role_reviews",
      "producer_role_id": "tester",
      "payload": {
        "content": "Tests should cover invalid input, boundary values, and regression behavior."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:10Z"
    },
    {
      "id": "artifact_0004",
      "kind": "review",
      "output": "reviews",
      "producer_step_id": "role_reviews",
      "producer_role_id": "security",
      "payload": {
        "content": "Error messages should not expose internal values or sensitive request details."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:12Z"
    },
    {
      "id": "artifact_0005",
      "kind": "critique",
      "output": "critiques",
      "producer_step_id": "cross_critique",
      "producer_role_id": "maintainer",
      "payload": {
        "content": "The tester review should distinguish missing tests from unknown existing coverage."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:15Z"
    },
    {
      "id": "artifact_0006",
      "kind": "critique",
      "output": "critiques",
      "producer_step_id": "cross_critique",
      "producer_role_id": "tester",
      "payload": {
        "content": "The maintainer review assumes documentation requirements not shown in the input."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:16Z"
    },
    {
      "id": "artifact_0007",
      "kind": "critique",
      "output": "critiques",
      "producer_step_id": "cross_critique",
      "producer_role_id": "security",
      "payload": {
        "content": "The reviews should explicitly check whether validation errors include sensitive values."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:17Z"
    },
    {
      "id": "artifact_0008",
      "kind": "synthesis",
      "output": "final_synthesis",
      "producer_step_id": "final",
      "producer_role_id": "synthesizer",
      "payload": {
        "content": "Final review: add boundary tests, verify error message safety, and document externally visible validation behavior."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T10:00:20Z"
    }
  ],
  "trace_id": "trace_0001",
  "started_at": "2026-07-07T10:00:00Z",
  "completed_at": "2026-07-07T10:00:21Z"
}
```

## 9. Trace JSON

```json
{
  "id": "trace_0001",
  "run_id": "run_0001",
  "events": [
    {
      "id": "evt_0001",
      "type": "RunCreated",
      "timestamp": "2026-07-07T10:00:00Z",
      "run_id": "run_0001",
      "step_id": null,
      "payload": {}
    },
    {
      "id": "evt_0002",
      "type": "RunValidated",
      "timestamp": "2026-07-07T10:00:00Z",
      "run_id": "run_0001",
      "step_id": null,
      "payload": {
        "protocol_id": "code_review",
        "protocol_version": "0.1.0"
      }
    },
    {
      "id": "evt_0003",
      "type": "RunStarted",
      "timestamp": "2026-07-07T10:00:01Z",
      "run_id": "run_0001",
      "step_id": null,
      "payload": {}
    },
    {
      "id": "evt_0004",
      "type": "StepStarted",
      "timestamp": "2026-07-07T10:00:02Z",
      "run_id": "run_0001",
      "step_id": "frame",
      "payload": {
        "inputs": ["user_input"],
        "resolved_artifact_ids": []
      }
    },
    {
      "id": "evt_0005",
      "type": "MessageSent",
      "timestamp": "2026-07-07T10:00:02Z",
      "run_id": "run_0001",
      "step_id": "frame",
      "payload": {
        "message_id": "msg_0001"
      }
    },
    {
      "id": "evt_0006",
      "type": "MessageReceived",
      "timestamp": "2026-07-07T10:00:05Z",
      "run_id": "run_0001",
      "step_id": "frame",
      "payload": {
        "message_id": "msg_0002"
      }
    },
    {
      "id": "evt_0007",
      "type": "ArtifactCreated",
      "timestamp": "2026-07-07T10:00:05Z",
      "run_id": "run_0001",
      "step_id": "frame",
      "payload": {
        "artifact_id": "artifact_0001",
        "output": "framing",
        "kind": "framing",
        "producer_role_id": "framer"
      }
    },
    {
      "id": "evt_0008",
      "type": "StepCompleted",
      "timestamp": "2026-07-07T10:00:05Z",
      "run_id": "run_0001",
      "step_id": "frame",
      "payload": {
        "produced_artifact_ids": ["artifact_0001"]
      }
    },
    {
      "id": "evt_0009",
      "type": "StepStarted",
      "timestamp": "2026-07-07T10:00:06Z",
      "run_id": "run_0001",
      "step_id": "role_reviews",
      "payload": {
        "inputs": ["framing"],
        "resolved_artifact_ids": ["artifact_0001"]
      }
    },
    {
      "id": "evt_0010",
      "type": "StepCompleted",
      "timestamp": "2026-07-07T10:00:12Z",
      "run_id": "run_0001",
      "step_id": "role_reviews",
      "payload": {
        "produced_artifact_ids": ["artifact_0002", "artifact_0003", "artifact_0004"]
      }
    },
    {
      "id": "evt_0011",
      "type": "StepStarted",
      "timestamp": "2026-07-07T10:00:13Z",
      "run_id": "run_0001",
      "step_id": "cross_critique",
      "payload": {
        "inputs": ["reviews"],
        "resolved_artifact_ids": ["artifact_0002", "artifact_0003", "artifact_0004"]
      }
    },
    {
      "id": "evt_0012",
      "type": "StepCompleted",
      "timestamp": "2026-07-07T10:00:17Z",
      "run_id": "run_0001",
      "step_id": "cross_critique",
      "payload": {
        "produced_artifact_ids": ["artifact_0005", "artifact_0006", "artifact_0007"]
      }
    },
    {
      "id": "evt_0013",
      "type": "StepStarted",
      "timestamp": "2026-07-07T10:00:18Z",
      "run_id": "run_0001",
      "step_id": "final",
      "payload": {
        "inputs": ["framing", "reviews", "critiques"],
        "resolved_artifact_ids": [
          "artifact_0001",
          "artifact_0002",
          "artifact_0003",
          "artifact_0004",
          "artifact_0005",
          "artifact_0006",
          "artifact_0007"
        ]
      }
    },
    {
      "id": "evt_0014",
      "type": "ArtifactCreated",
      "timestamp": "2026-07-07T10:00:20Z",
      "run_id": "run_0001",
      "step_id": "final",
      "payload": {
        "artifact_id": "artifact_0008",
        "output": "final_synthesis",
        "kind": "synthesis",
        "producer_role_id": "synthesizer"
      }
    },
    {
      "id": "evt_0015",
      "type": "StepCompleted",
      "timestamp": "2026-07-07T10:00:20Z",
      "run_id": "run_0001",
      "step_id": "final",
      "payload": {
        "produced_artifact_ids": ["artifact_0008"]
      }
    },
    {
      "id": "evt_0016",
      "type": "RunCompleted",
      "timestamp": "2026-07-07T10:00:21Z",
      "run_id": "run_0001",
      "step_id": null,
      "payload": {
        "final_artifact_id": "artifact_0008"
      }
    }
  ]
}
```

## 10. Failed Run With Partial Artifacts

```json
{
  "id": "run_0002",
  "protocol": {
    "id": "code_review",
    "version": "0.1.0"
  },
  "status": "failed",
  "input": {
    "kind": "file",
    "source": "pr.diff",
    "hash": "sha256:def456"
  },
  "artifacts": [
    {
      "id": "artifact_0001",
      "kind": "framing",
      "output": "framing",
      "producer_step_id": "frame",
      "producer_role_id": "framer",
      "payload": {
        "content": "The input appears to describe a validation change."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T11:00:05Z"
    },
    {
      "id": "artifact_0002",
      "kind": "review",
      "output": "reviews",
      "producer_step_id": "role_reviews",
      "producer_role_id": "maintainer",
      "payload": {
        "content": "The change is understandable, but behavior should be documented."
      },
      "metadata": {
        "model": "gpt-5-mini",
        "finish_reason": "stop"
      },
      "created_at": "2026-07-07T11:00:08Z"
    }
  ],
  "trace_id": "trace_0002",
  "started_at": "2026-07-07T11:00:00Z",
  "completed_at": "2026-07-07T11:00:09Z"
}
```

Failed trace excerpt:

```json
{
  "id": "trace_0002",
  "run_id": "run_0002",
  "events": [
    {
      "id": "evt_0001",
      "type": "RunStarted",
      "timestamp": "2026-07-07T11:00:00Z",
      "run_id": "run_0002",
      "step_id": null,
      "payload": {}
    },
    {
      "id": "evt_0002",
      "type": "StepStarted",
      "timestamp": "2026-07-07T11:00:06Z",
      "run_id": "run_0002",
      "step_id": "role_reviews",
      "payload": {
        "inputs": ["framing"],
        "resolved_artifact_ids": ["artifact_0001"]
      }
    },
    {
      "id": "evt_0003",
      "type": "ArtifactCreated",
      "timestamp": "2026-07-07T11:00:08Z",
      "run_id": "run_0002",
      "step_id": "role_reviews",
      "payload": {
        "artifact_id": "artifact_0002",
        "output": "reviews",
        "kind": "review",
        "producer_role_id": "maintainer"
      }
    },
    {
      "id": "evt_0004",
      "type": "StepFailed",
      "timestamp": "2026-07-07T11:00:09Z",
      "run_id": "run_0002",
      "step_id": "role_reviews",
      "payload": {
        "role_id": "tester",
        "error_code": "provider_error",
        "message": "Provider request failed."
      }
    },
    {
      "id": "evt_0005",
      "type": "RunFailed",
      "timestamp": "2026-07-07T11:00:09Z",
      "run_id": "run_0002",
      "step_id": null,
      "payload": {
        "failed_step_id": "role_reviews",
        "error_code": "provider_error"
      }
    }
  ]
}
```

## 11. ExecutionContext

Not durable core, but required by the engine.

Conceptual shape:

```json
{
  "run_id": "run_0001",
  "output_index": {
    "framing": ["artifact_0001"],
    "reviews": ["artifact_0002", "artifact_0003", "artifact_0004"],
    "critiques": ["artifact_0005", "artifact_0006", "artifact_0007"]
  },
  "current_step_id": "final"
}
```

Responsibilities:

- resolve `inputs` to artifact ids;
- maintain output-to-artifact mapping;
- prepare step execution;
- keep operational state out of durable `Run`.

## 12. Decisions Deferred

Explicitly deferred:

- `Claim`, `Evidence`, `Critique`, `Decision` as core entities;
- durable `Message`;
- payload schemas per artifact kind;
- semantic validation of artifact payload;
- domain-specific artifact kinds;
- global artifact kind registry;
- branching;
- loops;
- conditions;
- votes;
- gates;
- human input;
- subprotocols;
- real parallel execution;
- failed run resume;
- deterministic replay;
- persistent database;
- MCP;
- shell;
- tools;
- GitHub integration;
- multiple providers;
- long-term memory;
- advanced permissions;
- Markdown rendering by artifact schema.

The v0.1 model should remain small enough that implementation mostly becomes parsing, validation, execution bookkeeping, and artifact creation.
