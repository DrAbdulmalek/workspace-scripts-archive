#!/usr/bin/env python3
"""REVIEW-GENSPARK-03 round-3 — per-repo pushed_at/archived spot checks (endpoints that
survive secondary limits) + enumerate the 8 public open issues. Read-only, unauth."""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import os

BASE = 'https://api.github.com'
HDR = {'User-Agent': 'review-genspark-03-read-only-audit', 'Accept': 'application/vnd.github+json'}
OUT_DIR = '/home/z/my-project/download/REVIEW-GENSPARK-03'
OWNER = 'DrAbdulmalek'
EV = os.path.join(OUT_DIR, 'api_evidence.json')

def get(path):
    req = urllib.request.Request(BASE + path, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:
            return e.code, None
    except Exception:
        return -1, None

out = []
def rec(claim, expected, actual, verdict, evidence=''):
    out.append({'claim': claim, 'expected': expected, 'actual': actual,
                'verdict': verdict, 'evidence': evidence})
    print(f"[{verdict}] {claim}\n    expected={expected}\n    actual={actual}"
          + (f"\n    evidence={evidence}" if evidence else ''))
    time.sleep(3)

# pushed_at + archived per-repo (spot checks incl. the divergence claim for telegram-tools)
checks = {
    'telegram-tools': ('2026-08-13', None),
    'DrAbdulmalek': ('2026-06-27', None),
    'medical-ocr-ground-truth': ('2026-07-07', True),
    'scanner-fixer': ('2026-07-07', True),
    'OmniFile_Processor': ('2026-08-01', True),
    'medical-handwriting-ocr': ('2026-07-07', True),
    'radiology-ai-platform': ('2026-08-01', False),
    'repo-sync-toolkit': ('2026-08-01', False),
}
for name, (exp_push, exp_arch) in checks.items():
    s, b = get(f'/repos/{OWNER}/{name}')
    if s == 200 and b:
        push = str(b.get('pushed_at', ''))[:10]
        arch = b.get('archived')
        ok_push = push.startswith(exp_push)
        ok_arch = (exp_arch is None) or (arch == exp_arch)
        rec(f'{name}: pushed_at={exp_push} archived={exp_arch}', 'مطابقة',
            f'pushed_at={push} archived={arch}', 'MATCH' if (ok_push and ok_arch) else 'MISMATCH')
    else:
        rec(f'{name}: pushed_at/archived', 'مطابقة', f'HTTP {s}', 'BLOCKED')

# enumerate public open issues
s, b = get('/search/issues?q=' + urllib.parse.quote(f'user:{OWNER} type:issue state:open') + '&per_page=100&sort=created')
time.sleep(6)
if s == 200 and b and b.get('total_count') is not None:
    items = [{'repo': i['repository_url'].split('/repos/')[-1], 'n': i['number'],
              'title': i['title'][:70], 'created': i['created_at'][:10]} for i in b.get('items', [])]
    rec('سرد Issues المفتوحة على المستودعات العامة (لحسم 11 مقابل 15)', 'قائمة كاملة',
        f"total={b['total_count']}", 'INFO', json.dumps(items, ensure_ascii=False, indent=1))
else:
    rec('سرد Issues المفتوحة العامة', 'قائمة', f'HTTP {s}', 'BLOCKED')

with open(EV, encoding='utf-8') as f:
    ev = json.load(f)
ev['round3'] = out
with open(EV, 'w', encoding='utf-8') as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print('\nsaved to', EV)
