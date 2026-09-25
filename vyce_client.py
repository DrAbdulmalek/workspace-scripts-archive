#!/usr/bin/env python3
"""Vyce AI gateway client (OpenAI-compatible) for project work.

Security contract:
  - The API key is NEVER stored in this file or any repo file.
    It is loaded only from /home/z/my-project/.env.local (chmod 600)
    or the VYCE_API_KEY environment variable.
  - Per owner's PHI governance (Mistral precedent): do NOT send
    project/PHI/sensitive data through this third-party proxy.

Usage:
  python3 vyce_client.py models
  python3 vyce_client.py chat "prompt" [-m MODEL] [-s SYSTEM] [--max-tokens N]
  python3 vyce_client.py vision IMAGE_PATH "prompt" [-m MODEL]
  python3 vyce_client.py ask "prompt"            # plain-text answer, auto-fallback model
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

ENV_FILE = "/home/z/my-project/.env.local"
DEFAULT_BASE = "https://vyceai.com/v1"
TIMEOUT = 120
# Preferred order: proven-stable first, then fallbacks if one is down.
FALLBACK_MODELS = ["claude-sonnet-4-6", "deepseek-v4-flash-lr", "deepseek-v4-flash"]


def load_env(path: str = ENV_FILE) -> None:
    if os.environ.get("VYCE_API_KEY"):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


def _headers() -> dict:
    load_env()
    key = os.environ.get("VYCE_API_KEY")
    if not key:
        sys.exit(f"ERROR: VYCE_API_KEY not set (check {ENV_FILE})")
    base = os.environ.get("VYCE_API_BASE", DEFAULT_BASE).rstrip("/")
    # Cloudflare bans the default Python-urllib signature (error 1010);
    # a curl-style User-Agent passes.
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0",
    }, base


def _post(path: str, payload: dict, retries: int = 4):
    headers, base = _headers()
    url = f"{base}{path}"
    data = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(body).get("error", {})
                code, msg = err.get("code", e.code), err.get("message", "")[:120]
            except Exception:
                code, msg = e.code, body[:120]
            # 4xx (auth/bad request) -> retrying will not help
            if 400 <= e.code < 500 and e.code != 429:
                raise RuntimeError(f"HTTP {e.code} [{code}]: {msg}") from None
            last_err = f"HTTP {e.code} [{code}]: {msg}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"network: {e}"
        if attempt < retries:
            time.sleep(attempt * 8)
    raise RuntimeError(f"failed after {retries} attempts: {last_err}")


def models() -> list:
    headers, base = _headers()
    req = urllib.request.Request(f"{base}/models", headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8")).get("data", [])


def chat(model: str, messages: list, max_tokens: int = 2048,
         temperature: float | None = None, retries: int = 4) -> dict:
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        payload["temperature"] = temperature
    out = _post("/chat/completions", payload, retries=retries)
    choice = out["choices"][0]["message"]
    return {
        "model": out.get("model", model),
        "content": choice.get("content") or "",
        "finish_reason": out["choices"][0].get("finish_reason"),
        "usage": out.get("usage", {}),
    }


def ask(prompt: str, system: str | None = None, max_tokens: int = 2048) -> str:
    """Plain-text answer with automatic fallback across proven models."""
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    last_err = None
    for model in FALLBACK_MODELS:
        try:
            return chat(model, messages, max_tokens=max_tokens)["content"]
        except RuntimeError as e:
            last_err = e
    raise RuntimeError(f"all fallback models failed; last: {last_err}")


def vision(image_path: str, prompt: str, model: str = "nemotron-vision",
           max_tokens: int = 1024) -> dict:
    mime = mimetypes.guess_type(image_path)[0] or "image/png"
    with open(image_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ],
    }]
    return chat(model, messages, max_tokens=max_tokens)


def _cli() -> None:
    ap = argparse.ArgumentParser(description="Vyce AI client")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("models", help="list available models")

    p_chat = sub.add_parser("chat", help="single chat call (JSON output)")
    p_chat.add_argument("prompt")
    p_chat.add_argument("-m", "--model", default=FALLBACK_MODELS[0])
    p_chat.add_argument("-s", "--system", default=None)
    p_chat.add_argument("--max-tokens", type=int, default=2048)

    p_ask = sub.add_parser("ask", help="plain-text answer, auto model fallback")
    p_ask.add_argument("prompt")
    p_ask.add_argument("-s", "--system", default=None)
    p_ask.add_argument("--max-tokens", type=int, default=2048)

    p_vis = sub.add_parser("vision", help="image + prompt (JSON output)")
    p_vis.add_argument("image")
    p_vis.add_argument("prompt")
    p_vis.add_argument("-m", "--model", default="nemotron-vision")

    a = ap.parse_args()
    if a.cmd == "models":
        print(json.dumps(models(), indent=2, ensure_ascii=False))
    elif a.cmd == "chat":
        msgs = ([{"role": "system", "content": a.system}] if a.system else []) + [
            {"role": "user", "content": a.prompt}]
        print(json.dumps(chat(a.model, msgs, a.max_tokens), indent=2, ensure_ascii=False))
    elif a.cmd == "ask":
        print(ask(a.prompt, a.system, a.max_tokens))
    elif a.cmd == "vision":
        print(json.dumps(vision(a.image, a.prompt, a.model), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
