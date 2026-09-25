#!/usr/bin/env python3
"""Classify secret-pattern matches WITHOUT printing any secret value.

For every match we print only: file, pattern class, length, and the first 12
hex chars of sha256(value) (one-way fingerprint). Values stay in memory.
"""
import hashlib
import re
import sys

TARGETS = [
    '/home/z/my-project/upload/طلب فتح Issues للتصحيحات المقترحة في مشاريع DrAbdulmalek.txt',
    '/home/z/my-project/repos/omni-medical-suite/tools/repo_admin/git-sync/config/settings.env.example',
    '/home/z/my-project/repos/omni-medical-suite/apps/handwriting-demo/frontend/dictionary.html',
]

PATTERNS = {
    # label: (pattern, prefix_len_to_ignore_for_placeholder_test)
    'GH-CLASSIC (ghp_)': (rb'ghp_[A-Za-z0-9]{20,}', 4),
    'GH-FINE (github_pat_)': (rb'github_pat_[A-Za-z0-9_]{20,}', 11),
    'GH-OAUTH (gho_/ghs_)': (rb'gh[os]_[A-Za-z0-9]{20,}', 4),
    'HUGGINGFACE (hf_)': (rb'hf_[A-Za-z0-9]{30,}', 3),
    'TELEGRAM-BOT (id:secret)': (rb'[0-9]{8,12}:[A-Za-z0-9_-]{35}', 0),
}

for path in TARGETS:
    try:
        with open(path, 'rb') as fh:
            data = fh.read()
    except OSError as exc:
        print(f'{path}\n  READ ERROR: {exc}')
        continue
    print(path)
    found_any = False
    for label, (pat, plen) in PATTERNS.items():
        seen = {}
        for m in re.finditer(pat, data):
            v = m.group()
            fp = hashlib.sha256(v).hexdigest()[:12]
            seen.setdefault(fp, (len(v), v))
        for fp, (ln, v) in sorted(seen.items()):
            found_any = True
            body = v[plen:].decode('ascii', 'ignore')
            same = len(set(body)) == 1
            print(f'  [{label}] len={ln} sha256_prefix={fp} '
                  f'body_all_same_char={same}')
    if not found_any:
        print('  (no matches)')
