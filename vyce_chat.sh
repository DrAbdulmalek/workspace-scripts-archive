#!/usr/bin/env bash
# Vyce AI (OpenAI-compatible) minimal client.
# Usage:
#   vyce_chat.sh MODEL "prompt"
#   echo "text" | vyce_chat.sh MODEL -
# Working models as of 2026-09-14: claude-sonnet-4-6, deepseek-v4-flash-lr
# Unstable/maintenance: deepseek-v4-flash (500/timeout), gpt-5.6-new (503),
#                       nemotron-ultra-550b (500), nemotron-vision (500)
set -euo pipefail
ENV_FILE="/home/z/my-project/.env.local"
[ -r "$ENV_FILE" ] && set -a && . "$ENV_FILE" && set +a
: "${VYCE_API_KEY:?VYCE_API_KEY not set - check $ENV_FILE}"
: "${VYCE_API_BASE:=https://vyceai.com/v1}"
MODEL="${1:?usage: vyce_chat.sh MODEL \"prompt\"|-}"
PROMPT="${2:?usage: vyce_chat.sh MODEL \"prompt\"|-}"
if [ "$PROMPT" = "-" ]; then PROMPT="$(cat)"; fi
PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"model":sys.argv[1],"messages":[{"role":"user","content":sys.argv[2]}]}))' "$MODEL" "$PROMPT")"
# Service is intermittently flaky (HTTP 500 between 200s) -> retry with backoff.
for ATTEMPT in 1 2 3 4; do
  OUT="$(curl -sS -m 120 "$VYCE_API_BASE/chat/completions" \
    -H "Authorization: Bearer $VYCE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")" && \
  if ! printf %s "$OUT" | grep -q '"type":"server_error"'; then
    printf %s "$OUT"; exit 0
  fi
  echo "attempt $ATTEMPT failed (server_error), retrying..." >&2
  sleep $((ATTEMPT * 8))
done
printf %s "$OUT"; exit 1
