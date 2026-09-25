#!/usr/bin/env bash
# Poll until an API window opens on the rotating egress IP, then fire the full batch FAST.
set -u
EV=/home/z/my-project/download/forensic-audit/evidence
for i in $(seq 1 40); do
  R=$(curl -sS -m 12 "https://api.github.com/rate_limit" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['resources']['core']['remaining'])" 2>/dev/null)
  echo "poll $i: remaining=$R"
  if [ "${R:-0}" -ge 5 ] 2>/dev/null; then
    echo "WINDOW OPEN — firing batch"
    curl -sS -m 25 "https://api.github.com/users/DrAbdulmalek" -o $EV/user.json
    curl -sS -m 25 "https://api.github.com/users/DrAbdulmalek/repos?per_page=100&type=owner&sort=pushed" -o $EV/repos_p1.json
    curl -sS -m 25 "https://api.github.com/repos/DrAbdulmalek/omni-medical-suite/pulls/123" -o $EV/pr123_now.json
    curl -sS -m 25 "https://api.github.com/repos/DrAbdulmalek/omni-medical-suite/commits/0e4294a5173c59c007349bf29a80869eb2a60596/check-runs?per_page=100" -o $EV/checkruns_now.json
    echo "batch fired"
    break
  fi
  sleep 14
done
echo "loop end"
