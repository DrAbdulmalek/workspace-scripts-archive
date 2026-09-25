#!/usr/bin/env python3
"""V1.2.1 DOCUMENT-ONLY HARDENING verification (READ-ONLY).
Checks: HOLD intact, E.1-E.7 applied at exact locations, no edits outside the
authorized set (diff hunk audit), residual-text absence, contradiction
spot-checks, D1 ordering-safety probe. Never prints secret values."""
import re, subprocess, sys

BASE = "/home/z/my-project/download/ocr-phase1/"
PROMPT = BASE + "MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md"
V12 = BASE + "archive/PROMPT_v1.2_DRAFT_20260914.md"
DIFF = BASE + "review/V1.2_TO_V1.2.1_UNIFIED_DIFF.patch"

text = open(PROMPT, encoding="utf-8").read()
lines = text.split("\n")
ok = True
def check(name, cond, detail=""):
    global ok
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond: ok = False

# 1. Authorization + version bookkeeping
check("Authorization = HOLD intact", "Authorization:      HOLD" in text)
check("Version bumped to v1.2.1-DRAFT", "Version:            v1.2.1-DRAFT (v1.2 + FINAL-VERIFICATION residuals E.1–E.7 applied, 2026-09-15)" in text)
check("New Revised line present", "v1.2.1 DOCUMENT-ONLY HARDENING applies FINAL-VERIFICATION" in text)

# 2. E.1-E.7 marker presence with line anchors
def find(pat):
    return [i for i, l in enumerate(lines, 1) if re.search(pat, l)]
anchors = {
    "E.1 DUPLICATE precedence": find(r"DUPLICATE precedence — one primary STATUS per row"),
    "E.2 manifest reproducibility": find(r"reproducibility columns added v1\.2\.1 E\.2"),
    "E.3 owner-only authority": find(r"drafted by the owner only"),
    "E.4 header colon": find(r"Grant-time inputs:"),
    "E.5 canonical segments": find(r"11 canonical fields"),
    "E.6 branch existence line": find(r"phase-1 branch existence:  FOUND \| NOT FOUND"),
    "E.7 resolution criterion": find(r"RESOLUTION CRITERION \(v1\.2\.1 E\.7"),
}
for k, v in anchors.items():
    check(f"{k} present", len(v) == 1, f"line {v[0]}" if v else "MISSING")

# 3. Residual old strings must be gone (the only allowed occurrence of the old phrase is
#    the new criterion's own quotation of what it replaces — line-anchored)
dpi_hits = [i for i, l in enumerate(lines, 1) if "300 DPI equivalent" in l and "replaces" not in l]
check("'300 DPI equivalent' gone (quotation in criterion header allowed)", len(dpi_hits) == 0,
      f"still at lines {dpi_hits}" if dpi_hits else "")
gone = [
    ("'segments`/`blocks' slash gone", r"segments`/`blocks"),
    ("colon-less 'Grant-time inputs   ' gone", r"Grant-time inputs   "),
    ("'(prompt v1.2)' self-ref gone", r"\(prompt v1\.2\)"),
    ("'this prompt \\(v1.2\\)\\.' gone", r"this prompt \(v1\.2\)\."),
    ("old verdict 'may be drafted;' gone", r"may be drafted;"),
]
for name, pat in gone:
    hits = find(pat)
    check(name, len(hits) == 0, f"still at lines {hits}" if hits else "")

# 4. BYTE-LEVEL RECONSTRUCTION TEST — apply ONLY the authorized replacements to the
#    archived v1.2 text; the result must equal the actual v1.2.1 file byte-for-byte.
#    This proves ZERO changes outside the authorized E.1-E.7 + bookkeeping set.
R = [  # (old, new) — exactly the 11 authorized edits
    ("Version:            v1.2-DRAFT (v1.1 + proactive review gate #0 findings F1–F20 applied, 2026-09-14)",
     "Version:            v1.2.1-DRAFT (v1.2 + FINAL-VERIFICATION residuals E.1–E.7 applied, 2026-09-15)"),
    ("Grant-time inputs   The GRANT message must attach (a missing item → the agent requests it and WAITS):",
     "Grant-time inputs:  The GRANT message must attach (a missing item → the agent requests it and WAITS):"),
    ("Revised:            2026-09-14 — v1.2 applies proactive-review findings F1–F20\n                    (download/ocr-phase1/review/PHASE1_PROMPT_REVIEW_SYNTHESIS.md)",
     "Revised:            2026-09-14 — v1.2 applies proactive-review findings F1–F20\n                    (download/ocr-phase1/review/PHASE1_PROMPT_REVIEW_SYNTHESIS.md)\nRevised:            2026-09-15 — v1.2.1 DOCUMENT-ONLY HARDENING applies FINAL-VERIFICATION\n                    residuals E.1–E.7\n                    (download/ocr-phase1/review/V1.2_FINAL_VERIFICATION_REPORT.md)"),
    ("- Required fields (owner-specified FINAL set):\n  `text`, `segments`/`blocks`, `confidence`, `engine`, `language`, `metadata`,\n  `preprocessing`, `fallback_chain`, `provenance`, `warnings`, `errors`.",
     "- Required fields (owner-specified FINAL set — 11 canonical fields):\n  `text`, `segments`, `confidence`, `engine`, `language`, `metadata`,\n  `preprocessing`, `fallback_chain`, `provenance`, `warnings`, `errors`.\n  `blocks` is NOT a canonical field and never appears in `contract/result.py`: it is a\n  legacy/source field name ONLY, mapped INTO `segments` via CONTRACT_FIELD_MAPPING (F15)."),
    ("      classes). `SUITABLE` = PHI-free + format supported by the production OCR path +\n      resolution ≥ 300 DPI equivalent + content class representative of production use.",
     "      classes). `SUITABLE` = PHI-free + format supported by the production OCR path +\n      resolution meeting the RESOLUTION CRITERION (below) + content class representative\n      of production use.\n  RESOLUTION CRITERION (v1.2.1 E.7 — replaces \"300 DPI equivalent\"; measurable per input\n  type; quality-adequacy principle retained):\n  (R-a) the image carries density metadata (DPI/DPCM, e.g. TIFF/JPEG/PNG metadata) →\n        effective density ≥ 300 DPI (≥ 118.11 DPCM);\n  (R-b) the image carries NO density metadata (typical for PNG/JPEG/WebP and synthetic\n        renders) → pixel floor: long edge ≥ 2480 px AND short edge ≥ 1750 px (= 300 DPI\n        across a 5.83 × 8.27 in document area);\n  (R-c) a smaller image may be included ONLY with a manifest annotation\n        `resolution_exception=<reason>` AND passing characterization on the production\n        path — adequacy is proven by measurement, never assumed.\n  The criterion branch applied (R-a, R-b, or R-c) is recorded per image in its manifest\n  row (inside `expected_characteristics`)."),
    ("- Manifest row template (F11):\n  `image_sha256 | source | license/provenance | synthetic? (REAL/SYNTHETIC) |\n   expected_characteristics | test_file | status (PASS/FAIL/BLOCKED)`",
     "- Manifest row template (F11; reproducibility columns added v1.2.1 E.2):\n  `image_sha256 | source | license/provenance | synthetic? (REAL/SYNTHETIC) |\n   ocr_engine | ocr_engine_version | model_identifier | preprocessing_profile |\n   expected_characteristics | test_file | status (PASS/FAIL/BLOCKED)`\n  Reproducibility rule (E.2): the four added columns pin the EXACT engine conditions that\n  produced the characterization baseline — `ocr_engine` + `ocr_engine_version` (the engine\n  actually invoked by the production path), `model_identifier` (model/weights/checkpoint\n  identifier where applicable, e.g. TrOCR checkpoint or Paddle model name; `N/A` if the\n  engine has none), `preprocessing_profile` (the named preprocessing/profile identifier\n  used for the baseline run; `NONE` if no profile). A row missing any of the four is\n  INVALID and the manifest MUST NOT be frozen until complete. If any of the four changes\n  later, affected golden outputs are regenerated and the manifest re-frozen before Phase\n  2–4 reuse. The corpus itself is NOT changed by this rule."),
    ("- UNPROVEN    verification was attempted and BLOCKED — the exact blocker is documented\n              (source unreachable, tooling missing, rate limit). NEVER a guess label.",
     "- UNPROVEN    verification was attempted and BLOCKED — the exact blocker is documented\n              (source unreachable, tooling missing, rate limit). NEVER a guess label.\n\nDUPLICATE precedence — one primary STATUS per row, decided mechanically (v1.2.1 E.1):\nDUPLICATE is a PRIMARY status, not a secondary finding: it is assigned whenever\nhash-identical content exists at MORE THAN ONE path in the destination tree (multiplicity\nmakes any single MIGRATED/EQUIVALENT destination undefined). Apply this decision order to\nEVERY row — first match wins, no judgment calls:\n  1. UNPROVEN    the verification step itself could not complete (blocker documented).\n  2. MISSING     the existence check COMPLETED and found no destination at the referenced\n                 path.\n  3. DUPLICATE   the destination tree contains ≥ 2 hash-identical copies of the unit —\n                 record EVERY such path in the FILE cell.\n  4. DIVERGED    destination exists AND hash differs AND (AST differs OR behavioral\n                 difference shown by diff/test evidence).\n  5. MIGRATED    exactly ONE destination path, hash-identical, migration map claims it.\n  6. EQUIVALENT  exactly ONE destination path, measured equal (hash-identical or\n                 AST-equal); map claims irrelevant.\nNo row carries two STATUS labels. A secondary relation observed on a DUPLICATE row (e.g.\nthe duplicated content is also hash-identical to the source, or the migration map claims\nit) is recorded in the TEST cell prefixed `also:` and in the D7 findings table — NEVER in\nthe STATUS cell. Destination copies that are NOT hash-identical to each other are NOT\nDUPLICATE: each candidate path is assessed individually (steps 4–6) and the multiplicity\nitself is recorded as an `also:` finding. This precedence is uniform for D5a and D5b rows."),
    ("   existence checks:  <path> FOUND | MISSING   (one line per item 6 path)",
     "   existence checks:  <path> FOUND | MISSING   (one line per item 6 path)\n   phase-1 branch existence:  FOUND | NOT FOUND   (branch name used in the check: <name>;\n                      expected `feat/ocr-consolidation-phase1`; via `git ls-remote\n                      <suite-remote-url> refs/heads/<name>`)"),
    ("      Task:      MASTER OCR CONSOLIDATION — PHASE 1 (prompt v1.2)",
     "      Task:      MASTER OCR CONSOLIDATION — PHASE 1 (prompt v1.2.1)"),
    ("  FIXTURE_MANIFEST; this prompt (v1.2).",
     "  FIXTURE_MANIFEST; this prompt (v1.2.1)."),
    ("- Verdict: `PASS` → Phase-2 authorization may be drafted; `PASS-WITH-CONDITIONS` → conditions\n  enumerated and folded into the Phase-2 prompt; `FAIL` → failing items listed and Phase-1\n  rework scoped. Banned words apply to review outputs too (P15).",
     "- Verdict: `PASS` → Phase-2 authorization may be drafted by the owner only. No external\n  reviewer and no execution agent holds authorization authority: reviewers score, the\n  owner decides. `PASS-WITH-CONDITIONS` → conditions enumerated and folded into the\n  Phase-2 prompt; `FAIL` → failing items listed and Phase-1 rework scoped. Banned words\n  apply to review outputs too (P15)."),
]
v12_text = open(V12, encoding="utf-8").read()
recon = v12_text
applied = 0
for old, new in R:
    if old in recon:
        recon = recon.replace(old, new, 1)
        applied += 1
    else:
        check(f"reconstruction: old block #{R.index((old,new))+1} found in v1.2", False)
check("Reconstruction: all 11 authorized replacements applied", applied == len(R), f"{applied}/{len(R)}")
check("RECONSTRUCTION TEST: v1.2 + authorized edits == actual v1.2.1 (byte-identical)",
      recon == text, "MISMATCH — unaccounted changes exist" if recon != text else "zero out-of-scope edits")
diff = open(DIFF, encoding="utf-8").read()
hunks = re.findall(r"@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", diff)
check("Hunk count sanity (9 expected)", len(hunks) == 9, str(len(hunks)))

# 5. Contradiction spot-checks
check("F15 still says canonical name is `segments` (consistent with E.5)",
      "the canonical field name is `segments`; every existing" in text)
check("E.1 precedence consistent with DUPLICATE bullet",
      "- DUPLICATE   hash-identical content exists at MORE THAN ONE path in the destination tree." in text)
check("E.2 template keeps original 7 columns", "expected_characteristics | test_file | status (PASS/FAIL/BLOCKED)`" in text)
check("E.6 keeps original ACCESS REPORT lines", "existence checks:  <path> FOUND | MISSING   (one line per item 6 path)" in text)
check("E.3 keeps PASS-WITH-CONDITIONS mapping", "`PASS-WITH-CONDITIONS` → conditions enumerated and folded" in text)
check("E.7 keeps SUITABLE quality principle", "quality-adequacy principle retained" in text)
check("E.2 rule does not alter corpus rules", "must NOT silently invent its own real corpus" in text)
check("P4 read-only inspection clause intact", "Read-only INSPECTION of them is required by D1 (CONTRACT_FIELD_MAPPING)" in text)
check("Draft notice + F19 intact", "This file is a REVIEW DRAFT" in text)

# 6. D1 ordering-safety probe (verification item 6)
d1_start = next(i for i, l in enumerate(lines) if l.startswith("### D1 —"))
d1_end = next(i for i, l in enumerate(lines) if l.startswith("### D2 —"))
d1_block = "\n".join(lines[d1_start:d1_end])
order_pins = [r"before creating", r"only after the mapping", r"mapping table FIRST", r"MUST (?:be )?(?:complete|exist) before", r"inventory .* before", r"BEFORE .*contract/result\.py"]
pins = [p for p in order_pins if re.search(p, d1_block, re.I)]
print(f"[INFO] D1 ordering probe: explicit sequence pins found = {len(pins)} {pins}")
has_map_req = "Deliver a CONTRACT_FIELD_MAPPING table" in d1_block and "every existing field of" in d1_block
check("D1 mandates full field inventory/mapping (CONTRACT_FIELD_MAPPING)", has_map_req)

# 7. Stats
adds = sum(1 for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++"))
dels = sum(1 for l in diff.split("\n") if l.startswith("-") and not l.startswith("---"))
print(f"[INFO] v1.2 -> v1.2.1: +{adds} / -{dels} lines; doc now {len(lines)} lines (was 531)")

print("\nOVERALL:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
