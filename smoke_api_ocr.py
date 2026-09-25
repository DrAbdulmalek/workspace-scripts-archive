#!/usr/bin/env python3
"""TASK-02D smoke: FastAPI surface (Surface A core) + OCR engines on the upgraded stack."""
import os, sys, io, traceback

sys.path.insert(0, "/home/z/my-project/repos/omni-medical-suite")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")

results = []

def check(name, fn):
    try:
        detail = fn()
        results.append((name, "PASS", detail or ""))
    except Exception as e:
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))
        traceback.print_exc()

def fastapi_surface():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code in (200, 404), f"root -> {r.status_code}"
    r2 = c.get("/api/openapi.json")  # docs enabled in development, mounted under /api
    assert r2.status_code == 200 and "/api/ocr" in r2.text, f"openapi {r2.status_code} missing ocr routes"
    n_paths = len(r2.json().get("paths", {}))
    return f"root={r.status_code}, openapi 200, paths={n_paths}"
check("FastAPI app boot + TestClient + openapi routes", fastapi_surface)

def arabic_nlp_stack():
    import arabic_reshaper
    from bidi.algorithm import get_display
    import langdetect
    from rapidfuzz import fuzz
    s = get_display(arabic_reshaper.reshape("مرضى السكري"))
    langdetect.detect("هذا نص طبي عربي طويل بما يكفي للكشف عن اللغة العربية بشكل موثوق")
    score = fuzz.ratio("diabetes mellitus", "diabetes melitus")
    return f"reshaper+bidi ok, langdetect ok, rapidfuzz score={score}"
check("Arabic NLP stack (reshaper/bidi/langdetect/rapidfuzz)", arabic_nlp_stack)

def pytesseract_ocr():
    from PIL import Image, ImageDraw, ImageFont
    import pytesseract
    img = Image.new("RGB", (700, 160), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 60), "Patient has diabetes mellitus type 2", fill="black",
           font=ImageFont.load_default(size=32))
    txt = pytesseract.image_to_string(img, lang="eng").strip()
    assert "diabetes" in txt.lower(), f"weak OCR: {txt!r}"
    return f"tesseract eng ok: {txt[:50]!r}"
check("pytesseract OCR end-to-end (eng)", pytesseract_ocr)

def paddle_ocr():
    from paddleocr import PaddleOCR
    from PIL import Image, ImageDraw, ImageFont
    import arabic_reshaper
    from bidi.algorithm import get_display
    import numpy as np
    img = Image.new("RGB", (900, 200), "white")
    d = ImageDraw.Draw(img)
    shaped = get_display(arabic_reshaper.reshape("مواعيد العيادة"))
    d.text((60, 80), shaped, fill="black", font=ImageFont.load_default(size=48))
    arr = np.array(img)
    ocr = PaddleOCR(lang="ar", show_log=False) if _paddle_accepts_show_log() else PaddleOCR(lang="ar")
    try:
        res = ocr.predict(arr)
    except Exception:
        res = ocr.ocr(arr)
    assert res is not None
    return f"PaddleOCR(lang='ar') constructed + inference returned {len(res)} result group(s)"
def _paddle_accepts_show_log():
    try:
        import inspect
        from paddleocr import PaddleOCR
        return "show_log" in inspect.signature(PaddleOCR.__init__).parameters
    except Exception:
        return False
check("PaddleOCR Arabic engine (primary production OCR)", paddle_ocr)

print("\n=== API/OCR SMOKE RESULTS ===")
fails = 0
for name, st, err in results:
    print(f"  [{st}] {name}" + (f" — {err}" if err else ""))
    fails += st == "FAIL"
sys.exit(1 if fails else 0)
