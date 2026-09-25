#!/usr/bin/env python3
"""Build MANIFEST.sha256 for the session archive (excludes .git and the manifest itself)."""
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path


def main(root: str) -> int:
    root_path = Path(root).resolve()
    files = [
        p for p in sorted(root_path.rglob("*"))
        if p.is_file() and ".git" not in p.parts and p.name != "MANIFEST.sha256"
    ]
    lines = [
        "# Session Archive 2026-09-19 — MANIFEST.sha256",
        f"# generated_utc: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"# root: {root_path.name}",
        f"# files: {len(files)}",
        f"# total_bytes: {sum(p.stat().st_size for p in files)}",
        "# verify: sha256sum -c MANIFEST.sha256",
    ]
    for p in files:
        rel = p.relative_to(root_path).as_posix()
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{h}  {rel}")
    out = root_path / "MANIFEST.sha256"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"MANIFEST OK: {len(files)} files, {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
