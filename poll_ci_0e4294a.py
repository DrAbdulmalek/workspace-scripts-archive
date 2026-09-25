#!/usr/bin/env python3
"""poll_ci_0e4294a.py — authenticated CI poller for PR #123 new head.
Token from env GT (never printed, never written to disk).
Polls Actions runs for head_sha=0e4294a… until all completed or cycles exhausted."""
import json, os, sys, time, urllib.request

GT = os.environ.get("GT", "")
HEAD = "0e4294a5173c59c007349bf29a80869eb2a60596"
URL = f"https://api.github.com/repos/DrAbdulmalek/omni-medical-suite/actions/runs?head_sha={HEAD}&per_page=100"

def fetch():
    req = urllib.request.Request(URL, headers={
        "Authorization": f"Bearer {GT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "p0-ci-poller (read-only)",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def table(runs):
    lines = []
    done = True
    for r in sorted(runs, key=lambda x: x["name"]):
        st, cc = r["status"], r["conclusion"]
        if st != "completed":
            done = False
        lines.append(f"  {r['name']:<38} {st:<12} {cc if cc else '-'}")
    return done, "\n".join(lines)

cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 6
for i in range(cycles):
    runs = fetch().get("workflow_runs", [])
    done, tbl = table(runs)
    print(f"--- poll {i+1}/{cycles} @ {time.strftime('%H:%M:%S')} : {len(runs)} runs ---")
    print(tbl)
    if done:
        print("ALL_COMPLETED")
        break
    if i < cycles - 1:
        time.sleep(80)
