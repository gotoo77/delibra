# External coding-agent integration: exploration note

Status: **hypothesis only** (2026-11-17). This document does not authorize a core API change or claim an integration exists.

## Motivation

A separate local-first development stack may use:
- an external **orchestrator** (such as OpenCode) to choose and sequence tasks;
- a local or cloud **LLM** to reason;
- **GPE Agent** as a constrained worker for project inspection, worktrees, allowed code modifications and typed verification;
- optionally **Delibra** to produce durable review/decision artifacts and trace structured reasoning.

These roles must remain separate. In particular, Delibra does not issue privileged machine commands, enforce execution sandboxing, or own a general autonomous agent loop. See [Architecture Principles](architecture-principles.md) and [PHILOSOPHY.md](../PHILOSOPHY.md).

## What Delibra actually provides

The current CLI/runtime executes declared derivation protocols with mock, OpenAI and Ollama providers. It records `run.json`, `trace.json` and artifacts; existing code/design/decision review presets are candidates for independent use. It does **not** expose an OpenCode/GPE Agent orchestration adapter or a long-term retrieval/memory engine.

## Optional integration hypothesis

The external orchestrator might pass a *bounded, sanitized* diagnostic or code diff to an existing Delibra review preset, then receive review artifacts. It remains responsible for deciding whether to act, and it requests any allowed action via the separate secured worker. Worker results serve as external evidence; Delibra must not reinterpret a successful transport request as successful code verification.

Potential review triggers: competing diagnoses, architecture choices or a high-risk patch. Routine formatting and fixed tests should not require a deliberation run.

## Evaluation before implementation

Compare a set of existing coding tasks with/without a Delibra review step. Measure:
- correct diagnosis and review usefulness, assessed against testable evidence;
- reproducibility and auditability of artifacts;
- latency, token usage and unnecessary review overhead;
- preservation of confidential input and bounded context.

Keep integration in an external adapter or preset until repeated real use establishes a missing capability. Do not add an agent workflow engine, classifier, execution controls or provider-specific fields to Delibra's durable core.

## Routing / classifier concept

An optional upstream classifier may propose when to invoke a review protocol. This is an **external product/workflow decision**, not Delibra runtime behavior; classifier scores must not authorize worker actions.

## Current decision

Document the possible complementarity; **defer coupling**. First demonstrate one secure round trip between a local-model orchestrator and an existing GPE Agent typed capability.
