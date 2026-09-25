#!/usr/bin/env bash
# TASK-02C — Evidence bundle: safety behavior, scanner-fixer exit-code control,
# coverage proof, negative test, duplicate-handling notes.
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02c-evidence
mkdir -p "$OUT"
cd "$REPO"
source /home/z/my-project/repos/venv-old-scan/bin/activate

echo "=============================================================="
echo "[1] SAFETY CHECK in combined OLD env (prod + scanners + nltk)"
echo "    Question: does safety's DB flag nltk too?"
echo "=============================================================="
timeout 300 safety check --full-report --ignore 64396 --ignore 64459 > "$OUT/safety_check_old_env.log" 2>&1
SAFETY_RC=$?
echo "safety exit code: $SAFETY_RC"
grep -inE "nltk|vulnerab|no known|Reported" "$OUT/safety_check_old_env.log" | head -8
tail -5 "$OUT/safety_check_old_env.log"

echo
echo "=============================================================="
echo "[2] CONTROL: pip-audit -r requirements.txt ONLY (api+ml+base)"
echo "    Expect: exit 0 (ecdsa ignored as documented) while"
echo "    scanner-fixer skip message still present -> proves the"
echo "    scanner-fixer message is informational, exit-code-neutral."
echo "=============================================================="
pip-audit --progress-spinner off -r requirements.txt --skip-editable \
  --ignore PYSEC-2026-1325 > "$OUT/control_reqtxt_only.log" 2>&1
CTRL_RC=$?
echo "control exit code: $CTRL_RC"
grep -E "^Found" "$OUT/control_reqtxt_only.log"
grep -in "scanner-fixer" "$OUT/control_reqtxt_only.log" | head -3

echo
echo "=============================================================="
echo "[3] COVERAGE PROOF: full audited dependency list (JSON)"
echo "    Verify: base/api/ml/gradio/hf-space deps present;"
echo "    nltk/safety/pip-audit/regex/dparse/safety-schemas ABSENT."
echo "=============================================================="
pip-audit --progress-spinner off \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable \
  --ignore PYSEC-2026-1325 \
  -f json > "$OUT/NEW_audit.json" 2>"$OUT/NEW_audit_json.stderr"
JSON_RC=$?
echo "json-run exit code: $JSON_RC"
python3 - "$OUT/NEW_audit.json" << 'PY'
import json, sys
d = json.load(open(sys.argv[1]))
deps = d.get("dependencies", [])
names = sorted({x["name"].lower() for x in deps})
print(f"total distinct packages in audited target set: {len(names)}")
must_have = ["fastapi","sqlalchemy","qdrant-client","celery","python-jose","cryptography",
             "scikit-learn","scikit-image","lmdb","opencv-python-headless","pymupdf",
             "matplotlib","arabic-reshaper","sentencepiece","jiwer","symspellpy",
             "gradio","paddleocr","paddlepaddle","huggingface-hub","datasets","pandas",
             "torch","transformers","numpy","pillow","pydantic","uvicorn"]
missing = [m for m in must_have if m not in names]
print("must-have production deps present:", "YES - all" if not missing else f"MISSING: {missing}")
scanner = ["nltk","safety","pip-audit","regex","dparse","safety-schemas","typer","authlib","cyclonedx-python-lib"]
leaked = [s for s in scanner if s in names]
print("scanner-only deps leaked into audit target:", leaked if leaked else "NONE (correctly excluded)")
print()
print("packages in audited set (first 60):")
print(", ".join(names[:60]))
PY

echo
echo "=============================================================="
echo "[4] NEGATIVE TEST: isolated temp requirements with a"
echo "    known-vulnerable pin (pyyaml==5.3.1). No repo file touched."
echo "    Expect: non-zero exit + advisory detection."
echo "=============================================================="
TMPD=$(mktemp -d)
printf 'pyyaml==5.3.1\n' > "$TMPD/req-negative-test.txt"
pip-audit --progress-spinner off -r "$TMPD/req-negative-test.txt" > "$OUT/negative_test.log" 2>&1
NEG_RC=$?
echo "negative-test exit code: $NEG_RC"
grep -E "^Found|pyyaml.*PYSEC|pyyaml.*CVE|pyyaml.*GHSA" "$OUT/negative_test.log" | head -4
echo "$TMPD" > /tmp/negtmp_path
rm -rf "$TMPD"

echo
echo "SUMMARY CODES: safety=$SAFETY_RC control=$CTRL_RC json=$JSON_RC negative=$NEG_RC"
