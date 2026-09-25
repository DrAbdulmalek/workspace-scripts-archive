#!/usr/bin/env python3
"""TASK-02D — per-test-ID diff of BEFORE vs AFTER junitxml runs."""
import xml.etree.ElementTree as ET

EV = "/home/z/my-project/download/task02d-evidence"

def load(path):
    t = ET.parse(path)
    out = {}
    for tc in t.iter("testcase"):
        cls = tc.get("classname", "")
        key = f"{cls}::{tc.get('name')}"
        if tc.find("failure") is not None:
            st = "failed"
        elif tc.find("error") is not None:
            st = "error"
        elif tc.find("skipped") is not None:
            st = "skipped"
        else:
            st = "passed"
        out[key] = st
    return out

before = load(f"{EV}/pytest_BEFORE.xml")
after = load(f"{EV}/pytest_AFTER.xml")
print(f"BEFORE tests: {len(before)}  AFTER tests: {len(after)}")

from collections import Counter
cb, ca = Counter(before.values()), Counter(after.values())
print("BEFORE:", dict(cb))
print("AFTER:  ", dict(ca))

changed = []
for k in set(before) | set(after):
    b, a = before.get(k), after.get(k)
    if b != a:
        changed.append((k, b, a))

if not changed:
    print("\nPER-TEST DIFF: ZERO differences — identical outcomes for every single test ID.")
else:
    print(f"\n{len(changed)} tests changed status:")
    for k, b, a in sorted(changed):
        print(f"  {k}: {b} -> {a}")
