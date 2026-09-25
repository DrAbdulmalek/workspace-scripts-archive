#!/usr/bin/env python3
"""REVIEW-GENSPARK-03 — live GitHub verification (unauthenticated, READ-ONLY).

Verifies Genspark's portfolio-review claims against public GitHub API.
No tokens, no credentials, no mutations anywhere. Results saved as JSON evidence.
Unauthenticated caveat: private repos return 404 and search sees public repos only.
"""
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
os.makedirs(OUT_DIR, exist_ok=True)

results = []
raw_evidence = {}

def get(path):
    req = urllib.request.Request(BASE + path, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode('utf-8')), dict(r.headers)
    except urllib.error.HTTPError as e:
        body = None
        try:
            body = json.loads(e.read().decode('utf-8'))
        except Exception:
            pass
        return e.code, body, dict(e.headers)
    except Exception:
        return -1, None, {}

def rec(claim, expected, actual, verdict, evidence=''):
    results.append({'claim': claim, 'expected': expected, 'actual': actual,
                    'verdict': verdict, 'evidence': evidence})
    print(f"[{verdict}] {claim}\n    expected={expected}\n    actual={actual}"
          + (f"\n    evidence={evidence}" if evidence else ''))

def rate_ok(headers):
    rem = headers.get('x-ratelimit-remaining')
    return rem is None or rem not in ('0',)

# ---------------------------------------------------------------- 0. rate limit
s, body, h = get('/rate_limit')
print(f"rate_limit: core={body['resources']['core']['remaining']}/{body['resources']['core']['limit']} "
      f"search={body['resources']['search']['remaining']}/{body['resources']['search']['limit']}" if s == 200 and body else f"rate_limit probe failed: {s}")

# ---------------------------------------------------------------- 1. user
s, body, h = get(f'/users/{OWNER}')
time.sleep(0.7)
if s == 200 and body:
    raw_evidence['user'] = {k: body.get(k) for k in ('login', 'public_repos', 'created_at', 'updated_at')}
    pub = body.get('public_repos')
    verdict = 'MATCH' if pub == 24 else 'MISMATCH'
    rec('عدد المستودعات العامة (الجدول/الشريحة 2 تقول 24؛ النص يقول 26)', '24 أو 26', pub, verdict,
        'يحسم تناقض 8/26 مقابل 10/24')
else:
    rec('عدد المستودعات العامة', '24 أو 26', f'HTTP {s}', 'BLOCKED')

# ---------------------------------------------------------------- 2. public repos list
s, repos, h = get(f'/users/{OWNER}/repos?per_page=100&sort=pushed&direction=desc')
time.sleep(0.7)
repo_map = {}
if s == 200 and isinstance(repos, list):
    for r in repos:
        repo_map[r['name']] = {
            'pushed_at': r.get('pushed_at'), 'archived': r.get('archived'),
            'language': r.get('language'), 'description': r.get('description'),
            'fork': r.get('fork'), 'default_branch': r.get('default_branch'),
        }
    raw_evidence['public_repos'] = repo_map
    rec('عدد الصفوف في قائمة المستودعات العامة', 'يساوي public_repos', len(repos),
        'MATCH' if len(repos) == pub else 'MISMATCH')
else:
    rec('قائمة المستودعات العامة', 'قائمة كاملة', f'HTTP {s}', 'BLOCKED')

# pushed_at spot-checks vs Genspark table (public repos only)
expected_push = {
    'omni-medical-suite': '2026-09-18', 'manjaro-care': '2026-09-06',
    'manjaro-doctor': '2026-08-13', 'dictionaries-csv': '2026-08-02',
    'omni-medical-dictionaries': '2026-08-02', 'telegram-tools': '2026-08-13',
    'intelli-file-manager': '2026-08-02', 'arabic-medical-glossary': '2026-08-02',
    'sync-github': '2026-08-02', 'medical-ocr-demo': '2026-08-02',
    'glossary-api': '2026-08-02', 'medical-ocr-trainer-hf': '2026-08-01',
    'OmniFile_Processor': '2026-08-01', 'reset-net': '2026-09-01',
    'repo-sync-toolkit': '2026-08-01', 'radiology-ai-platform': '2026-08-01',
    'DrAbdulmalek': '2026-06-27',
    'arabic-medical-ocr-baseline': '2026-07-07', 'medical-ocr-ground-truth': '2026-07-07',
    'scanner-fixer': '2026-07-07', 'medical-ocr-trainer': '2026-07-07',
    'medical-ocr-benchmarks': '2026-07-07', 'medical-ocr-training-hub': '2026-07-07',
    'medical-handwriting-ocr': '2026-07-07',
}
push_ok, push_bad = [], []
for name, exp in expected_push.items():
    got = (repo_map.get(name) or {}).get('pushed_at', '')
    (push_ok if str(got).startswith(exp) else push_bad).append(f'{name}:{got[:10]}|exp:{exp}')
rec('أعمدة «آخر push» في جدول الـ34 (المستودعات العامة فقط)', '24 مطابقة', 
    f'مطابق={len(push_ok)} مخالف={len(push_bad)}', 'MATCH' if not push_bad else 'PARTIAL',
    'مخالفات: ' + ('; '.join(push_bad) if push_bad else 'لا شيء'))

# archived flags for the 7 "مؤرشفة نصًّا" repos
ARCH7 = ['arabic-medical-ocr-baseline', 'medical-ocr-ground-truth', 'scanner-fixer',
         'medical-ocr-trainer', 'medical-ocr-benchmarks', 'medical-ocr-training-hub',
         'medical-handwriting-ocr']
arch_flags = {n: (repo_map.get(n) or {}).get('archived') for n in ARCH7}
omnifile_arch = (repo_map.get('OmniFile_Processor') or {}).get('archived')
rec('علم isArchived للمستودعات السبعة الموسومة «مؤرشفة» (فجوة أقرّتها Genspark)',
    'true × 7', json.dumps(arch_flags), 
    'MATCH' if all(v is True for v in arch_flags.values()) else 'MISMATCH')
rec('OmniFile_Processor مؤرشف على GitHub؟', 'true', omnifile_arch,
    'MATCH' if omnifile_arch is True else 'MISMATCH')

# descriptions claiming lineage
for nm in ('manjaro-care', 'reset-net', 'sync-github'):
    d = (repo_map.get(nm) or {}).get('description')
    if d:
        rec(f'وصف {nm} (ادعاء «restored from omni-medical-suite history»)', 'يذكر النسب', d[:120],
            'MATCH' if 'omni' in (d or '').lower() or 'restored' in (d or '').lower() else 'CHECK',
            'وصف حي')

# ---------------------------------------------------------------- 3. omni-medical-suite
s, body, h = get(f'/repos/{OWNER}/omni-medical-suite')
time.sleep(0.7)
if s == 200 and body:
    raw_evidence['suite'] = {k: body.get(k) for k in ('pushed_at', 'open_issues_count', 'archived', 'default_branch')}
    oic = body.get('open_issues_count')  # issues + PRs
    rec('omni-medical-suite: open_issues+PRs (32 PR + 3 issues = 35)', 35, oic,
        'MATCH' if oic == 35 else 'MISMATCH')
    rec('omni-medical-suite pushed_at', '2026-09-18', str(body.get('pushed_at'))[:10],
        'MATCH' if str(body.get('pushed_at', '')).startswith('2026-09-18') else 'MISMATCH')
else:
    rec('omni-medical-suite', 'متاح عام', f'HTTP {s}', 'BLOCKED')

s, body, h = get(f'/repos/{OWNER}/omni-medical-suite/commits?sha=main&per_page=1')
time.sleep(0.7)
if s == 200 and isinstance(body, list) and body:
    c = body[0]
    msg = c['commit']['message'].splitlines()[0]
    date = c['commit']['committer']['date']
    raw_evidence['suite_main_tip'] = {'sha': c['sha'], 'date': date, 'msg': msg}
    rec('آخر commit على main للمستودع الأم', '2026-09-02/03 specialty TM (#114)',
        f"{date[:10]} {msg[:70]}", 'MATCH' if 'specialty' in msg.lower() else 'CHECK',
        f"sha={c['sha'][:12]}")
else:
    rec('آخر commit على main للمستودع الأم', '2026-09-02', f'HTTP {s}', 'BLOCKED')

s, pulls, h = get(f'/repos/{OWNER}/omni-medical-suite/pulls?state=open&per_page=100')
time.sleep(0.7)
if s == 200 and isinstance(pulls, list):
    nums = {p['number'] for p in pulls}
    raw_evidence['suite_open_pulls_count'] = len(pulls)
    rec('عدد PR المفتوحة في omni-medical-suite', 32, len(pulls),
        'MATCH' if len(pulls) == 32 else 'MISMATCH')
    sec = {123: 10, 119: 13, 118: 14, 122: 11, 106: 19, 102: 22, 90: 26, 86: 26, 115: 17, 116: 17}
    ages = {p['number']: p.get('created_at', '')[:10] for p in pulls if p['number'] in sec}
    missing = [n for n in sec if n not in nums]
    rec('الـPR الأمنية العشر موجودة ومفتوحة (#123,#119,#118,#122,#106,#102,#90,#86,#115,#116)',
        'كلها موجودة', f'missing={missing}', 'MATCH' if not missing else 'MISMATCH',
        'created_at: ' + json.dumps(ages))
else:
    rec('PR المفتوحة في omni-medical-suite', 32, f'HTTP {s}', 'BLOCKED')

s, issues, h = get(f'/repos/{OWNER}/omni-medical-suite/issues?state=open&per_page=100')
time.sleep(0.7)
if s == 200 and isinstance(issues, list):
    real = [i for i in issues if 'pull_request' not in i]
    inums = sorted(i['number'] for i in real)
    raw_evidence['suite_open_issues'] = inums
    rec('Issues مفتوحة في omni-medical-suite (تتوقع #104,#126,#127)', 3,
        f'{len(real)} {inums}', 'MATCH' if len(real) == 3 else 'MISMATCH')
else:
    rec('Issues مفتوحة في omni-medical-suite', 3, f'HTTP {s}', 'BLOCKED')

# ---------------------------------------------------------------- 4. manjaro-care
s, body, h = get(f'/repos/{OWNER}/manjaro-care')
time.sleep(0.7)
if s == 200 and body:
    raw_evidence['manjaro-care'] = {'pushed_at': body.get('pushed_at'), 'description': body.get('description')}
    rec('manjaro-care pushed_at', '2026-09-06', str(body.get('pushed_at'))[:10],
        'MATCH' if str(body.get('pushed_at', '')).startswith('2026-09-06') else 'MISMATCH')
else:
    rec('manjaro-care pushed_at', '2026-09-06', f'HTTP {s}', 'BLOCKED')

s, body, h = get(f'/repos/{OWNER}/manjaro-care/commits?per_page=3')
time.sleep(0.7)
if s == 200 and isinstance(body, list) and body:
    c = body[0]
    rec('آخر commit على manjaro-care (الافتراضي)', '2026-09-02',
        f"{c['commit']['committer']['date'][:10]} {c['commit']['message'].splitlines()[0][:60]}",
        'MATCH' if c['commit']['committer']['date'].startswith('2026-09-02') else 'MISMATCH',
        f"sha={c['sha'][:12]}")
else:
    rec('آخر commit على manjaro-care', '2026-09-02', f'HTTP {s}', 'BLOCKED')

s, pulls, h = get(f'/repos/{OWNER}/manjaro-care/pulls?state=closed&per_page=100')
time.sleep(0.7)
if s == 200 and isinstance(pulls, list):
    merged = sorted(p['number'] for p in pulls if p.get('merged_at') and '2026-09-01' <= p['merged_at'][:10] <= '2026-09-02')
    raw_evidence['manjaro_care_merged_window'] = merged
    rec('PR مدمجة في manjaro-care بين 2026-09-01 و09-02 (ادعاء: 8 — #1..#8)', 8,
        f'{len(merged)} {merged}', 'MATCH' if len(merged) == 8 and merged == [1, 2, 3, 4, 5, 6, 7, 8] else 'MISMATCH')
else:
    rec('PR مدمجة في manjaro-care', 8, f'HTTP {s}', 'BLOCKED')

# ---------------------------------------------------------------- 5. repo-sync-toolkit
s, pulls, h = get(f'/repos/{OWNER}/repo-sync-toolkit/pulls?state=open&per_page=100')
time.sleep(0.7)
if s == 200 and isinstance(pulls, list):
    info = {p['number']: p.get('created_at', '')[:10] for p in pulls}
    rec('repo-sync-toolkit: PR #1 و#2 مفتوحة منذ ~2026-07-31', '[1,2] @07-31',
        json.dumps(info), 'MATCH' if set(info) == {1, 2} else 'MISMATCH')
else:
    rec('repo-sync-toolkit PRs', '[1,2]', f'HTTP {s}', 'BLOCKED')

# ---------------------------------------------------------------- 6. consolidated tag on archived repos
cons_ok, cons_bad = [], []
for n in ARCH7:
    s, body, h = get(f'/repos/{OWNER}/{n}/commits?per_page=1')
    time.sleep(0.7)
    if s == 200 and isinstance(body, list) and body:
        msg = body[0]['commit']['message'].splitlines()[0].lower()
        date = body[0]['commit']['committer']['date'][:10]
        (cons_ok if ('consolidated' in msg) else cons_bad).append(f'{n}@{date}:{msg[:45]}')
    else:
        cons_bad.append(f'{n}:HTTP{s}')
rec('وسم «consolidated into omni-medical-suite» في آخر commit للسبعة', '7/7',
    f'{len(cons_ok)}/7', 'MATCH' if not cons_bad else 'PARTIAL',
    'فاشلة: ' + ('; '.join(cons_bad) if cons_bad else 'لا شيء'))

# ---------------------------------------------------------------- 7. private probes
for nm in ('omni-medical-workspace', 'malek_data', 'omni-medical-suite_dict',
           'medical-translation-intake', 'medical-translation-bot'):
    s, body, h = get(f'/repos/{OWNER}/{nm}')
    time.sleep(0.7)
    rec(f'{nm} غير مرئي بدون مصادقة (يدعم تصنيفه «خاص»)', '404', s,
        'MATCH' if s == 404 else 'CHECK')

# ---------------------------------------------------------------- 8. searches
def search(q, label, expected, note=''):
    s, body, h = get('/search/issues?q=' + urllib.parse.quote(q) + '&per_page=1')
    time.sleep(5)
    if s == 200 and body and 'total_count' in body:
        tc = body['total_count']
        rec(label, expected, tc, note or ('MATCH' if tc == expected else 'CHECK (بحث مجهول يرى العامة فقط)'))
        return tc
    rec(label, expected, f'HTTP {s}', 'BLOCKED')
    return None

search(f'user:{OWNER}+type:pr+state:open', 'إجمالي PR مفتوحة (ادعاء 89 يشمل الخاصة؛ المجهور منها حسب الجدول = 86)', 89,
       note='توقع 86 لأن البحث المجهول يستثني المستودعات الخاصة (workspace/bot/malek_data = 3)')
search(f'user:{OWNER}+type:pr+state:open+author:app/dependabot', 'PR من dependabot', 60)
search(f'user:{OWNER}+type:issue+state:open', 'Issues مفتوحة (ادعاء 11؛ الجدول يجمع 15 منها 10 عامة)', 11,
       note='توقع 10 لأن البحث المجهول يستثني الخاصة (intake/bot/malek×2/suite_dict = 5)')
search(f'user:{OWNER}+type:pr+is:merged', 'PR مدمجة (ادعاء 66)', 66)

# ---------------------------------------------------------------- save + summary
with open(os.path.join(OUT_DIR, 'api_evidence.json'), 'w', encoding='utf-8') as f:
    json.dump({'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'method': 'unauthenticated read-only GitHub REST API',
               'results': results, 'raw': raw_evidence}, f, ensure_ascii=False, indent=2)

counts = {}
for r in results:
    counts[r['verdict']] = counts.get(r['verdict'], 0) + 1
print('\n==== SUMMARY ====')
print(json.dumps(counts, indent=2))
print(f'evidence file: {OUT_DIR}/api_evidence.json')
