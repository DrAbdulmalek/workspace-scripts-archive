#!/usr/bin/env bash
# TASK-02C — Reproduce the OLD "Scan Dependencies" environment exactly as
# .github/workflows/security-scan.yml step "Install project dependencies and scanners" does.
# Mirrors: python -m pip install --upgrade pip setuptools wheel
#          pip install -r requirements.txt
#          pip install --upgrade setuptools
#          pip install safety pip-audit
set -euo pipefail

REPO=/home/z/my-project/repos/omni-medical-suite
VENV=/home/z/my-project/repos/venv-old-scan
cd "$REPO"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

python -m pip install --upgrade pip setuptools wheel 2>&1 | tail -2
echo "=== [1/3] pip install -r requirements.txt ==="
pip install -r requirements.txt 2>&1 | tail -4
echo "=== [2/3] pip install --upgrade setuptools ==="
pip install --upgrade setuptools 2>&1 | tail -2
echo "=== [3/3] pip install safety pip-audit ==="
pip install safety pip-audit 2>&1 | tail -4

echo "=== ENVIRONMENT SNAPSHOT ==="
python --version
pip --version
pip list 2>/dev/null | grep -iE "^(nltk|safety|pip-audit|scanner.?fixer|safety-schemas|dparse|regex|click|typer) " || true
echo "=== safety dependency chain (pip show) ==="
pip show safety 2>/dev/null | grep -E "^(Name|Version|Requires)"
echo "=== what requires nltk (reverse deps scan) ==="
python - << 'PY'
from importlib.metadata import distributions
who = []
for d in distributions():
    reqs = d.requires or []
    for r in reqs:
        base = r.split(';')[0].strip().split(' ')[0].split('>=')[0].split('==')[0].split('<')[0].split('>')[0].split('[')[0].strip()
        if base.lower() == 'nltk':
            who.append(d.metadata['Name'])
print("packages whose dependency list includes nltk:", who)
PY
