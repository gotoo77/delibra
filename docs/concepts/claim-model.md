# Claim Model

## Status

Hypothesis

## Core Status

Rejected for v0.1

## Motivation

Artifacts preserve durable outputs of derivation, but some artifacts may contain more granular knowledge structures.

A future claim model might represent assertions, evidence, critiques, and decisions across multiple protocol families.

Possible shape:

```text
Claim
Evidence
Critique
Decision
```

This may apply to code review, design review, decision review, investigations, text critique, and games.

## Evidence

Current evidence is conceptual only.

The core model explicitly keeps `Claim`, `Evidence`, `Critique`, and `Decision` out of v0.1. They may appear as artifact payload content, preset conventions, renderer concerns, or product-layer concepts.

## Protocols Requiring It

```text
code_review: unknown
design_review: unknown
decision_review: unknown
```

Current pressure: 0/3 unrelated protocols.

## Can Remain Outside The Core?

Yes.

For v0.1, claims can remain inside artifact payloads, renderer conventions, preset-specific schemas, or product-layer analysis.

## Decision

Wait.

Do not introduce `Claim`, `Evidence`, `Critique`, or `Decision` into the durable core until they satisfy the governance rule in ADR-0001.

The question is not whether the concept is useful. The question is whether removing it would make the core less coherent.
