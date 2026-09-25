#!/usr/bin/env python3
"""Independent E.8 verbatim check (fresh-context re-verification). READ-ONLY.
Compares the E.8 block in the live v1.2.2 doc, token-by-token, against the
canonical owner-relayed ChatGPT wording. Allowed adaptations:
  (a) provenance insert "(v1.2.2 E.8; owner-approved via ChatGPT review)"
  (b) double quotes -> backticks (document convention)
Any OTHER token difference = FAIL."""
import re, sys

DOC = "/home/z/my-project/download/ocr-phase1/MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md"

CANONICAL = (
    'D1 execution order — normative: BEFORE creating "packages/omni_ocr/contract/result.py" '
    'or "contract/__init__.py", the agent MUST complete the read-only inventory of all 3 '
    'existing "OCRResult" contracts and all 6 identified wrappers, populate '
    '"CONTRACT_FIELD_MAPPING" for every mapped field, and document any unmapped/ambiguous '
    'fields and potential information loss. The canonical contract MUST then be checked '
    'against the completed inventory and mapping. No canonical field may be introduced, '
    'removed, renamed, or collapsed without an explicit mapping decision and '
    'information-preservation rationale.'
)

text = open(DOC, encoding="utf-8").read()
lines = text.split("\n")

# locate block start
starts = [i for i, l in enumerate(lines) if l.startswith("- D1 execution order — normative")]
if len(starts) != 1:
    print(f"FAIL: E.8 block start found {len(starts)} times"); sys.exit(1)
s = starts[0]
# block = bullet line + following wrapped lines until next bullet/heading
block_lines = [lines[s]]
j = s + 1
while j < len(lines) and lines[j].startswith("  ") and lines[j].strip():
    block_lines.append(lines[j]); j += 1
raw = " ".join(x.strip() for x in block_lines)

# strip bullet marker + provenance insert
doc_norm = raw
doc_norm = re.sub(r"^- ", "", doc_norm)
doc_norm = re.sub(r"\s*\(v1\.2\.2 E\.8; owner-approved via ChatGPT review\)", "", doc_norm)
# backticks -> double quotes (documented adaptation)
doc_norm = doc_norm.replace("`", '"')
# whitespace normalize
doc_norm = re.sub(r"\s+", " ", doc_norm).strip()
canon_norm = re.sub(r"\s+", " ", CANONICAL).strip()

print(f"Block location : line {s+1}..{j} ({j-s} lines)")
print(f"Doc tokens     : {len(doc_norm.split())}")
print(f"Canon tokens   : {len(canon_norm.split())}")

if doc_norm == canon_norm:
    print("\nVERBATIM MATCH: doc E.8 == ChatGPT canonical wording (token-for-token), "
          "after ONLY the two disclosed adaptations (provenance insert, quotes->backticks).")
    sys.exit(0)

# token-level diff for transparency
dt, ct = doc_norm.split(), canon_norm.split()
import difflib
sm = difflib.SequenceMatcher(None, ct, dt)
print("\nVERBATIM MISMATCH — token diffs (canonical -> doc):")
fail = False
for op, a1, a2, b1, b2 in sm.get_opcodes():
    if op != "equal":
        fail = True
        print(f"  {op.upper():8s} canon[{a1}:{a2}]={ct[a1:a2]!r} doc[{b1}:{b2}]={dt[b1:b2]!r}")
print("\nOVERALL:", "FAIL" if fail else "PASS")
sys.exit(1 if fail else 0)
