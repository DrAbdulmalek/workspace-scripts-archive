#!/usr/bin/env python3
"""Summarize preserved GitHub evidence JSONs into a compact table for the report."""
import json
from pathlib import Path

BASE = Path("/home/z/my-project")
FILES = {
    "repos_p1 (2026-09-13)": BASE / "download/forensic-audit/evidence/repos_p1.json",
    "gh_repos_detail": BASE / "download/OMNI-EXECUTION/inventories/gh_repos_detail.json",
}

for label, path in FILES.items():
    print(f"===== {label} :: {path.name} =====")
    if not path.exists():
        print("MISSING")
        continue
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        data = data.get("repos", data.get("data", [data]))
    print(f"count={len(data)}")
    print(f"{'name':34} {'vis':8} {'lang':10} {'sizeKB':>9} {'pushed_at':21} {'def_branch':10} {'issues':>6}")
    for r in sorted(data, key=lambda x: x.get("pushed_at") or "", reverse=True):
        vis = "PRIVATE" if r.get("private") else "public"
        print(f"{r.get('name','?'):34} {vis:8} {str(r.get('language')):10} "
              f"{r.get('size',0):>9} {str(r.get('pushed_at')):21} "
              f"{str(r.get('default_branch')):10} {r.get('open_issues_count', r.get('open_issues', 0)):>6}")
    print()
