#!/bin/bash
# Start MyCasa Pro - Backend API + Frontend UI + WhatsApp Sync

set -e
cd "$(dirname "$0")"

echo "🏠 Starting MyCasa Pro..."

# Load .env if present (for MYCASA_* settings)
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Resolve Python binary
PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "❌ Python not found. Install Python 3 and try again."
    exit 1
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Host/port configuration
BIND_HOST="${MYCASA_BIND_HOST:-0.0.0.0}"
API_PORT="${MYCASA_API_PORT:-6709}"
UI_PORT="${MYCASA_UI_PORT:-3000}"
PUBLIC_HOST="${MYCASA_PUBLIC_HOST:-}"
if [ -z "$PUBLIC_HOST" ]; then
    # Try to detect a LAN IP for cross-device access
    if command -v python3 >/dev/null 2>&1; then
        PUBLIC_HOST="$(python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); 
try:
    s.connect(('8.8.8.8',80)); print(s.getsockname()[0])
except Exception:
    print('')
finally:
    s.close()" 2>/dev/null)"
    fi
    if [ -z "$PUBLIC_HOST" ]; then
        PUBLIC_HOST="$(ipconfig getifaddr en0 2>/dev/null || true)"
    fi
    if [ -z "$PUBLIC_HOST" ]; then
        PUBLIC_HOST="$(ipconfig getifaddr en1 2>/dev/null || true)"
    fi
    if [ -z "$PUBLIC_HOST" ]; then
        PUBLIC_HOST="127.0.0.1"
    fi
fi
RELOAD_FLAG=""
if [ "${MYCASA_RELOAD:-0}" = "1" ]; then
    RELOAD_FLAG="--reload"
fi

# Kill existing processes
echo -e "${YELLOW}Stopping existing processes...${NC}"
pkill -f "uvicorn.*backend.api.main" 2>/dev/null || true
pkill -f "uvicorn api.main" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
if command -v lsof &> /dev/null; then
    UI_PIDS="$(lsof -tiTCP:${UI_PORT} -sTCP:LISTEN 2>/dev/null || true)"
    if [ -n "$UI_PIDS" ]; then
        echo -e "${YELLOW}Stopping UI on port ${UI_PORT}...${NC}"
        kill $UI_PIDS 2>/dev/null || true
    fi
fi
sleep 1

# Start WhatsApp sync (if wacli available)
if command -v wacli &> /dev/null; then
    echo -e "${BLUE}Starting WhatsApp sync...${NC}"
    pkill -f "wacli sync" 2>/dev/null || true
    nohup wacli sync --follow > /tmp/wacli-sync.log 2>&1 &
    sleep 1
fi

# Create data directory (allow override)
DATA_DIR="${MYCASA_DATA_DIR:-$PWD/data}"
mkdir -p "$DATA_DIR/logs"

# One-time migration from /tmp to persistent data dir (if needed)
if [ -z "$MYCASA_DATA_DIR" ]; then
    if [ -f "/tmp/mycasa-data/mycasa.db" ] && [ ! -f "$DATA_DIR/mycasa.db" ]; then
        echo -e "${YELLOW}Migrating DB from /tmp/mycasa-data to ${DATA_DIR}...${NC}"
        cp /tmp/mycasa-data/mycasa.db "$DATA_DIR/mycasa.db"
    fi
fi

# Activate venv if present (preferred)
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install backend deps if needed
if ! "$PYTHON_BIN" -c "import fastapi" 2>/dev/null; then
    echo -e "${BLUE}Installing backend dependencies...${NC}"
    "$PYTHON_BIN" -m pip install -r requirements.txt -q
fi

# Start Backend API (new unified backend)
echo -e "${BLUE}Starting Backend API (port ${API_PORT})...${NC}"
export MYCASA_DATA_DIR="${DATA_DIR}"
export MYCASA_DATABASE_URL="${MYCASA_DATABASE_URL:-sqlite:///$DATA_DIR/mycasa.db}"
export MYCASA_LOG_FILE="${MYCASA_LOG_FILE:-$DATA_DIR/logs/mycasa.log}"
export DATABASE_URL="${DATABASE_URL:-$MYCASA_DATABASE_URL}"
export NEXT_PUBLIC_API_URL="http://${PUBLIC_HOST}:${API_PORT}"
nohup "$PYTHON_BIN" -m uvicorn api.main:app --host "$BIND_HOST" --port "$API_PORT" $RELOAD_FLAG > /tmp/mycasa-api.log 2>&1 &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API..."
sleep 3

# Test API
if curl -s "http://${PUBLIC_HOST}:${API_PORT}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is running${NC}"
else
    echo -e "${YELLOW}⚠ API may still be starting...${NC}"
fi

# Start Frontend UI
if [ -d "frontend/node_modules" ]; then
    echo -e "${BLUE}Starting Frontend UI (port ${UI_PORT})...${NC}"
    ENV_FILE="$PWD/frontend/.env.local"
    if [ -f "$ENV_FILE" ]; then
        if grep -q "^NEXT_PUBLIC_API_URL=" "$ENV_FILE"; then
            sed -i '' "s#^NEXT_PUBLIC_API_URL=.*#NEXT_PUBLIC_API_URL=http://${PUBLIC_HOST}:${API_PORT}#g" "$ENV_FILE"
        else
            echo "NEXT_PUBLIC_API_URL=http://${PUBLIC_HOST}:${API_PORT}" >> "$ENV_FILE"
        fi
    else
        echo "NEXT_PUBLIC_API_URL=http://${PUBLIC_HOST}:${API_PORT}" > "$ENV_FILE"
    fi
    UI_LOCK="$PWD/frontend/.next/dev/lock"
    if [ -f "$UI_LOCK" ]; then
        echo -e "${YELLOW}Clearing stale Next.js dev lock...${NC}"
        rm -f "$UI_LOCK"
    fi
    cd frontend
    nohup npm run dev -- --hostname "$BIND_HOST" --port "$UI_PORT" > /tmp/mycasa-frontend.log 2>&1 &
    UI_PID=$!
    cd ..
    sleep 3
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${YELLOW}Frontend not installed. Run: cd frontend && npm install${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  MyCasa Pro is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  📡 API:      http://${PUBLIC_HOST}:${API_PORT}"
echo "  📡 API Docs: http://${PUBLIC_HOST}:${API_PORT}/docs"
echo "  🖥️  UI:       http://${PUBLIC_HOST}:${UI_PORT}"
echo ""
echo "  Logs:"
echo "    API:      tail -f /tmp/mycasa-api.log"
echo "    Frontend: tail -f /tmp/mycasa-frontend.log"
echo "    WhatsApp: tail -f /tmp/wacli-sync.log"
echo ""
echo "  CLI: ./mycasa status"
echo ""
echo "  To stop: pkill -f 'uvicorn|next dev|wacli sync'"
echo ""
