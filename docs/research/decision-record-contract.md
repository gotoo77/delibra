# Decision Record Local Contract

## Status

Experimental local contract. No validator implementation, generic artifact
contract, or runtime change is defined by this document.

This contract exists to classify the representative fixtures in
`decision-record-fixtures.md` before implementing any validation code.

## Core Distinction

This experiment separates two axes:

- `structural_validation`
- `acceptance_status`

Invariant:

```text
structural_validity does not imply accepted.
```

This is the main expected divergence from `puzzle_spec`. A decision record can
be structurally complete while still awaiting review, approval, policy checks,
or human judgment.

## Minimal Local Fields

The local `decision_record` contract requires:

- `decision`
- `status`
- `options_considered`
- `reasons`
- `consequences`
- `uncertainties`
- `pending_conditions`

These fields are application-owned. They are not proposed as Delibra core
fields.

## Deterministic Structural Rules

`decision`:

- must be a non-empty string.

`options_considered`:

- must be a non-empty list.

`reasons`:

- must be a non-empty list.
- The contract checks that reasons are recorded, not whether they are
  persuasive.

`consequences`:

- must be a non-empty list.

`uncertainties`:

- must be present as a list.
- The list may be empty when absence of known uncertainty is explicitly
  represented by the record.

`pending_conditions`:

- must be present as a list.
- The list may be empty.

`status`:

- must be one of:
  - `proposed`
  - `pending_review`
  - `accepted`
  - `rejected`

## Local Status Coherence

The contract reads status from the record and checks it for local consistency.
It does not decide whether the decision deserves acceptance.

Rules:

- `status = accepted` requires `pending_conditions` to be empty.
- `status = pending_review` may have non-empty `pending_conditions`.
- `status = proposed` means no acceptance has been acquired.
- `status = rejected` means no promotion is authorized by this local contract.

This makes `contradictory_status` deterministically expressible without free
text interpretation.

## Fixture Classification

| Fixture | structural_validation | acceptance_status |
|---|---|---|
| `valid_structural_decision_record` | valid | undecided |
| `missing_required_fields` | invalid | not_evaluated |
| `no_explicit_decision` | invalid | not_evaluated |
| `options_without_reasons` | invalid | not_evaluated |
| `structurally_valid_but_not_accepted` | valid | pending_review or rejected |
| `contradictory_status` | invalid | not_evaluated |

## Fixture Implications

`valid_structural_decision_record` proves only that the record is structurally
complete. It does not prove acceptance.

`options_without_reasons` is structurally invalid because a decision record
without recorded reasons is only a decision announcement or assertion, not a
usable decision record.

`structurally_valid_but_not_accepted` must pass structural validation while
preserving a non-accepted status such as `pending_review` or `rejected`.

`contradictory_status` is invalid when it combines `status = accepted` with
non-empty `pending_conditions`.

## Non-Goals

- no `decision_record` validator implementation;
- no final JSON schema;
- no generic artifact contract;
- no warning severity model;
- no qualitative evaluation of reasons;
- no automatic acceptance decision;
- no runtime changes.

## Completion Criterion

This contract is sufficient when it classifies the six representative fixtures
without ambiguity and preserves the separation between structural validity and
acceptance.
