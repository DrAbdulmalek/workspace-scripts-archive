#!/usr/bin/env python3
"""TASK-02D — enrich findings table with severity (CVSS / GHSA ratings) from OSV."""
import json, urllib.request, time

EV = "/home/z/my-project/download/task02d-evidence"

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                return {"_err": str(e)}
            time.sleep(2)

rows = []
for line in open(f"{EV}/BEFORE_findings_table.txt"):
    pkg, ver, aid, fix, surf = line.strip().split("|")
    rows.append((pkg, ver, aid, fix, surf))

out = []
for pkg, ver, aid, fix, surf in rows:
    sev, aliases = "n/a", ""
    d = get(f"https://api.osv.dev/v1/vulns/{aid}")
    if "_err" not in d:
        aliases = ", ".join(d.get("aliases", [])[:2])
        sev_blocks = d.get("severity", [])
        cvss = next((s["score"] for s in sev_blocks if s.get("type") in ("CVSS_V3", "CVSS_V4")), "")
        if not cvss:
            for al in d.get("aliases", []):
                if al.startswith("GHSA-"):
                    g = get(f"https://api.osv.dev/v1/vulns/{al}")
                    if "_err" not in g:
                        db = g.get("database_specific", {})
                        sev = db.get("severity", "")
                        gs = g.get("severity", [])
                        cvss = next((s["score"] for s in gs if s.get("type") in ("CVSS_V3", "CVSS_V4")), "")
                        if cvss or sev:
                            aliases = ", ".join(g.get("aliases", [])[:2])
                            break
        if cvss:
            # extract base score from vector
            import re
            m = re.search(r"/([A-Z]\d(?:\.\d)?)(?:$|/)", cvss)
            base = m.group(1) if m else "?"
            sev = f"{cvss.split('/')[0]}:{base}" if base != "?" else cvss[:30]
        elif not sev:
            sev = "n/a"
    else:
        aliases = "fetch-fail"
    out.append({"pkg": pkg, "ver": ver, "id": aid, "fix": fix, "surf": surf, "sev": sev, "alias": aliases})
    time.sleep(0.3)

with open(f"{EV}/BEFORE_findings_severity.json", "w") as f:
    json.dump(out, f, indent=1)

with open(f"{EV}/BEFORE_findings_table_enriched.md", "w") as f:
    f.write("| Package | Installed | Advisory | Aliases | Severity | Fixed Version | Path | Surface | Runtime Used? |\n")
    f.write("|---|---|---|---|---|---|---|---|---|\n")
    for r in out:
        direct = "Direct" if r["pkg"] in ("gradio", "transformers", "pillow", "Pillow", "ecdsa") else "Transitive"
        f.write(f"| {r['pkg']} | {r['ver']} | {r['id']} | {r['alias']} | {r['sev']} | {r['fix'] or 'NONE (no fix released)'} | {direct} | {r['surf']} | Yes |\n")

print("rows:", len(out))
sev_missing = sum(1 for r in out if r["sev"] == "n/a")
print("severity n/a:", sev_missing)
for r in out[:5]:
    print(r["pkg"], r["id"], r["sev"], "|", r["alias"])
