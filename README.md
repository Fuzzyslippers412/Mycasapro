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

## Vercel (frontend) + hosted backend
MyCasa Pro requires a long-running FastAPI backend for agents, scheduling, and webhooks. Vercel is used for the frontend only.

See docs:
- `docs/DEPLOY_VERCEL.md`
- `docs/INSTALL.md`
