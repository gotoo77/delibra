# Observed Frictions

This is not a backlog.

Observed frictions record problems seen in field notes. A friction is evidence,
not a feature request. It describes what made Delibra harder to use,
understand, inspect, trust, or evolve.

Frequency increases confidence, not urgency. A friction becomes design input
only when the evidence is repeated, severe, or architecturally clarifying.

## Status

- `observe`: recorded, but not enough evidence yet.
- `candidate`: repeated or severe enough to deserve design work.
- `accepted`: a design direction has been chosen.
- `resolved`: an implementation addressed it.
- `dropped`: intentionally not pursued.

## Frictions

| ID | Friction | Kind | Observed In | Frequency | Status |
|---|---|---|---|---:|---|
| F001 | Final synthesis requires manual extraction from `run.json`. | output access | 0001, 0002, 0003, 0004, 0005 | 5 | candidate |
| F002 | Manual run/inspect command wiring is repetitive. | workflow | 0002, 0003 | 2 | observe |
| F003 | Large inputs may make `--input-text` awkward or hit shell argument limits. | input | 0005 | 1 | observe |
| F004 | Semantic value of decision recipes cannot be judged with mock output. | evaluation | 0004, 0005 | 2 | observe |
