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
export OPENAI_TIMEOUT_SECONDS=180
export OPENAI_MAX_OUTPUT_TOKENS=800

delibra run \
  --protocol presets/code_review.yaml \
  --provider openai \
  --input-text "Review this change." \
  --run-output run.json \
  --trace-output trace.json \
  --progress
```

Use `--progress` for long runs to print step and role progress to stderr without
changing the machine-readable run and trace output files.

Run with local Ollama:

```bash
ollama pull llama3.2

export OLLAMA_MODEL=llama3.2
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_TIMEOUT_SECONDS=180
export OLLAMA_MAX_OUTPUT_TOKENS=1200

delibra run \
  --protocol presets/code_review.yaml \
  --provider ollama \
  --input-text "Review this change." \
  --run-output run.json \
  --trace-output trace.json \
  --progress
```

`OLLAMA_BASE_URL` defaults to `http://localhost:11434`.
`OLLAMA_MAX_OUTPUT_TOKENS` maps to Ollama `options.num_predict`.

Inspect canonical outputs:

```bash
delibra inspect --run run.json
delibra inspect --run run.json --trace trace.json
```

Analyze run health metrics:

```bash
delibra analyze-run --run run.json --trace trace.json
```

Run a real-use code review scenario:

```bash
scripts/run_real_code_review.sh
PROVIDER=mock scripts/run_real_code_review.sh
PROVIDER=openai OPENAI_API_KEY=... OPENAI_MODEL=... OPENAI_TIMEOUT_SECONDS=180 OPENAI_MAX_OUTPUT_TOKENS=800 scripts/run_real_code_review.sh
scripts/run_real_code_review.sh HEAD~2..HEAD
```

This scenario runs the `code_review` preset against a real Git diff and writes disposable outputs to a temporary directory by default. It is not a test fixture. Mock is safe and default; it validates the mechanics but does not perform a semantic code review. OpenAI is opt-in. `OPENAI_TIMEOUT_SECONDS` controls the per-request HTTP timeout and defaults to 120 seconds. `OPENAI_MAX_OUTPUT_TOKENS` bounds provider output and defaults to 800. `DELIBRA_PROGRESS_INTERVAL_SECONDS` controls the heartbeat interval and defaults to 2 seconds. Set `DELIBRA_DEBUG_PROVIDER=1` to print runtime-only provider diagnostics such as model, timeout, max output tokens, and input character length. Read `final_synthesis.txt` for the review text, and use `inspect.txt` for the artifact summary. Do not commit generated `input.patch`, `run.json`, `trace.json`, `inspect.txt`, or `final_synthesis.txt` files.

The scenario script is a repository developer workflow, not a stable package interface. It requires Bash and Git; on Windows, use WSL or a compatible Bash environment. Diff selection is deterministic: an explicit range argument wins, otherwise the script uses `HEAD~1..HEAD` when available, otherwise it falls back to `git diff --no-ext-diff --no-textconv` for tracked working-tree changes. Staged-only and untracked files are not included by that fallback. Empty diffs fail with `No diff found. Nothing to review.` OpenAI mode sends the selected diff to the configured provider and may incur API cost. Generated outputs may contain sensitive code and model output; the script creates them with owner-only permissions, but they should still be treated as disposable. Current CLI input is passed through `--input-text`, so very large diffs may hit process argument limits; keep real-use scenario diffs small until a file-input CLI exists.

Run tests:

```bash
python3 -m unittest
```
