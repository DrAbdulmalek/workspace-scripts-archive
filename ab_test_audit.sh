#!/usr/bin/env bash
# TASK-02C — A/B test: OLD env-wide pip-audit vs NEW explicit -r audit
# Run from the OLD-environment venv (venv-old-scan) which contains
# production deps + scanner tooling (safety, pip-audit, nltk 3.10.3).
set -uo pipefail

REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02c-evidence
mkdir -p "$OUT"
cd "$REPO"
source /home/z/my-project/repos/venv-old-scan/bin/activate

echo "################################################################"
echo "# A) OLD COMMAND (current CI): pip-audit --desc --ignore PYSEC-2026-1325"
echo "#    env-wide audit of the combined environment (prod + scanners)"
echo "################################################################"
pip-audit --progress-spinner off --desc --ignore PYSEC-2026-1325 > "$OUT/OLD_pip-audit_envwide.log" 2>&1
OLD_RC=$?
echo "OLD exit code: $OLD_RC"
grep -nE "nltk|PYSEC-2026-3740|No fix|error|Warning" "$OUT/OLD_pip-audit_envwide.log" | head -20
echo "--- last 12 lines of OLD log ---"
tail -12 "$OUT/OLD_pip-audit_envwide.log"

echo
echo "################################################################"
echo "# B) NEW COMMAND (proposed fix): explicit production requirement"
echo "#    targets — NOT the ambient environment"
echo "################################################################"
pip-audit --progress-spinner off \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable \
  --desc \
  --ignore PYSEC-2026-1325 > "$OUT/NEW_pip-audit_r_targets.log" 2>&1
NEW_RC=$?
echo "NEW exit code: $NEW_RC"
grep -nE "nltk|PYSEC-2026-3740|scanner-fixer|not found on PyPI|error|Warning|safety|pip-audit" "$OUT/NEW_pip-audit_r_targets.log" | head -20
echo "--- last 15 lines of NEW log ---"
tail -15 "$OUT/NEW_pip-audit_r_targets.log"

echo
echo "SUMMARY: OLD_RC=$OLD_RC  NEW_RC=$NEW_RC"
