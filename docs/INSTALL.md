# Installation (Local)

This app runs a FastAPI backend and a Next.js frontend. Use the setup wizard or run it manually.

## Requirements
- Python 3.11+
- Node.js 18+
- Git

## Recommended (wizard)
```bash
cd /path/to/mycasa-pro
cp .env.example .env
./mycasa setup
```

## Manual (two terminals)
### macOS / Linux
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

### Windows PowerShell
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

## URLs
- UI: http://127.0.0.1:3000
- API: http://127.0.0.1:6709
- API Docs: http://127.0.0.1:6709/docs

## Qwen OAuth (default)
```bash
./mycasa llm qwen-login
```
Default model: `qwen3-coder-next`.

## Connectors (user-owned credentials)
### Gmail (gog)
```bash
brew install doitintl/tap/gog
gog auth login
```

### WhatsApp (wacli)
```bash
npm install -g @nicholasoxford/wacli
wacli auth
```

## Troubleshooting
### Backend not reachable
```bash
tail -f /tmp/mycasa-api.log
```

Restart:
```bash
MYCASA_API_PORT=6709 ./start_all.sh
```

Reset stale API host in browser:
```js
localStorage.removeItem("mycasa_api_base_override")
```
