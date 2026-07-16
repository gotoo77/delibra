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
delibra presets list
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

Run a named local preset:

```bash
delibra run \
  --preset code_review \
  --provider mock \
  --input-text "Review this change." \
  --run-output run.json \
  --trace-output trace.json
```

`--protocol` accepts an explicit YAML path. `--preset` resolves a named protocol
from the local `presets/` directory. Use `delibra presets list` to discover
available local presets.

Input can be supplied as inline text, a UTF-8 text file, or an inline JSON
object:

```bash
delibra run \
  --preset decision_review \
  --provider mock \
  --input-file decision.txt \
  --run-output run.json \
  --trace-output trace.json

delibra run \
  --preset decision_review \
  --provider mock \
  --input-json '{"kind":"decision","title":"Ship v1","risk":3}' \
  --run-output run.json \
  --trace-output trace.json
```

Run with an explicit execution policy:

```bash
cat > policy.yaml <<'YAML'
id: cheap-review
mode: cheap
budget:
  max_estimated_units: 3000
default_step_budget:
  max_output_units: 300
YAML

delibra run \
  --protocol presets/code_review.yaml \
  --provider mock \
  --policy policy.yaml \
  --input-text "Review this change." \
  --run-output run.json \
  --trace-output trace.json
```

Execution policies are runtime-only. They are traced through neutral
`PolicyApplied`, `PolicyDecision`, and `BudgetExceeded` events without adding
provider, model, token, or cost fields to durable protocol, run, trace, or
artifact objects.

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

Use `--progress` for long runs to print elapsed step and role progress to stderr.
Progress timings are computed locally for terminal display. These measurements
are ephemeral and do not modify the run, trace, or artifact formats.

In v0.1, multi-role `fanout` and `criticize` steps execute roles sequentially.
They are semantic fanout steps, not parallel execution primitives.

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

Check local providers without installing or downloading anything:

```bash
delibra doctor local
```

`doctor local` is passive by default. It checks whether known local provider
endpoints are reachable and whether they report installed models.

Run an explicit minimal Ollama inference check:

```bash
delibra doctor local --check-inference --provider ollama --model llama3.2
```

If `--check-inference` is used without `--model`, Delibra uses `OLLAMA_MODEL`
when it is set. Otherwise it lists visible models and explains that an explicit
model is required. The inference check uses a short 10 second timeout and asks
for a very small response. Delibra never installs Ollama, downloads models, or
writes files from `doctor local`.

Inspect canonical outputs:

```bash
delibra inspect --run run.json
delibra inspect --run run.json --trace trace.json
delibra inspect --run run.json --artifact artifact_0001
```

Analyze run health metrics:

```bash
delibra analyze-run --run run.json --trace trace.json
```

Compare completed runs mechanically:

```bash
delibra compare-runs \
  --run first.run.json \
  --trace first.trace.json \
  --run second.run.json \
  --trace second.trace.json \
  --output comparison.md
```

`compare-runs` is an experimental Delibra Observatory helper. It consumes
persisted `run.json` / `trace.json` pairs, aligns artifacts by protocol position
(`step_id`, `role_id`, `output`, `artifact_kind`, and ordinal when needed), and
writes a Markdown draft marked `review_required`. Step kind is not reconstructed
because it is not persisted in `run.json` or `trace.json`. The draft reports
input identity by deterministic digest and size by default. It does not call
providers, rank models, infer provider/model from file names, or interpret
artifact content.

An optional experiment manifest can declare external comparison dimensions such
as human variant labels, controlled dimensions, changed dimensions, and known
provider/model metadata:

```bash
delibra compare-runs \
  --manifest experiment.json \
  --run first.run.json \
  --trace first.trace.json \
  --run second.run.json \
  --trace second.trace.json \
  --output comparison.md
```

Internal Delibra ids remain opaque and provider-free. File names are navigation
labels only. Persisted `run.json` and `trace.json` content is authoritative for
run, trace, protocol, input, artifact, and event facts. The manifest is
authoritative only for external experimental context; contradictions with
persisted content are reported in the generated draft.

Run a real-use code review scenario:

```bash
scripts/run_real_code_review.sh
PROVIDER=mock scripts/run_real_code_review.sh
PROVIDER=openai OPENAI_API_KEY=... OPENAI_MODEL=... OPENAI_TIMEOUT_SECONDS=180 OPENAI_MAX_OUTPUT_TOKENS=800 scripts/run_real_code_review.sh
scripts/run_real_code_review.sh HEAD~2..HEAD
```

This scenario runs the `code_review` preset against a real Git diff and writes disposable outputs to a temporary directory by default. It is not a test fixture. Mock is safe and default; it validates the mechanics but does not perform a semantic code review. OpenAI is opt-in. `OPENAI_TIMEOUT_SECONDS` controls the per-request HTTP timeout and defaults to 120 seconds. `OPENAI_MAX_OUTPUT_TOKENS` bounds provider output and defaults to 800. `DELIBRA_PROGRESS_INTERVAL_SECONDS` controls the heartbeat interval and defaults to 2 seconds. Set `DELIBRA_DEBUG_PROVIDER=1` to print runtime-only provider diagnostics such as model, timeout, max output tokens, and input character length. Read `final_synthesis.txt` for the review text, and use `inspect.txt` for the artifact summary. Do not commit generated `input.patch`, `run.json`, `trace.json`, `inspect.txt`, or `final_synthesis.txt` files.

The scenario script is a repository developer workflow, not a stable package interface. It requires Bash and Git; on Windows, use WSL or a compatible Bash environment. Diff selection is deterministic: an explicit range argument wins, otherwise the script uses `HEAD~1..HEAD` when available, otherwise it falls back to `git diff --no-ext-diff --no-textconv` for tracked working-tree changes. Staged-only and untracked files are not included by that fallback. Empty diffs fail with `No diff found. Nothing to review.` OpenAI mode sends the selected diff to the configured provider and may incur API cost. Generated outputs may contain sensitive code and model output; the script creates them with owner-only permissions, but they should still be treated as disposable.

Run tests:

```bash
python3 -m unittest
```
