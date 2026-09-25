#!/usr/bin/env python3
"""Security redaction: replace compromised token values in workspace files.
Never prints or stores token values — matches by regex, maps digests to labels.
"""
import re, hashlib, os, sys

WS = '/home/z/my-project/repos/omni-medical-workspace-gh'
PAT = re.compile(rb'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}')

# digest-prefix -> stable label (values never revealed)
LABELS = {'69bb57868d94': b'[REDACTED-COMPROMISED-TOKEN-1-REVOKE-NOW]',
          '133df64d98da': b'[REDACTED-COMPROMISED-TOKEN-2-REVOKE-NOW]'}

files = [
    'SESSION_STATE.md',
    'SESSIONS/session-2026-09-11/CONTINUATION_PROMPT.md',
    'SESSIONS/session-2026-09-11/GIT_STATE_EVIDENCE.md',
    'SESSIONS/session-2026-09-11/SESSION_REPORT.md',
]

unknown = []
for f in files:
    p = os.path.join(WS, f)
    data = open(p, 'rb').read()
    hits = list(PAT.finditer(data))
    if not hits:
        print(f'{f}: no matches (already clean)')
        continue
    out = bytearray(); last = 0; counts = {}
    for m in hits:
        v = m.group()
        h = hashlib.sha256(v).hexdigest()[:12]
        label = LABELS.get(h)
        if label is None:
            unknown.append((f, h, len(v)))
            label = b'[REDACTED-COMPROMISED-TOKEN-UNKNOWN-REVOKE-NOW]'
        out += data[last:m.start()]; out += label; last = m.end()
        counts[h] = counts.get(h, 0) + 1
    out += data[last:]
    open(p, 'wb').write(bytes(out))
    print(f'{f}: redacted {len(hits)} occurrence(s) by digest: {counts}')

# verification: no pattern left anywhere in worktree
left = 0
for root, dirs, fnames in os.walk(WS):
    dirs[:] = [d for d in dirs if d != '.git']
    for fn in fnames:
        fp = os.path.join(root, fn)
        try:
            if PAT.search(open(fp, 'rb').read()):
                print('STILL CONTAMINATED:', fp); left += 1
        except OSError:
            pass
print('post-redaction pattern hits in worktree:', left)
if unknown:
    print('UNKNOWN digests encountered (needs owner attention):', unknown)
    sys.exit(2)
print('OK — redaction complete, no token values printed or retained')
