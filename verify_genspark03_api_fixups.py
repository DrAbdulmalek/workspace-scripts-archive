#!/usr/bin/env python3
"""REVIEW-GENSPARK-03 fixups — retries with slower pacing + corrected search quoting.
Read-only, unauthenticated. Merges results into api_evidence.json under 'fixups'."""
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
            return r.status, json.loads(r.read().decode('utf-8')), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode('utf-8'))
        except Exception:
            body = None
        return e.code, body, dict(e.headers)
    except Exception:
        return -1, None, {}

fixups = []
def rec(claim, expected, actual, verdict, evidence=''):
    fixups.append({'claim': claim, 'expected': expected, 'actual': actual,
                   'verdict': verdict, 'evidence': evidence})
    print(f"[{verdict}] {claim}\n    expected={expected}\n    actual={actual}"
          + (f"\n    evidence={evidence}" if evidence else ''))
    time.sleep(2.5)

# 1) user public_repos (retry)
s, body, h = get(f'/users/{OWNER}')
if s == 200 and body:
    rec('عدد المستودعات العامة (يعيد حسم 24 مقابل 26)', '24 (جدول) أو 26 (نص)',
        body.get('public_repos'), 'RESOLVED', f"login={body.get('login')}")
else:
    rec('عدد المستودعات العامة', '24 أو 26', f'HTTP {s}', 'BLOCKED')

# 2) public repos list (retry) -> pushed_at + archived flags
s, repos, h = get(f'/users/{OWNER}/repos?per_page=100&sort=pushed&direction=desc')
if s == 200 and isinstance(repos, list):
    rmap = {r['name']: {'pushed_at': r.get('pushed_at'), 'archived': r.get('archived'),
                        'language': r.get('language'), 'description': r.get('description')}
            for r in repos}
    expected_push = {
        'omni-medical-suite': '2026-09-18', 'manjaro-care': '2026-09-06',
        'manjaro-doctor': '2026-08-13', 'dictionaries-csv': '2026-08-02',
        'omni-medical-dictionaries': '2026-08-02', 'telegram-tools': '2026-08-13',
        'intelli-file-manager': '2026-08-02', 'arabic-medical-glossary': '2026-08-02',
        'sync-github': '2026-08-02', 'medical-ocr-demo': '2026-08-02',
        'glossary-api': '2026-08-02', 'medical-ocr-trainer-hf': '2026-08-01',
        'OmniFile_Processor': '2026-08-01', 'reset-net': '2026-09-01',
        'repo-sync-toolkit': '2026-08-01', 'radiology-ai-platform': '2026-08-01',
        'DrAbdulmalek': '2026-06-27', 'arabic-medical-ocr-baseline': '2026-07-07',
        'medical-ocr-ground-truth': '2026-07-07', 'scanner-fixer': '2026-07-07',
        'medical-ocr-trainer': '2026-07-07', 'medical-ocr-benchmarks': '2026-07-07',
        'medical-ocr-training-hub': '2026-07-07', 'medical-handwriting-ocr': '2026-07-07',
    }
    bad = [f'{n}:{(rmap.get(n) or {}).get("pushed_at","")[:10]}|exp:{e}'
           for n, e in expected_push.items()
           if not str((rmap.get(n) or {}).get('pushed_at', '')).startswith(e)]
    rec('أعمدة «آخر push» للـ24 مستودعًا العامًا في جدول Genspark', '24/24 مطابقة',
        f'مطابق={len(expected_push)-len(bad)}/{len(expected_push)}',
        'MATCH' if not bad else 'PARTIAL', 'مخالفات: ' + ('; '.join(bad) if bad else 'لا شيء'))

    ARCH7 = ['arabic-medical-ocr-baseline', 'medical-ocr-ground-truth', 'scanner-fixer',
             'medical-ocr-trainer', 'medical-ocr-benchmarks', 'medical-ocr-training-hub',
             'medical-handwriting-ocr']
    flags = {n: (rmap.get(n) or {}).get('archived') for n in ARCH7}
    rec('isArchived للسبعة الموسومة «مؤرشفة» (فجوة أقرّتها Genspark — سُدَّت)', 'true×7',
        json.dumps(flags), 'MATCH' if all(v is True for v in flags.values()) else 'MISMATCH')
    rec('OmniFile_Processor مؤرشف؟', 'true', (rmap.get('OmniFile_Processor') or {}).get('archived'),
        'MATCH' if (rmap.get('OmniFile_Processor') or {}).get('archived') is True else 'MISMATCH')
    for nm in ('manjaro-care', 'reset-net', 'sync-github', 'repo-sync-toolkit'):
        d = (rmap.get(nm) or {}).get('description')
        if d is not None:
            rec(f'وصف {nm}', 'نص حي', d[:140], 'INFO')
    # language spot checks
    langs = {n: (rmap.get(n) or {}).get('language') for n in
             ('omni-medical-suite', 'manjaro-care', 'manjaro-doctor', 'reset-net', 'sync-github')}
    rec('لغات المستودعات (Shell لمانجارو-دوكتور وريسيت-نت؛ Python للبقية)', 'كما بالجدول',
        json.dumps(langs), 'INFO')
    with open(EV + '.repos.json', 'w', encoding='utf-8') as f:
        json.dump(rmap, f, ensure_ascii=False, indent=2)
else:
    rec('قائمة المستودعات العامة', 'قائمة', f'HTTP {s}', 'BLOCKED')

# 3) suite main tip (retry)
s, body, h = get(f'/repos/{OWNER}/omni-medical-suite/commits?sha=main&per_page=1')
if s == 200 and isinstance(body, list) and body:
    c = body[0]
    rec('آخر commit على main للمستودع الأم', '2026-09-02/03 specialty TM (#114)',
        f"{c['commit']['committer']['date'][:10]} {c['commit']['message'].splitlines()[0][:70]}",
        'MATCH' if 'specialty' in c['commit']['message'].lower() else 'CHECK',
        f"sha={c['sha'][:12]} — يطابق النسخة المحلية 39640a6 إن كان الشا نفسه")
else:
    rec('آخر commit على main للمستودع الأم', '2026-09-02', f'HTTP {s}', 'BLOCKED')

# 4) manjaro-care default tip (retry)
s, body, h = get(f'/repos/{OWNER}/manjaro-care/commits?per_page=1')
if s == 200 and isinstance(body, list) and body:
    c = body[0]
    rec('آخر commit على manjaro-care', '2026-09-02',
        f"{c['commit']['committer']['date'][:10]} {c['commit']['message'].splitlines()[0][:60]}",
        'MATCH' if c['commit']['committer']['date'].startswith('2026-09-02') else 'MISMATCH',
        f"sha={c['sha'][:12]}")
else:
    rec('آخر commit على manjaro-care', '2026-09-02', f'HTTP {s}', 'BLOCKED')

# 5) manjaro-care PR #2 fate (KEY discrepancy — 7 merged in window, not 8)
s, body, h = get(f'/repos/{OWNER}/manjaro-care/pulls/2')
if s == 200 and body:
    rec('manjaro-care PR #2: مدموجة؟ ومتى؟ (ادعاء Genspark: 8 مدمجة بين 09-01 و09-02)',
        'merged=true @2026-09-01..02',
        f"merged={body.get('merged')} merged_at={str(body.get('merged_at'))[:10]} state={body.get('state')} "
        f"title={str(body.get('title'))[:60]}",
        'RESOLVED', 'يحدد ما إذا كان ادعاء «8 مدمجة» صحيحًا أم 7')
else:
    rec('manjaro-care PR #2', 'تفاصيل', f'HTTP {s}', 'BLOCKED')

# 6) bot private probe retry
s, body, h = get(f'/repos/{OWNER}/medical-translation-bot')
rec('medical-translation-bot غير مرئي بدون مصادقة (يدعم «خاص»)', '404', s,
    'MATCH' if s == 404 else ('BLOCKED' if s == 403 else 'CHECK'))

# 7) searches with corrected quoting (spaces, not '+')
def search(q, label, expected, on_match='MATCH'):
    s, body, h = get('/search/issues?q=' + urllib.parse.quote(q) + '&per_page=1')
    time.sleep(6)
    if s == 200 and body and 'total_count' in body:
        tc = body['total_count']
        rec(label, expected, tc, on_match if tc == expected else 'CHECK')
    else:
        rec(label, expected, f'HTTP {s}', 'BLOCKED')

search(f'user:{OWNER} type:pr state:open',
       'إجمالي PR مفتوحة (مجهول يرى العامة فقط؛ توقع 86 إن كان 89 صحيحًا مع 3 خاصة)', 89,
       on_match='CHECK — المفروض 86')
search(f'user:{OWNER} type:pr state:open author:app/dependabot',
       'PR dependabot المفتوحة (ادعاء 60 — كلها على مستودعات عامة)', 60,
       on_match='MATCH')
search(f'user:{OWNER} type:issue state:open',
       'Issues مفتوحة (مجهول يرى العامة فقط؛ توقع 10 من أصل 15 حسب الجدول)', 11,
       on_match='CHECK — المفروض 10')
search(f'user:{OWNER} type:pr is:merged',
       'PR مدمجة (ادعاء 66؛ المجهول يرى العامة فقط)', 66, on_match='CHECK')

# merge into evidence file
with open(EV, encoding='utf-8') as f:
    ev = json.load(f)
ev['fixups'] = fixups
with open(EV, 'w', encoding='utf-8') as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)

counts = {}
for r in fixups:
    counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
print('\n==== FIXUPS SUMMARY ====')
print(json.dumps(counts, indent=2))
