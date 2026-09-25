#!/usr/bin/env bash
# TASK-02D — Negative security control + env-mode audits of the installed state
set -uo pipefail
EV=/home/z/my-project/download/task02d-evidence
PA_OLD=/home/z/my-project/repos/venv-old-scan/bin/pip-audit

echo "== [1] NEGATIVE CONTROL (file mode — the mode the workflow uses) =="
printf 'pyyaml==5.3.1\n' > "$EV/negcontrol-requirements.txt"
set +e
"$PA_OLD" -r "$EV/negcontrol-requirements.txt" > "$EV/negcontrol_filemode.log" 2>&1
echo "negctl file-mode exit: $? (expect non-zero)"
grep -E "pyyaml|PYSEC|GHSA|vulnerab" "$EV/negcontrol_filemode.log" | head -5
set -e

echo "== [2] NEGATIVE CONTROL (env mode, isolated venv) =="
export PATH="$HOME/.local/bin:$PATH"
uv venv /home/z/my-project/repos/venv-negctl --python 3.11 >/dev/null 2>&1
uv pip install --python /home/z/my-project/repos/venv-negctl/bin/python -q pyyaml==5.3.1 pip-audit 2>&1 | tail -1
set +e
/home/z/my-project/repos/venv-negctl/bin/pip-audit -f json -o "$EV/negcontrol_envmode.json" > "$EV/negcontrol_envmode.log" 2>&1
echo "negctl env-mode exit: $? (expect non-zero)"
python3 -c "
import json
d = json.load(open('$EV/negcontrol_envmode.json'))
for dep in d.get('dependencies', []):
    for v in dep.get('vulns', []) or []:
        print(f\"  detected: {dep['name']} {dep['version']} {v['id']}\")"
set -e

echo "== [3] ENV-MODE audit: production smoke venv (Surface C installed state) =="
uv pip install --python /home/z/my-project/repos/venv-t02d-prod/bin/python -q pip-audit 2>&1 | tail -1
set +e
/home/z/my-project/repos/venv-t02d-prod/bin/pip-audit --skip-editable -f json -o "$EV/AFTER_envmode_prod.json" > "$EV/AFTER_envmode_prod.log" 2>&1
echo "prod env-mode exit: $?"
python3 -c "
import json
d = json.load(open('$EV/AFTER_envmode_prod.json'))
n = 0
for dep in d.get('dependencies', []):
    for v in dep.get('vulns', []) or []:
        n += 1; print(f\"  {dep['name']} {dep['version']} {v['id']}\")
print(f'  prod env findings: {n}')"
set -e

echo "== [4] ENV-MODE audit: Surface A test venv (dev.txt installed state) =="
uv pip install --python /home/z/my-project/repos/venv-t02d-a/bin/python -q pip-audit 2>&1 | tail -1
set +e
/home/z/my-project/repos/venv-t02d-a/bin/pip-audit --skip-editable -f json -o "$EV/AFTER_envmode_A.json" > "$EV/AFTER_envmode_A.log" 2>&1
echo "A env-mode exit: $?"
python3 -c "
import json
d = json.load(open('$EV/AFTER_envmode_A.json'))
n = 0
for dep in d.get('dependencies', []):
    for v in dep.get('vulns', []) or []:
        n += 1; print(f\"  {dep['name']} {dep['version']} {v['id']}\")
print(f'  surface-A env findings: {n} (expect only ecdsa PYSEC-2026-1325)')"
set -e
echo DONE
