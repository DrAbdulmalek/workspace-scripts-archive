#!/usr/bin/env python3
"""Check revocation status of the two compromised tokens (in-memory only).

- Extracts candidate token bytes from LOCAL git history objects (99987e1..2a3a8cf).
- Never prints, logs, or writes token values. Prints digest prefix + HTTP verdict only.
- A 200 => token ACTIVE (revocation still pending). A 401 => invalid/revoked.
- Nothing is persisted anywhere; variables die with the process.
"""
import hashlib, json, re, subprocess, urllib.request

REPO = '/home/z/my-project/repos/omni-medical-workspace-gh'
PAT = re.compile(rb'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}')
FILES = ['SESSION_STATE.md',
         'SESSIONS/session-2026-09-11/CONTINUATION_PROMPT.md',
         'SESSIONS/session-2026-09-11/GIT_STATE_EVIDENCE.md',
         'SESSIONS/session-2026-09-11/SESSION_REPORT.md']
COMMIT = '2a3a8cfd186c33ce7eff456978f2a927d5dd2359'

tokens = {}  # digest -> bytes (memory only)
for f in FILES:
    blob = subprocess.run(['git', '-C', REPO, 'show', f'{COMMIT}:{f}'],
                          capture_output=True).stdout
    for m in PAT.finditer(blob):
        v = m.group()
        d = hashlib.sha256(v).hexdigest()[:12]
        tokens.setdefault(d, v)

print(f'candidates extracted from history: {len(tokens)} '
      f'(digests: {", ".join(sorted(tokens))}) — values held in memory only')

for d in sorted(tokens):
    tok = tokens[d]
    req = urllib.request.Request('https://api.github.com/user')
    req.add_header('Authorization', b'Bearer ' + tok)
    req.add_header('User-Agent', 'omni-workspace-security-check')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
            scopes = r.headers.get('X-OAuth-Scopes', '(none)')
            print(f'TOKEN[{d[:12]}]: HTTP {r.status} => ACTIVE — login={body.get("login")}, '
                  f'scopes="{scopes}" → REVOCATION STILL REQUIRED')
    except urllib.error.HTTPError as e:
        detail = ''
        try:
            detail = json.loads(e.read().decode()).get('message', '')
        except Exception:
            pass
        if e.code == 401:
            print(f'TOKEN[{d[:12]}]: HTTP 401 => INVALID/REVOKED ({detail}) → risk from this token CLOSED')
        else:
            print(f'TOKEN[{d[:12]}]: HTTP {e.code} => INCONCLUSIVE ({detail}) — re-check needed')
    except Exception as ex:
        print(f'TOKEN[{d[:12]}]: NETWORK/OTHER ERROR ({type(ex).__name__}) — INCONCLUSIVE')

# best-effort memory hygiene
tokens.clear()
print('done — no values written to disk, logs, or stdout')
