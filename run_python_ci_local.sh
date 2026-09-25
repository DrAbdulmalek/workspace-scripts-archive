#!/usr/bin/env bash
# Local replication of .github/workflows/python-ci.yml "Run tests" step (PR #123 audit)
# Documented delta: local = Python 3.12.14 venv (/home/z/.venv) vs CI = 3.11 ubuntu-latest
# Evidence out: /home/z/my-project/download/p0-push/evidence/pr123-ci/
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/p0-push/evidence/pr123-ci
mkdir -p "$OUT"
cd "$REPO"
export ENVIRONMENT=development
export DEBUG=true
export JWT_SECRET_KEY='ci-test-secret-key-32-chars-long!!'
python3 -m pytest tests/ -v --tb=short \
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
  > "$OUT/python_ci_local_py312.log" 2>&1
rc=$?
echo "PYTEST_EXIT=$rc"
echo "=== last 45 lines ==="
tail -45 "$OUT/python_ci_local_py312.log"
exit $rc
