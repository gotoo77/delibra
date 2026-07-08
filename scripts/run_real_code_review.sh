#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

PROVIDER="${PROVIDER:-mock}"
OUTPUT_DIR="${DELIBRA_OUTPUT_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/delibra-code-review.XXXXXX")}"
GIT_ROOT="${DELIBRA_GIT_ROOT:-$ROOT}"
RANGE="${1:-}"

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
read -r -a DELIBRA_CMD <<< "${DELIBRA_BIN:-python3 -m delibra}"

if [[ "$PROVIDER" != "mock" && "$PROVIDER" != "openai" ]]; then
  echo "run_real_code_review: unsupported PROVIDER: $PROVIDER" >&2
  exit 1
fi

if [[ "$PROVIDER" == "openai" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "run_real_code_review: OPENAI_API_KEY is required when PROVIDER=openai" >&2
    exit 1
  fi
  if [[ -z "${OPENAI_MODEL:-}" ]]; then
    echo "run_real_code_review: OPENAI_MODEL is required when PROVIDER=openai" >&2
    exit 1
  fi
fi

mkdir -p "$OUTPUT_DIR"

if [[ -n "$RANGE" ]]; then
  DIFF_LABEL="$RANGE"
  git -C "$GIT_ROOT" diff "$RANGE" > "$OUTPUT_DIR/input.patch"
elif git -C "$GIT_ROOT" rev-parse --verify HEAD~1 >/dev/null 2>&1; then
  DIFF_LABEL="HEAD~1..HEAD"
  git -C "$GIT_ROOT" diff HEAD~1..HEAD > "$OUTPUT_DIR/input.patch"
else
  DIFF_LABEL="working tree"
  git -C "$GIT_ROOT" diff > "$OUTPUT_DIR/input.patch"
fi

if [[ ! -s "$OUTPUT_DIR/input.patch" ]]; then
  echo "run_real_code_review: selected diff is empty ($DIFF_LABEL)" >&2
  echo "run_real_code_review: pass a git range, create a commit, or add working tree changes" >&2
  exit 1
fi

"${DELIBRA_CMD[@]}" run \
  --protocol "$ROOT/presets/code_review.yaml" \
  --provider "$PROVIDER" \
  --input-text "$(cat "$OUTPUT_DIR/input.patch")" \
  --run-output "$OUTPUT_DIR/run.json" \
  --trace-output "$OUTPUT_DIR/trace.json"

"${DELIBRA_CMD[@]}" inspect \
  --run "$OUTPUT_DIR/run.json" \
  --trace "$OUTPUT_DIR/trace.json" \
  > "$OUTPUT_DIR/inspect.txt"

cat "$OUTPUT_DIR/inspect.txt"

echo
echo "Delibra real code review scenario complete."
echo "Provider: $PROVIDER"
echo "Diff: $DIFF_LABEL"
echo "Output directory: $OUTPUT_DIR"
echo
echo "Generated files:"
echo "  $OUTPUT_DIR/input.patch"
echo "  $OUTPUT_DIR/run.json"
echo "  $OUTPUT_DIR/trace.json"
echo "  $OUTPUT_DIR/inspect.txt"
echo
echo "Next steps:"
echo "  Review inspect.txt for the artifact summary."
echo "  Open run.json for durable artifacts."
echo "  Keep generated outputs disposable; do not commit them."
