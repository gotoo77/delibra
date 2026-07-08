#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

if [[ "$#" -gt 1 ]]; then
  echo "run_real_code_review: expected zero or one git range argument" >&2
  exit 1
fi

PROVIDER="${PROVIDER:-mock}"
OUTPUT_DIR="${DELIBRA_OUTPUT_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/delibra-code-review.XXXXXX")}"
GIT_ROOT="${DELIBRA_GIT_ROOT:-$ROOT}"
RANGE="${1:-}"
PROGRESS_INTERVAL_SECONDS="${DELIBRA_PROGRESS_INTERVAL_SECONDS:-2}"
CHILD_PID=""

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
read -r -a DELIBRA_CMD <<< "${DELIBRA_BIN:-python3 -m delibra}"

cleanup_child() {
  if [[ -n "$CHILD_PID" ]]; then
    kill "$CHILD_PID" >/dev/null 2>&1 || true
  fi
}

run_with_heartbeat() {
  local label="$1"
  shift

  printf "run_real_code_review: waiting for %s" "$label"
  set +e
  "$@" &
  CHILD_PID=$!
  while kill -0 "$CHILD_PID" >/dev/null 2>&1; do
    sleep "$PROGRESS_INTERVAL_SECONDS"
    if kill -0 "$CHILD_PID" >/dev/null 2>&1; then
      printf "."
    fi
  done
  wait "$CHILD_PID"
  local status=$?
  CHILD_PID=""
  set -e
  printf "\n"

  if [[ "$status" -ne 0 ]]; then
    echo "run_real_code_review: $label failed" >&2
    return "$status"
  fi
}

trap cleanup_child INT TERM

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

echo "run_real_code_review: provider=$PROVIDER"
if [[ "$PROVIDER" == "openai" ]]; then
  echo "run_real_code_review: openai_model=$OPENAI_MODEL"
  echo "run_real_code_review: openai_timeout_seconds=${OPENAI_TIMEOUT_SECONDS:-120}"
  echo "run_real_code_review: openai_max_output_tokens=${OPENAI_MAX_OUTPUT_TOKENS:-800}"
  if [[ "${DELIBRA_DEBUG_PROVIDER:-}" == "1" ]]; then
    echo "run_real_code_review: provider debug enabled"
  fi
fi
echo "run_real_code_review: output_dir=$OUTPUT_DIR"
echo "run_real_code_review: git_root=$GIT_ROOT"
echo "run_real_code_review: progress_interval_seconds=$PROGRESS_INTERVAL_SECONDS"

if [[ -n "$RANGE" ]]; then
  DIFF_LABEL="$RANGE"
  echo "run_real_code_review: selecting diff range $DIFF_LABEL"
  if ! git -C "$GIT_ROOT" diff --no-ext-diff --no-textconv "$RANGE" > "$OUTPUT_DIR/input.patch"; then
    echo "run_real_code_review: invalid git range: $DIFF_LABEL" >&2
    exit 1
  fi
elif git -C "$GIT_ROOT" rev-parse --verify HEAD~1 >/dev/null 2>&1; then
  DIFF_LABEL="HEAD~1..HEAD"
  echo "run_real_code_review: selecting default diff range $DIFF_LABEL"
  git -C "$GIT_ROOT" diff --no-ext-diff --no-textconv HEAD~1..HEAD > "$OUTPUT_DIR/input.patch"
else
  DIFF_LABEL="working tree"
  echo "run_real_code_review: selecting working tree diff"
  git -C "$GIT_ROOT" diff --no-ext-diff --no-textconv > "$OUTPUT_DIR/input.patch"
fi

if [[ ! -s "$OUTPUT_DIR/input.patch" ]]; then
  echo "run_real_code_review: No diff found. Nothing to review. ($DIFF_LABEL)" >&2
  echo "run_real_code_review: pass a non-empty git range, create a commit, or add tracked working tree changes" >&2
  exit 1
fi

echo "run_real_code_review: captured $(wc -l < "$OUTPUT_DIR/input.patch") diff lines"
echo "run_real_code_review: starting delibra run"
run_with_heartbeat "delibra run" "${DELIBRA_CMD[@]}" run \
  --protocol "$ROOT/presets/code_review.yaml" \
  --provider "$PROVIDER" \
  --input-text "$(cat "$OUTPUT_DIR/input.patch")" \
  --run-output "$OUTPUT_DIR/run.json" \
  --trace-output "$OUTPUT_DIR/trace.json"
echo "run_real_code_review: delibra run completed"

echo "run_real_code_review: extracting final synthesis"
python3 - "$OUTPUT_DIR/run.json" "$OUTPUT_DIR/final_synthesis.txt" <<'PY'
import json
import sys

run_path, output_path = sys.argv[1], sys.argv[2]
with open(run_path, encoding="utf-8") as f:
    run = json.load(f)

final_artifact = None
for artifact in run.get("artifacts", []):
    if artifact.get("output") == "final_synthesis":
        final_artifact = artifact

if final_artifact is None:
    raise SystemExit("run_real_code_review: final_synthesis artifact not found")

payload = final_artifact.get("payload", {})
content = payload.get("content")
if not isinstance(content, str) or not content:
    content = json.dumps(payload, indent=2, sort_keys=True)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(content)
    if not content.endswith("\n"):
        f.write("\n")
PY

echo "run_real_code_review: inspecting durable outputs"
"${DELIBRA_CMD[@]}" inspect \
  --run "$OUTPUT_DIR/run.json" \
  --trace "$OUTPUT_DIR/trace.json" \
  > "$OUTPUT_DIR/inspect.txt"
echo "run_real_code_review: inspect completed"

cat "$OUTPUT_DIR/inspect.txt"

echo
echo "Final synthesis preview:"
sed -n '1,80p' "$OUTPUT_DIR/final_synthesis.txt"

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
echo "  $OUTPUT_DIR/final_synthesis.txt"
echo
echo "Next steps:"
echo "  Read final_synthesis.txt for the review text."
echo "  Review inspect.txt for the artifact summary."
echo "  Open run.json for durable artifacts."
if [[ "$PROVIDER" == "openai" ]]; then
  echo "  OpenAI mode sent the selected diff to the configured provider and may incur API cost."
fi
if [[ "$PROVIDER" == "mock" ]]; then
  echo "  Mock output validates the scenario mechanics; use PROVIDER=openai for a real model review."
fi
echo "  Treat generated outputs as sensitive; do not commit or share them blindly."
