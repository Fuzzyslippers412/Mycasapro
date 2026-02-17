#!/bin/bash
cd "$(dirname "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║${NC}                                                              ${PURPLE}║${NC}"
echo -e "${PURPLE}║${NC}     ${CYAN}🏠  M Y C A S A   P R O${NC}                                 ${PURPLE}║${NC}"
echo -e "${PURPLE}║${NC}     ${NC}AI-Driven Home Operating System                         ${PURPLE}║${NC}"
echo -e "${PURPLE}║${NC}     ${GREEN}Powered by Galidima${NC}                                     ${PURPLE}║${NC}"
echo -e "${PURPLE}║${NC}                                                              ${PURPLE}║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Load .env if present
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "${RED}❌ Virtual environment not found. Run: python3 -m venv .venv${NC}"
    exit 1
fi

# Host/port configuration
BIND_HOST="${MYCASA_BIND_HOST:-0.0.0.0}"
API_PORT="${MYCASA_API_PORT:-6709}"
UI_PORT="${MYCASA_UI_PORT:-3000}"
PUBLIC_HOST="${MYCASA_PUBLIC_HOST:-}"
if [ -z "$PUBLIC_HOST" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PUBLIC_HOST="$(python3 - <<'PY'\nimport socket\ntry:\n    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\n    s.connect(('8.8.8.8',80))\n    print(s.getsockname()[0])\nexcept Exception:\n    print('')\nfinally:\n    try: s.close()\n    except Exception: pass\nPY\n)"
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

# Create data directory (allow override)
DATA_DIR="${MYCASA_DATA_DIR:-$PWD/data}"
mkdir -p "$DATA_DIR/logs"

# Initialize database if needed
if [ ! -f "data/mycasa.db" ]; then
    echo -e "${BLUE}🗄️  Initializing database...${NC}"
    python3 -c "from database import init_db; init_db()" 2>/dev/null || true
fi

# Kill any existing processes on our ports (if lsof exists)
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:8505 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

echo -e "${CYAN}🚀 Starting MyCasa Pro...${NC}"
echo -e "${GREEN}   → Backend:  http://${PUBLIC_HOST}:${API_PORT}${NC}"
echo -e "${GREEN}   → Frontend: http://${PUBLIC_HOST}:${UI_PORT}${NC}"
echo ""

# Start FastAPI backend
echo -e "${BLUE}Starting API server...${NC}"
export MYCASA_DATA_DIR="${DATA_DIR}"
export MYCASA_DATABASE_URL="${MYCASA_DATABASE_URL:-sqlite:///$DATA_DIR/mycasa.db}"
export MYCASA_LOG_FILE="${MYCASA_LOG_FILE:-$DATA_DIR/logs/mycasa.log}"
export DATABASE_URL="${DATABASE_URL:-$MYCASA_DATABASE_URL}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://${PUBLIC_HOST}:${API_PORT}}"
uvicorn api.main:app --host "$BIND_HOST" --port "$API_PORT" $RELOAD_FLAG &
BACKEND_PID=$!

# Start Next.js frontend
echo -e "${BLUE}Starting frontend...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
    npm install
fi
npm run dev -- --hostname "$BIND_HOST" --port "$UI_PORT" &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}✅ MyCasa Pro is running${NC}"
echo -e "   Backend PID: $BACKEND_PID"
echo -e "   Frontend PID: $FRONTEND_PID"
echo ""
echo -e "${CYAN}Press Ctrl+C to stop${NC}"

# Wait for either process to exit
wait
