from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def _secret() -> bytes:
    return os.getenv("AUTH_SECRET", "").encode("utf-8")


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_token(organization: str, user: str, ttl_seconds: int = 3600) -> str:
    secret = _secret()
    if not secret:
        raise RuntimeError("AUTH_SECRET 未配置")
    payload = {
        "org": organization,
        "user": user,
        "exp": int(time.time()) + ttl_seconds,
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def verify_token(token: str) -> dict | None:
    secret = _secret()
    if not secret or "." not in token:
        return None
    body, signature = token.split(".", 1)
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
    try:
        provided = _b64decode(signature)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected, provided):
        return None
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    if not payload.get("org") or not payload.get("user"):
        return None
    return payload


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("用法: python -m app.auth <org-code> <user-email>")
    print(issue_token(sys.argv[1], sys.argv[2]))
