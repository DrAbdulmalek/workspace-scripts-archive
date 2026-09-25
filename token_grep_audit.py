#!/usr/bin/env python3
"""Classify ghp_/github_pat_ pattern matches in persisted files WITHOUT revealing values.
Prints: file, line no, match length, charset profile, SHA256 digest prefix (12 hex).
Never prints the matched value itself.
"""
import hashlib
import re
import glob
import os

PAT = re.compile(rb'ghp_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}')
ROOTS = [
    '/home/z/my-project/download',
    '/home/z/my-project/upload',
    '/home/z/my-project/scripts',
    '/home/z/my-project/repos/omni-medical-suite/apps/handwriting-demo/frontend/dictionary.html',
    '/home/z/my-project/repos/omni-medical-suite/tools/repo_admin/git-sync/config/settings.env.example',
    '/home/z/my-project/worklog.md',
]

targets = set()
for r in ROOTS:
    if os.path.isfile(r):
        targets.add(r)
    elif os.path.isdir(r):
        for path in glob.glob(os.path.join(r, '**', '*'), recursive=True):
            if os.path.isfile(path) and os.path.getsize(path) < 5_000_000:
                targets.add(path)

found_any = False
for path in sorted(targets):
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except Exception:
        continue
    if b'ghp_' not in data and b'github_pat_' not in data:
        continue
    for m in PAT.finditer(data):
        found_any = True
        v = m.group()
        d12 = hashlib.sha256(v).hexdigest()[:12]
        lower = sum(1 for c in v if 97 <= c <= 122)
        upper = sum(1 for c in v if 65 <= c <= 90)
        digit = sum(1 for c in v if 48 <= c <= 57)
        other = len(v) - lower - upper - digit
        line_no = data[:m.start()].count(b'\n') + 1
        print(f'MATCH file={path} line={line_no} len={len(v)} '
              f'lower={lower} upper={upper} digit={digit} other={other} sha256_12={d12}')

if not found_any:
    print('NO MATCHES FOUND in scanned roots')
