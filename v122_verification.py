#!/usr/bin/env python3
"""V1.2.2 verification (E.8 ONLY, owner-approved via ChatGPT review). READ-ONLY.
Byte-level reconstruction test: v1.2.1 archive + 5 authorized edits == actual v1.2.2."""
import re, sys

BASE = "/home/z/my-project/download/ocr-phase1/"
PROMPT = BASE + "MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md"
V121 = BASE + "archive/PROMPT_v1.2.1_DRAFT_20260915.md"
DIFF = BASE + "review/V1.2.1_TO_V1.2.2_UNIFIED_DIFF.patch"

text = open(PROMPT, encoding="utf-8").read()
lines = text.split("\n")
ok = True
def check(name, cond, detail=""):
    global ok
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond: ok = False

# 1. HOLD + version bookkeeping
check("Authorization = HOLD intact", "Authorization:      HOLD" in text)
check("Version bumped to v1.2.2-DRAFT",
      "Version:            v1.2.2-DRAFT (v1.2.1 + residual E.8 — normative D1 execution order, applied 2026-09-15)" in text)
check("New Revised line (E.8 ONLY)", "v1.2.2 applies residual E.8 ONLY (normative D1 execution" in text)

# 2. E.8 block present exactly once, with ChatGPT's normative keywords (text-wide search,
#    keywords may span wrapped lines)
def find(pat): return [i for i, l in enumerate(lines, 1) if re.search(pat, l)]
def find_ml(pat):
    return sorted({1 + text[:m.start()].count("\n") for m in re.finditer(pat, text, re.M)})
anchor = find(r"D1 execution order — normative \(v1\.2\.2 E\.8")
check("E.8 block present exactly once", len(anchor) == 1, f"line {anchor[0]}" if anchor else "MISSING")
for kw, desc in [
    (r"BEFORE\s*$|BEFORE creating", "BEFORE creating keyword"),
    (r"the agent MUST\s*$|MUST\s+complete the read-only inventory", "MUST complete read-only inventory"),
    (r"all 3 existing `OCRResult` contracts", "3 OCRResult contracts"),
    (r"all 6\s+identified wrappers", "6 identified wrappers"),
    (r"populate `CONTRACT_FIELD_MAPPING` for every mapped field", "populate mapping for every mapped field"),
    (r"document any unmapped/ambiguous fields and potential information loss", "unmapped/ambiguous + loss documentation"),
    (r"MUST then be checked against the completed inventory and mapping", "contract checked against completed mapping"),
    (r"No canonical\s+field may be introduced, removed, renamed, or collapsed", "no field change without mapping decision"),
    (r"explicit mapping\s+decision and information-preservation rationale", "information-preservation rationale"),
]:
    hits = find_ml(kw)
    check(f"E.8 keyword: {desc}", bool(hits), f"lines {hits[:3]}" if hits else "MISSING")

# 3. Byte-level reconstruction: v1.2.1 + 5 authorized edits == v1.2.2
E8 = ("- File: `packages/omni_ocr/contract/result.py` (+ `contract/__init__.py`).\n"
      "- D1 execution order — normative (v1.2.2 E.8; owner-approved via ChatGPT review): BEFORE\n"
      "  creating `packages/omni_ocr/contract/result.py` or `contract/__init__.py`, the agent MUST\n"
      "  complete the read-only inventory of all 3 existing `OCRResult` contracts and all 6\n"
      "  identified wrappers, populate `CONTRACT_FIELD_MAPPING` for every mapped field, and\n"
      "  document any unmapped/ambiguous fields and potential information loss. The canonical\n"
      "  contract MUST then be checked against the completed inventory and mapping. No canonical\n"
      "  field may be introduced, removed, renamed, or collapsed without an explicit mapping\n"
      "  decision and information-preservation rationale.\n"
      "- Required fields (owner-specified FINAL set — 11 canonical fields):")
R = [
    ("Version:            v1.2.1-DRAFT (v1.2 + FINAL-VERIFICATION residuals E.1–E.7 applied, 2026-09-15)",
     "Version:            v1.2.2-DRAFT (v1.2.1 + residual E.8 — normative D1 execution order, applied 2026-09-15)"),
    ("Revised:            2026-09-15 — v1.2.1 DOCUMENT-ONLY HARDENING applies FINAL-VERIFICATION\n                    residuals E.1–E.7\n                    (download/ocr-phase1/review/V1.2_FINAL_VERIFICATION_REPORT.md)",
     "Revised:            2026-09-15 — v1.2.1 DOCUMENT-ONLY HARDENING applies FINAL-VERIFICATION\n                    residuals E.1–E.7\n                    (download/ocr-phase1/review/V1.2_FINAL_VERIFICATION_REPORT.md)\nRevised:            2026-09-15 — v1.2.2 applies residual E.8 ONLY (normative D1 execution\n                    order: inventory + CONTRACT_FIELD_MAPPING BEFORE contract creation;\n                    owner-approved via ChatGPT review)"),
    ("- File: `packages/omni_ocr/contract/result.py` (+ `contract/__init__.py`).\n- Required fields (owner-specified FINAL set — 11 canonical fields):", E8),
    ("      Task:      MASTER OCR CONSOLIDATION — PHASE 1 (prompt v1.2.1)",
     "      Task:      MASTER OCR CONSOLIDATION — PHASE 1 (prompt v1.2.2)"),
    ("  FIXTURE_MANIFEST; this prompt (v1.2.1).",
     "  FIXTURE_MANIFEST; this prompt (v1.2.2)."),
]
v121 = open(V121, encoding="utf-8").read()
recon, applied = v121, 0
for old, new in R:
    if old in recon:
        recon = recon.replace(old, new, 1); applied += 1
check("Reconstruction: all 5 authorized replacements applied", applied == 5, f"{applied}/5")
check("RECONSTRUCTION TEST: v1.2.1 + E.8 edits == actual v1.2.2 (byte-identical)", recon == text,
      "MISMATCH" if recon != text else "zero out-of-scope edits")
diff = open(DIFF, encoding="utf-8").read()
check("Diff hunks = 5", len(re.findall(r"@@ -\d+", diff)) == 5)

# 4. Contradiction spot-checks (E.8 vs context)
check("P4 read-only inspection clause still intact (E.8 aligned)",
      "Read-only INSPECTION of them is required by D1 (CONTRACT_FIELD_MAPPING)" in text)
check("INFORMATION-PRESERVATION RULE still intact",
      "preserve information that exists today in the\n  3 OCRResult contracts + 6 wrappers" in text)
check("F15 canonical naming still intact", "the canonical field name is `segments`; every existing" in text)
check("F8 execution order still D1 first", "Execution order (F8): D1 → D2 → D3 (contract layer)" in text)
check("F12/§11 self-references consistent (no stale v1.2.1 self-refs)",
      "(prompt v1.2.1)" not in text and "this prompt (v1.2.1)" not in text,
      "stale self-reference found" if "(prompt v1.2.1)" in text else "")
v121_mentions = find_ml(r"v1\.2\.1")
# 5 legitimate occurrences: Version lineage (1) + Revised history (1) + provenance
# annotations of applied residuals E.1/E.2/E.7 (3). Stale SELF-refs already excluded above.
check("'v1.2.1' occurrences all legitimate (lineage + history + E.1/E.2/E.7 annotations)",
      len(v121_mentions) == 5, f"lines {v121_mentions}")

# 5. D1 ordering probe — now MUST find the sequence pin
d1s = next(i for i, l in enumerate(lines) if l.startswith("### D1 —"))
d1e = next(i for i, l in enumerate(lines) if l.startswith("### D2 —"))
d1 = "\n".join(lines[d1s:d1e])
check("D1 ORDERING SAFETY: sequence pin now PRESENT (inventory/mapping BEFORE contract creation)",
      bool(re.search(r"BEFORE\s*\n?\s*creating `packages/omni_ocr/contract/result\.py`", d1)))

print(f"\n[INFO] doc now {len(lines)-1} lines (was 586); E.8 block at lines {anchor[0]}-{anchor[0]+7}")
print("\nOVERALL:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
