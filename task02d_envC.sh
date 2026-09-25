#!/usr/bin/env bash
# TASK-02D — Environment C (hf-space/requirements.txt surface) on py3.11,
# mirroring hf-space/Dockerfile install (`pip install -r requirements.txt`).
# DISCLOSED SUBSTITUTION: torch installed from the official CPU index
# (same version pin 2.14.0 resolves; CUDA nvidia extras ~3GB skipped due to
# sandbox disk limits). Runtime semantics for Marian inference unchanged.
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
cd "$REPO"

VC=/home/z/my-project/repos/venv-envC
if [ ! -x "$VC/bin/python" ]; then uv venv "$VC" --python 3.11 --seed >/dev/null 2>&1; fi
"$VC/bin/python" -m pip install -q --upgrade pip 2>&1 | tail -1

echo "=== torch 2.14.0 (CPU index — disclosed substitution) ==="
"$VC/bin/python" -m pip install -q --no-cache-dir "torch==2.14.0" --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -1
echo "torch install exit=$?"

echo "=== install -r hf-space/requirements.txt (Dockerfile.gradio/hf-space path) ==="
"$VC/bin/python" -m pip install --no-cache-dir -q -r hf-space/requirements.txt 2>&1 | tail -2
echo "install exit=$?"

echo "=== resolved versions (Env C) ==="
"$VC/bin/python" - << 'PY'
from importlib.metadata import version
for p in ("gradio","pillow","transformers","torch","huggingface_hub","pydantic","paddlepaddle","paddleocr","numpy"):
    try: print(f"  {p:<22} {version(p)}")
    except Exception: print(f"  {p:<22} MISSING")
PY

echo "=== pip check ==="
"$VC/bin/python" -m pip check; echo "pip check exit=$?"

echo "=== hf-space app_core UI construction on gradio 6.26 ==="
"$VC/bin/python" - << 'PY'
import sys, importlib.util
spec = importlib.util.spec_from_file_location("omni_gradio_app_core", "/home/z/my-project/repos/omni-medical-suite/hf-space/app_core.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print("app_core imported; demo:", type(m.demo).__name__)
assert m.demo is not None
app_obj, url, _ = m.demo.launch(server_name="127.0.0.1", server_port=7903, auth=("smoke","smoke-pass"), prevent_thread_lock=True, quiet=True)
print("AUTHED LAUNCH OK:", url)
import httpx
r = httpx.get(url, auth=("smoke","smoke-pass"), timeout=15)
print("HTTP GET with auth:", r.status_code)
r2 = httpx.get(url, timeout=15)  # no auth
print("HTTP GET without auth (expect 401):", r2.status_code)
m.demo.close()
print("close OK")
PY
echo "authed-launch smoke exit=$?"

echo "=== REAL production translation path: translate_text (MarianMT ar->en) ==="
HF_HOME=/home/z/my-project/repos/.hf_cache "$VC/bin/python" - << 'PY'
import importlib.util, logging
logging.disable(logging.WARNING)
spec = importlib.util.spec_from_file_location("omni_gradio_app_core2", "/home/z/my-project/repos/omni-medical-suite/hf-space/app_core.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
out = m.translate_text("التقرير الطبي جاهز المريض بحاجة إلى فحص", "Arabic → English")
print(out[:400])
PY
echo "translate smoke exit=$?"

echo "=== PIL smoke on Env C (pillow 12.3.0) ==="
"$VC/bin/python" - << 'PY'
from PIL import Image
import io
base = Image.new("RGB", (300, 200), (10, 120, 60))
for fmt in ("JPEG","PNG","TIFF","WEBP"):
    buf = io.BytesIO(); base.save(buf, format=fmt); buf.seek(0)
    back = Image.open(buf); back.load(); assert back.size == (300,200)
print("all format roundtrips OK:", Image.__version__ if hasattr(Image,'__version__') else "PIL")
PY
echo "PIL smoke exit=$?"
