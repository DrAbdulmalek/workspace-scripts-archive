#!/usr/bin/env python3
"""Proactive multi-model review of the MASTER OCR CONSOLIDATION PHASE 1 prompt (v1.1-DRAFT)
via the Vyce AI gateway. Independent reviewers: claude-sonnet-4-6 + deepseek models.

Security: document pre-flight-scanned (secret patterns) before transmission — CLEAN
(only public commit SHAs). Owner directive = explicit opt-in for this transmission.
"""

import datetime
import json
import os
import sys

sys.path.insert(0, "/home/z/my-project/scripts")
import vyce_client as vyce  # noqa: E402

DOC = "/home/z/my-project/download/ocr-phase1/MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md"
OUT = "/home/z/my-project/download/ocr-phase1/review"
MODELS = ["claude-sonnet-4-6", "deepseek-v4-flash-lr", "deepseek-v4-flash"]

RUBRIC = """You are a senior software-architecture reviewer performing an INDEPENDENT pre-execution \
review of a master prompt that will be handed to an AI coding agent to execute "Phase 1" of an \
OCR consolidation program in a medical-imaging monorepo. You have NO other context: judge the \
document strictly on its own text. Be adversarial and specific — generic praise is useless.

Evaluate these dimensions:

1. INTERNAL CONSISTENCY — contradictions between sections (e.g., authorized scope vs \
prohibitions vs deliverables), directives that cannot all be satisfied simultaneously.
2. COMPLETENESS — undefined acceptance criteria, deliverables specified too loosely to verify, \
missing definitions of terms the agent must act on.
3. ACTIONABILITY — places where a competent agent would have to GUESS (arbitrary choices, \
underspecified inputs such as images/fixtures/sources, missing decision points).
4. PROHIBITION/SCOPE INTERACTIONS — hard prohibitions (P1–P15) that collide with the authorized \
scope (S1–S5) or the deliverables (D1–D7); e.g., "extend X" vs "create NEW files only".
5. TESTABILITY & MEASUREMENT — characterization tests, equivalence matrices, STATUS enums: \
are they measurable and unambiguous? Is the fixture corpus well-defined and stable?
6. RISK & SAFETY — security gate, PHI/cloud rules, baseline drift: failure modes not covered \
(e.g., what if the baseline moves MID-execution? partial push failures? dependency/env blockers?).
7. PROCESS GAPS — the flow includes a "CHATGPT REVIEW" gate after Phase 1: is that gate \
defined (inputs, rubric, pass/fail)? Any missing rollback/time-budget/prioritization rules?

OUTPUT FORMAT (strict, no preamble):
For each finding, exactly:
SEVERITY: BLOCKER | MAJOR | MINOR | SUGGESTION
SECTION: <section id or name>
FINDING: <what is wrong, one tight paragraph>
RECOMMENDATION: <concrete fix, one to three sentences>

Order findings: BLOCKERs first, then MAJOR, MINOR, SUGGESTION. Aim for the 8-15 most \
valuable findings, not an exhaustive nitpick list. End with:
OVERALL VERDICT: READY-TO-EXECUTE | READY-AFTER-EDITS | NEEDS-REWORK
OVERALL ASSESSMENT: <one paragraph>
"""


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    # Optional CLI arg: review ONE model only (robust against gateway slowness /
    # shell timeouts); models with an existing non-empty review file are skipped.
    only = sys.argv[1] if len(sys.argv) > 1 else None
    with open(DOC, "r", encoding="utf-8") as fh:
        doc = fh.read()
    prompt = RUBRIC + "\n\n===== DOCUMENT UNDER REVIEW =====\n\n" + doc
    print(f"document: {len(doc)} chars; review prompt: {len(prompt)} chars", flush=True)

    summary = {}
    for model in MODELS:
        marker = os.path.join(OUT, f"review_{model.replace('/', '_')}.md")
        if os.path.exists(marker) and os.path.getsize(marker) > 1000:
            print(f"[skip] {model} already reviewed -> {marker}", flush=True)
            summary[model] = "SKIPPED (exists)"
            continue
        if only and model != only:
            continue
        print(f"[review] -> {model} ...", flush=True)
        t0 = datetime.datetime.utcnow()
        try:
            r = vyce.chat(model, [{"role": "user", "content": prompt}], max_tokens=8000)
            dt = (datetime.datetime.utcnow() - t0).total_seconds()
            fname = os.path.join(OUT, f"review_{model.replace('/', '_')}.md")
            with open(fname, "w", encoding="utf-8") as fh:
                fh.write(
                    "# Independent Pre-Execution Review\n\n"
                    f"- Reviewer model: `{model}` (via Vyce AI gateway, vyceai.com/v1)\n"
                    f"- Generated: {t0.isoformat()}Z (duration {dt:.0f}s)\n"
                    "- Document under review: `MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md` "
                    "v1.1-DRAFT (Authorization: HOLD)\n"
                    "- Method: single-pass blind review against a 7-dimension rubric; "
                    "no project context given to the reviewer (fresh-eyes policy)\n"
                    f"- Usage: {json.dumps(r.get('usage', {}))}\n\n---\n\n"
                    f"{r['content']}\n"
                )
            print(f"  OK ({dt:.0f}s, {len(r['content'])} chars) -> {fname}", flush=True)
            summary[model] = "OK"
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}", flush=True)
            summary[model] = f"FAIL: {e}"

    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    with open(os.path.join(OUT, f"_run_summary_{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump({"run": stamp, "models": summary}, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
