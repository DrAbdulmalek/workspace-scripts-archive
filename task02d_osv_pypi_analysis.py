#!/usr/bin/env python3
"""TASK-02D — advisory range analysis + PyPI availability check.
For each no-fix advisory: fetch OSV record, determine affected ranges
(fixed vs last_affected) to see whether a newer version escapes it.
For target packages: list latest PyPI versions."""
import json, urllib.request, sys

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "task02d-audit"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

NO_FIX = [("gradio","PYSEC-2026-211"),("gradio","PYSEC-2026-1410"),("gradio","PYSEC-2026-1412"),
          ("gradio","PYSEC-2026-1417"),("gradio","PYSEC-2026-1418"),("gradio","PYSEC-2026-1421"),
          ("transformers","PYSEC-2025-217")]

print("=== OSV affected-range analysis for no-fix advisories ===")
for pkg, adv in NO_FIX:
    try:
        rec = get(f"https://api.osv.dev/v1/vulns/{adv}")
    except Exception as e:
        print(f"  {adv} [{pkg}]: FETCH ERROR {e}"); continue
    ranges = []
    for aff in rec.get("affected", []):
        if aff.get("package", {}).get("name", "").lower() != pkg: continue
        for ec in aff.get("ranges", []):
            evs = [e for e in ec.get("events", [])]
            ranges.append(evs)
    # summarize
    summary = []
    for evs in ranges:
        parts = []
        for e in evs:
            for k, v in e.items():
                parts.append(f"{k}={v}")
        summary.append(", ".join(parts))
    aliases = ",".join(rec.get("aliases", [])[:3])
    print(f"  {adv} [{pkg}] aliases={aliases}")
    for s in summary: print(f"      {s}")

print()
print("=== PyPI latest versions ===")
for pkg in ("gradio", "pillow", "transformers", "paddlepaddle", "paddleocr", "numpy", "huggingface-hub", "pydantic"):
    try:
        d = get(f"https://pypi.org/pypi/{pkg}/json")
        print(f"  {pkg}: latest={d['info']['version']}")
    except Exception as e:
        print(f"  {pkg}: ERROR {e}")
