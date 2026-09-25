#!/usr/bin/env bash
# TASK-02D — BEFORE audit reproduction (Phase: RE-AUDIT)
# Reproduces, from a clean sandbox, both audit modes:
#   1) ENV-WIDE  (old CI behavior)      -> expected: nltk false positive (scanner tooling)
#   2) EXPLICIT  (production surfaces)  -> expected: the real production vulnerability set
set -uo pipefail
EV=/home/z/my-project/download/task02d-evidence
REPO=/home/z/my-project/repos/omni-medical-suite
PY=/home/z/my-project/repos/venv-old-scan/bin/python
PA=/home/z/my-project/repos/venv-old-scan/bin/pip-audit
mkdir -p "$EV"
cd "$REPO"

echo "== [0] record environment =="
"$PY" -m pip freeze > "$EV/before_pip_freeze.txt" 2>/dev/null || "$PY" -c "import importlib.metadata as m; [print(f'{d.metadata[\"Name\"]}=={d.version}') for d in m.distributions()]" > "$EV/before_pip_freeze.txt"
wc -l "$EV/before_pip_freeze.txt"

echo "== [1] ENV-WIDE audit (old CI mode) =="
# mirrors: pip-audit --desc --ignore PYSEC-2026-1325
set +e
"$PA" --desc --ignore PYSEC-2026-1325 -f json -o "$EV/BEFORE_envwide.json" > "$EV/BEFORE_envwide.log" 2>&1
RC1=$?
set -e
echo "env-wide exit code: $RC1"
grep -c "nltk" "$EV/BEFORE_envwide.json" || true

echo "== [2] EXPLICIT production-surface audit (TASK-02C mode) =="
set +e
"$PA" --desc \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable \
  -f json -o "$EV/BEFORE_explicit.json" > "$EV/BEFORE_explicit.log" 2>&1
RC2=$?
set -e
echo "explicit exit code: $RC2"

echo "== [3] explicit audit, human-readable with descriptions =="
set +e
"$PA" --desc \
  -r requirements.txt \
  -r requirements/gradio.txt \
  -r hf-space/requirements.txt \
  --skip-editable > "$EV/BEFORE_explicit_human.log" 2>&1
RC3=$?
set -e
echo "explicit human exit code: $RC3"
tail -5 "$EV/BEFORE_explicit_human.log"

echo "== [4] per-surface audits for surface mapping =="
for f in requirements.txt requirements/gradio.txt hf-space/requirements.txt; do
  name=$(echo "$f" | tr '/' '_')
  set +e
  "$PA" --desc -r "$f" --skip-editable -f json -o "$EV/BEFORE_surface_${name}.json" > "$EV/BEFORE_surface_${name}.log" 2>&1
  echo "surface $f exit: $?"
  set -e
done
echo "DONE"
