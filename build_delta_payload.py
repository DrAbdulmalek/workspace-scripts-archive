#!/usr/bin/env python3
"""Build the TARGETED DELTA REVIEW payload for the E.8 block from the ACTUAL v1.2.2 file.
Material-only (no session context) — blind delta review per fresh-eyes policy."""
P = "/home/z/my-project/download/ocr-phase1/MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md"
lines = open(P, encoding="utf-8").read().split("\n")

def section(start_pat, end_pat):
    s = next(i for i, l in enumerate(lines) if l.startswith(start_pat))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith(end_pat))
    return "\n".join(lines[s:e])

d1 = section("### D1 —", "### D2 —")
p34 = "\n".join(l for l in lines if l.startswith(("| P3 |", "| P4 |")))
g4 = next(l for l in lines if l.startswith("| G4 |"))
f8 = "\n".join(lines[203:207])  # §7 execution order block (F8)

payload = f"""TARGETED DELTA REVIEW (NOT a full review). One normative block was added to the D1
section of a Phase-1 implementation prompt (OCR consolidation; the phase is ADDITIVE-ONLY:
it creates a new canonical contract layer and must NOT rewrite existing engines).
Your job is to review ONLY the added block against the unchanged surrounding material.

ADDED BLOCK (v1.2.2 E.8):
---
- D1 execution order — normative (v1.2.2 E.8; owner-approved via ChatGPT review): BEFORE
  creating `packages/omni_ocr/contract/result.py` or `contract/__init__.py`, the agent MUST
  complete the read-only inventory of all 3 existing `OCRResult` contracts and all 6
  identified wrappers, populate `CONTRACT_FIELD_MAPPING` for every mapped field, and
  document any unmapped/ambiguous fields and potential information loss. The canonical
  contract MUST then be checked against the completed inventory and mapping. No canonical
  field may be introduced, removed, renamed, or collapsed without an explicit mapping
  decision and information-preservation rationale.
---

UNCHANGED SURROUNDING MATERIAL:
---
{d1}
---

Related rules (unchanged):
---
{p34}
{g4}

Execution order (unchanged, F8):
---
{f8}
---

ANSWER STRICTLY IN THIS FORMAT (no extra prose before/after):
VERDICT: PASS | PASS-WITH-CONDITIONS | FAIL
F1: <finding or "none"> (severity: BLOCKER | MAJOR | MINOR | INFO)
F2: ...
CHECK-A (contradiction with the unchanged material, cite which rule): <one paragraph or "none">
CHECK-B (mechanically enforceable without executor interpretation): <one paragraph>
CHECK-C (does it enforce inventory -> mapping -> loss analysis -> canonical contract, and block any retrofit path?): <one paragraph>
CHECK-D (information-preservation gaps introduced by the block itself): <one paragraph or "none">
"""
open("/home/z/my-project/download/ocr-phase1/review/_delta_payload_E8.txt", "w", encoding="utf-8").write(payload)
print("payload written:", len(payload), "chars")
