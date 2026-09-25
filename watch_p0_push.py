#!/usr/bin/env python3
"""watch_p0_push.py — READ-ONLY post-push evidence collector for the P0 PR chain.

Protocol role: feed the user's Independent Review Gate with RAW, unmodified
remote evidence. Green CI alone is NOT merge-ready; the human gate decides.

What it collects (all anonymous, no credentials, GET only):
  1. git ls-remote                          -> ls-remote-<stamp>.txt
  2. PR lookup (head=branch, base=main)     -> pr-lookup-<stamp>.json
  3. PR detail (base/head SHAs, state)      -> pr-<n>-detail-<stamp>.json
  4. PR commits (must be exactly f69e31a)   -> pr-<n>-commits-<stamp>.json
  5. PR files (must be 14)                  -> pr-<n>-files-<stamp>.json
  6. Combined commit status for head SHA    -> commit-status-<stamp>.json
  7. Check runs for head SHA                -> check-runs-<stamp>.json
  8. Actions workflow runs for head SHA     -> actions-runs-<stamp>.json

Guarantees:
  - Never pushes, never amends, never touches main or #118-#122.
  - JSON files are saved byte-for-byte as received (no filtering, no editing).
  - Prints a compact STATUS verdict; the user reviews the raw files themselves.
"""

import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "DrAbdulmalek/omni-medical-suite"
BRANCH = "fix/p0-phi-egress-and-ocr-observability"
BASE_MAIN = "39640a6dbba741eaf13e078dad64719e147ea79b"
EXPECTED_HEAD = "0e4294a5173c59c007349bf29a80869eb2a60596"
EXPECTED_FILES = 15
EV = "/home/z/my-project/download/p0-push/evidence"
API = f"https://api.github.com/repos/{REPO}"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "p0-push-watcher (read-only evidence collection)",
}


def http_get(url):
    """Anonymous GET. Returns (body_bytes, status, rate_remaining)."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read(), r.status, r.headers.get("x-ratelimit-remaining", "?")
    except urllib.error.HTTPError as e:
        return e.read(), e.code, e.headers.get("x-ratelimit-remaining", "?") if e.headers else "?"


def save(name, data):
    path = os.path.join(EV, name)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as f:
        f.write(data)
    return path


def parse(body):
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def main():
    os.makedirs(EV, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    print(f"=== P0 post-push watcher {stamp}Z — READ-ONLY / anonymous / GET-only ===")

    # ---- 1. git ls-remote -------------------------------------------------
    proc = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{REPO}.git"],
        capture_output=True, text=True, timeout=60,
    )
    save(f"ls-remote-{stamp}.txt", proc.stdout)
    remote_main = remote_branch = None
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, ref = parts
        if ref == "refs/heads/main":
            remote_main = sha
        elif ref == f"refs/heads/{BRANCH}":
            remote_branch = sha
    print(f"[1] remote main  = {remote_main or 'ABSENT'}")
    print(f"    remote branch = {remote_branch or 'NOT PUSHED YET'}")

    if remote_main is not None and remote_main != BASE_MAIN:
        print(f"    !! WARNING: remote main MOVED (expected {BASE_MAIN}) — report to user before anything else")
    if remote_branch is None:
        print("\nSTATUS: BRANCH NOT PUSHED YET — nothing to watch. Waiting for user push (PUSH-INSTRUCTIONS.md Option A/B).")
        return 0
    if remote_branch != EXPECTED_HEAD:
        print(f"    !! WARNING: remote branch SHA {remote_branch} != expected {EXPECTED_HEAD[:12]} — DO NOT proceed; report as-is")

    # ---- 2. PR lookup (403-tolerant) ---------------------------------------
    body, code, remaining = http_get(
        f"{API}/pulls?head={REPO.split('/')[0]}:{BRANCH}&base=main&state=all"
    )
    save(f"pr-lookup-{stamp}.json", body)
    print(f"[2] PR lookup HTTP {code} (rate remaining: {remaining})")
    parsed = parse(body)
    prs = parsed if isinstance(parsed, list) else []
    if code != 200 and not prs:
        print("    !! PR lookup unavailable (rate-limited or error) — continuing with SHA-based evidence only")
        pr = None
    elif not prs:
        print("\nSTATUS: BRANCH PUSHED, NO PR YET — next protocol step: open exactly ONE PR to main using pr-body.md.")
        return 0
    else:
        pr = prs[0]
    if pr is None:
        pr_num = None
    else:
        pr_num, pr_state = pr["number"], pr["state"]
        print(f"    found PR #{pr_num} state={pr_state} draft={pr.get('draft')}")

    # ---- 3-5. PR detail / commits / files (skipped if PR lookup failed) ----
    detail, commits, files = None, [], []
    if pr_num is not None:
        for label, path, fname in (
            ("detail", f"/pulls/{pr_num}", f"pr-{pr_num}-detail-{stamp}.json"),
            ("commits", f"/pulls/{pr_num}/commits?per_page=100", f"pr-{pr_num}-commits-{stamp}.json"),
            ("files", f"/pulls/{pr_num}/files?per_page=100", f"pr-{pr_num}-files-{stamp}.json"),
        ):
            body, code, remaining = http_get(API + path)
            save(fname, body)
            print(f"[{3 if label=='detail' else 4 if label=='commits' else 5}] PR {label} HTTP {code} -> {fname}")
        d = parse(open(os.path.join(EV, f"pr-{pr_num}-detail-{stamp}.json"), "rb").read())
        c = parse(open(os.path.join(EV, f"pr-{pr_num}-commits-{stamp}.json"), "rb").read())
        f_ = parse(open(os.path.join(EV, f"pr-{pr_num}-files-{stamp}.json"), "rb").read())
        if isinstance(d, dict):
            detail = d
        commits = c if isinstance(c, list) else []
        files = f_ if isinstance(f_, list) else []

    if detail:
        head_sha, base_sha = detail["head"]["sha"], detail["base"]["sha"]
        print(f"    head={head_sha[:12]} base={base_sha[:12]} commits={len(commits)} files={len(files)}")
        ok_head = head_sha == EXPECTED_HEAD
        ok_commits = len(commits) == 2 and commits[-1]["sha"] == EXPECTED_HEAD
        ok_files = len(files) == EXPECTED_FILES
        print(f"    head == {EXPECTED_HEAD[:12]}:            {'OK' if ok_head else 'MISMATCH'}")
        print(f"    exactly 2 commits, last == {EXPECTED_HEAD[:12]}: {'OK' if ok_commits else 'CHECK RAW'}")
        print(f"    exactly {EXPECTED_FILES} files:             {'OK' if ok_files else f'ACTUAL {len(files)}'}")
        print(f"    title: {detail.get('title','')!r}")

    # ---- 6-8. CI evidence for head SHA ------------------------------------
    for idx, (label, path, fname) in enumerate(
        (
            ("combined status", f"/commits/{remote_branch}/status", f"commit-status-{stamp}.json"),
            ("check runs", f"/commits/{remote_branch}/check-runs", f"check-runs-{stamp}.json"),
            ("actions runs", f"/actions/runs?head_sha={remote_branch}&per_page=100", f"actions-runs-{stamp}.json"),
        ),
        start=6,
    ):
        body, code, remaining = http_get(API + path)
        save(fname, body)
        print(f"[{idx}] {label} HTTP {code} -> {fname}")

    checks = parse(open(os.path.join(EV, f"check-runs-{stamp}.json"), "rb").read()) or {}
    runs = parse(open(os.path.join(EV, f"actions-runs-{stamp}.json"), "rb").read()) or {}
    cr_list = checks.get("check_runs", [])
    wf_list = runs.get("workflow_runs", [])

    print("\n--- CI check runs (raw verdicts) ---")
    if not cr_list:
        print("    (none yet)")
    for cr in cr_list:
        print(f"    {cr.get('name','?'):<40} status={cr.get('status'):<12} conclusion={cr.get('conclusion')}")
    print("--- Actions workflow runs ---")
    if not wf_list:
        print("    (none yet)")
    for wf in wf_list:
        print(f"    #{wf.get('id')} {str(wf.get('name'))[:38]:<40} status={wf.get('status'):<12} conclusion={wf.get('conclusion')}")
        print(f"        {wf.get('html_url')}")

    # ---- verdict -----------------------------------------------------------
    pending = [c for c in cr_list if c.get("status") != "completed"] + [
        w for w in wf_list if w.get("status") not in ("completed",)
    ]
    failed = [c for c in cr_list if c.get("conclusion") not in ("success", None, "skipped")] + [
        w for w in wf_list if w.get("conclusion") not in ("success", None, "skipped")
    ]
    if pending:
        print("\nSTATUS: CI IN PROGRESS — wait for completion, then re-run watcher.")
    elif failed:
        print(f"\nSTATUS: CI HAS FAILURES ({len(failed)}) — send raw evidence to user AS-IS for Independent Review Gate.")
    elif cr_list or wf_list:
        print("\nSTATUS: CI GREEN — per protocol this does NOT make the PR merge-ready; human diff review is next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
