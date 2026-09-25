#!/usr/bin/env python3
"""Secret scan over the verification corpus (READ-ONLY). Prints class, count, line
numbers ONLY — never any secret value. 40-hex runs classified against the known
public commit SHAs."""
import glob
import re

FILES = [
    "/home/z/my-project/download/ocr-phase1/MASTER_OCR_CONSOLIDATION_PHASE1_PROMPT.md",
    "/home/z/my-project/download/ocr-phase1/archive/PROMPT_v1.1_DRAFT_20260914.md",
    "/home/z/my-project/download/ocr-phase1/GOVERNANCE_ROUND4_DECISIONS.md",
] + sorted(glob.glob("/home/z/my-project/download/ocr-phase1/review/*"))

PUBLIC_SHAS = {
    "39640a6dbba741eaf13e078dad64719e147ea79b",
    "0e4294a5173c59c007349bf29a80869eb2a60596",
}
# Local document integrity fingerprints (SHA-256 of OUR OWN deliverable files — hashes of
# local documents, not credentials; classified deliberately, values are already public in
# the project's own verification reports).
LOCAL_DOC_FINGERPRINTS = {
    "5c7e78d5aeaa42641b60749e94a85b12216464b453a4bcfad0a853e64ccddd0f",  # v1.2 archive (pre-edit)
    "59ca0d8dc6296b78bfd045397a2ac114fc2497ec3fd38f93f601f6cb39c72d62",  # v1.2.1 archive (pre-E.8)
    "8050e7ee141ee356b3e624b79c970fa9638e3653122e9d0c0eeb4618f46dd499",  # v1.2.2 current
}
KNOWN_HEX = PUBLIC_SHAS | LOCAL_DOC_FINGERPRINTS

PATTERNS = {
    "openai-style-key": r"sk-[A-Za-z0-9]{20,}",
    "github-token": r"gh[posu]_[A-Za-z0-9]{30,}",
    "github-fine-grained-pat": r"github_pat_[A-Za-z0-9_]{20,}",
    "aws-access-key": r"AKIA[0-9A-Z]{16}",
    "slack-token": r"xox[baprs]-[A-Za-z0-9-]+",
    "private-key-block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "jwt": r"eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}",
    "bearer-literal": r"Bearer\s+[A-Za-z0-9_\-\.]{25,}",
    "password-assignment": r"(?i)(password|passwd|secret)\s*[=:]\s*['\"][^'\"]{8,}",
}

overall = {"clean": 0, "public-sha-only": 0, "SECRET-HIT": 0}
for path in FILES:
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        continue
    findings = {}
    verdict = "clean"
    for i, line in enumerate(lines, 1):
        for name, pat in PATTERNS.items():
            if re.search(pat, line):
                findings.setdefault(name, []).append(i)
                verdict = "SECRET-HIT"
        for m in re.finditer(r"\b[a-f0-9]{40,}\b", line):
            s = m.group(0)
            if s in PUBLIC_SHAS:
                kind = "PUBLIC-COMMIT-SHA"
            elif s in LOCAL_DOC_FINGERPRINTS:
                kind = "LOCAL-DOC-FINGERPRINT"
            else:
                kind = "UNKNOWN-HEX40"
            findings.setdefault(kind, []).append(i)
            if kind == "UNKNOWN-HEX40":
                verdict = "SECRET-HIT"
    if verdict == "clean" and findings:
        verdict = "public-sha-only"
    overall[verdict] += 1
    short = path.replace("/home/z/my-project/download/ocr-phase1/", "")
    if findings:
        detail = "; ".join(f"{k}: lines {v[:8]}{'…' if len(v) > 8 else ''} x{len(v)}"
                           for k, v in sorted(findings.items()))
        print(f"[{verdict:16s}] {short}\n                   {detail}")
    else:
        print(f"[{'clean':16s}] {short}")

print("\nSUMMARY:", overall)
print("NOTE: values NOT printed by design. Only line locations shown.")
