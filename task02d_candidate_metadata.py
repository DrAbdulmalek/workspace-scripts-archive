#!/usr/bin/env python3
"""TASK-02D — candidate version metadata forensics.
Check requires_dist of candidate target versions to detect conflicts
(pydantic caps, numpy<2 from paddle, huggingface_hub, torch)."""
import json, urllib.request

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "task02d-audit"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def requires(pkg, ver=None):
    d = get(f"https://pypi.org/pypi/{pkg}/json")
    v = ver or d["info"]["version"]
    rel = d["releases"].get(v) or []
    # use the version-specific metadata via /pypi/{pkg}/{ver}/json
    dv = get(f"https://pypi.org/pypi/{pkg}/{v}/json")
    return v, dv["info"]["requires_dist"] or []

CANDIDATES = [
    ("gradio", "6.26.0"), ("gradio", "6.16.0"),
    ("transformers", "5.16.1"), ("transformers", "5.10.0"),
    ("paddlepaddle", "3.3.1"), ("paddlepaddle", "3.0.0"),
    ("paddleocr", "2.7.3"), ("paddleocr", "3.7.0"),
]
WATCH = ("pillow","numpy","pydantic","huggingface","torch","fastapi","gradio","typer","regex","python")

for pkg, ver in CANDIDATES:
    try:
        v, rl = requires(pkg, ver)
    except Exception as e:
        print(f"{pkg} {ver}: ERROR {e}"); continue
    hits = [r for r in rl if any(w in r.lower().split(">=")[0].split("<")[0].split("=")[0].split("!")[0].split("[")[0] for w in WATCH)]
    print(f"=== {pkg} {v} ({len(rl)} deps) — relevant constraints:")
    for h in hits: print(f"    {h}")
    print()
