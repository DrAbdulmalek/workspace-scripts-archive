"""Gate 3 runtime smoke (no real Hub push) — P0-A/P0-B acceptance evidence.

Run inside the repo with the project venv:
    cd repos/omni-medical-suite && ../venvs/omni/bin/python ../../scripts/gate3_smoke.py

Demonstrates, with huggingface-boundary mocked (never touches network):
  1. OMNI_HF_EXPORT_ENABLED unset → save_to_hf stages locally,
     push_to_hub is NOT called, message says data was saved locally only.
  2. flush_queue() refuses when export is disabled (no fake success).
  3. PaddleOCR raising → structured ocr_status shows paddle_status="error",
     selected_engine/tesseract fallback visible, and NO clean Arabic
     "document" is fabricated.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

REPO = Path("/home/z/my-project/repos/omni-medical-suite")
sys.path.insert(0, str(REPO))

ok = True


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    ok = ok and cond


print("== Gate 3.1: export disabled → local staging only, push_to_hub never called ==")
tmp = tempfile.mkdtemp(prefix="gate3-queue-")
import os

os.environ["OMNI_HF_QUEUE_DIR"] = tmp
os.environ.pop("OMNI_HF_EXPORT_ENABLED", None)
os.environ.pop("OMNI_HF_EXPORT_RAW_TEXT", None)
os.environ.pop("OMNI_HF_DATASET_PRIVATE", None)
for mod in list(sys.modules):
    if "hf_dataset_service" in mod:
        del sys.modules[mod]

import app.services.hf_dataset_service as svc

svc.HAS_HF = True
svc.HF_TOKEN = "smoke-token"
fake_dataset = MagicMock()
svc.Dataset = fake_dataset
svc.load_dataset = MagicMock(side_effect=RuntimeError("no network"))

msg = svc.save_to_hf("نص مصحح", "نص خام", {}, "prescription", consent=True)
print("  save_to_hf message:", json.dumps(msg, ensure_ascii=False))
check("staged locally", svc.count_pending() == 1)
check("push_to_hub NOT called", fake_dataset.from_pandas.return_value.push_to_hub.call_count == 0)
check("message says local-only", "محلياً" in msg and "لم يتم رفع أي بيانات" in msg)

res = svc.flush_queue()
print("  flush_queue message:", json.dumps(res, ensure_ascii=False))
check("flush refuses (no fake success)", "معطّل" in res and fake_dataset.from_pandas.return_value.push_to_hub.call_count == 0)
check("pending rows still local", svc.count_pending() == 1)

print()
print("== Gate 3.2: Paddle raise → visible error, not a clean document ==")
import numpy as np

import app.services.ocr_service as ocr
import app.gradio_full_hitl as hitl


class Boom:
    def ocr(self, *a, **k):
        raise RuntimeError("paddle exploded (simulated)")


ocr.get_paddle_ocr = lambda: Boom()
hitl._run_paddle_ocr = lambda img: ocr._run_paddle_ocr(img)
hitl._run_tesseract = lambda img: ("", 0.0, "unavailable")

image = np.full((32, 32, 3), 200, dtype=np.uint8)
cleaned, corrected, raw_text, entities, status_str, ocr_status = hitl.full_process(image)
print("  ocr_status:", json.dumps(ocr_status, ensure_ascii=False))
check("paddle_status == error", ocr_status["paddle_status"] == "error")
check("no fabricated document", corrected == "" and raw_text == "")
check("user_visible_error present", bool(ocr_status["user_visible_error"]))
check("placeholder never corrected", "[لم يتم اكتشاف نص]" not in corrected)

print()
print("GATE 3 SMOKE:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
