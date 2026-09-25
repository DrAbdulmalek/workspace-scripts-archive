#!/usr/bin/env python3
"""Secret scan over the session archive before packaging (Session Archive 2026-09-19).
Prints only class/file/line — NEVER the secret value itself. Exit 1 on any hit."""
import re
import sys
from pathlib import Path

PATTERNS = {
    "github_pat": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "ghp": re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    "ghs": re.compile(r"ghs_[A-Za-z0-9]{30,}"),
    "gho": re.compile(r"gho_[A-Za-z0-9]{30,}"),
    "aws_akia": re.compile(r"AKIA[0-9A-Z]{16}"),
    "openai_like": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "slack": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "gitlab_pat": re.compile(r"glpat-[A-Za-z0-9_-]{15,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer": re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{30,}"),
}
MAX_BYTES = 2_000_000


def main(root: str) -> int:
    root_path = Path(root)
    hits = 0
    scanned = 0
    for p in sorted(root_path.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
            data = p.read_bytes()
        except OSError:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue  # binary (bundles/zip) — skip content scan
        scanned += 1
        rel = p.relative_to(root_path)
        for line_no, line in enumerate(text.splitlines(), 1):
            for name, rx in PATTERNS.items():
                m = rx.search(line)
                if m:
                    hits += 1
                    print(f"HIT class={name} file={rel}:{line_no} (value not printed)")
    print(f"SCAN SUMMARY: files_text_scanned={scanned} hits={hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
