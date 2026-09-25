#!/usr/bin/env bash
# Finalize session archive: commit -> bundle -> end-to-end verification (clone back + sha256 -c + SHA match).
set -euo pipefail
BASE=/home/z/my-project
STAGE="$BASE/download/session-archive-20260919"
BUNDLE="$BASE/download/session-archive-20260919.bundle"
HASHES="$BASE/download/session-archive-20260919-FINAL-HASHES.txt"
SCRATCH="$BASE/scratch/ws-verify-$(date +%Y%m%dT%H%M%SZ)"

echo "== 1) commit =="
git -C "$STAGE" init -q -b main
git -C "$STAGE" config user.name "Super Z (session archive)"
git -C "$STAGE" config user.email "superz@session.local"
git -C "$STAGE" add -A
git -C "$STAGE" commit -q -F - <<'MSG'
Session archive 2026-09-19: omni-medical-suite session evidence (post reset #9)

Contents: worklog.md, M001_RECONSTRUCTION_RECORD.md, download/** (surviving
evidence: OMNI-EXECUTION + audit-branch handover bundles, forensic-audit,
task02d-remote-audit, ocr-phase1, olmocr reports, M001 FINAL GATE INCIDENT),
scripts/** (session tooling + this packaging chain).

Purpose: owner-ready persistence package for GitHub workspace upload.
Sandbox push BLOCKED: no credentials in environment (raw evidence in
README-UPLOAD.md section 4). Owner pushes per README-UPLOAD.md section 3.
MSG

ARCHIVE_SHA=$(git -C "$STAGE" rev-parse HEAD)
echo "ARCHIVE_COMMIT_SHA=$ARCHIVE_SHA"
git -C "$STAGE" status --short --branch | head -3

echo "== 2) bundle (full, with HEAD) =="
rm -f "$BUNDLE"
git -C "$STAGE" bundle create "$BUNDLE" --all HEAD
git -C "$STAGE" bundle verify "$BUNDLE"
git -C "$STAGE" bundle list-heads "$BUNDLE"

echo "== 3) end-to-end verification: clone back =="
rm -rf "$SCRATCH"; mkdir -p "$SCRATCH"
git clone -q "$BUNDLE" "$SCRATCH/archive"
CLONE_SHA=$(git -C "$SCRATCH/archive" rev-parse HEAD)
echo "CLONE_COMMIT_SHA=$CLONE_SHA"
[ "$ARCHIVE_SHA" = "$CLONE_SHA" ] && echo "SHA_MATCH=YES" || { echo "SHA_MATCH=NO"; exit 1; }
git -C "$SCRATCH/archive" status --short | head -3

echo "== 4) sha256 -c inside clone =="
cd "$SCRATCH/archive"
awk '{ if ($0 !~ /^#/ && NF) print }' MANIFEST.sha256 | sha256sum -c - > "$SCRATCH/sha256check.txt" 2>&1 || true
OK_N=$(awk '/: OK$/ {ok++} END {print ok+0}' "$SCRATCH/sha256check.txt")
BAD_N=$(awk '/FAILED|NO SUCH|open or read/ {bad++} END {print bad+0}' "$SCRATCH/sha256check.txt")
echo "SHA256CHECK_OK=$OK_N BAD=$BAD_N"
[ "$BAD_N" = "0" ] || { tail -5 "$SCRATCH/sha256check.txt"; exit 1; }

echo "== 5) FINAL-HASHES =="
BUNDLE_SHA=$(sha256sum "$BUNDLE" | awk '{print $1}')
BUNDLE_SIZE=$(wc -c < "$BUNDLE")
cat > "$HASHES" <<EOF
# Session Archive 2026-09-19 — FINAL HASHES (generated outside the bundle)
generated_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)
archive_commit_sha: $ARCHIVE_SHA
clone_back_match: YES ($CLONE_SHA)
sha256_manifest_check: OK=$OK_N BAD=0
bundle_path: download/session-archive-20260919.bundle
bundle_size_bytes: $BUNDLE_SIZE
bundle_sha256: $BUNDLE_SHA
bundle_prerequisites: NONE (standalone full bundle, HEAD line included)
EOF
cat "$HASHES"

echo "== 6) cleanup scratch =="
rm -rf "$SCRATCH"
echo "FINALIZE OK"
