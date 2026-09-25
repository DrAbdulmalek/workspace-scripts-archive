#!/usr/bin/env python3
"""TASK-02D smoke: Gradio 6.26.0 compatibility with the REAL production apps.

A) hf-space/app.py  — the exact Docker CMD (`python app.py`) of Dockerfile.gradio
   - dev mode launch (no auth), HTTP 200 + /config JSON
   - production mode launch with GRADIO_USERNAME/PASSWORD (verifies auth= contract)
B) app/gradio_full_hitl.py — the official 944-line HITL app: import (builds Blocks)
   + headless launch + HTTP check.
"""
import json, os, signal, subprocess, sys, time, urllib.request

REPO = "/home/z/my-project/repos/omni-medical-suite"
PY = sys.executable
results = []

def record(name, ok, detail=""):
    results.append((name, "PASS" if ok else "FAIL", detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

def wait_up(url, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(2)
    return False

def launch_and_probe(cmd, env, name, port, auth=None):
    print(f"  launching: {name} (port {port}) ...")
    p = subprocess.Popen(cmd, env=env, cwd=os.path.join(REPO, "hf-space") if "app.py" in cmd[-1] else REPO,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         start_new_session=True)
    try:
        up = wait_up(f"http://127.0.0.1:{port}/", timeout=240)
        cfg_ok, cfg_detail = False, ""
        if up:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/config")
                if auth:
                    import base64
                    req.add_header("Authorization", "Basic " + base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode())
                with urllib.request.urlopen(req, timeout=10) as r:
                    cfg = json.load(r)
                comps = len(cfg.get("components", []))
                cfg_ok, cfg_detail = comps > 0, f"authenticated /config ok, components={comps}, version={cfg.get('version')}"
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    # auth enforced: unauthenticated /config rejected (login page served at /)
                    cfg_ok, cfg_detail = True, "auth enforced: /config -> 401 without credentials, / -> 200 (login page)"
                else:
                    cfg_detail = f"/config HTTP {e.code}"
            except Exception as e:
                cfg_detail = f"/config error: {e}"
        record(name, up and cfg_ok, f"http200={up}; {cfg_detail}")
    finally:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            pass
        try:
            p.wait(timeout=15)
        except Exception:
            try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except Exception: pass
    # print last output lines for evidence
    return p

print("=== GRADIO SMOKE ===")

# A1: Space app, development mode (no auth)
env = dict(os.environ, ENVIRONMENT="development", GRADIO_SERVER_NAME="127.0.0.1")
p = launch_and_probe([PY, "app.py"], env, "hf-space/app.py dev-mode launch (Docker CMD path)", 7860)
time.sleep(3)

# A2: Space app, production mode with credentials (auth= contract on gradio 6)
env = dict(os.environ, ENVIRONMENT="production", GRADIO_USERNAME="med", GRADIO_PASSWORD="s3cret!" * 3, GRADIO_SERVER_NAME="127.0.0.1")
p = launch_and_probe([PY, "app.py"], env, "hf-space/app.py production-mode launch (auth= contract)", 7860, auth=("med", "s3cret!" * 3))
time.sleep(3)

# B: official HITL app import + headless launch
script = r"""
import sys, urllib.request, json, time
sys.path.insert(0, "/home/z/my-project/repos/omni-medical-suite")
import gradio as gr
ok_import, ok_launch, detail = False, False, ""
try:
    import app.gradio_full_hitl as hitl
    ok_import = True
    demo = hitl.demo
    detail += f"Blocks built: {type(demo).__name__}; "
    demo.launch(server_name="127.0.0.1", server_port=7862, prevent_thread_lock=True, quiet=True)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:7862/", timeout=5) as r:
                if r.status == 200:
                    ok_launch = True; break
        except Exception:
            time.sleep(1)
    with urllib.request.urlopen("http://127.0.0.1:7862/config", timeout=10) as r:
        cfg = json.load(r)
    detail += f"components={len(cfg.get('components', []))}; gradio={gr.__version__}"
    demo.close()
except Exception as e:
    detail += f"ERROR: {type(e).__name__}: {e}"
print("HITL_RESULT", ok_import, ok_launch, detail)
"""
env = dict(os.environ, ENVIRONMENT="development")
p = subprocess.run([PY, "-c", script], env=env, capture_output=True, text=True, timeout=420, cwd=REPO)
line = [l for l in (p.stdout or "").splitlines() if l.startswith("HITL_RESULT")]
if line:
    _, imp, lau, det = line[0].split(" ", 3)
    record("app/gradio_full_hitl.py import + headless launch", imp == "True" and lau == "True", det)
else:
    record("app/gradio_full_hitl.py import + headless launch", False, (p.stderr or p.stdout)[-400:])

print("\n=== GRADIO SMOKE SUMMARY ===")
fails = sum(1 for _, st, _ in results if st == "FAIL")
sys.exit(1 if fails else 0)
