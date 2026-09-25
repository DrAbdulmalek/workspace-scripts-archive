"""Extract gradio 6.0.0 changelog narrative (breaking/removed/changed APIs)."""
import re

text = open('/tmp/gradio-changelog.md', encoding='utf-8', errors='replace').read()
m = re.search(r'(#+ \[?6\.0\.0[^\n]*\n)(.*?)(#+ \[?5\.)', text, re.S)
if not m:
    print("6.0.0 section NOT FOUND")
    raise SystemExit(1)
sec = m.group(2)
# remove commit-hash links and PR links
clean = re.sub(r'\[[^\]]*\]\(https://github\.com/[^)]*\)', '', sec)
clean = re.sub(r'\[\d+\]', '', clean)
out = []
for line in clean.split('\n'):
    l = line.strip()
    if not l:
        continue
    if l.startswith('#'):
        out.append(l[:120])
    elif l.startswith('-') and len(l) > 12:
        out.append('   ' + l[2:200])
print('\n'.join(out))
