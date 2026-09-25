#!/usr/bin/env bash
# Build staging tree of the 2026-09-19 session archive (copies only; no git ops here).
set -euo pipefail
BASE=/home/z/my-project
STAGE="$BASE/download/session-archive-20260919"

mkdir -p "$STAGE/download" "$STAGE/scripts"

# 1) worklog
cp "$BASE/worklog.md" "$STAGE/worklog.md"

# 2) download/* — exclude the staging dir itself
cd "$BASE/download"
shopt -s nullglob
for entry in * .[!.]*; do
  [ -e "$entry" ] || continue
  [ "$entry" = "session-archive-20260919" ] && continue
  cp -r "$entry" "$STAGE/download/"
done

# 3) scripts/*
cd "$BASE/scripts"
for f in *; do
  [ -e "$f" ] || continue
  cp -r "$f" "$STAGE/scripts/"
done

echo "COPY OK"
find "$STAGE" -type f | wc -l
du -sh "$STAGE"
