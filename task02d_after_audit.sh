#!/usr/bin/env bash
# TASK-02D — AFTER audit: production surfaces with upgraded floors
set -uo pipefail
EV=/home/z/my-project/download/task02d-evidence
REPO=/home/z/my-project/repos/omni-medical-suite
PA=/home/z/my-project/repos/venv-old-scan/bin/pip-audit
mkdir -p "$EV"
cd "$REPO"

echo "== [1] AFTER combined explicit audit (NO ignore) =="
set +e
"$PA" --desc \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable \
  -f json -o "$EV/AFTER_explicit.json" > "$EV/AFTER_explicit.log" 2>&1
echo "exit(no-ignore): $?"
set -e

echo "== [2] AFTER combined WITH workflow ignore (mirrors patched workflow) =="
set +e
"$PA" --desc \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable \
  --ignore PYSEC-2026-1325 \
  -f json -o "$EV/AFTER_explicit_wignore.json" > "$EV/AFTER_explicit_wignore.log" 2>&1
echo "exit(with-ignore): $?"
set -e

echo "== [3] AFTER per-surface =="
for f in requirements.txt requirements/gradio.txt hf-space/requirements.txt; do
  name=$(echo "$f" | tr '/' '_')
  set +e
  "$PA" --desc -r "$f" --skip-editable -f json -o "$EV/AFTER_surface_${name}.json" > "$EV/AFTER_surface_${name}.log" 2>&1
  echo "surface $f exit: $?"
  set -e
done
echo DONE
