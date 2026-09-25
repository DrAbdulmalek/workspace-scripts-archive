#!/usr/bin/env bash
# TASK-02D — post-fix combined resolution + pip-audit on py3.12 (sandbox) and py3.11 (CI).
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
cd "$REPO"

summarize() {
python3 - "$1" << 'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception as e: print("  no json:", e); raise SystemExit
watch={"gradio","pillow","transformers","torch","numpy","huggingface-hub","paddlepaddle","paddleocr","pydantic"}
names={}
for dep in d.get("dependencies",[]):
    n=dep["name"].lower()
    if n in watch: names[n]=dep.get("version")
for k in sorted(names): print(f"  {k:<20} {names[k]}")
print("  total deps:", len(d.get("dependencies",[])))
PY
}

echo "=== [py3.12] pip-audit combined (post-fix) ==="
V312=/home/z/my-project/repos/venv-audit313   # actually py3.12.14 as created earlier
"$V312/bin/pip-audit" --progress-spinner off \
  -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
  --skip-editable --ignore PYSEC-2026-1325 -f json -o "$OUT/audit_fixed_py312.json" 2>"$OUT/audit_fixed_py312.stderr"
echo "exit=$?"
summarize "$OUT/audit_fixed_py312.json"
grep -E "^Found" "$OUT/audit_fixed_py312.stderr" 2>/dev/null || true
# pip-audit prints summary to stdout when not json-only; capture text run too
"$V312/bin/pip-audit" --progress-spinner off \
  -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
  --skip-editable --ignore PYSEC-2026-1325 > "$OUT/audit_fixed_py312_text.log" 2>&1
echo "text-run exit=$?"
grep -E "^Found|No known vulnerabilities" "$OUT/audit_fixed_py312_text.log" | head -2

echo
echo "=== [py3.11] build venv via uv (seeded) and run pip-audit combined (post-fix) ==="
V311=/home/z/my-project/repos/venv-audit311
if [ ! -x "$V311/bin/python" ]; then uv venv "$V311" --python 3.11 --seed; fi
"$V311/bin/python" -m pip install -q --upgrade pip pip-audit 2>&1 | tail -1
"$V311/bin/python" --version
"$V311/bin/pip-audit" --progress-spinner off \
  -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
  --skip-editable --ignore PYSEC-2026-1325 -f json -o "$OUT/audit_fixed_py311.json" 2>"$OUT/audit_fixed_py311.stderr"
echo "exit=$?"
summarize "$OUT/audit_fixed_py311.json"
"$V311/bin/pip-audit" --progress-spinner off \
  -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
  --skip-editable --ignore PYSEC-2026-1325 > "$OUT/audit_fixed_py311_text.log" 2>&1
echo "text-run exit=$?"
grep -E "^Found|No known vulnerabilities" "$OUT/audit_fixed_py311_text.log" | head -2
