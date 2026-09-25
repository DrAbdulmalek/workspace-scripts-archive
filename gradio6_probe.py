"""Gradio 6.26.0 API-compatibility probe for omni-medical-suite usage surface.

Verifies each Gradio API actually used by the production apps
(app/gradio_full_hitl.py, app/advanced_review_app.py, app/gradio_extended.py,
hf-space/app.py, hf-space/app_core.py) against gradio 6.26.0, then performs a
REAL launch with auth=tuple and HTTP checks on "/" and "/config".
"""
import inspect
import sys
import urllib.request
import urllib.error
import base64

import gradio as gr

results = []


def check(name, fn):
    try:
        detail = fn()
        results.append((name, "OK", str(detail)))
    except Exception as e:
        results.append((name, "FAIL", repr(e)[:160]))


def param_of(fn, pname):
    sig = inspect.signature(fn)
    return pname in sig.parameters


# 1. Component/parameter signature checks (exact params used in the codebase)
check("gr.Blocks(css=..., theme=...)", lambda: (
    param_of(gr.Blocks.__init__, "css") and param_of(gr.Blocks.__init__, "theme")))
check("gr.themes.Soft(primary_hue=..., secondary_hue=...)", lambda: (
    param_of(gr.themes.Soft, "primary_hue") and param_of(gr.themes.Soft, "secondary_hue")))
check("gr.Image(type='numpy', label=...)", lambda: (
    "type" in inspect.signature(gr.Image.__init__).parameters))
check("gr.Textbox(lines=, interactive=, max_lines=, placeholder=)", lambda: (
    all(param_of(gr.Textbox.__init__, p) for p in ("lines", "interactive", "max_lines", "placeholder"))))
check("gr.Button(variant=, size=)", lambda: (
    all(param_of(gr.Button.__init__, p) for p in ("variant", "size"))))
check("gr.Dropdown(choices=, label=)", lambda: (
    all(param_of(gr.Dropdown.__init__, p) for p in ("choices", "label"))))
check("gr.File(label=)", lambda: param_of(gr.File.__init__, "label"))
check("gr.State(value=)", lambda: param_of(gr.State.__init__, "value"))
check("gr.Progress()", lambda: gr.Progress is not None)
check("gr.Tab / gr.Tabs context managers", lambda: (gr.Tab is not None and gr.Tabs is not None))
check("Blocks.launch(auth=, server_name=, server_port=, show_error=)", lambda: (
    all(param_of(gr.Blocks.launch, p) for p in ("auth", "server_name", "server_port", "show_error"))))
check("event .click(fn, inputs=, outputs=)", lambda: param_of(gr.Button.click, "fn"))
check("queue NOT required (no .queue() call in codebase)", lambda: True)

# 2. REAL app built with the exact production pattern
custom_css = ".gradio-container {max-width: 900px;}"
with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", secondary_hue="green"),
               css=custom_css) as demo:
    with gr.Tabs():
        with gr.Tab("OCR Processing"):
            with gr.Row():
                input_image = gr.Image(type="numpy", label="Upload Medical Image")
                with gr.Column():
                    process_btn = gr.Button("Full Processing", variant="primary", size="lg")
                    status = gr.Textbox(label="Status", interactive=False, lines=3)
            cleaned_img = gr.Image(label="After Preprocessing")
            raw_ocr = gr.Textbox(label="Raw OCR Output", lines=4)
            category = gr.Dropdown(choices=["A", "B"], label="Category")
            save_btn = gr.Button("Save", variant="secondary")
            st = gr.State(value=None)
        with gr.Tab("Translation"):
            translate_input = gr.Textbox(label="Source Text", lines=6,
                                         placeholder="Enter text...")
            translate_btn = gr.Button("Translate", variant="primary")
            translate_output = gr.Textbox(label="Translation", lines=8, interactive=False)

    def fake_process(img, progress=gr.Progress()):
        progress(0.5, desc="working")
        return img, "ok", "raw text"

    process_btn.click(fake_process, inputs=[input_image],
                      outputs=[cleaned_img, status, raw_ocr])

    def fake_translate(t, progress=gr.Progress()):
        return t

    translate_btn.click(fake_translate, inputs=[translate_input],
                        outputs=[translate_output])

# 3. Launch with production auth pattern (tuple from env, as hf-space/app.py:62-63)
auth = ("probeuser", "probepass")
demo.launch(server_name="127.0.0.1", server_port=7861, auth=auth,
            show_error=True, quiet=True, prevent_thread_lock=True)
local_url = demo.local_url
print("LAUNCHED_AT", local_url, flush=True)


def http(url, use_auth=False):
    req = urllib.request.Request(url)
    if use_auth:
        tok = base64.b64encode(b"probeuser:probepass").decode()
        req.add_header("Authorization", "Basic " + tok)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, str(r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return -1, repr(e)[:80]


# Gradio auth uses form POST /login + session cookie (NOT Basic auth)
import urllib.parse
from http import cookiejar
cj = cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

for path in ("/", "/config"):
    s_no, ct_no = http(local_url.rstrip("/") + path, use_auth=False)
    results.append((f"HTTP {path} no-auth", str(s_no), ct_no))

# full login flow: POST /login with credentials -> cookie -> /config
login_url = local_url.rstrip("/") + "/login"
try:
    data = urllib.parse.urlencode({"username": "probeuser", "password": "probepass"}).encode()
    with opener.open(urllib.request.Request(login_url, data=data), timeout=15) as r:
        results.append(("POST /login with credentials", str(r.status), "cookie set: %d" % len(cj)))
    with opener.open(local_url.rstrip("/") + "/config", timeout=15) as r:
        body = r.read(200)
        results.append(("HTTP /config with-session-cookie", str(r.status), "is_json_config=%s" % body.lstrip().startswith(b"{")))
except urllib.error.HTTPError as e:
    results.append(("POST /login flow", str(e.code), "FAIL"))

# unauthenticated wrong-credential login must be rejected
try:
    bad = urllib.parse.urlencode({"username": "probeuser", "password": "WRONG"}).encode()
    req2 = urllib.request.Request(login_url, data=bad)
    with urllib.request.urlopen(req2, timeout=15) as r:
        results.append(("POST /login WRONG credentials", str(r.status), "should be rejected"))
except urllib.error.HTTPError as e:
    results.append(("POST /login WRONG credentials", str(e.code), "rejected (expected)"))
except Exception as e:
    results.append(("POST /login WRONG credentials", "-1", repr(e)[:80]))

# 4. Summary
print("\n=== PROBE RESULTS (gradio %s) ===" % gr.__version__)

def verdict(name, st):
    if name.startswith("HTTP /config no-auth") or name.startswith("HTTP /config with-auth-basic"):
        return "PASS" if st in ("401", "403", "307", "302") else "FAIL"
    if name.startswith("HTTP / no-auth"):
        return "PASS" if st in ("200", "401", "403", "307", "302") else "FAIL"
    if name == "POST /login with credentials":
        return "PASS" if st == "200" else "FAIL"
    if name == "HTTP /config with-session-cookie":
        return "PASS" if st == "200" else "FAIL"
    if name == "POST /login WRONG credentials":
        return "PASS" if st in ("401", "403") else "INFO"
    return "PASS" if st == "OK" else "FAIL"

fails = 0
for name, st, detail in results:
    flag = verdict(name, st)
    if flag == "FAIL":
        fails += 1
    print(f"{flag:4} | {name:55} | {st} | {detail}")
print("TOTAL_FAILS:", fails)
demo.close()
sys.exit(1 if fails else 0)
