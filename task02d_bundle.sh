#!/usr/bin/env bash
# TASK-02D — finalize evidence bundle
set -e
EV=/home/z/my-project/download/task02d-evidence
SC=/home/z/my-project/scripts
mkdir -p "$EV/scripts"

# generation/verification scripts used in this task
for f in task02d_before_audit.sh task02d_parse_before.py task02d_after_audit.sh \
         task02d_testdiff.py task02d_negcontrol_envaudit.sh \
         smoke_pillow.py smoke_transformers.py smoke_gradio_app.py smoke_api_ocr.py; do
  cp "$SC/$f" "$EV/scripts/" 2>/dev/null || echo "missing: $f"
done

# save the exact working-tree diff for the record
cd /home/z/my-project/repos/omni-medical-suite
git diff > "$EV/TASK-02D.patch"
git diff --stat > "$EV/TASK-02D-diffstat.txt"
git status --short > "$EV/final_git_status.txt"

echo "=== evidence bundle contents ==="
ls -la "$EV" | awk '{print $5, $9}' | tail -n +2
echo "--- scripts ---"
ls "$EV/scripts"
