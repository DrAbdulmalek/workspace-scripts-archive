#!/usr/bin/env python3
"""REVIEW-GENSPARK-03 — secrets presence check (fingerprints only, never raw values).

Cross-checks Genspark's report claims:
  Claim 1: a GitHub PAT (masked ghp_...03b9) was pasted into Genspark chat.
  Claim 2: an external provider key (masked sk-...f8686) was pasted into Genspark chat.

This script scans the local upload file that transited THIS environment and reports:
  - pattern type, count, length, last-4 suffix, SHA-256 fingerprint (16 hex), tagged.
It NEVER prints raw secret material.
"""
import hashlib
import re
import sys

PATH = '/home/z/my-project/upload/طلب فتح Issues للتصحيحات المقترحة في مشاريع DrAbdulmalek.txt'

CLAIMED_GHP_SUFFIX = '03b9'      # from Genspark mask: ghp_...03b9
CLAIMED_GHP_FP16 = '69bb57868d94c64a'  # fingerprint previously verified in this env
CLAIMED_SK_SUFFIX = 'f8686'      # from Genspark mask: sk-...f8686

def fp16(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:16]

def main() -> int:
    try:
        with open(PATH, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f'UPLOAD_FILE MISSING: {PATH}')
        return 2

    print(f'upload file scanned: {len(data)} bytes (raw values never printed)')

    # --- GitHub PAT candidates -------------------------------------------------
    ghp = {m.group() for m in re.finditer(rb'(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{20,}', data)}
    print(f'GHP_TOKEN candidates: {len(ghp)}')
    for t in sorted(ghp):
        sfx = t[-4:].decode('ascii', 'replace')
        f = fp16(t)
        print(f'  GHP_TOKEN len={len(t)} suffix4={sfx} SHA-256-fingerprint16={f}')
        print(f'    suffix==03b9 (Genspark mask)? {sfx == CLAIMED_GHP_SUFFIX}')
        print(f'    fp16=={CLAIMED_GHP_FP16} (prior local verification)? {f == CLAIMED_GHP_FP16}')

    # --- external provider sk- key candidates (word-boundary guarded) ----------
    sk = {m.group() for m in re.finditer(rb'(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}', data)}
    # filter obvious non-keys containing a hyphen-run or spaces (regex excludes spaces already)
    print(f'SK_KEY candidates: {len(sk)}')
    for t in sorted(sk):
        sfx = t[-5:].decode('ascii', 'replace')
        f = fp16(t)
        print(f'  SK_KEY len={len(t)} suffix5={sfx} SHA-256-fingerprint16={f}')
        print(f'    suffix endswith f8686 (Genspark mask)? {sfx.endswith(CLAIMED_SK_SUFFIX)}')

    if not sk:
        print('  => no sk- style key ever transited this environment (claim 2 unverifiable locally)')
    return 0

if __name__ == '__main__':
    sys.exit(main())
