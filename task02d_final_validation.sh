#!/usr/bin/env bash
# TASK-02D — FINAL validation round: pip-audit (py3.11+py3.12), resolution table,
# negative control, per-surface final versions.
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
cd "$REPO"

summarize() {
python3 - "$1" << 'PY'
import json,sys
d=json.load(open(sys.argv[1]))
watch={"gradio","pillow","transformers","torch","numpy","huggingface-hub","paddlepaddle","paddleocr","pydantic","sentencepiece","fastapi"}
for dep in sorted(d.get("dependencies",[]), key=lambda x:x["name"].lower()):
    if dep["name"].lower() in watch: print(f"  {dep['name'].lower():<20} {dep.get('version')}")
print("  total deps:", len(d.get("dependencies",[])))
PY
}

for PYV in 311 312; do
  BIN=/home/z/my-project/repos/venv-audit$PYV/bin/pip-audit
  echo "=== FINAL pip-audit combined on py$PYV: $( $BIN --version 2>/dev/null || echo '?') ==="
  "$BIN" --progress-spinner off \
    -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
    --skip-editable --ignore PYSEC-2026-1325 -f json -o "$OUT/final_audit_py$PYV.json" 2>"$OUT/final_audit_py$PYV.stderr"
  echo "json-run exit=$?"
  "$BIN" --progress-spinner off \
    -r requirements.txt -r requirements/gradio.txt -r hf-space/requirements.txt \
    --skip-editable --ignore PYSEC-2026-1325 > "$OUT/final_audit_py$PYV.log" 2>&1
  echo "text-run exit=$?"
  grep -E "^Found|No known vulnerabilities" "$OUT/final_audit_py$PYV.log" | head -1
  summarize "$OUT/final_audit_py$PYV.json"
  echo
done

echo "=== per-surface final resolution (py3.11) ==="
V=/home/z/my-project/repos/venv-audit311
for s in A requirements.txt; do :; done
"$V/bin/pip" install --dry-run --ignore-installed -q --report "$OUT/final_res_A.json" -r requirements.txt 2>/dev/null; echo "root A exit=$?"
"$V/bin/pip" install --dry-run --ignore-installed -q --report "$OUT/final_res_B.json" -r requirements/gradio.txt 2>/dev/null; echo "root B exit=$?"
"$V/bin/pip" install --dry-run --ignore-installed -q --report "$OUT/final_res_C.json" -r hf-space/requirements.txt 2>/dev/null; echo "root C exit=$?"
python3 - << 'PY'
import json
watch={"gradio","pillow","transformers","torch","paddlepaddle","paddleocr","sentencepiece","numpy","huggingface-hub","pydantic"}
for label in ("A","B","C"):
    d=json.load(open(f'/home/z/my-project/download/task02d-evidence/final_res_{label}.json'))
    pkgs={i["metadata"]["name"].lower():i["metadata"]["version"] for i in d.get("install",[])}
    sel={k:v for k,v in pkgs.items() if k in watch}
    print(f"  root {label}: " + ", ".join(f"{k}={v}" for k,v in sorted(sel.items())) + f"  ({len(pkgs)} pkgs)")
PY

echo
echo "=== NEGATIVE CONTROL (isolated, no repo files touched) ==="
TMPD=$(mktemp -d); printf 'pyyaml==5.3.1\n' > "$TMPD/neg.txt"
/home/z/my-project/repos/venv-audit311/bin/pip-audit --progress-spinner off -r "$TMPD/neg.txt" > "$OUT/final_negative_control.log" 2>&1
echo "negative exit=$? (expect non-zero)"
grep -E "^Found|pyyaml" "$OUT/final_negative_control.log" | head -3
rm -rf "$TMPD"
