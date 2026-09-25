#!/usr/bin/env bash
# TASK-02D — per-surface resolution forensics (pre-fix baseline).
# Dry-run resolution per production surface; record resolved versions of
# security-critical packages. Metadata-only via PEP 658 (no wheel installs).
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
mkdir -p "$OUT"
cd "$REPO"

VENV=/home/z/my-project/repos/venv-resolver
if [ ! -d "$VENV" ]; then python3 -m venv "$VENV"; "$VENV/bin/pip" install -q --upgrade pip; fi
PIP="$VENV/bin/pip"

run_root() {
  local label="$1"; shift
  echo "=== $label ==="
  $PIP install --dry-run --ignore-installed --quiet --report "$OUT/resolution_${label}.json" "$@" 2>"$OUT/resolution_${label}.stderr"
  local rc=$?
  echo "  exit=$rc"
  python3 - "$OUT/resolution_${label}.json" << 'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    print("  no report:", e); raise SystemExit
watch = {"gradio","pillow","transformers","torch","paddlepaddle","paddleocr","numpy","huggingface-hub","pydantic","fastapi","opencv-python","opencv-python-headless","scikit-learn","regex","typer"}
for item in d.get("install", []):
    n = item["metadata"]["name"].lower()
    if n in watch:
        print(f"  {n:<24} {item['metadata']['version']}")
PY
  if [ $rc -ne 0 ]; then echo "  --- stderr tail ---"; tail -12 "$OUT/resolution_${label}.stderr"; fi
}

run_root A -r requirements.txt
run_root B -r requirements/gradio.txt
run_root C -r hf-space/requirements.txt
