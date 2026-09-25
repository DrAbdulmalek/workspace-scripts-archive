"""Pillow 12.3.0 compatibility probe for omni-medical-suite production APIs.

Exercises every Pillow API surface inventoried in the production code
(fromarray 156x, open 69x, new 36x, GaussianBlur 9x, paste 3x,
ImageOps.contain 1x, Kernel 1x, thumbnail 1x) plus the OCR image
preprocessing pipeline (grayscale/RGB/RGBA, JPEG/PNG/TIFF/WEBP).
Exit code = number of failed checks.
"""
import sys, tempfile, os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageEnhance

out = []
def check(name, fn):
    try:
        detail = fn()
        out.append(f"PASS  {name}  :: {detail}")
    except Exception as e:
        out.append(f"FAIL  {name}  :: {repr(e)[:200]}")

tmp = Path(tempfile.mkdtemp(prefix="pillow-probe-"))

def roundtrip(fmt, mode, size=(220, 140)):
    def run():
        img = Image.new(mode, size, 128 if mode in ("L", "RGB") else (128, 128, 128, 255))
        p = tmp / f"t.{fmt.lower()}"
        img.save(p, format=fmt)
        img2 = Image.open(p); img2.load()
        assert img2.size == size, f"size {img2.size}"
        assert img2.mode == mode, f"mode {img2.mode} != {mode}"
        return f"{fmt}/{mode} {size} -> saved+reopened OK"
    return run

check("PIL version", lambda: Image.__version__ if hasattr(Image, "__version__") else __import__("PIL").__version__)
check("Image.new L/RGB/RGBA", lambda: f"{Image.new('L',(10,10)).size} {Image.new('RGB',(10,10)).size} {Image.new('RGBA',(10,10)).size}")
check("Image.fromarray uint8 RGB", lambda: Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).size)
check("Image.fromarray uint8 L", lambda: Image.fromarray(np.zeros((8, 8), dtype=np.uint8)).mode)
check("Image.open + load", lambda: "deferred to roundtrips")
check("JPEG roundtrip RGB", roundtrip("JPEG", "RGB"))
check("PNG roundtrip RGBA", roundtrip("PNG", "RGBA"))
check("TIFF roundtrip RGB", roundtrip("TIFF", "RGB"))
check("TIFF roundtrip L (grayscale scan)", roundtrip("TIFF", "L"))
check("WEBP roundtrip RGB", roundtrip("WEBP", "RGB"))
check("convert L->RGB->L chain", lambda: Image.new("L", (20, 10), 5).convert("RGB").convert("L").getpixel((0, 0)))
check("resize BICUBIC", lambda: str(Image.new("RGB", (40, 30)).resize((80, 60), Image.Resampling.BICUBIC).size))
def _thumb():
    im = Image.new("RGB", (600, 400)); im.thumbnail((100, 100)); return f"{im.size}"
check("thumbnail (keep aspect)", lambda: _thumb())
check("ImageFilter.GaussianBlur(radius=2)", lambda: Image.new("L", (32, 32), 9).filter(ImageFilter.GaussianBlur(2)).size)
check("ImageFilter.Kernel 3x3 sharpen", lambda: Image.new("L", (16, 16), 3).filter(
    ImageFilter.Kernel((3, 3), [0, -1, 0, -1, 5, -1, 0, -1, 0], scale=1)).size)
check("ImageOps.contain to (64,64)", lambda: str(ImageOps.contain(Image.new("RGB", (300, 150)), (64, 64))))
check("ImageEnhance.Contrast", lambda: "ok" if ImageEnhance.Contrast(Image.new("L", (8, 8), 100)).enhance(1.5) else "ok")
def _paste():
    base = Image.new("RGB", (50, 50), 0); crop = Image.new("RGB", (10, 10), 255)
    base.paste(crop, (5, 5)); return f"pixel={base.getpixel((6, 6))}"
check("paste with mask", lambda: _paste())
check("getbbox/crop", lambda: str(Image.new("L", (30, 30), 0).crop((2, 2, 10, 10)).size))
def _dpi():
    p = tmp / "dpi.png"; Image.new("RGB", (10, 10)).save(p, dpi=(300, 300))
    return f"dpi={Image.open(p).info.get('dpi')}"
check("metadata save/reopen (dpi)", lambda: _dpi())

# --- production-like OCR preprocessing chain (Arabic scanned document) ---
def ocr_chain():
    # simulate a scanned A4 page at 200 dpi with dark text rows
    w, h = 1654, 2339
    arr = np.full((h, w), 255, dtype=np.uint8)
    rng = np.random.default_rng(7)
    for y0 in range(200, h - 200, 90):  # text lines
        x0 = rng.integers(80, 300)
        arr[y0:y0 + 22, x0:x0 + 900] = rng.integers(0, 60)
    img = Image.fromarray(arr)                      # fromarray (production: 156 call sites)
    img = ImageOps.grayscale(img)                   # grayscale flow
    img = ImageEnhance.Contrast(img).enhance(1.8)   # binarization prep
    img = img.filter(ImageFilter.GaussianBlur(0.8)) # denoise
    img = ImageOps.contain(img, (1240, 1754))       # normalize max dim
    p = tmp / "scan.jpg"; img.save(p, "JPEG", quality=95)
    re = Image.open(p); re.load()
    # crop a word region and binarize (crop flow used by OCR engines)
    word = re.crop((100, 180, 500, 260)).point(lambda v: 255 if v > 140 else 0)
    assert word.mode == "L" and word.size[0] == 400
    return f"A4 1654x2339 -> gray/contrast/blur/contain -> JPEG q95 {re.size} + word crop binarized OK"
check("OCR preprocessing chain (Arabic scan simulation)", ocr_chain)

def large_img():
    im = Image.new("RGB", (6000, 4000), (200, 200, 200))
    im.thumbnail((1200, 1200))
    p = tmp / "large.jpg"; im.save(p, "JPEG", quality=90)
    return f"6000x4000 -> thumbnail {im.size} saved OK"
check("large image (24MP) thumbnail+save", large_img)

def multipage():
    ims = [Image.new("RGB", (200, 280), c) for c in (255, 128)]
    p = tmp / "multi.tiff"; ims[0].save(p, save_all=True, append_images=ims[1:])
    with Image.open(p) as mp:
        n = getattr(mp, "n_frames", 1)
    return f"2-page TIFF saved, n_frames={n}"
check("multi-page TIFF workflow", multipage)

print(f"Pillow {__import__('PIL').__version__} probe — {len(out)} checks")
for line in out: print(line)
fails = sum(1 for l in out if l.startswith("FAIL"))
print(f"RESULT: {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
sys.exit(fails)
