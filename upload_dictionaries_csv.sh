#!/usr/bin/env bash
# Upload converted dictionaries CSV to GitHub repo DrAbdulmalek/dictionaries-csv
# Governance: token NEVER printed (SHA-256 fingerprint only), no force push,
#             secrets-scan before push, verify remote SHA after push.
# Token source (priority): env GH_TOKEN -> /home/z/my-project/.secrets/gh_token
set -euo pipefail

OWNER="DrAbdulmalek"
REPO="dictionaries-csv"
CSV_DIR="/home/z/my-project/download/dictionaries-csv"
STAGE_DIR="/home/z/my-project/repos/dictionaries-csv"
TOKEN_FILE="/home/z/my-project/.secrets/gh_token"
LOG="/home/z/my-project/download/dictionaries-csv/upload_results.txt"
ALLOW_PUBLIC="${ALLOW_PUBLIC:-0}"   # default: private repo (safer for personal dictionaries)

mkdir -p "$(dirname "$LOG")"
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }

# ---- 1) token resolution ----------------------------------------------------
if [ -n "${GH_TOKEN:-}" ]; then
  TOKEN="$GH_TOKEN"; SRC="env GH_TOKEN"
elif [ -f "$TOKEN_FILE" ]; then
  TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"; SRC="$TOKEN_FILE"
else
  log "FAIL: no token (env GH_TOKEN empty, $TOKEN_FILE missing) — PERSISTENCE=BLOCKED"
  exit 2
fi
if [ -z "$TOKEN" ]; then log "FAIL: token empty — PERSISTENCE=BLOCKED"; exit 2; fi

FP="$(printf %s "$TOKEN" | sha256sum | cut -c1-16)"
log "token source: $SRC | sha256 fingerprint: $FP...(truncated) | length: ${#TOKEN} chars"
[ "$SRC" != "env GH_TOKEN" ] && [ "$(stat -c %a "$TOKEN_FILE")" != "600" ] && \
  log "WARN: $TOKEN_FILE perms != 600"

# ---- 2) preconditions -------------------------------------------------------
[ -d "$CSV_DIR" ] || { log "FAIL: $CSV_DIR missing — run convert_dictionaries_to_csv.py first"; exit 2; }
N_CSV=$(ls "$CSV_DIR"/*.csv 2>/dev/null | wc -l)
[ "$N_CSV" -ge 1 ] || { log "FAIL: no CSV files in $CSV_DIR"; exit 2; }
log "found $N_CSV CSV file(s) to upload"

# ---- 3) secrets scan (never push a leaked secret) ---------------------------
if grep -REn "ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH) PRIVATE KEY" "$CSV_DIR" >/dev/null 2>&1; then
  log "FAIL: secret-like pattern found in $CSV_DIR — push aborted"; exit 3
fi
log "secrets scan: clean"

# ---- 4) repo existence / creation -------------------------------------------
HTTP_CODE=$(curl -s -o /tmp/repo_check.json -w "%{http_code}" -m 30 \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$OWNER/$REPO")
if [ "$HTTP_CODE" = "200" ]; then
  log "repo $OWNER/$REPO exists (private=$(grep -o '"private": *[a-z]*' /tmp/repo_check.json | head -1))"
elif [ "$HTTP_CODE" = "404" ]; then
  PRIV="true"; [ "$ALLOW_PUBLIC" = "1" ] && PRIV="false"
  log "repo missing -> creating (private=$PRIV)"
  CREATE_CODE=$(curl -s -o /tmp/repo_create.json -w "%{http_code}" -m 30 \
    -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
    "https://api.github.com/user/repos" \
    -d "{\"name\":\"$REPO\",\"private\":$PRIV,\"description\":\"Arabic orthopedic/medical dictionaries converted to CSV\"}")
  [ "$CREATE_CODE" = "201" ] || { log "FAIL: repo create HTTP $CREATE_CODE: $(cat /tmp/repo_create.json | head -c 300)"; exit 4; }
  log "repo created"
else
  log "FAIL: repo check HTTP $HTTP_CODE"; exit 4
fi

# ---- 5) staging repo + commit -----------------------------------------------
mkdir -p "$STAGE_DIR"
cd "$STAGE_DIR"
if [ ! -d .git ]; then git init -b main -q; fi
git config user.name  "Omni Audit Bot"
git config user.email "audit@omni.local"
cp -f "$CSV_DIR"/*.csv .
# README + manifest of sources (sha256, sizes) for provenance
if [ -f "$CSV_DIR/conversion_report.json" ]; then cp -f "$CSV_DIR/conversion_report.json" .; fi
{ echo "# dictionaries-csv"; echo; echo "Converted from owner dictionary .txt files (encoding/delimiter auto-detected)."; echo "Generated $(date -u +%F). Report: conversion_report.json"; } > README.md
sha256sum "$CSV_DIR"/*.csv > MANIFEST.sha256 || true
git add -A
git commit -q -m "Add dictionary CSVs converted from owner .txt files ($(date -u +%F)); rows+provenance in conversion_report.json" || log "nothing new to commit"
SHA=$(git rev-parse HEAD)
log "commit: $SHA"

# ---- 6) push via askpass (token never in URL/config/argv) --------------------
ASKPASS="$(mktemp /tmp/askpass.XXXXXX)"; chmod 700 "$ASKPASS"
printf '#!/bin/sh\ncase "$1" in *Username*) echo x-access-token;; *Password*) echo "$DICT_GH_TOKEN";; esac\n' > "$ASKPASS"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$OWNER/$REPO.git"
export DICT_GH_TOKEN="$TOKEN" GIT_ASKPASS="$ASKPASS"
PUSH_OUT=$(GIT_TERMINAL_PROMPT=0 git push -u origin main 2>&1) && PUSH_OK=1 || PUSH_OK=0
echo "$PUSH_OUT" | tee -a "$LOG" | grep -E "error|fatal|rejected" && { unset DICT_GH_TOKEN; rm -f "$ASKPASS"; log "FAIL: push error"; exit 5; } || true
[ "$PUSH_OK" = "1" ] || { unset DICT_GH_TOKEN; rm -f "$ASKPASS"; log "FAIL: push failed (see above)"; exit 5; }
log "push: OK"

# ---- 7) remote SHA verification (askpass env still active) -------------------
REMOTE_SHA=$(GIT_TERMINAL_PROMPT=0 git ls-remote origin main | cut -f1)
unset DICT_GH_TOKEN; rm -f "$ASKPASS"
if [ "$REMOTE_SHA" = "$SHA" ]; then
  log "VERIFY: remote main == $SHA — PROVEN"
else
  log "FAIL: remote SHA $REMOTE_SHA != local $SHA"; exit 6
fi
log "SUCCESS: $N_CSV CSV file(s) live at https://github.com/$OWNER/$REPO"
