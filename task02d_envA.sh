#!/usr/bin/env bash
# TASK-02D — Environment A (requirements.txt surface = api.txt + ml.txt)
# Mirror of .github/workflows/lint-test.yml install recipe, post-fix pins.
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
cd "$REPO"

VA=/home/z/my-project/repos/venv-envA
if [ ! -d "$VA" ]; then
  uv venv "$VA" --python 3.11 --seed 2>&1 | tail -1
fi
PIP=("$VA/bin/python" -m pip)
"${PIP[@]}" install -q --upgrade pip 2>&1 | tail -1

echo "=== install (lint-test recipe) ==="
"${PIP[@]}" install -q pytest pytest-cov pytest-asyncio 2>&1 | tail -1
"${PIP[@]}" install -q opencv-python Pillow numpy 2>&1 | tail -1
"${PIP[@]}" install -q "huggingface-hub<1.0.0" "pydantic<2.11.0" 2>&1 | tail -1
"${PIP[@]}" install -q python-jose passlib bcrypt python-multipart 2>&1 | tail -1
"${PIP[@]}" install -q httpx gradio 2>&1 | tail -1
"${PIP[@]}" install -q -r requirements/api.txt 2>&1 | tail -2
"${PIP[@]}" install -q -r requirements/ml.txt 2>&1 | tail -2
"${PIP[@]}" install -q -e packages/scanner_fixer 2>&1 | tail -1

echo "=== resolved security-relevant versions in Env A ==="
"$VA/bin/python" - << 'PY'
from importlib.metadata import version
for p in ("gradio","pillow","huggingface_hub","pydantic","fastapi","numpy","opencv-python-headless","Pillow"):
    try: print(f"  {p:<24} {version(p)}")
    except Exception: pass
PY

echo "=== pip check (Env A) ==="
"$VA/bin/python" -m pip check 2>&1 | tail -3
echo "pip check exit=$?"

echo "=== import smoke (Env A) ==="
"$VA/bin/python" - << 'PY'
import importlib
mods = ["fastapi","PIL","cv2","jose","passlib","sqlalchemy","celery","qdrant_client","httpx","gradio","pandas","skimage","matplotlib","openpyxl","fpdf","pdfplumber","pymupdf","langdetect","rapidfuzz","lmdb"]
bad = []
for m in mods:
    try: importlib.import_module(m)
    except Exception as e: bad.append((m, str(e)[:80]))
print("imports OK" if not bad else f"IMPORT FAILURES: {bad}")
PY

echo "=== pytest (lint-test selection, post-fix Env A) ==="
export ENVIRONMENT=development DEBUG=true JWT_SECRET_KEY='ci-test-secret-key-32-chars-long!!'
"$VA/bin/python" -m pytest tests/ -q --tb=short -p no:cacheprovider \
  --ignore=tests/test_build_training_data.py \
  --ignore=tests/test_mobile_review_server.py \
  --ignore=tests/integration/ \
  --ignore=tests/test_e2e.py \
  --ignore=tests/test_htr.py \
  --ignore=tests/test_integration.py \
  --ignore=tests/test_integration_full.py \
  --ignore=tests/test_api_performance.py \
  --ignore=tests/test_ocr_engine.py \
  --ignore=tests/test_performance.py \
  --ignore=tests/test_pr92_production_specialty_runtime.py \
  --ignore=tests/test_sensitive_scanner.py \
  --ignore=tests/test_summarizer.py \
  > "$OUT/pytest_envA_postfix.log" 2>&1
echo "pytest exit=$?"
tail -5 "$OUT/pytest_envA_postfix.log"
