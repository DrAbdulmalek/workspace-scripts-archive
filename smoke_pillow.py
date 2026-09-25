#!/usr/bin/env python3
"""TASK-02D smoke: Pillow 12.3.0 compatibility for the medical image pipeline.

Exercises every Pillow API surface used by the production code paths
(hf-space/packages/vision/*, app/scanner_tab.py, packages/omni_ocr/*,
packages/scanner_fixer) plus the Arabic-text rendering flow.
"""
import io, sys, traceback

results = []

def check(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
    except Exception as e:
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))
        traceback.print_exc()

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
import arabic_reshaper
from bidi.algorithm import get_display

R = (255, 0, 0); G = (0, 255, 0); B = (0, 0, 255)

def rnd(w, h, mode="RGB"):
    img = Image.new(mode, (w, h))
    d = ImageDraw.Draw(img)
    for i in range(0, w, 16):
        d.line([(i, 0), (i, h)], fill=(R if i % 32 else G) if mode == "RGB" else (255 if i % 32 else 0), width=4)
    return img

# 1. JPEG RGB
def jpeg_rgb():
    img = rnd(256, 128, "RGB")
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=90)
    buf.seek(0); out = Image.open(buf); out.load()
    assert out.format == "JPEG" and out.size == (256, 128) and out.mode == "RGB"
check("JPEG open/save RGB", jpeg_rgb)

# 2. PNG RGBA + alpha_composite
def png_rgba():
    img = rnd(128, 128, "RGBA")
    buf = io.BytesIO(); img.save(buf, "PNG")
    buf.seek(0); out = Image.open(buf).convert("RGBA")
    bg = Image.new("RGBA", out.size, (255, 255, 255, 255))
    comp = Image.alpha_composite(bg, out)
    assert comp.mode == "RGBA" and comp.size == (128, 128)
check("PNG RGBA + alpha_composite", png_rgba)

# 3. TIFF multi-page
def tiff_multi():
    a, b = rnd(64, 64, "RGB"), rnd(64, 64, "RGB")
    buf = io.BytesIO(); a.save(buf, "TIFF", save_all=True, append_images=[b])
    buf.seek(0); t = Image.open(buf)
    n = 1
    try:
        while True:
            t.seek(n); n += 1
    except EOFError:
        pass
    assert n == 2, f"expected 2 pages, got {n}"
check("TIFF multi-page save/load", tiff_multi)

# 4. WEBP
def webp():
    img = rnd(100, 60, "RGB")
    buf = io.BytesIO(); img.save(buf, "WEBP", quality=80)
    buf.seek(0); out = Image.open(buf)
    assert out.format == "WEBP" and out.size == (100, 60)
check("WEBP open/save", webp)

# 5. grayscale / conversions used by OCR preprocessing
def gray():
    img = rnd(120, 120, "RGB")
    g = img.convert("L")
    assert g.mode == "L"
    back = g.convert("RGB")
    assert back.mode == "RGB"
    arr_like = g.point(lambda p: 255 if p > 128 else 0)  # binarization used by OCR flows
    assert arr_like.mode == "L"
check("grayscale convert + binarize", gray)

# 6. resize/thumbnail/crop/rotate/transpose (scanner_fixer + HTR line pipeline)
def geo():
    img = rnd(400, 300, "RGB")
    r1 = img.resize((200, 150), Image.Resampling.BILINEAR)
    assert r1.size == (200, 150)
    t = img.copy(); t.thumbnail((100, 100))
    assert max(t.size) <= 100
    c = img.crop((0, 0, 50, 50)); assert c.size == (50, 50)
    rot = img.rotate(90, expand=True); assert rot.size == (300, 400)
    flip = ImageOps.flip(img); assert flip.size == img.size
    gray_autocontrast = ImageOps.autocontrast(img.convert("L"))
    assert gray_autocontrast.mode == "L"
check("resize/thumbnail/crop/rotate/transpose/autocontrast", geo)

# 7. filters + enhancers (scanner deskew/denoise flows)
def filt():
    img = rnd(128, 128, "L")
    img.filter(ImageFilter.MedianFilter(3))
    img.filter(ImageFilter.GaussianBlur(1.5))
    img.filter(ImageFilter.SHARPEN)
    ImageEnhance.Contrast(img).enhance(1.5)
    ImageEnhance.Sharpness(img).enhance(2.0)
check("filters + enhance", filt)

# 8. Arabic text rendering path (arabic-reshaper + bidi + PIL draw)
def arabic_render():
    text = "الرحيل إلى العيادة"
    shaped = get_display(arabic_reshaper.reshape(text))
    img = Image.new("RGB", (600, 100), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=28)
    d.text((10, 30), shaped, fill="black", font=font)
    buf = io.BytesIO(); img.save(buf, "PNG")
    buf.seek(0); out = Image.open(buf); out.load()
    assert out.size == (600, 100)
check("Arabic reshaper+bidi+PIL render", arabic_render)

# 9. large image (document scan scale)
def large():
    img = Image.new("RGB", (2480, 3500), "white")  # A4 @300dpi
    d = ImageDraw.Draw(img); d.rectangle([100, 100, 2380, 3400], outline="black", width=5)
    small = img.resize((620, 875))
    assert small.size == (620, 875)
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=75)
    assert buf.tell() > 0
check("large A4@300dpi image ops", large)

# 10. EXIF/metadata round-trip
def meta():
    img = rnd(64, 64, "RGB")
    exif = Image.Exif(); exif[274] = 1  # orientation
    buf = io.BytesIO(); img.save(buf, "JPEG", exif=exif)
    buf.seek(0); out = Image.open(buf)
    _ = ImageOps.exif_transpose(out)
    assert out.getexif().get(274) == 1
check("EXIF metadata + exif_transpose", meta)

print("\n=== PILLOW SMOKE RESULTS ===")
fails = 0
for name, st, err in results:
    print(f"  [{st}] {name}" + (f" — {err}" if err else ""))
    fails += st == "FAIL"
import PIL
print(f"Pillow version: {PIL.__version__}")
sys.exit(1 if fails else 0)
