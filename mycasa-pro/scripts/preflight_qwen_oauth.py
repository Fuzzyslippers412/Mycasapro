#!/usr/bin/env python3
"""
MyCasa Pro preflight test:
- Backend + system health
- Register/login user
- Settings + system live/monitor
- Qwen OAuth device flow
- Chat with manager + finance agent
- Tasks CRUD
- Finance portfolio/bills/spend summary
- Inbox stats
- Approvals request/list
- Agent context list + detail
- Janitor audit

Usage:
  python3 scripts/preflight_qwen_oauth.py
  python3 scripts/preflight_qwen_oauth.py --api-base http://127.0.0.1:6709
  python3 scripts/preflight_qwen_oauth.py --api-base "$MYCASA_API_BASE_URL"
  python3 scripts/preflight_qwen_oauth.py --allow-destructive
  python3 scripts/preflight_qwen_oauth.py --isolated
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import uuid
import webbrowser
import socket
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ApiError(Exception):
    def __init__(self, status: int, message: str, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _request_json(
    method: str,
    url: str,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
) -> Tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except HTTPError as e:
        body_raw = e.read().decode("utf-8", errors="ignore")
        try:
            body_json = json.loads(body_raw) if body_raw else None
        except Exception:
            body_json = body_raw
        raise ApiError(e.code, f"{method} {url} failed", body_json)
    except URLError as e:
        raise ApiError(0, f"{method} {url} failed: {e.reason}")


def _request_multipart(
    url: str,
    token: Optional[str],
    fields: Dict[str, str],
    file_field: Tuple[str, str, str, bytes],
    timeout: int = 15,
) -> Tuple[int, Any]:
    boundary = f"----MyCasaPreflight{uuid.uuid4().hex}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    field_name, filename, content_type, data = file_field
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(data)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, data=bytes(body), headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            body_raw = resp.read().decode("utf-8")
            return resp.status, json.loads(body_raw) if body_raw else {}
    except HTTPError as e:
        body_raw = e.read().decode("utf-8", errors="ignore")
        try:
            body_json = json.loads(body_raw) if body_raw else None
        except Exception:
            body_json = body_raw
        raise ApiError(e.code, f"{url} failed", body_json)
    except URLError as e:
        raise ApiError(0, f"{url} failed: {e.reason}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    print(msg, flush=True)


def _check(name: str, ok: bool, detail: str = "") -> Dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "detail": detail,
        "timestamp": _now_iso(),
    }


def _find_repo_root() -> str:
    return str(Path(__file__).resolve().parent.parent)


def _find_python_executable(repo_root: str) -> str:
    candidates = [
        Path(repo_root) / ".venv" / "bin" / "python",
        Path(repo_root) / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _find_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return int(port)


def _wait_for_backend(api_base: str, timeout: int = 45) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            _request_json("GET", f"{api_base}/health", timeout=5)
            return True
        except ApiError:
            time.sleep(1.5)
    return False


def _tiny_png_bytes() -> bytes:
    # 1x1 PNG
    raw = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    return base64.b64decode(raw)


def _start_isolated_backend() -> Dict[str, Any]:
    repo_root = _find_repo_root()
    python_exec = _find_python_executable(repo_root)
    port = _find_free_port()
    data_dir = tempfile.mkdtemp(prefix="mycasa-preflight-")
    api_base = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["MYCASA_BIND_HOST"] = "127.0.0.1"
    env["MYCASA_API_PORT"] = str(port)
    env["MYCASA_DATA_DIR"] = data_dir
    env["MYCASA_DATABASE_URL"] = f"sqlite:///{data_dir}/mycasa.db"
    env["DATABASE_URL"] = env["MYCASA_DATABASE_URL"]
    env.pop("NEXT_PUBLIC_API_URL", None)

    cmd = [
        python_exec,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    ready = _wait_for_backend(api_base, timeout=60)
    return {
        "process": proc,
        "api_base": api_base,
        "data_dir": data_dir,
        "ready": ready,
    }


def _register_or_login(api_base: str, username: str, email: str, password: str) -> str:
    register_url = f"{api_base}/api/auth/register"
    login_url = f"{api_base}/api/auth/login"
    payload = {"username": username, "email": email, "password": password}
    try:
        status, data = _request_json("POST", register_url, payload=payload, timeout=15)
        token = data.get("access_token") or data.get("token")
        if not token:
            raise ApiError(status, "Register returned no token", data)
        return token
    except ApiError as e:
        if e.status != 409:
            raise
        # fallback to login
        payload = {"username": username, "password": password}
        status, data = _request_json("POST", login_url, payload=payload, timeout=15)
        token = data.get("access_token") or data.get("token")
        if not token:
            raise ApiError(status, "Login returned no token", data)
        return token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--isolated", action="store_true")
    parser.add_argument("--username", default=os.getenv("MYCASA_TEST_USERNAME") or f"smoke_{uuid.uuid4().hex[:8]}")
    parser.add_argument("--email", default=os.getenv("MYCASA_TEST_EMAIL") or f"smoke_{uuid.uuid4().hex[:8]}@example.com")
    parser.add_argument("--password", default=os.getenv("MYCASA_TEST_PASSWORD") or "ChangeMe123!")
    parser.add_argument("--skip-oauth", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--allow-destructive", action="store_true")
    parser.add_argument("--report", default="/tmp/mycasa-preflight-report.json")
    args = parser.parse_args()

    api_base = args.api_base
    use_isolated = args.isolated or not api_base
    isolated_context = None
    results: list[Dict[str, Any]] = []
    failures = 0

    if use_isolated:
        _log("[preflight] Starting isolated backend instance...")
        isolated_context = _start_isolated_backend()
        api_base = isolated_context["api_base"]
        if not isolated_context["ready"]:
            results.append(_check("backend_status", False, "Isolated backend failed to start"))
            _write_report(args.report, results)
            try:
                proc = isolated_context.get("process")
                if proc:
                    proc.terminate()
            except Exception:
                pass
            return 1
        results.append(
            _check(
                "isolated_backend",
                True,
                f"{api_base} data_dir={isolated_context.get('data_dir')}",
            )
        )
    else:
        api_base = api_base.rstrip("/")

    _log(f"[preflight] API base: {api_base}")

    # 1) Backend health
    try:
        _, status_data = _request_json("GET", f"{api_base}/status", timeout=10)
        results.append(_check("backend_status", True, "OK"))
    except ApiError as e:
        results.append(_check("backend_status", False, f"{e}"))
        failures += 1
        _log("[preflight] Backend not reachable.")
        _write_report(args.report, results)
        if isolated_context:
            proc = isolated_context.get("process")
            if proc:
                proc.terminate()
        return 1

    # 2) System status
    try:
        _, sys_data = _request_json("GET", f"{api_base}/api/system/status", timeout=10)
        results.append(_check("system_status", True, "OK"))
    except ApiError as e:
        results.append(_check("system_status", False, str(e)))
        failures += 1

    # 2b) System monitor + live status
    try:
        _request_json("GET", f"{api_base}/api/system/monitor", timeout=10)
        results.append(_check("system_monitor", True, "OK"))
    except ApiError as e:
        results.append(_check("system_monitor", False, str(e)))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/system/live", timeout=10)
        results.append(_check("system_live", True, "OK"))
    except ApiError as e:
        results.append(_check("system_live", False, str(e)))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/system/health", timeout=10)
        results.append(_check("system_health", True, "OK"))
    except ApiError as e:
        results.append(_check("system_health", False, str(e)))
        failures += 1

    # 2c) System startup (idempotent)
    try:
        _request_json("POST", f"{api_base}/api/system/startup", timeout=20)
        results.append(_check("system_startup", True, "OK"))
    except ApiError as e:
        results.append(_check("system_startup", False, f"{e.body or e}"))
        failures += 1

    # 2c) Fleet + connectors health
    try:
        _request_json("GET", f"{api_base}/api/fleet/health", timeout=10)
        results.append(_check("fleet_health", True, "OK"))
    except ApiError as e:
        results.append(_check("fleet_health", False, str(e)))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/fleet/agents", timeout=10)
        results.append(_check("fleet_agents", True, "OK"))
    except ApiError as e:
        results.append(_check("fleet_agents", False, str(e)))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/connectors/health", timeout=10)
        results.append(_check("connectors_health", True, "OK"))
    except ApiError as e:
        results.append(_check("connectors_health", False, str(e)))
        failures += 1

    # 3) Register or login
    try:
        token = _register_or_login(api_base, args.username, args.email, args.password)
        results.append(_check("auth_register_login", True, f"user={args.username}"))
    except ApiError as e:
        results.append(_check("auth_register_login", False, f"{e.body or e}"))
        failures += 1
        _write_report(args.report, results)
        return 1

    # 4) Auth me + update profile
    try:
        _, me = _request_json("GET", f"{api_base}/api/auth/me", token=token)
        results.append(_check("auth_me", True, me.get("username", "")))
    except ApiError as e:
        results.append(_check("auth_me", False, f"{e.body or e}"))
        failures += 1

    try:
        display_name = f"Smoke Test {uuid.uuid4().hex[:4]}"
        _, me_updated = _request_json(
            "PATCH",
            f"{api_base}/api/auth/me",
            token=token,
            payload={"display_name": display_name},
        )
        results.append(_check("auth_update_profile", True, me_updated.get("display_name", "")))
    except ApiError as e:
        results.append(_check("auth_update_profile", False, f"{e.body or e}"))
        failures += 1

    # 4b) Avatar upload
    try:
        _, avatar = _request_multipart(
            f"{api_base}/api/auth/avatar",
            token=token,
            fields={},
            file_field=("file", "avatar.png", "image/png", _tiny_png_bytes()),
            timeout=15,
        )
        if not avatar.get("avatar_url"):
            raise ApiError(500, "Avatar upload returned no avatar_url", avatar)
        results.append(_check("auth_avatar_upload", True, "OK"))
    except ApiError as e:
        results.append(_check("auth_avatar_upload", False, f"{e.body or e}"))
        failures += 1

    # 4c) Settings + data counts
    try:
        _request_json("GET", f"{api_base}/api/settings/system", token=token)
        results.append(_check("settings_system", True, "OK"))
    except ApiError as e:
        results.append(_check("settings_system", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/settings/notifications", token=token)
        results.append(_check("settings_notifications", True, "OK"))
    except ApiError as e:
        results.append(_check("settings_notifications", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/settings/agent/security", token=token)
        results.append(_check("settings_security_agent", True, "OK"))
    except ApiError as e:
        results.append(_check("settings_security_agent", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/settings/agents/enabled", token=token)
        results.append(_check("settings_agents_enabled", True, "OK"))
    except ApiError as e:
        results.append(_check("settings_agents_enabled", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/data/counts", token=token)
        results.append(_check("data_counts", True, "OK"))
    except ApiError as e:
        results.append(_check("data_counts", False, f"{e.body or e}"))
        failures += 1

    # 4d) Janitor preflight info
    try:
        _request_json("GET", f"{api_base}/api/janitor/preflight-info", timeout=10)
        results.append(_check("janitor_preflight_info", True, "OK"))
    except ApiError as e:
        results.append(_check("janitor_preflight_info", False, f"{e.body or e}"))
        failures += 1

    # 4e) Backup export
    try:
        _, backup = _request_json("POST", f"{api_base}/backup/export", token=token, timeout=30)
        if backup.get("success") is False:
            raise ApiError(500, "Backup export failed", backup)
        results.append(_check("backup_export", True, backup.get("timestamp", "OK")))
    except ApiError as e:
        results.append(_check("backup_export", False, f"{e.body or e}"))
        failures += 1

    # 4f) Data management actions (destructive)
    if args.allow_destructive:
        try:
            _, res = _request_json("POST", f"{api_base}/api/data/inbox/mark-all-read", token=token, timeout=15)
            if res.get("success") is False:
                raise ApiError(500, "Mark all read failed", res)
            results.append(_check("data_mark_all_read", True, f"cleared={res.get('cleared_count', 0)}"))
        except ApiError as e:
            results.append(_check("data_mark_all_read", False, f"{e.body or e}"))
            failures += 1

        try:
            _, res = _request_json("POST", f"{api_base}/api/data/bills/mark-all-paid", token=token, timeout=15)
            if res.get("success") is False:
                raise ApiError(500, "Mark all bills paid failed", res)
            results.append(_check("data_mark_all_bills_paid", True, f"cleared={res.get('cleared_count', 0)}"))
        except ApiError as e:
            results.append(_check("data_mark_all_bills_paid", False, f"{e.body or e}"))
            failures += 1

        try:
            _, res = _request_json("POST", f"{api_base}/api/data/activity/clear", token=token, timeout=15)
            if res.get("success") is False:
                raise ApiError(500, "Clear activity failed", res)
            results.append(_check("data_clear_activity", True, f"cleared={res.get('cleared_count', 0)}"))
        except ApiError as e:
            results.append(_check("data_clear_activity", False, f"{e.body or e}"))
            failures += 1
    else:
        results.append(_check("data_mark_all_read", True, "skipped (add --allow-destructive)"))
        results.append(_check("data_mark_all_bills_paid", True, "skipped (add --allow-destructive)"))
        results.append(_check("data_clear_activity", True, "skipped (add --allow-destructive)"))

    # 5) Qwen OAuth device flow
    if not args.skip_oauth:
        try:
            _, oauth_start = _request_json("POST", f"{api_base}/api/llm/qwen/oauth/start", token=token, timeout=15)
            session_id = oauth_start.get("session_id")
            if not session_id:
                raise ApiError(500, "OAuth start returned no session_id", oauth_start)
            verification_url = oauth_start.get("verification_uri_complete") or oauth_start.get("verification_uri")
            user_code = oauth_start.get("user_code")
            if not verification_url or not user_code:
                raise ApiError(500, "OAuth start returned no verification URL or user code", oauth_start)
            _log(f"[preflight] Qwen OAuth user code: {user_code}")
            _log(f"[preflight] Qwen OAuth URL: {verification_url}")
            if verification_url and not args.no_open:
                webbrowser.open(verification_url)

            expires_at = oauth_start.get("expires_at")
            interval = int(oauth_start.get("interval_seconds") or 5)
            deadline = time.time() + 600
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at)
                    deadline = min(deadline, exp.timestamp())
                except Exception:
                    pass

            status = "pending"
            while time.time() < deadline:
                time.sleep(max(2, interval))
                _, poll = _request_json(
                    "POST",
                    f"{api_base}/api/llm/qwen/oauth/poll",
                    token=token,
                    payload={"session_id": session_id},
                    timeout=15,
                )
                status = poll.get("status")
                if status == "pending":
                    interval = int(poll.get("interval_seconds") or interval)
                    continue
                if status == "success":
                    results.append(_check("qwen_oauth", True, "connected"))
                    break
                if status in {"error", "expired"}:
                    raise ApiError(400, f"OAuth {status}", poll)

            if status != "success":
                raise ApiError(408, "OAuth timed out", {"status": status})

            # verify system settings reflect oauth
            _, settings = _request_json("GET", f"{api_base}/api/settings/system", token=token)
            if settings.get("llm_oauth_connected"):
                results.append(_check("qwen_oauth_settings", True, "stored"))
            else:
                results.append(_check("qwen_oauth_settings", False, "not stored"))
                failures += 1
        except ApiError as e:
            results.append(_check("qwen_oauth", False, f"{e.body or e}"))
            failures += 1
    else:
        results.append(_check("qwen_oauth", True, "skipped"))

    # 6) Chat with manager
    try:
        _, chat = _request_json(
            "POST",
            f"{api_base}/manager/chat",
            token=token,
            payload={"message": "Hello Galidima, confirm chat is online."},
            timeout=60,
        )
        if chat.get("error"):
            raise ApiError(500, "Manager chat error", chat)
        if not (chat.get("response") or "").strip():
            raise ApiError(500, "Manager chat empty response", chat)
        results.append(_check("manager_chat", True, "response ok"))
    except ApiError as e:
        results.append(_check("manager_chat", False, f"{e.body or e}"))
        failures += 1

    # 6b) Manager task creation should persist to maintenance
    task_title = f"Preflight cleanup {uuid.uuid4().hex[:6]}"
    created_task_id = None
    try:
        _, task_chat = _request_json(
            "POST",
            f"{api_base}/manager/chat",
            token=token,
            payload={"message": f"Add a task to {task_title} by Friday."},
            timeout=60,
        )
        created_task = task_chat.get("task_created") or {}
        created_task_id = created_task.get("task_id")
        # Verify task appears in list
        _, task_list = _request_json("GET", f"{api_base}/api/tasks?limit=50", token=token, timeout=15)
        tasks = task_list.get("tasks") or []
        found = None
        for t in tasks:
            if t.get("title") == task_title:
                found = t
                created_task_id = created_task_id or t.get("id")
                break
        if not found:
            raise ApiError(500, "Task not found after manager chat", task_chat)
        results.append(_check("manager_task_create", True, f"id={created_task_id}"))
    except ApiError as e:
        results.append(_check("manager_task_create", False, f"{e.body or e}"))
        failures += 1

    if created_task_id:
        try:
            _request_json("DELETE", f"{api_base}/api/tasks/{created_task_id}", token=token, timeout=10)
            results.append(_check("manager_task_cleanup", True, "OK"))
        except ApiError as e:
            results.append(_check("manager_task_cleanup", False, f"{e.body or e}"))
            failures += 1

    # 7) Chat with finance agent
    try:
        _, chat = _request_json(
            "POST",
            f"{api_base}/api/agents/finance/chat",
            token=token,
            payload={"message": "Quick status."},
            timeout=60,
        )
        if chat.get("error"):
            raise ApiError(500, "Finance chat error", chat)
        if not (chat.get("response") or "").strip():
            raise ApiError(500, "Finance chat empty response", chat)
        results.append(_check("finance_chat", True, "response ok"))
    except ApiError as e:
        results.append(_check("finance_chat", False, f"{e.body or e}"))
        failures += 1

    # 8) Tasks CRUD
    task_id = None
    try:
        _, task = _request_json(
            "POST",
            f"{api_base}/api/tasks",
            token=token,
            payload={
                "title": "Preflight task",
                "description": "Created by preflight test",
                "category": "maintenance",
                "priority": "medium",
            },
            timeout=20,
        )
        task_id = task.get("id") or task.get("task_id")
        if not task_id:
            raise ApiError(500, "Task create missing id", task)
        results.append(_check("task_create", True, f"id={task_id}"))
    except ApiError as e:
        results.append(_check("task_create", False, f"{e.body or e}"))
        failures += 1

    if task_id:
        try:
            _request_json("GET", f"{api_base}/api/tasks/{task_id}", token=token, timeout=10)
            results.append(_check("task_get", True, "OK"))
        except ApiError as e:
            results.append(_check("task_get", False, f"{e.body or e}"))
            failures += 1

        try:
            _request_json(
                "PATCH",
                f"{api_base}/api/tasks/{task_id}",
                token=token,
                payload={"priority": "high"},
                timeout=10,
            )
            results.append(_check("task_update", True, "OK"))
        except ApiError as e:
            results.append(_check("task_update", False, f"{e.body or e}"))
            failures += 1

        try:
            _request_json(
                "PATCH",
                f"{api_base}/api/tasks/{task_id}/complete",
                token=token,
                payload={"completion_notes": "preflight complete"},
                timeout=10,
            )
            results.append(_check("task_complete", True, "OK"))
        except ApiError as e:
            results.append(_check("task_complete", False, f"{e.body or e}"))
            failures += 1

        if args.allow_destructive:
            try:
                _, res = _request_json(
                    "POST",
                    f"{api_base}/api/data/tasks/mark-all-complete",
                    token=token,
                    timeout=15,
                )
                if res.get("success") is False:
                    raise ApiError(500, "Mark all tasks complete failed", res)
                results.append(_check("data_mark_all_tasks_complete", True, f"cleared={res.get('cleared_count', 0)}"))
            except ApiError as e:
                results.append(_check("data_mark_all_tasks_complete", False, f"{e.body or e}"))
                failures += 1
        else:
            results.append(_check("data_mark_all_tasks_complete", True, "skipped (add --allow-destructive)"))

        try:
            _request_json("DELETE", f"{api_base}/api/tasks/{task_id}", token=token, timeout=10)
            results.append(_check("task_delete", True, "OK"))
        except ApiError as e:
            results.append(_check("task_delete", False, f"{e.body or e}"))
            failures += 1

    # 9) Finance endpoints
    try:
        _request_json("GET", f"{api_base}/api/finance/portfolio", token=token, timeout=15)
        results.append(_check("finance_portfolio", True, "OK"))
    except ApiError as e:
        results.append(_check("finance_portfolio", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/finance/bills/upcoming", token=token, timeout=15)
        results.append(_check("finance_bills_upcoming", True, "OK"))
    except ApiError as e:
        results.append(_check("finance_bills_upcoming", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/finance/spend/summary?days=7", token=token, timeout=15)
        results.append(_check("finance_spend_summary", True, "OK"))
    except ApiError as e:
        results.append(_check("finance_spend_summary", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/finance/spend/report?days=30", token=token, timeout=15)
        results.append(_check("finance_spend_report", True, "OK"))
    except ApiError as e:
        results.append(_check("finance_spend_report", False, f"{e.body or e}"))
        failures += 1

    # 10) Inbox stats
    try:
        _request_json("GET", f"{api_base}/api/inbox/messages?limit=5", token=token, timeout=15)
        results.append(_check("inbox_messages", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_messages", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/inbox/unread-count", token=token, timeout=15)
        results.append(_check("inbox_unread", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_unread", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/inbox/stats", token=token, timeout=15)
        results.append(_check("inbox_stats", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_stats", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/inbox/search?q=test", token=token, timeout=15)
        results.append(_check("inbox_search", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_search", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/inbox/sync-status", token=token, timeout=15)
        results.append(_check("inbox_sync_status", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_sync_status", False, f"{e.body or e}"))
        failures += 1

    # 10b) Inbox launch/stop (no auth required)
    try:
        _request_json("POST", f"{api_base}/api/inbox/launch", timeout=20)
        results.append(_check("inbox_launch", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_launch", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("POST", f"{api_base}/api/inbox/stop", timeout=10)
        results.append(_check("inbox_stop", True, "OK"))
    except ApiError as e:
        results.append(_check("inbox_stop", False, f"{e.body or e}"))
        failures += 1

    # 11) Approvals
    try:
        _request_json(
            "POST",
            f"{api_base}/api/approvals/request",
            payload={"action": "preflight_check", "payload": {"timestamp": _now_iso()}},
            timeout=10,
        )
        results.append(_check("approvals_request", True, "OK"))
    except ApiError as e:
        results.append(_check("approvals_request", False, f"{e.body or e}"))
        failures += 1

    try:
        _request_json("GET", f"{api_base}/api/approvals", timeout=10)
        results.append(_check("approvals_list", True, "OK"))
    except ApiError as e:
        results.append(_check("approvals_list", False, f"{e.body or e}"))
        failures += 1

    # 12) Agent context list + detail
    try:
        _, agents = _request_json("GET", f"{api_base}/api/agents", token=token, timeout=15)
        count = len(agents.get("agents") or [])
        results.append(_check("agent_context_list", True, f"{count} agents"))
        agent_id = (agents.get("agents") or [{}])[0].get("id") if count else None
        if agent_id:
            _request_json("GET", f"{api_base}/api/agents/{agent_id}/context", token=token, timeout=15)
            results.append(_check("agent_context_detail", True, agent_id))
    except ApiError as e:
        results.append(_check("agent_context_list", False, f"{e.body or e}"))
        failures += 1

    # 13) Janitor audit
    try:
        _, audit = _request_json("POST", f"{api_base}/api/janitor/run-audit", timeout=60)
        if not audit.get("success"):
            raise ApiError(500, "Janitor audit failed", audit)
        results.append(_check("janitor_audit", True, "ok"))
    except ApiError as e:
        results.append(_check("janitor_audit", False, f"{e.body or e}"))
        failures += 1

    # 14) Auth logout + re-login
    try:
        _request_json("POST", f"{api_base}/api/auth/logout", token=token, timeout=10)
        results.append(_check("auth_logout", True, "OK"))
    except ApiError as e:
        results.append(_check("auth_logout", False, f"{e.body or e}"))
        failures += 1

    try:
        token = _register_or_login(api_base, args.username, args.email, args.password)
        _request_json("GET", f"{api_base}/api/auth/me", token=token, timeout=10)
        results.append(_check("auth_relogin", True, "OK"))
    except ApiError as e:
        results.append(_check("auth_relogin", False, f"{e.body or e}"))
        failures += 1

    _write_report(args.report, results)

    if failures > 0:
        try:
            _request_json(
                "POST",
                f"{api_base}/api/janitor/incidents",
                payload={
                    "severity": "high",
                    "category": "preflight",
                    "title": "Preflight failures detected",
                    "details": f"{failures} checks failed. Report: {args.report}",
                    "source": "preflight",
                },
                timeout=10,
            )
        except ApiError:
            pass

    _log("\n[preflight] Summary")
    for item in results:
        status = "OK" if item["ok"] else "FAIL"
        _log(f"  - {status} {item['name']}: {item['detail']}")

    if isolated_context:
        proc = isolated_context.get("process")
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()

    return 0 if failures == 0 else 1


def _write_report(path: str, results: list[Dict[str, Any]]) -> None:
    payload = {
        "timestamp": _now_iso(),
        "results": results,
    }
    try:
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        _log(f"[preflight] Report written to {path}")
    except Exception as e:
        _log(f"[preflight] Failed to write report: {e}")


if __name__ == "__main__":
    sys.exit(main())
