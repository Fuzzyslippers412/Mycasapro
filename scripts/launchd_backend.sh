#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PUBLIC_HOST="${MYCASA_PUBLIC_HOST:-}"
if [ -z "$PUBLIC_HOST" ]; then
  PUBLIC_HOST="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [ -z "$PUBLIC_HOST" ]; then
    PUBLIC_HOST="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [ -z "$PUBLIC_HOST" ]; then
    PUBLIC_HOST="127.0.0.1"
  fi
fi

API_PORT="${MYCASA_API_PORT:-8000}"
BIND_HOST="${MYCASA_BIND_HOST:-0.0.0.0}"

export DATABASE_URL="${DATABASE_URL:-sqlite:///$REPO_DIR/data/mycasa.db}"
export MYCASA_LOG_FILE="${MYCASA_LOG_FILE:-$REPO_DIR/data/logs/mycasa.log}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://${PUBLIC_HOST}:${API_PORT}}"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec python3 -m uvicorn api.main:app --host "$BIND_HOST" --port "$API_PORT"
