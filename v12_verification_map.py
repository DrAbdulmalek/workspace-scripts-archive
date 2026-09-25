#!/usr/bin/env python3
"""F1-F20 location map + section resolution for the v1.2 verification (READ-ONLY)."""
import re

DOC = "/home/z/my-project/download/ocr-phase1/MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md"

lines = open(DOC, encoding="utf-8").read().split("\n")

sections = []
for i, l in enumerate(lines, 1):
    m = re.match(r"^(#{2,4})\s+(.*)", l)
    if m:
        sections.append((i, m.group(2).strip()))


def section_of(n: int) -> str:
    cur = "(header block)"
    for ln, t in sections:
        if ln <= n:
            cur = t
        else:
            break
    return cur


occ = {f"F{i}": [] for i in range(1, 21)}
anchor = {}
for i, l in enumerate(lines, 1):
    for m in re.finditer(r"\bF(\d+)\b", l):
        occ[f"F{m.group(1)}"].append(i)
    for m in re.finditer(r"\(F(\d+)\)", l):
        anchor.setdefault(f"F{m.group(1)}", []).append(i)

for k in sorted(occ, key=lambda x: int(x[1:])):
    req_lines = anchor.get(k, [])
    print(f"{k:4s}| definition-anchors: {req_lines}")
    print(f"     | all occurrences   : {occ[k]}")
    for n in occ[k]:
        print(f"     | L{n:<4d} [{section_of(n)}]")
        print(f"     |        text: {lines[n-1].strip()[:110]}")
    print()
