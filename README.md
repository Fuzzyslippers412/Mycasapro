# MyCasa Pro

Local-first home operating system for homeowners and renters. Next.js UI + FastAPI backend.

## Quick Install (no scripts)

**macOS / Linux**
```bash
cd /path/to/mycasa-pro
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
python install.py install
## install.py will install missing Python deps automatically (use --no-deps to skip)
export MYCASA_API_BASE_URL=http://127.0.0.1:6709 MYCASA_BACKEND_PORT=6709 MYCASA_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709
# new terminal
cd frontend && echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" > .env.local && npm install && npm run dev
```

**macOS / Linux (single command)**
```bash
MYCASA_API_PORT=6709 ./start_all.sh
```
_Default port is 6709; setting `MYCASA_API_PORT` is optional._
If you want to access from another device on the same network:
```bash
MYCASA_PUBLIC_HOST=<your-lan-ip> MYCASA_BIND_HOST=0.0.0.0 ./start_all.sh
```

**Terminal Setup Wizard (recommended)**
```bash
./mycasa setup
```
The wizard checks dependencies, configures ports/env, initializes DB, starts services, and guides Qwen OAuth.

**Windows PowerShell**
```powershell
cd C:\path\to\mycasa-pro
copy .env.example .env
py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1
python install.py install
$env:MYCASA_API_BASE_URL="http://127.0.0.1:6709"; $env:MYCASA_BACKEND_PORT="6709"; $env:MYCASA_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709
# new terminal
cd frontend; "NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" | Out-File -Encoding utf8 .env.local; npm install; npm run dev
```

## Requirements
- Python 3.11+
- Node.js 18+ (npm)
- Git

## Repo cleanup (recommended before publishing)
Remove tracked dev artifacts and duplicate folders:
```bash
bash scripts/cleanup_repo.sh
# review output, then apply:
bash scripts/cleanup_repo.sh --apply
```

## Quickstart (macOS / Linux)
```bash
cd /path/to/mycasa-pro
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
python install.py install

# Backend (terminal 1)
export MYCASA_API_BASE_URL=http://127.0.0.1:6709
export MYCASA_BACKEND_PORT=6709
export MYCASA_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709

# Frontend (terminal 2)
cd frontend
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" > .env.local
npm install
npm run dev
```

## Quickstart (Windows PowerShell)
```powershell
cd C:\path\to\mycasa-pro
copy .env.example .env

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python install.py install

# Backend (terminal 1)
$env:MYCASA_API_BASE_URL="http://127.0.0.1:6709"
$env:MYCASA_BACKEND_PORT="6709"
$env:MYCASA_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709

# Frontend (terminal 2)
cd frontend
"NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" | Out-File -Encoding utf8 .env.local
npm install
npm run dev
```

Open:
- UI: http://127.0.0.1:3000
- API: http://127.0.0.1:6709

## Quick CLI Commands
```bash
# Open the UI in your browser
./mycasa open

# Start/stop the system runtime (agents + lifecycle)
./mycasa system start
./mycasa system stop
```

## Factory Reset (start over clean)
```bash
./mycasa reset
```
This stops services, wipes local data/config, and clears caches. After reset:
```bash
./mycasa setup
./start_all.sh
```
If the UI still points to a wrong port, clear the browser override:
```js
// in browser console
localStorage.removeItem("mycasa_api_base_override")
```

## Qwen OAuth (Terminal)
Authenticate Qwen from the terminal (device flow):
```bash
./mycasa llm qwen-login
```
Default uses the direct device flow (no MyCasa login required). If you want to route through the API (requires MyCasa login), use:
```bash
./mycasa llm qwen-login --api
```
Environment options:
```bash
MYCASA_API_BASE_URL=http://127.0.0.1:6709 MYCASA_USERNAME=youruser MYCASA_PASSWORD=yourpass ./mycasa llm qwen-login
```

## Vercel (frontend) + hosted backend
MyCasa Pro requires a long-running FastAPI backend for agents, scheduling, and webhooks. Vercel is used for the frontend only.

See docs:
- `docs/DEPLOY_VERCEL.md`
- `docs/INSTALL.md`
