# Delibra Field Notes

Field notes document observed usage evidence from real Delibra runs.

They are not roadmap items, feature requests, concept notes, or accepted architecture decisions. A field note records what happened, what was confusing, what friction appeared, and what decision was made after the run.

Use field notes to accumulate evidence before changing Delibra. A repeated friction across several notes may become a bug fix, documentation update, preset issue, runtime issue, or concept tension. A single interesting idea is not enough.

## Raw Outputs

Do not commit generated run outputs:

- `input.patch`
- `run.json`
- `trace.json`
- `inspect.txt`
- `final_synthesis.txt`
- provider outputs

Keep raw artifacts outside the repository, for example:

```bash
mkdir -p ~/dev/delibra-runs
```

Generated outputs may contain sensitive code, provider responses, or model output. Treat them as disposable and do not share them blindly.

## Suggested Workflow

1. Run Delibra on a real input.
2. Store raw outputs outside the repo.
3. Inspect `inspect.txt` and `final_synthesis.txt`.
4. Add a short field note using `TEMPLATE.md`.
5. Classify the observed friction without turning it into a roadmap item.

The goal is to discover what Delibra actually needs by using it.
