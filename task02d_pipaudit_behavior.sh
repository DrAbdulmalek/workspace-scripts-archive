#!/usr/bin/env bash
# TASK-02D — reproduce pip-audit's exact resolution behavior (combined -r?),
# on the sandbox python AND on Python 3.11 (CI's interpreter via uv).
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
cd "$REPO"

# --- python 3.13 (sandbox default) venv with pip-audit ---
V313=/home/z/my-project/repos/venv-audit313
if [ ! -d "$V313" ]; then
  python3 -m venv "$V313"
  "$V313/bin/pip" install -q --upgrade pip >/dev/null
  "$V313/bin/pip" install -q pip-audit >/dev/null 2>&1
fi
echo "=== pip-audit on $(python3 --version) — 3 surfaces, versions it audits ==="
"$V313/bin/pip-audit" --progress-spinner off \
  -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
  --skip-editable --ignore PYSEC-2026-1325 -f json -o "$OUT/audit_combined_py313.json" 2>"$OUT/audit_combined_py313.stderr"
echo "exit=$?"
python3 - "$OUT/audit_combined_py313.json" << 'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception as e: print("no json:", e); raise SystemExit
watch={"gradio","pillow","transformers","torch","numpy","huggingface-hub","paddlepaddle","paddleocr"}
names={}
for dep in d.get("dependencies",[]):
    n=dep["name"].lower()
    if n in watch: names[n]=dep.get("version")
for k in sorted(names): print(f"  {k:<20} {names[k]}")
print("  total deps:", len(d.get("dependencies",[])))
PY

# --- Python 3.11 via uv (CI's interpreter) ---
if [ ! -d /home/z/my-project/repos/venv-audit311 ]; then
  uv python install 3.11 --quiet 2>/dev/null || uv python install 3.11
  uv venv /home/z/my-project/repos/venv-audit311 --python 3.11
  /home/z/my-project/repos/venv-audit311/bin/pip install -q --upgrade pip
  /home/z/my-project/repos/venv-audit311/bin/pip install -q pip-audit
fi
echo
echo "=== pip-audit on $(/home/z/my-project/repos/venv-audit311/bin/python --version) — 3 surfaces ==="
/home/z/my-project/repos/venv-audit311/bin/pip-audit --progress-spinner off \
  -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
  --skip-editable --ignore PYSEC-2026-1325 -f json -o "$OUT/audit_combined_py311.json" 2>"$OUT/audit_combined_py311.stderr"
echo "exit=$?"
python3 - "$OUT/audit_combined_py311.json" << 'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception as e: print("no json:", e); raise SystemExit
watch={"gradio","pillow","transformers","torch","numpy","huggingface-hub","paddlepaddle","paddleocr"}
names={}
for dep in d.get("dependencies",[]):
    n=dep["name"].lower()
    if n in watch: names[n]=dep.get("version")
for k in sorted(names): print(f"  {k:<20} {names[k]}")
print("  total deps:", len(d.get("dependencies",[])))
PY
