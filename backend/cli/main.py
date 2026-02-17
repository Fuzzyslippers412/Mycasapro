#!/usr/bin/env python3
"""
MyCasa Pro CLI
Command-line interface for MyCasa Pro backend
"""
import click
import requests
import json
import subprocess
import sys
import os
import time
import webbrowser
import shutil
import socket
import getpass
from pathlib import Path
from datetime import date
from typing import Optional, Tuple, List

API_BASE = (
    os.environ.get("MYCASA_API_URL")
    or os.environ.get("MYCASA_API_BASE_URL")
    or "http://127.0.0.1:6709"
)

def _read_env_value(repo_dir: Path, key: str) -> Optional[str]:
    env_path = repo_dir / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None

def _get_frontend_url() -> str:
    env_url = os.environ.get("MYCASA_FRONTEND_URL")
    if env_url:
        return env_url
    repo_dir = _repo_root()
    env_file_url = _read_env_value(repo_dir, "MYCASA_FRONTEND_URL")
    if env_file_url:
        return env_file_url
    return "http://localhost:3000"


def api_call(method: str, endpoint: str, data: dict = None) -> dict:
    """Make API call to backend"""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=data)
        elif method == "POST":
            resp = requests.post(url, json=data)
        elif method == "PATCH":
            resp = requests.patch(url, json=data)
        elif method == "PUT":
            resp = requests.put(url, json=data)
        else:
            return {"error": f"Unknown method: {method}"}
        
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Backend not running. Start with: mycasa backend start"}
    except Exception as e:
        return {"error": str(e)}


def print_json(data: dict):
    """Pretty print JSON"""
    click.echo(json.dumps(data, indent=2, default=str))

def _step(title: str) -> None:
    click.echo(f"\n==> {title}")

def _ok(message: str) -> None:
    click.echo(f"✓ {message}")

def _warn(message: str) -> None:
    click.echo(f"! {message}")

def _err(message: str) -> None:
    click.echo(f"✗ {message}")

def _run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, stderr=subprocess.STDOUT)
        return 0, out.decode().strip()
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output.decode().strip()

def _port_available(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) != 0

def _detect_lan_ip() -> Optional[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None

def _choose_port(default_port: int) -> int:
    port = default_port
    if _port_available(port):
        return port
    _warn(f"Port {port} is in use.")
    port = click.prompt("Choose a different port", default=default_port + 1, type=int)
    return port

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _ensure_env_file(repo_dir: Path) -> None:
    env_path = repo_dir / ".env"
    example_path = repo_dir / ".env.example"
    if env_path.exists():
        return
    if example_path.exists():
        shutil.copy2(example_path, env_path)
        click.echo("✓ Created .env from .env.example")

def _set_env_var(env_path: Path, key: str, value: str) -> None:
    if not env_path.exists():
        env_path.write_text("")
    lines = env_path.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n")

def _write_frontend_env(repo_dir: Path, api_base: str) -> None:
    frontend_env = repo_dir / "frontend" / ".env.local"
    frontend_env.write_text(f"NEXT_PUBLIC_API_URL={api_base}\n")
    click.echo(f"✓ Wrote {frontend_env}")

def _wait_for_health(api_base: str, timeout_seconds: int = 10) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            resp = requests.get(f"{api_base}/health", timeout=2)
            if resp.ok:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def _configure_personal_mode(repo_dir: Path) -> None:
    _step("Personal mode")
    env_path = repo_dir / ".env"
    enable_personal = click.confirm("Enable Personal Mode (no account required)?", default=True)
    _set_env_var(env_path, "MYCASA_PERSONAL_MODE", "1" if enable_personal else "0")
    if not enable_personal:
        _ok("Personal mode disabled. You can enable it later in .env.")
        return

    display_name = click.prompt("What should I call you?", default=getpass.getuser())
    household_name = click.prompt("Household name", default="My Home")
    timezone = click.prompt("Timezone", default="America/Los_Angeles")

    try:
        from core.settings_typed import get_settings_store
        settings = get_settings_store().get()
        settings.system.household_name = household_name
        settings.system.timezone = timezone
        get_settings_store().save(settings)
    except Exception:
        _warn("Could not update system settings file (settings.json). You can update later in Settings.")

    try:
        from database import get_db
        from auth.personal_mode import ensure_personal_user
        with get_db() as db:
            ensure_personal_user(db, display_name=display_name)
        _ok("Personal profile saved.")
    except Exception:
        _warn("Could not update personal user profile. You can update later in Settings.")

def _safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    if str(path) in {"/", str(Path.home())}:
        _warn(f"Refusing to delete unsafe path: {path}")
        return
    shutil.rmtree(path, ignore_errors=True)

def _resolve_data_dir(repo_dir: Path) -> Path:
    env_data_dir = os.environ.get("MYCASA_DATA_DIR") or _read_env_value(repo_dir, "MYCASA_DATA_DIR")
    if env_data_dir:
        return Path(os.path.expanduser(env_data_dir)).resolve()
    return (repo_dir / "data").resolve()

def _resolve_db_path(repo_dir: Path) -> Optional[Path]:
    db_url = os.environ.get("MYCASA_DATABASE_URL") or _read_env_value(repo_dir, "MYCASA_DATABASE_URL")
    if not db_url:
        return _resolve_data_dir(repo_dir) / "mycasa.db"
    if db_url.startswith("sqlite:///"):
        return Path(db_url.replace("sqlite:///", "/")).resolve()
    if db_url.startswith("sqlite:////"):
        return Path(db_url.replace("sqlite:////", "/")).resolve()
    return None

def _qwen_login_flow(api_base: str, username: Optional[str], password: Optional[str], token: Optional[str], no_browser: bool):
    auth_token = token
    if not auth_token:
        if not username:
            username = click.prompt("Username")
        if not password:
            password = click.prompt("Password", hide_input=True)
        try:
            resp = requests.post(f"{api_base}/api/auth/login", json={
                "username": username,
                "password": password,
            })
            if resp.status_code >= 400:
                click.echo(f"✗ Login failed: {resp.text}")
                return False
            data = resp.json()
            auth_token = data.get("token")
            if not auth_token:
                click.echo("✗ Login failed: token not returned")
                return False
        except requests.exceptions.ConnectionError:
            click.echo(f"✗ Backend not running at {api_base}. Start with: ./start_all.sh")
            return False

    headers = {"Authorization": f"Bearer {auth_token}"}
    try:
        start = requests.post(f"{api_base}/api/llm/qwen/oauth/start", headers=headers)
        if start.status_code >= 400:
            click.echo(f"✗ OAuth start failed: {start.text}")
            return False
        payload = start.json()
    except requests.exceptions.ConnectionError:
        click.echo(f"✗ Backend not running at {api_base}. Start with: ./start_all.sh")
        return False

    verification_url = payload.get("verification_uri_complete") or payload.get("verification_uri")
    user_code = payload.get("user_code")
    session_id = payload.get("session_id")
    interval = int(payload.get("interval_seconds") or 5)
    expires_at = payload.get("expires_at")

    click.echo("\nQwen OAuth device flow")
    click.echo(f"  Verification URL: {verification_url}")
    click.echo(f"  User code: {user_code}")
    if expires_at:
        click.echo(f"  Expires at: {expires_at}")

    if verification_url and not no_browser:
        try:
            webbrowser.open(verification_url, new=2)
        except Exception:
            pass

    click.echo("\nWaiting for authorization... (press Ctrl+C to cancel)")
    while True:
        try:
            poll = requests.post(
                f"{api_base}/api/llm/qwen/oauth/poll",
                headers=headers,
                json={"session_id": session_id},
            )
        except requests.exceptions.ConnectionError:
            click.echo(f"\n✗ Backend not reachable at {api_base}")
            return False
        if poll.status_code >= 400:
            click.echo(f"\n✗ Poll failed: {poll.text}")
            return False
        result = poll.json()
        status = result.get("status")
        if status == "pending":
            time.sleep(interval)
            continue
        if status == "success":
            click.echo("\n✓ Qwen OAuth connected.")
            if result.get("resource_url"):
                click.echo(f"  Resource URL: {result.get('resource_url')}")
            if result.get("expires_at"):
                click.echo(f"  Expires at: {result.get('expires_at')}")
            return True
        if status == "expired":
            click.echo("\n✗ Device code expired. Run again.")
            return False
        click.echo(f"\n✗ OAuth failed: {result.get('message')}")
        return False

def _qwen_login_direct(no_browser: bool) -> bool:
    from core.qwen_oauth import (
        request_device_authorization_sync,
        poll_device_token_sync,
        build_oauth_settings,
    )
    from core.settings_typed import get_settings_store
    from core.llm_client import reset_llm_client

    try:
        payload = request_device_authorization_sync()
    except Exception as exc:
        _err(f"Qwen device authorization failed: {exc}")
        return False
    verification_url = payload.get("verification_uri_complete") or payload.get("verification_uri")
    user_code = payload.get("user_code")
    interval = int(payload.get("interval") or 5)
    expires_in = int(payload.get("expires_in") or 600)
    deadline = time.time() + expires_in

    click.echo("\nQwen OAuth device flow")
    click.echo(f"  Verification URL: {verification_url}")
    click.echo(f"  User code: {user_code}")
    click.echo(f"  Expires in: {expires_in}s")

    if verification_url and not no_browser:
        try:
            webbrowser.open(verification_url, new=2)
        except Exception:
            pass

    click.echo("\nWaiting for authorization... (press Ctrl+C to cancel)")
    while time.time() < deadline:
        result = poll_device_token_sync(payload["device_code"], payload["code_verifier"])
        status = result.get("status")
        if status == "pending":
            time.sleep(interval)
            continue
        if status == "success":
            token_data = result.get("token") or {}
            oauth_settings = build_oauth_settings(token_data)
            store = get_settings_store()
            settings = store.get()
            settings.system.llm_auth_type = "qwen-oauth"
            settings.system.llm_provider = "openai-compatible"
            settings.system.llm_base_url = oauth_settings.get("resource_url")
            settings.system.llm_oauth = oauth_settings
            store.save(settings)
            reset_llm_client()
            click.echo("\n✓ Qwen OAuth connected.")
            return True
        if status == "error":
            click.echo(f"\n✗ OAuth failed: {result.get('error_description') or result.get('error')}")
            return False
        time.sleep(interval)

    click.echo("\n✗ Device code expired. Run again.")
    return False
@click.group()
def cli():
    """MyCasa Pro - Home Operating System CLI"""


# ============ BACKEND ============

@cli.group()
def backend():
    """Backend service management"""


@backend.command("start")
@click.option("--port", default=6709, help="API port")
def backend_start(port: int):
    """Start the backend API server"""
    click.echo(f"Starting MyCasa Pro backend on port {port}...")
    
    backend_dir = Path(__file__).parent.parent
    
    # Start uvicorn
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(port), "--reload"],
        cwd=str(backend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for startup
    time.sleep(2)
    
    # Check health
    result = api_call("GET", "/health")
    if "error" not in result:
        click.echo(f"✓ Backend running at http://localhost:{port}")
        click.echo(f"  Docs: http://localhost:{port}/docs")
    else:
        click.echo(f"✗ Failed to start: {result.get('error')}")


@backend.command("stop")
def backend_stop():
    """Stop the backend API server"""
    click.echo("Stopping MyCasa Pro backend...")
    subprocess.run(["pkill", "-f", "uvicorn.*api.main"], capture_output=True)
    click.echo("✓ Backend stopped")


@backend.command("status")
def backend_status():
    """Check backend status"""
    result = api_call("GET", "/health")
    if "error" in result:
        click.echo(f"✗ Backend offline: {result['error']}")
    else:
        click.echo(f"✓ Backend healthy")
        click.echo(f"  Uptime: {result.get('uptime_seconds', 0):.0f}s")
        click.echo(f"  DB: {result.get('db_status', 'unknown')}")
        click.echo(f"  Active tasks: {result.get('active_tasks', 0)}")
        connectors = result.get("connectors", {})
        click.echo(f"  Gmail: {connectors.get('gmail', 'unknown')}")
        click.echo(f"  WhatsApp: {connectors.get('whatsapp', 'unknown')}")


# ============ UI ============

@cli.group()
def ui():
    """UI management"""


@ui.command("start")
def ui_start():
    """Start the frontend UI"""
    click.echo("Starting MyCasa Pro UI...")
    
    frontend_dir = Path(__file__).parent.parent.parent / "frontend"
    
    if not (frontend_dir / "node_modules").exists():
        click.echo("Installing dependencies...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), capture_output=True)
    
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(3)
    click.echo("✓ UI running at http://localhost:3000")


@ui.command("stop")
def ui_stop():
    """Stop the frontend UI"""
    subprocess.run(["pkill", "-f", "next dev"], capture_output=True)
    click.echo("✓ UI stopped")


@cli.command("open")
def open_ui():
    """Open the MyCasa Pro UI in your browser"""
    url = _get_frontend_url()
    click.echo(f"Opening {url}...")
    try:
        webbrowser.open(url, new=2)
        click.echo("✓ Opened browser")
    except Exception as exc:
        click.echo(f"✗ Failed to open browser: {exc}")


# ============ SYSTEM LIFECYCLE ============

@cli.group()
def system():
    """System lifecycle controls"""


@system.command("start")
def system_start():
    """Start the system (agents + runtime)"""
    result = api_call("POST", "/system/startup")
    if result.get("success") or result.get("status") == "success":
        click.echo("✓ System started")
        return
    click.echo(f"✗ Failed to start: {result}")


@system.command("stop")
def system_stop():
    """Stop the system (agents + runtime)"""
    result = api_call("POST", "/system/shutdown")
    if result.get("success") or result.get("status") == "success":
        click.echo("✓ System stopped")
        return
    click.echo(f"✗ Failed to stop: {result}")


# ============ INTAKE ============

@cli.command("intake")
@click.option("--income-name", default="J.P. Morgan Brokerage", help="Primary income source name")
@click.option("--income-type", default="brokerage", help="Account type")
@click.option("--institution", default="J.P. Morgan", help="Institution name")
@click.option("--monthly-limit", default=10000.0, help="Monthly spend limit")
@click.option("--daily-limit", default=150.0, help="Daily spend limit")
@click.option("--system-limit", default=1000.0, help="System cost limit")
def run_intake(income_name, income_type, institution, monthly_limit, daily_limit, system_limit):
    """Complete system intake/setup"""
    click.echo("Running system intake...")
    
    data = {
        "primary_income_source": {
            "name": income_name,
            "account_type": income_type,
            "institution": institution,
            "is_primary": True
        },
        "monthly_spend_limit": monthly_limit,
        "daily_spend_limit": daily_limit,
        "system_cost_limit": system_limit,
        "enable_gmail": True,
        "enable_whatsapp": True,
        "notification_channels": ["whatsapp"]
    }
    
    result = api_call("POST", "/intake", data)
    
    if result.get("status") == "success":
        click.echo("✓ Intake completed successfully")
        if result.get("next_steps"):
            click.echo("Next steps:")
            for step in result["next_steps"]:
                click.echo(f"  - {step}")
    else:
        click.echo(f"✗ Intake failed: {result}")


# ============ LLM / QWEN OAUTH ============

@cli.group()
def llm():
    """LLM authentication and setup"""


@llm.command("qwen-login")
@click.option("--api-base", default=API_BASE, help="API base URL")
@click.option("--username", envvar="MYCASA_USERNAME", help="MyCasa username")
@click.option("--password", envvar="MYCASA_PASSWORD", help="MyCasa password", hide_input=True)
@click.option("--token", envvar="MYCASA_TOKEN", help="Existing auth token")
@click.option("--no-browser", is_flag=True, help="Do not open the verification URL in a browser")
@click.option("--api/--direct", "use_api", default=False, help="Use backend API (requires MyCasa login) instead of direct device flow")
def qwen_login(api_base: str, username: Optional[str], password: Optional[str], token: Optional[str], no_browser: bool, use_api: bool):
    """Authenticate Qwen via device OAuth and store tokens."""
    if use_api:
        _qwen_login_flow(api_base, username, password, token, no_browser)
    else:
        _qwen_login_direct(no_browser)


# ============ SETUP WIZARD ============

@cli.command("setup")
@click.option("--api-port", default=6709, help="API port to use")
@click.option("--start-frontend/--no-start-frontend", default=True, help="Start frontend after setup")
@click.option("--start-backend/--no-start-backend", default=True, help="Start backend after setup")
def setup(api_port: int, start_frontend: bool, start_backend: bool):
    """Interactive setup wizard (env, deps, backend, frontend, Qwen OAuth)."""
    repo_dir = _repo_root()
    click.echo("MyCasa Pro setup wizard (step-by-step)\n")

    # 0) System checks
    _step("System checks")
    py_ok = sys.version_info >= (3, 11)
    if py_ok:
        _ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        _err("Python 3.11+ required")
        return
    node_code, node_ver = _run_cmd(["node", "-v"])
    npm_code, npm_ver = _run_cmd(["npm", "-v"])
    if node_code == 0:
        _ok(f"Node {node_ver}")
    else:
        _warn("Node not found (required for frontend)")
    if npm_code == 0:
        _ok(f"npm {npm_ver}")
    else:
        _warn("npm not found (required for frontend)")

    # 1) Ports
    _step("Ports")
    api_port = _choose_port(api_port)
    ui_port = 3000 if _port_available(3000) else _choose_port(3000)
    expose_lan = click.confirm("Expose the UI/API to other devices on your LAN?", default=False)
    bind_host = "0.0.0.0" if expose_lan else "127.0.0.1"
    public_host = "127.0.0.1"
    if expose_lan:
        public_host = _detect_lan_ip() or click.prompt("Enter your LAN IP", default="127.0.0.1")
    api_base = f"http://{public_host}:{api_port}"
    _ok(f"API port {api_port}")
    _ok(f"UI port {ui_port}")
    _ok(f"Bind host {bind_host}")
    _ok(f"Public host {public_host}")
    os.environ["MYCASA_API_URL"] = api_base
    os.environ["MYCASA_API_BASE_URL"] = api_base

    # 2) Environment
    _step("Environment")
    _ensure_env_file(repo_dir)
    env_path = repo_dir / ".env"
    _set_env_var(env_path, "MYCASA_API_BASE_URL", api_base)
    _set_env_var(env_path, "MYCASA_BACKEND_PORT", str(api_port))
    _set_env_var(env_path, "MYCASA_BIND_HOST", bind_host)
    _set_env_var(env_path, "MYCASA_PUBLIC_HOST", public_host)
    _set_env_var(env_path, "MYCASA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    _ok(f"Configured {env_path}")

    # 3) Python deps + DB
    _step("Python dependencies")
    if click.confirm("Install Python dependencies (requirements.txt)?", default=True):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=str(repo_dir))
    _step("Database")
    if click.confirm("Initialize database and defaults?", default=True):
        subprocess.run([sys.executable, "install.py", "install"], cwd=str(repo_dir))
        _ok("Database initialized")

    # 3b) Personal mode
    _configure_personal_mode(repo_dir)

    # 4) Backend
    _step("Backend")
    if start_backend:
        click.echo("Starting backend...")
        log_file = Path("/tmp/mycasa-api.log")
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", bind_host, "--port", str(api_port)],
            cwd=str(repo_dir),
            stdout=open(log_file, "a"),
            stderr=open(log_file, "a"),
        )
        if _wait_for_health(api_base, timeout_seconds=12):
            _ok(f"Backend running at {api_base}")
        else:
            _warn("Backend did not respond yet. Check /tmp/mycasa-api.log")
            try:
                tail = log_file.read_text().splitlines()[-20:]
                if tail:
                    click.echo("\nLast 20 lines of /tmp/mycasa-api.log:")
                    click.echo("\n".join(tail))
            except Exception:
                pass

    # 5) Frontend
    _step("Frontend")
    _write_frontend_env(repo_dir, api_base)
    if click.confirm("Install frontend dependencies?", default=True):
        subprocess.run(["npm", "install"], cwd=str(repo_dir / "frontend"))
    if start_frontend:
        click.echo("Starting frontend...")
        subprocess.Popen(
            ["npm", "run", "dev", "--", "--hostname", bind_host, "--port", str(ui_port)],
            cwd=str(repo_dir / "frontend"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _ok(f"Frontend starting at http://{public_host}:{ui_port}")

    # 6) Qwen OAuth
    _step("Qwen OAuth")
    if click.confirm("Connect Qwen OAuth now?", default=True):
        _qwen_login_direct(False)

    click.echo("\nSetup complete.")


@cli.command("reset")
@click.option("--yes", is_flag=True, help="Skip confirmation prompts")
@click.option("--keep-env", is_flag=True, help="Keep .env and frontend/.env.local")
@click.option("--keep-data", is_flag=True, help="Keep data/backups/logs (only clears caches)")
def reset(yes: bool, keep_env: bool, keep_data: bool):
    """Factory reset local MyCasa Pro (clear config, data, caches)."""
    repo_dir = _repo_root()
    click.echo("This will stop running services and wipe local MyCasa data/config.")
    if not yes:
        if not click.confirm("Continue?", default=False):
            click.echo("Aborted.")
            return
        confirm = click.prompt('Type "RESET" to confirm', default="", show_default=False)
        if confirm.strip().upper() != "RESET":
            click.echo("Aborted.")
            return

    _step("Stopping services")
    subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
    subprocess.run(["pkill", "-f", "next dev"], capture_output=True)
    subprocess.run(["pkill", "-f", "wacli sync"], capture_output=True)
    _ok("Stopped running processes (if any).")

    _step("Reset database (if running)")
    result = api_call("POST", "/database/reset")
    if result.get("success") or result.get("status") == "success":
        _ok("Database reset via API.")
    elif result.get("error"):
        _warn(result["error"])

    _step("Clearing local data")
    if not keep_data:
        data_dir = _resolve_data_dir(repo_dir)
        db_path = _resolve_db_path(repo_dir)
        backup_dir = Path(_read_env_value(repo_dir, "MYCASA_BACKUP_PATH") or (repo_dir / "backups"))
        logs_dir = repo_dir / "logs"

        _safe_rmtree(data_dir)
        _safe_rmtree(backup_dir)
        _safe_rmtree(logs_dir)
        if db_path and db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                _warn(f"Could not delete DB file: {db_path}")
        _ok("Local data cleared.")
    else:
        _ok("Data kept (per --keep-data).")

    _step("Clearing config + caches")
    if not keep_env:
        env_path = repo_dir / ".env"
        frontend_env = repo_dir / "frontend" / ".env.local"
        if env_path.exists():
            env_path.unlink()
            _ok("Removed .env")
        if frontend_env.exists():
            frontend_env.unlink()
            _ok("Removed frontend/.env.local")
    else:
        _ok("Config kept (per --keep-env).")

    frontend_cache = repo_dir / "frontend" / ".next"
    _safe_rmtree(frontend_cache)
    try:
        Path("/tmp/mycasa-api.log").unlink(missing_ok=True)
        Path("/tmp/mycasa-frontend.log").unlink(missing_ok=True)
        Path("/tmp/wacli-sync.log").unlink(missing_ok=True)
    except Exception:
        pass
    _ok("Caches cleared.")

    click.echo("\nReset complete.")
    click.echo("Next: run ./mycasa setup to reconfigure, then ./start_all.sh to launch.")


# ============ TASKS ============

@cli.group()
def tasks():
    """Task management"""


@tasks.command("list")
@click.option("--status", help="Filter by status")
@click.option("--limit", default=20, help="Max results")
def tasks_list(status, limit):
    """List tasks"""
    params = {"limit": limit}
    if status:
        params["status"] = status
    
    result = api_call("GET", "/tasks", params)
    
    if "tasks" in result:
        for task in result["tasks"]:
            status_icon = "✓" if task["status"] == "completed" else "○"
            click.echo(f"{status_icon} [{task['id']}] {task['title']} ({task['status']})")
    else:
        click.echo(f"Error: {result}")


@tasks.command("create")
@click.argument("title")
@click.option("--category", default="general", help="Task category")
@click.option("--priority", default="medium", help="Priority level")
def tasks_create(title, category, priority):
    """Create a new task"""
    data = {
        "title": title,
        "category": category,
        "priority": priority
    }
    
    result = api_call("POST", "/tasks", data)
    
    if result.get("status") == "success":
        click.echo(f"✓ Created task #{result['data']['task_id']}: {title}")
    else:
        click.echo(f"✗ Failed: {result}")


@tasks.command("complete")
@click.argument("task_id", type=int)
@click.option("--evidence", help="Completion evidence")
def tasks_complete(task_id, evidence):
    """Mark a task as complete"""
    params = {}
    if evidence:
        params["evidence"] = evidence
    
    result = api_call("PATCH", f"/tasks/{task_id}/complete", params)
    
    if result.get("status") == "success":
        click.echo(f"✓ Task #{task_id} completed")
    else:
        click.echo(f"✗ Failed: {result}")


# ============ TRANSACTIONS ============

@cli.group()
def transactions():
    """Transaction management"""


@transactions.command("list")
@click.option("--days", default=7, help="Days to look back")
@click.option("--category", help="Filter by category")
def transactions_list(days, category):
    """List transactions"""
    from datetime import timedelta
    
    start = (date.today() - timedelta(days=days)).isoformat()
    params = {"start_date": start, "limit": 50}
    if category:
        params["category"] = category
    
    result = api_call("GET", "/transactions", params)
    
    if "transactions" in result:
        for txn in result["transactions"]:
            click.echo(f"${txn['amount']:>8.2f} | {txn['date']} | {txn['merchant'] or 'Unknown'} | {txn['category'] or 'Uncategorized'}")
    else:
        click.echo(f"Error: {result}")


@transactions.command("summary")
@click.option("--days", default=7, help="Days to summarize")
def transactions_summary(days):
    """Get spending summary"""
    result = api_call("GET", "/transactions/summary", {"days": days})
    
    if "total_spend" in result:
        click.echo(f"Spending Summary ({days} days)")
        click.echo(f"  Total: ${result['total_spend']:,.2f}")
        click.echo(f"  Daily Avg: ${result['avg_daily']:,.2f}")
        click.echo(f"  Transactions: {result['transaction_count']}")
        
        if result.get("by_category"):
            click.echo("\nBy Category:")
            for cat, amount in sorted(result["by_category"].items(), key=lambda x: -x[1]):
                click.echo(f"  {cat}: ${amount:,.2f}")
    else:
        click.echo(f"Error: {result}")


# ============ JOBS ============

@cli.group()
def jobs():
    """Contractor job management"""


@jobs.command("list")
@click.option("--status", help="Filter by status")
def jobs_list(status):
    """List contractor jobs"""
    params = {}
    if status:
        params["status"] = status
    
    result = api_call("GET", "/jobs", params)
    
    if "jobs" in result:
        for job in result["jobs"]:
            cost = f"${job['estimated_cost']:,.2f}" if job.get('estimated_cost') else "TBD"
            click.echo(f"[{job['id']}] {job['description'][:40]} | {job['status']} | {cost}")
    else:
        click.echo(f"Error: {result}")


@jobs.command("create")
@click.argument("description")
@click.option("--contractor", help="Contractor name")
@click.option("--cost", type=float, help="Estimated cost")
def jobs_create(description, contractor, cost):
    """Create a contractor job"""
    data = {
        "description": description,
        "contractor_name": contractor,
        "estimated_cost": cost
    }
    
    result = api_call("POST", "/jobs", data)
    
    if result.get("status") == "success":
        click.echo(f"✓ Created job #{result['data']['job_id']}")
        if result.get("next_steps"):
            click.echo("Next steps:")
            for step in result["next_steps"]:
                click.echo(f"  - {step}")
    else:
        click.echo(f"✗ Failed: {result}")


# ============ COST ============

@cli.group()
def cost():
    """Cost tracking"""


@cost.command("summary")
@click.option("--period", default="month", help="Period: today, month, all")
def cost_summary(period):
    """Get cost summary"""
    result = api_call("GET", "/cost", {"period": period})
    
    if "total_cost" in result:
        click.echo(f"System Cost Summary ({period})")
        click.echo(f"  Total: ${result['total_cost']:.4f}")
        click.echo(f"  Tokens In: {result['total_tokens_in']:,}")
        click.echo(f"  Tokens Out: {result['total_tokens_out']:,}")
        click.echo(f"  Budget Used: {result['budget_used_pct']:.1f}%")
    else:
        click.echo(f"Error: {result}")


@cost.command("budget")
def cost_budget():
    """Check budget status"""
    result = api_call("GET", "/cost/budget")
    
    if "budgets" in result:
        click.echo("Budget Status:")
        for b in result["budgets"]:
            status = "✓" if b["can_proceed"] else "✗"
            click.echo(f"  {status} {b['name']}: ${b['current_spend']:,.2f} / ${b['limit']:,.2f} ({b['pct_used']:.1f}%)")
            for w in b.get("warnings", []):
                click.echo(f"    ⚠ {w}")
    else:
        click.echo(f"Error: {result}")


# ============ BACKUP ============

@cli.group()
def backup():
    """Backup management"""


@backup.command("export")
@click.option("--notes", help="Backup notes")
def backup_export(notes):
    """Export database backup"""
    click.echo("Creating backup...")
    
    data = {}
    if notes:
        data["notes"] = notes
    
    result = api_call("POST", "/backup/export", data)
    
    if result.get("status") == "success":
        click.echo(f"✓ Backup created: {result['data']['filename']}")
        click.echo(f"  Path: {result['data']['path']}")
        click.echo(f"  Size: {result['data']['size_bytes']} bytes")
        click.echo(f"  Checksum: {result['data']['checksum'][:16]}...")
    else:
        click.echo(f"✗ Failed: {result}")


@backup.command("restore")
@click.argument("backup_path")
@click.option("--dry-run", is_flag=True, help="Verify only, don't restore")
def backup_restore(backup_path, dry_run):
    """Restore from backup"""
    click.echo(f"{'Verifying' if dry_run else 'Restoring'} backup...")
    
    data = {
        "backup_path": backup_path,
        "verify_checksum": True,
        "dry_run": dry_run
    }
    
    result = api_call("POST", "/backup/restore", data)
    
    if result.get("status") == "success":
        if dry_run:
            click.echo("✓ Backup verified successfully")
        else:
            click.echo("✓ Backup restored successfully")
        click.echo(f"  Backup ID: {result['data']['backup_id']}")
    else:
        click.echo(f"✗ Failed: {result}")


@backup.command("list")
def backup_list():
    """List available backups"""
    result = api_call("GET", "/backup/list")
    
    if "backups" in result:
        click.echo("Available backups:")
        for b in result["backups"]:
            click.echo(f"  {b['filename']} ({b['size_bytes']} bytes)")
    else:
        click.echo(f"Error: {result}")


# ============ EVENTS ============

@cli.command("events")
@click.option("--limit", default=20, help="Max events")
def show_events(limit):
    """Show recent events"""
    result = api_call("GET", "/events", {"limit": limit})
    
    if "events" in result:
        for event in result["events"]:
            click.echo(f"[{event['timestamp'][:19]}] {event['event_type']}: {event['action']}")
    else:
        click.echo(f"Error: {result}")


# ============ STATUS ============

@cli.command("status")
def show_status():
    """Show full system status"""
    result = api_call("GET", "/status")
    
    if "status" in result:
        click.echo("MyCasa Pro Status")
        click.echo(f"  System: {result['status']}")
        click.echo(f"  Database: {result['db']['status']}")
        click.echo(f"\nTasks:")
        click.echo(f"  Pending: {result['tasks']['pending']}")
        click.echo(f"  In Progress: {result['tasks']['in_progress']}")
        click.echo(f"\nCost ({result['cost'].get('month', 0):.2f} this month):")
        click.echo(f"  Budget: {result['cost']['budget_pct']:.1f}% used")
        click.echo(f"\nBudgets:")
        for b in result.get("budgets", []):
            click.echo(f"  {b['name']}: {b['pct']:.1f}% (${b['current']:,.2f} / ${b['limit']:,.2f})")
    else:
        click.echo(f"Error: {result}")


# ============ JANITOR ============

@cli.group()
def janitor():
    """Janitor agent - system health & maintenance (Salimata ✨)"""


@janitor.command("status")
def janitor_status():
    """Show Janitor agent status"""
    result = api_call("GET", "/api/janitor/status")
    
    if "agent" in result:
        agent = result["agent"]
        metrics = result.get("metrics", {})
        
        click.echo(f"✨ {agent['name']} - {agent['description']}")
        click.echo(f"  Status: {agent['status']}")
        click.echo(f"  Last Audit: {metrics.get('last_audit', 'never')}")
        click.echo(f"  System Health: {metrics.get('system_health', 'unknown')}")
        click.echo(f"  Findings: {metrics.get('findings_count', 0)}")
        click.echo(f"  Recent Edits: {metrics.get('recent_edits', 0)}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("audit")
def janitor_audit():
    """Run a comprehensive system health audit"""
    click.echo("✨ Running system audit...")
    
    result = api_call("GET", "/api/janitor/audit")
    
    if "health_score" in result:
        click.echo(f"\n✨ System Audit Complete")
        click.echo(f"  Health Score: {result['health_score']}%")
        click.echo(f"  Status: {result['status']}")
        click.echo(f"  Checks: {result['checks_passed']}/{result['checks_total']} passed")
        
        if result.get("findings"):
            click.echo(f"\nFindings ({len(result['findings'])}):")
            for f in result["findings"]:
                icon = "🔴" if f["severity"] == "P1" else "🟡" if f["severity"] == "P2" else "🟢"
                click.echo(f"  {icon} [{f['severity']}] {f['domain']}: {f['finding']}")
        else:
            click.echo("\n✅ No issues found!")
    else:
        click.echo(f"Error: {result}")


@janitor.command("cleanup")
@click.option("--days", default=7, help="Keep backups newer than N days")
def janitor_cleanup(days):
    """Clean up old backup files"""
    click.echo(f"✨ Cleaning backups older than {days} days...")
    
    result = api_call("POST", f"/api/janitor/cleanup?days_to_keep={days}", {})
    
    if "deleted" in result:
        click.echo(f"✓ Cleanup complete")
        click.echo(f"  Deleted: {result['deleted']} old backups")
        click.echo(f"  Kept: {result['kept']} recent backups")
        if result.get("errors"):
            click.echo(f"  Errors: {len(result['errors'])}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("history")
@click.option("--limit", default=20, help="Number of edits to show")
def janitor_history(limit):
    """Show recent file edit history"""
    result = api_call("GET", f"/api/janitor/history?limit={limit}")
    
    if "edits" in result:
        if result["edits"]:
            click.echo(f"✨ Recent Edits ({result['total']}):")
            for edit in result["edits"]:
                status = "✓" if edit["success"] else "✗"
                click.echo(f"  {status} {edit['timestamp'][:19]} | {edit['file']} | {edit['agent']}")
        else:
            click.echo("✨ No edit history yet")
    else:
        click.echo(f"Error: {result}")


@janitor.command("connectors")
def janitor_connectors():
    """Check Gmail and WhatsApp connector status"""
    result = api_call("GET", "/api/janitor/connectors")
    
    if "gmail" in result:
        click.echo("✨ Connector Status:")
        click.echo(f"  {result['gmail']['message']}")
        click.echo(f"  {result['whatsapp']['message']}")
        
        if result.get("any_connected"):
            click.echo("\n✅ Real data flowing through connected services")
        elif result.get("all_demo"):
            click.echo("\n📋 All connectors using demo data (configure via Settings)")
    else:
        click.echo(f"Error: {result}")


@janitor.command("backups")
@click.option("--limit", default=20, help="Number of backups to show")
def janitor_backups(limit):
    """List current backup files"""
    result = api_call("GET", f"/api/janitor/backups?limit={limit}")
    
    if "backups" in result:
        if result["backups"]:
            click.echo(f"✨ Backups ({result['count']}):")
            for b in result["backups"]:
                size_kb = b["size_bytes"] / 1024
                click.echo(f"  {b['modified'][:19]} | {size_kb:>7.1f}KB | {b['filename'][:50]}")
        else:
            click.echo("✨ No backup files found")
        click.echo(f"\n  Backup dir: {result.get('backup_dir', 'unknown')}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("logs")
@click.option("--limit", default=20, help="Number of logs to show")
def janitor_logs(limit):
    """Show Janitor activity logs"""
    result = api_call("GET", f"/api/janitor/logs?limit={limit}")
    
    if "logs" in result:
        if result["logs"]:
            click.echo(f"✨ Janitor Activity ({result['count']} logs):")
            for log in result["logs"]:
                status = "✓" if log.get("status") == "success" else "⚠" if log.get("status") == "warning" else "✗"
                click.echo(f"  {status} {log['timestamp'][:19]} | {log['action']}: {log['details'][:50]}")
        else:
            click.echo("✨ No activity logs yet")
    else:
        click.echo(f"Error: {result}")


@janitor.command("review")
@click.argument("file_path")
@click.argument("content_file", type=click.Path(exists=True))
def janitor_review(file_path, content_file):
    """Review a code change before applying it"""
    click.echo(f"✨ Reviewing changes to {file_path}...")
    
    try:
        with open(content_file, 'r') as f:
            new_content = f.read()
    except Exception as e:
        click.echo(f"✗ Could not read content file: {e}")
        return
    
    result = api_call("POST", "/api/janitor/review", {
        "file_path": file_path,
        "new_content": new_content,
    })
    
    if "approved" in result:
        status = "✅ APPROVED" if result["approved"] else "❌ BLOCKED"
        click.echo(f"\n{status}")
        click.echo(f"  Blockers: {result['blocker_count']}")
        click.echo(f"  Warnings: {result['warning_count']}")
        
        if result.get("concerns"):
            click.echo(f"\nConcerns:")
            for c in result["concerns"]:
                icon = "🔴" if c["severity"] == "blocker" else "🟡"
                click.echo(f"  {icon} {c['issue']}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("chat")
@click.argument("message")
def janitor_chat(message):
    """Chat with Salimata (Janitor Agent)"""
    result = api_call("POST", f"/api/janitor/chat?message={message}", {})
    
    if "response" in result:
        click.echo(result["response"])
    else:
        click.echo(f"Error: {result}")


# Entry point
app = cli

if __name__ == "__main__":
    cli()
