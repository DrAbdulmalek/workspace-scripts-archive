#!/usr/bin/env python3
"""CHECKPOINT-3 review closure: hash new artifacts, update OMNI-EXECUTION manifest,
sync the resilient /tmp mirror. Evidence-preservation only — no repo operations."""
import hashlib, json, os, shutil, time

ROOTS = [
    "/home/z/my-project/download/OMNI-EXECUTION",
    "/tmp/my-project/download/OMNI-EXECUTION",
    "/tmp/my-project/workspace-staging/OMNI-EXECUTION",
]
HOME = ROOTS[0]
REVIEW = os.path.join(HOME, "review")
NEW = [
    "review/CHECKPOINT-3_BASELINE_DRIFT.json",
    "review/D7_FORENSIC_REVIEW.md",
    "review/C1_C4_CLOSURE.md",
    "review/OCRRESULT_CONTRACT_FINAL_DECISION.md",
]

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

# 1. verify pre-existing manifest artifacts still OK in HOME
mp = os.path.join(HOME, "manifests/OMNI-EXECUTION_MANIFEST.json")
m = json.load(open(mp))
bad = 0
for a in m["artifacts"]:
    p = os.path.join(HOME, a["path"])
    if not os.path.exists(p) or sha(p) != a["sha256"]:
        bad += 1
        print("PRE-EXISTING MISMATCH:", a["path"])
print(f"pre-existing verified: {len(m['artifacts'])-bad}/{len(m['artifacts'])}")

# 2. append new artifacts (skip if already present)
have = {a["path"] for a in m["artifacts"]}
for rel in NEW:
    p = os.path.join(HOME, rel)
    if rel in have:
        continue
    m["artifacts"].append({"path": rel, "sha256": sha(p), "bytes": os.path.getsize(p)})
    print("ADDED:", rel)

m["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
m["note"] = ("covers CHECKPOINT-000 reconstructed + CHECKPOINT-1/2/3 bundles + "
             "CHECKPOINT-3 review closure (BASELINE DRIFT record, D7 forensic review, "
             "C1-C4 closure, final contract decision); manifest excludes itself")

# 3. write updated manifest to HOME, then sync mirrors (manifest + review dir)
with open(mp, "w") as f:
    json.dump(m, f, indent=1, ensure_ascii=False)
print("manifest updated:", len(m["artifacts"]), "artifacts")

for root in ROOTS[1:]:
    os.makedirs(os.path.join(root, "review"), exist_ok=True)
    for rel in NEW + ["manifests/OMNI-EXECUTION_MANIFEST.json"]:
        src = os.path.join(HOME, rel)
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

# 4. final verification across all three roots
print("\n--- cross-root verification ---")
ok = True
for rel in NEW + ["manifests/OMNI-EXECUTION_MANIFEST.json"]:
    ref = sha(os.path.join(HOME, rel))
    for root in ROOTS[1:]:
        h = sha(os.path.join(root, rel))
        if h != ref:
            ok = False
            print("MIRROR MISMATCH:", root, rel)
print("ALL MIRRORS IN SYNC" if ok else "MIRROR DRIFT DETECTED")
for rel in NEW:
    print(rel, sha(os.path.join(HOME, rel)))
