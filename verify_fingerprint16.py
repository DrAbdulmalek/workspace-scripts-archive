#!/usr/bin/env python3
"""Verify Genspark's 16-hex fingerprint claim (69bb57868d94c64a) against the
raw TOKEN-1 candidate in the owner's upload file — IN MEMORY ONLY.

Prints ONLY: length, sha256 hexdigest prefix (16 chars), placeholder test.
Never prints the value itself. Zero network.
"""
import hashlib
import re

PATH = ('/home/z/my-project/upload/'
        'طلب فتح Issues للتصحيحات المقترحة في مشاريع DrAbdulmalek.txt')
CLAIMED_FP16 = '69bb57868d94c64a'

with open(PATH, 'rb') as fh:
    data = fh.read()

candidates = {}
for m in re.finditer(rb'ghp_[A-Za-z0-9]{20,}', data):
    v = m.group()
    fp = hashlib.sha256(v).hexdigest()
    candidates.setdefault(fp, (len(v), m.start()))

print(f'unique ghp_ candidates: {len(candidates)}')
for fp, (ln, off) in sorted(candidates.items()):
    body = None
    print(f'len={ln} offset={off} sha256_prefix16={fp[:16]}')
    same_body = False
    # placeholder test: strip ghp_ prefix, check all-same-char
    print(f'  matches_genspark_fp16({CLAIMED_FP16}): '
          f'{fp[:16] == CLAIMED_FP16}')
