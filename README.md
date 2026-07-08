# Delibra

Delibra orchestrates artifact derivation. Models reason; Delibra preserves the resulting artifacts and trace.

## Local Development

Install the CLI in editable mode:

```bash
python3 -m pip install -e .
```

Run the CLI:

```bash
delibra --help
delibra validate --help
delibra run --help
```

Run with the default mock provider:

```bash
delibra run \
  --protocol presets/code_review.yaml \
  --provider mock \
  --input-text "Review this change." \
  --run-output run.json \
  --trace-output trace.json
```

Run with OpenAI:

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=...

delibra run \
  --protocol presets/code_review.yaml \
  --provider openai \
  --input-text "Review this change." \
  --run-output run.json \
  --trace-output trace.json
```

Run tests:

```bash
python3 -m unittest
```
