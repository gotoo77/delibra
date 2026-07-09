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
| F005 | CLI-centered orchestration makes Delibra harder to access for non-programmer users and harder to expose through web, desktop, or guided preset interfaces. | interface architecture | architecture review | 1 | candidate |
| F006 | Local LLM setup is hard to evaluate for curious non-expert users because provider availability, model availability, and recovery steps are not immediately visible. | local provider setup | architecture review | 1 | candidate |

## Notes

F005 is both a user friction and an architectural friction. The CLI is useful
for technical users, but it should become an adapter over shared application
services rather than the place where orchestration behavior lives. The technical
migration plan belongs in a future ADR or architecture note, not in this
friction log.

F006 should first be addressed by making local state visible before considering
any automation. Delibra can report reachable providers, visible models, and
recovery hints, but this does not imply automatic installation or model
download.
