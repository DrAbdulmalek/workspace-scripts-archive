#!/usr/bin/env bash
# TASK-02C — precise enumeration of NEW command findings + exit code
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02c-evidence
cd "$REPO"
source /home/z/my-project/repos/venv-old-scan/bin/activate

pip-audit --progress-spinner off \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable \
  --ignore PYSEC-2026-1325 \
  > "$OUT/NEW_full.log" 2>&1
RC=$?
echo "NEW COMMAND EXIT CODE: $RC"

echo
echo "=== compact findings table (Name/Version/ID/Fix) ==="
grep -E "^[a-zA-Z0-9_.-]+ +[0-9][0-9.A-Za-z+]* +(PYSEC|CVE|GHSA|OSV)" "$OUT/NEW_full.log" \
  | awk '{printf "%-28s %-10s %-20s fix=%s\n", $1, $2, $3, $4}' | sort -u

echo
echo "=== summary line ==="
grep -E "^Found" "$OUT/NEW_full.log"

echo
echo "=== skip-reason table ==="
sed -n '/^Name *Skip Reason/,$p' "$OUT/NEW_full.log"

echo
echo "=== distinct vulnerable packages ==="
grep -E "^[a-zA-Z0-9_.-]+ +[0-9][0-9.A-Za-z+]* +(PYSEC|CVE|GHSA|OSV)" "$OUT/NEW_full.log" | awk '{print $1, $2}' | sort -u

echo
echo "=== ignored IDs present ==="
grep -oE "PYSEC-2026-1325" "$OUT/NEW_full.log" | head -2 | wc -l
grep -nE "ignored|Ignored" "$OUT/NEW_full.log" | head -5
