#!/usr/bin/env python3
import base64
import json
import sys
import urllib.parse
import urllib.request

# Dependency: brew install cryptography
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BARK_BASE = "https://api.day.app/xxx"
ENCRYPTION_KEY = "xxx"
ENCRYPTION_IV = "xxx"

OPENAI_ICON_URL = "https://images.ctfassets.net/j22is2dtoxu1/intercom-img-d177d076c9a5453052925143/49d5d812b0a6fcc20a14faa8c629d9fb/icon-ios-1024_401x.png"
# Claude symbol (CC0) from Wikimedia, publicly accessible without auth.
CLAUDE_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Claude_AI_symbol.svg/960px-Claude_AI_symbol.svg.png"
# OpenCode icon
OPENCODE_ICON_URL = "https://opencode.ai/apple-touch-icon.png"

def _load_key_iv():
    key_bytes = ENCRYPTION_KEY.encode("utf-8")
    if len(key_bytes) != 32:
        return None, None

    iv_bytes = ENCRYPTION_IV.encode("utf-8")
    if len(iv_bytes) != 12:
        return None, None

    return key_bytes, iv_bytes


def _encrypt_aes_gcm(plaintext: bytes, key: bytes, iv: bytes):
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(iv, plaintext, None)
    return base64.b64encode(encrypted).decode("ascii")


def _load_payload() -> dict:
    if len(sys.argv) > 1:
        try:
            return json.loads(sys.argv[1])
        except json.JSONDecodeError:
            return {}
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if raw:
                return json.loads(raw)
    except Exception:
        return {}
    return {}


def _detect_source(payload: dict) -> str:
    """Detect the source of the payload: 'claude', 'opencode', or 'codex'."""
    if payload.get("hook_event_name"):
        return "claude"
    if payload.get("session_id") or payload.get("transcript_path"):
        return "claude"
    title = payload.get("title") or ""
    if "Claude" in title:
        return "claude"
    if "OpenCode" in title or "opencode" in title.lower():
        return "opencode"
    event_type = payload.get("event") or payload.get("type") or ""
    if event_type.startswith("session.") or event_type in ("session_completed", "file_edited"):
        return "opencode"
    return "codex"


def main() -> None:
    payload = _load_payload()
    source = _detect_source(payload)

    event_type = (
        payload.get("hook_event_name")
        or payload.get("type")
        or payload.get("event")
    )
    if source == "claude":
        title = payload.get("title") or "Claude Code"
        icon_url = CLAUDE_ICON_URL
    elif source == "opencode":
        title = payload.get("title") or "OpenCode"
        icon_url = OPENCODE_ICON_URL
    else:
        title = payload.get("title") or "Codex"
        icon_url = OPENAI_ICON_URL
    subtitle = event_type
    message = (
        payload.get("last-assistant-message")
        or payload.get("message")
        or payload.get("summary")
    )
    if not message:
        cwd = payload.get("cwd")
        if cwd and event_type:
            message = f"{event_type} in {cwd}"
        elif cwd:
            message = f"Event in {cwd}"
        elif event_type:
            message = f"Event: {event_type}"
        else:
            message = "Event"
    push_payload = {
        "title": title,
        "markdown": message,
        "icon": icon_url,
        "action": "none",
    }
    if subtitle:
        push_payload["subtitle"] = subtitle
    key_bytes, iv_bytes = _load_key_iv()
    if not key_bytes:
        return

    plaintext = json.dumps(push_payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    try:
        ciphertext = _encrypt_aes_gcm(plaintext, key_bytes, iv_bytes)
    except Exception:
        return
    if not ciphertext:
        return

    form = urllib.parse.urlencode({"ciphertext": ciphertext, "iv": ENCRYPTION_IV})
    req = urllib.request.Request(
        BARK_BASE,
        data=form.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
    except Exception:
        # Do not block Codex runs on notification failures.
        return


if __name__ == "__main__":
    main()
