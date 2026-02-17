"""
Qwen OAuth (Device Authorization Grant) support.
Implements the same device flow used by Qwen Code to obtain access tokens.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
import asyncio
import os
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse, urlunparse, parse_qsl, urlencode

import httpx

QWEN_OAUTH_BASE_URL = "https://chat.qwen.ai"
QWEN_OAUTH_DEVICE_ENDPOINT = f"{QWEN_OAUTH_BASE_URL}/api/v1/oauth2/device"
QWEN_OAUTH_DEVICE_CODE_ENDPOINT = f"{QWEN_OAUTH_BASE_URL}/api/v1/oauth2/device/code"
QWEN_OAUTH_TOKEN_ENDPOINT = f"{QWEN_OAUTH_BASE_URL}/api/v1/oauth2/token"
QWEN_OAUTH_CLIENT_ID = (
    os.getenv("QWEN_CLIENT_ID")
    or os.getenv("QWEN_OAUTH_CLIENT_ID")
    or "f0304373b74a44d2b584a3fb70ca9e56"
)
QWEN_OAUTH_SCOPE = "openid profile email model.completion"
QWEN_OAUTH_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
QWEN_OAUTH_CODE_CHALLENGE_METHOD = "S256"
DEFAULT_QWEN_RESOURCE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_OAUTH_AUTHORIZE_URL = f"{QWEN_OAUTH_BASE_URL}/authorize"
QWEN_OAUTH_CLIENT_SLUG = "qwen-code"
QWEN_OAUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "MyCasaPro/1.0",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def generate_code_verifier() -> str:
    # RFC 7636: length between 43-128 chars. token_urlsafe(64) yields ~86 chars.
    return secrets.token_urlsafe(64)[:96]


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _form_encode(data: Dict[str, Any]) -> Dict[str, str]:
    return {k: str(v) for k, v in data.items() if v is not None}


def request_device_authorization_sync() -> Dict[str, Any]:
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    payload_with_pkce = {
        "client_id": QWEN_OAUTH_CLIENT_ID,
        "scope": QWEN_OAUTH_SCOPE,
        "code_challenge": code_challenge,
        "code_challenge_method": QWEN_OAUTH_CODE_CHALLENGE_METHOD,
    }
    payload_minimal = {
        "client_id": QWEN_OAUTH_CLIENT_ID,
        "scope": QWEN_OAUTH_SCOPE,
    }
    headers = dict(QWEN_OAUTH_HEADERS)
    endpoints = [QWEN_OAUTH_DEVICE_ENDPOINT, QWEN_OAUTH_DEVICE_CODE_ENDPOINT]
    payloads = [payload_with_pkce, payload_minimal]
    response = None
    data = None

    with httpx.Client(timeout=15) as client:
        for endpoint in endpoints:
            for payload in payloads:
                response = client.post(endpoint, data=_form_encode(payload), headers=headers)
                if response.status_code >= 400:
                    continue
                try:
                    data = response.json()
                except Exception:
                    # Non-JSON response, try next endpoint/payload
                    data = None
                if data:
                    break
            if data:
                break

    if response is None or data is None:
        raise RuntimeError("Device authorization failed: no valid JSON response from Qwen")
    if response.status_code >= 400:
        raise RuntimeError(f"Device authorization failed: {response.status_code} {response.text}")
    if "device_code" not in data:
        raise RuntimeError(f"Device authorization failed: {data}")
    if data.get("user_code"):
        # Prefer the canonical Qwen authorize URL (matches Qwen Code / OpenClaw flow)
        user_code = quote(str(data["user_code"]))
        data["verification_uri_complete"] = f"{QWEN_OAUTH_AUTHORIZE_URL}?user_code={user_code}&client={QWEN_OAUTH_CLIENT_SLUG}"
    elif not data.get("verification_uri_complete") and data.get("verification_uri") and data.get("user_code"):
        parsed = urlparse(data["verification_uri"])
        query = dict(parse_qsl(parsed.query))
        query.setdefault("user_code", str(data["user_code"]))
        data["verification_uri_complete"] = urlunparse(parsed._replace(query=urlencode(query)))
    data["code_verifier"] = code_verifier
    data["code_challenge"] = code_challenge
    return data


def poll_device_token_sync(device_code: str, code_verifier: str) -> Dict[str, Any]:
    payload = {
        "grant_type": QWEN_OAUTH_GRANT_TYPE,
        "client_id": QWEN_OAUTH_CLIENT_ID,
        "device_code": device_code,
        "code_verifier": code_verifier,
    }
    headers = dict(QWEN_OAUTH_HEADERS)
    with httpx.Client(timeout=15) as client:
        response = client.post(QWEN_OAUTH_TOKEN_ENDPOINT, data=_form_encode(payload), headers=headers)

    # OAuth device flow polling responses
    if response.status_code == 400:
        try:
            data = response.json()
        except Exception:
            return {"status": "error", "error": "invalid_response", "error_description": response.text}
        if data.get("error") == "authorization_pending":
            return {"status": "pending"}
        return {"status": "error", "error": data.get("error"), "error_description": data.get("error_description")}
    if response.status_code == 429:
        try:
            data = response.json()
        except Exception:
            return {"status": "error", "error": "rate_limited", "error_description": response.text}
        if data.get("error") == "slow_down":
            return {"status": "pending", "slow_down": True}

    if response.status_code >= 400:
        return {"status": "error", "error": "http_error", "error_description": response.text}

    try:
        data = response.json()
    except Exception:
        return {"status": "error", "error": "invalid_response", "error_description": response.text}
    if "access_token" not in data:
        return {"status": "error", "error": data.get("error", "unknown_error"), "error_description": data.get("error_description")}
    return {"status": "success", "token": data}


async def request_device_authorization() -> Dict[str, Any]:
    return await asyncio.to_thread(request_device_authorization_sync)


async def poll_device_token(device_code: str, code_verifier: str) -> Dict[str, Any]:
    return await asyncio.to_thread(poll_device_token_sync, device_code, code_verifier)


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    return await asyncio.to_thread(refresh_access_token_sync, refresh_token)


def refresh_access_token_sync(refresh_token: str) -> Dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": QWEN_OAUTH_CLIENT_ID,
    }
    headers = dict(QWEN_OAUTH_HEADERS)
    with httpx.Client(timeout=15) as client:
        response = client.post(QWEN_OAUTH_TOKEN_ENDPOINT, data=_form_encode(payload), headers=headers)
    if response.status_code >= 400:
        raise RuntimeError(f"Token refresh failed: {response.status_code} {response.text}")
    try:
        data = response.json()
    except Exception:
        raise RuntimeError(f"Token refresh failed: invalid response {response.text}")
    if "access_token" not in data:
        raise RuntimeError(f"Token refresh failed: {data}")
    return data


def build_oauth_settings(token_data: Dict[str, Any]) -> Dict[str, Any]:
    expires_in = int(token_data.get("expires_in") or 0)
    expiry_date = _now_ms() + (expires_in * 1000)
    return {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type"),
        "resource_url": token_data.get("resource_url") or DEFAULT_QWEN_RESOURCE_URL,
        "expiry_date": expiry_date,
    }


def is_token_expired(oauth: Optional[Dict[str, Any]], skew_ms: int = 60000) -> bool:
    if not oauth:
        return True
    expiry_date = oauth.get("expiry_date")
    if not expiry_date:
        return False
    try:
        expiry_date = int(expiry_date)
    except Exception:
        return False
    return _now_ms() + skew_ms >= expiry_date
