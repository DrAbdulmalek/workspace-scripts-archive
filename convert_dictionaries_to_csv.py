#!/usr/bin/env python3
"""
Convert owner dictionary .txt files to CSV (UTF-8 BOM, Excel-friendly).

Targets (per owner request 2026-09-24):
  - ortho_dict_09_2017.txt
  - dics05052017.txt
  - dict - Copy.txt

Design:
  - Encoding detection: utf-8-sig -> utf-8 -> utf-16 -> cp1256 (Arabic legacy)
  - Delimiter detection per file (majority vote): TAB | pipe | " = " | " :: " | ";" | "؛" | plain list
  - Output: <name>.csv with columns id,term,translation  (or id,entry for plain lists)
  - Never modifies sources; writes to --outdir (default /home/z/my-project/download/dictionaries-csv)
  - Emits conversion_report.json with sha256 of every source + row counts.

Exit codes: 0 = all converted, 3 = one or more sources missing, 4 = no files at all.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

UPLOAD_DIR = Path(os.environ.get("DICT_UPLOAD_DIR", "/home/z/my-project/upload"))
OUT_DIR = Path(os.environ.get("DICT_OUT_DIR", "/home/z/my-project/download/dictionaries-csv"))

TARGET_FILES = [
    "ortho_dict_09_2017.txt",
    "dics05052017.txt",
    "dict - Copy.txt",
]

ENCODINGS = ["utf-8-sig", "utf-8", "utf-16", "cp1256"]

# (name, regex-free detector lambda) — first match wins for a line
def _detect_fmt(line: str) -> str:
    if "\t" in line:
        return "tab"
    if " | " in line or line.count("|") >= 1:
        return "pipe"
    if "::" in line:
        return "dcolon"
    if " = " in line or "\t=" in line:
        return "eq"
    if "؛" in line:
        return "semicolon_ar"
    if ";" in line:
        return "semicolon"
    stripped = line.strip()
    if stripped:
        return "plain"
    return "empty"


def read_with_encoding(path: Path) -> tuple[str, str]:
    """Return (text, encoding_used). Raises ValueError if none decode."""
    raw = path.read_bytes()
    errors = []
    for enc in ENCODINGS:
        try:
            text = raw.decode(enc)
            # cp1256 maps almost any byte; sanity check: replacement chars means wrong decode
            if enc == "cp1256" and "\ufffd" in text:
                errors.append(f"{enc}: replacement chars")
                continue
            return text, enc
        except (UnicodeDecodeError, UnicodeError) as e:
            errors.append(f"{enc}: {e}")
    raise ValueError("no encoding worked: " + "; ".join(errors))


def split_line(line: str, fmt: str) -> list[str]:
    s = line.rstrip("\n\r")
    if fmt == "tab":
        parts = s.split("\t")
    elif fmt == "pipe":
        parts = [p.strip() for p in s.split("|")]
    elif fmt == "dcolon":
        parts = [p.strip() for p in s.split("::", 1)]
    elif fmt == "eq":
        parts = [p.strip() for p in s.split("=", 1)]
    elif fmt == "semicolon_ar":
        parts = [p.strip() for p in s.split("؛", 1)]
    elif fmt == "semicolon":
        parts = [p.strip() for p in s.split(";", 1)]
    else:
        parts = [s.strip()]
    return [p.strip() for p in parts if p.strip()]


def convert_file(path: Path, out_dir: Path) -> dict:
    text, enc = read_with_encoding(path)
    lines = text.splitlines()
    nonempty = [ln for ln in lines if ln.strip()]

    # majority-vote format detection on non-empty lines
    votes: dict[str, int] = {}
    for ln in nonempty:
        f = _detect_fmt(ln)
        votes[f] = votes.get(f, 0) + 1
    fmt = max(votes, key=votes.get) if votes else "plain"

    rows: list[list[str]] = []
    malformed = 0
    for ln in nonempty:
        parts = split_line(ln, fmt)
        if not parts:
            continue
        if fmt == "plain":
            rows.append(parts[:1])
        else:
            if len(parts) >= 2:
                rows.append([parts[0], " ".join(parts[1:])])
            else:
                # line didn't match the majority format -> keep as single cell
                malformed += 1
                rows.append([parts[0], ""])

    out_name = path.stem + ".csv"
    out_path = out_dir / out_name
    has_translation = fmt != "plain"
    header = ["id", "term", "translation"] if has_translation else ["id", "entry"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for i, r in enumerate(rows, 1):
            w.writerow([i] + r) if has_translation else w.writerow([i, r[0]])

    return {
        "source": str(path),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_bytes": path.stat().st_size,
        "encoding": enc,
        "detected_format": fmt,
        "format_votes": votes,
        "output": str(out_path),
        "rows": len(rows),
        "malformed_lines": malformed,
        "header": header,
    }


def main() -> int:
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    results, missing = [], []
    for name in TARGET_FILES:
        p = UPLOAD_DIR / name
        if not p.is_file():
            missing.append(name)
            continue
        try:
            results.append(convert_file(p, out_dir))
        except ValueError as e:
            missing.append(f"{name} (decode failed: {e})")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": TARGET_FILES,
        "converted": results,
        "missing": missing,
        "total_rows": sum(r["rows"] for r in results),
    }
    (out_dir / "conversion_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"converted: {len(results)} file(s), {report['total_rows']} rows total")
    for r in results:
        print(f"  {Path(r['source']).name}: {r['rows']} rows, enc={r['encoding']}, fmt={r['detected_format']} -> {r['output']}")
    if missing:
        print(f"MISSING/FAILED: {missing}")
        return 3 if results else 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
