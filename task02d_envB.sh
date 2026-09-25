#!/usr/bin/env bash
# TASK-02D — Environment B (requirements/gradio.txt surface) on py3.11.
set -uo pipefail
REPO=/home/z/my-project/repos/omni-medical-suite
OUT=/home/z/my-project/download/task02d-evidence
cd "$REPO"

VB=/home/z/my-project/repos/venv-envB
if [ ! -x "$VB/bin/python" ]; then uv venv "$VB" --python 3.11 --seed >/dev/null 2>&1; fi
"$VB/bin/python" -m pip install -q --upgrade pip 2>&1 | tail -1

echo "=== install -r requirements/gradio.txt ==="
"$VB/bin/python" -m pip install -q -r requirements/gradio.txt 2>&1 | tail -2
echo "install exit=$?"
"$VB/bin/python" -m pip install -q -e packages/scanner_fixer 2>&1 | tail -1

echo "=== resolved versions ==="
"$VB/bin/python" - << 'PY'
from importlib.metadata import version
for p in ("gradio","pillow","huggingface_hub","pydantic","paddlepaddle","paddleocr","numpy","fastapi"):
    try: print(f"  {p:<22} {version(p)}")
    except Exception as e: print(f"  {p:<22} MISSING")
PY

echo "=== pip check ==="
"$VB/bin/python" -m pip check; echo "pip check exit=$?"

echo "=== gradio import + version ==="
"$VB/bin/python" -c "import gradio as gr; print('gradio', gr.__version__)"

echo "=== PIL image pipeline smoke (JPEG/PNG/TIFF/WEBP/gray/RGBA/resize/thumbnail/metadata) ==="
"$VB/bin/python" - << 'PY'
from PIL import Image, ImageFilter
import io, tempfile, os
results = []
base = Image.new("RGB", (400, 300), (200, 30, 30))
for fmt in ("JPEG", "PNG", "TIFF", "WEBP"):
    buf = io.BytesIO(); base.save(buf, format=fmt); buf.seek(0)
    back = Image.open(buf); back.load()
    results.append(f"{fmt}: roundtrip {back.size} mode={back.mode}")
gray = base.convert("L"); results.append(f"grayscale: {gray.mode}")
rgba = base.convert("RGBA"); buf = io.BytesIO(); rgba.save(buf, format="PNG"); buf.seek(0)
back = Image.open(buf); results.append(f"RGBA roundtrip: {back.mode}")
res = base.resize((100, 75), Image.LANCZOS); results.append(f"resize: {res.size}")
base.thumbnail((50, 50)); results.append(f"thumbnail: {base.size}")
base.filter(ImageFilter.GaussianBlur(1.5)); results.append("gaussian blur: ok")
with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
    base.save(f.name, "JPEG", quality=85); os.unlink(f.name)
results.append("file save/load: ok")
print(" | ".join(results))
PY
echo "PIL smoke exit=$?"

echo "=== Arabic OCR text-flow smoke (arabic_reshaper + python-bidi + langdetect + rapidfuzz) ==="
"$VB/bin/python" - << 'PY'
import arabic_reshaper
from bidi.algorithm import get_display
import langdetect, rapidfuzz
txt = "الطبية"
disp = get_display(arabic_reshaper.reshape(txt))
print("reshape+bidi ok:", repr(disp[:10]), "| langdetect:", langdetect.detect("This is a medical report"), "| fuzz:", round(rapidfuzz.fuzz.ratio("omni","omni"),0))
PY
echo "arabic-flow exit=$?"

echo "=== HITL gradio app UI construction (module-level gr.Blocks) on gradio 6.26 ==="
cd "$REPO"
"$VB/bin/python" - << 'PY'
import sys; sys.path.insert(0, "/home/z/my-project/repos/omni-medical-suite")
import importlib
m = importlib.import_module("app.gradio_full_hitl")
demo = getattr(m, "demo", None)
print("module imported; demo type:", type(demo).__name__)
assert demo is not None, "demo not built at import time"
print("Blocks built OK on gradio 6.26")
PY
echo "HITL UI smoke exit=$?"

echo "=== headless launch smoke (random port, prevent_thread_lock) ==="
"$VB/bin/python" - << 'PY'
import sys; sys.path.insert(0, "/home/z/my-project/repos/omni-medical-suite")
import importlib
m = importlib.import_module("app.gradio_full_hitl")
demo = m.demo
app_obj, local_url, shared_url = demo.launch(server_port=0, prevent_thread_lock=True, quiet=True)
print("launched:", local_url)
demo.close()
print("closed OK — launch API compatible with gradio 6.26")
PY
echo "launch smoke exit=$?"
