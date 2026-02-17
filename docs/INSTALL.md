# Installation (Local)

This app runs a FastAPI backend and a Next.js frontend. Use two terminals.

## Requirements
- Python 3.11+
- Node.js 18+
- Git

## macOS / Linux
```bash
cd /path/to/mycasa-pro
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python install.py install

# Backend
export MYCASA_API_BASE_URL=http://127.0.0.1:6709
export MYCASA_BACKEND_PORT=6709
export MYCASA_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709

# Frontend (new terminal)
cd frontend
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" > .env.local
npm install
npm run dev
```

Or on macOS/Linux:
```bash
MYCASA_API_PORT=6709 ./start_all.sh
```
_Default port is 6709; setting `MYCASA_API_PORT` is optional._

For access from another device on the same network:
```bash
MYCASA_PUBLIC_HOST=<your-lan-ip> MYCASA_BIND_HOST=0.0.0.0 ./start_all.sh
```

Or use the interactive wizard (recommended):
```bash
./mycasa setup
```
The wizard:
- Checks Python/Node/npm
- Picks safe ports
- Writes `.env` and `frontend/.env.local`
- Installs backend + frontend deps
- Initializes database
- Starts backend + frontend
- Offers Qwen OAuth device login

## Windows PowerShell
```powershell
cd C:\path\to\mycasa-pro
copy .env.example .env

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python install.py install

# Backend
$env:MYCASA_API_BASE_URL="http://127.0.0.1:6709"
$env:MYCASA_BACKEND_PORT="6709"
$env:MYCASA_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709

# Frontend (new terminal)
cd frontend
"NEXT_PUBLIC_API_URL=http://127.0.0.1:6709" | Out-File -Encoding utf8 .env.local
npm install
npm run dev
```

## URLs
- UI: http://127.0.0.1:3000
- API: http://127.0.0.1:6709

## Notes
- `install.py` initializes the SQLite database and seeds defaults.
- For production, use Postgres (set `MYCASA_DATABASE_URL`).

## Acceptance Tests
With the API running:
```bash
API_URL=http://127.0.0.1:6709 bash scripts/acceptance_test.sh
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
