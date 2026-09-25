#!/usr/bin/env python3
"""TASK-02D — parse BEFORE audit JSONs into the findings table."""
import json, sys, collections

EV = "/home/z/my-project/download/task02d-evidence"

def load(name):
    with open(f"{EV}/{name}") as f:
        return json.load(f)

def findings(d):
    """pip-audit JSON: dependencies[].vulns[]"""
    rows = []
    for dep in d.get("dependencies", []):
        for v in dep.get("vulns", []) or []:
            rows.append({
                "package": dep["name"],
                "version": dep["version"],
                "id": v["id"],
                "aliases": v.get("aliases", []),
                "fix_versions": v.get("fix_versions", []),
                "desc": (v.get("description") or "")[:160],
            })
    return rows

# 1) combined explicit audit
comb = findings(load("BEFORE_explicit.json"))
print(f"COMBINED explicit audit: {len(comb)} findings total")
pairs = collections.Counter((r["package"], r["version"], r["id"]) for r in comb)
uniq = sorted(pairs)
print(f"UNIQUE (package, version, advisory) pairs: {len(uniq)}")

# 2) per-surface mapping
surf = {}
for name, fn in [("A:requirements.txt", "BEFORE_surface_requirements.txt.json"),
                 ("B:gradio.txt", "BEFORE_surface_requirements_gradio.txt.json"),
                 ("C:hf-space", "BEFORE_surface_hf-space_requirements.txt.json")]:
    try:
        rows = findings(load(fn))
        surf[name] = {(r["package"], r["id"]) for r in rows}
        print(f"  {name}: {len(rows)} findings, {len(surf[name])} unique pkg+adv")
    except FileNotFoundError:
        print(f"  {name}: MISSING")

print()
print("=" * 100)
print(f"{'Package':<14}|{'Installed':<10}|{'Advisory':<22}|{'Fixed Version':<16}|Surfaces")
print("-" * 100)
for pkg, ver, aid in uniq:
    fxs = [r for r in comb if r["package"] == pkg and r["id"] == aid][0]["fix_versions"]
    ss = [s for s, st in surf.items() if (pkg, aid) in st]
    print(f"{pkg:<14}|{ver:<10}|{aid:<22}|{','.join(fxs) or 'NONE':<16}|{'+'.join(ss)}")

print()
print("Per-package unique advisory counts:")
by_pkg = collections.Counter(p for p, v, a in uniq)
for p, c in sorted(by_pkg.items()):
    vers = {v for pp, v, a in uniq if pp == p}
    print(f"  {p} {'/'.join(vers)}: {c} advisories")

# 3) env-wide audit (old CI mode) — what did it flag?
env = findings(load("BEFORE_envwide.json"))
print(f"\nENV-WIDE (old CI mode) findings: {len(env)}")
for r in sorted({(x['package'], x['version'], x['id']) for x in env}):
    print("  ", r)

# save the table for the report
with open(f"{EV}/BEFORE_findings_table.txt", "w") as f:
    for pkg, ver, aid in uniq:
        fxs = [r for r in comb if r["package"] == pkg and r["id"] == aid][0]["fix_versions"]
        ss = [s for s, st in surf.items() if (pkg, aid) in st]
        f.write(f"{pkg}|{ver}|{aid}|{','.join(fxs) or 'NONE'}|{'+'.join(ss)}\n")
print(f"\nSaved: {EV}/BEFORE_findings_table.txt")
