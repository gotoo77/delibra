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

Inspect canonical outputs:

```bash
delibra inspect --run run.json
delibra inspect --run run.json --trace trace.json
```

Run a real-use code review scenario:

```bash
scripts/run_real_code_review.sh
PROVIDER=mock scripts/run_real_code_review.sh
PROVIDER=openai OPENAI_API_KEY=... OPENAI_MODEL=... scripts/run_real_code_review.sh
scripts/run_real_code_review.sh HEAD~2..HEAD
```

This scenario runs the `code_review` preset against a real Git diff and writes disposable outputs to a temporary directory by default. It is not a test fixture. Mock is safe and default; OpenAI is opt-in. Do not commit generated `input.patch`, `run.json`, `trace.json`, or `inspect.txt` files.

Run tests:

```bash
python3 -m unittest
```
