#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR/frontend"

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

API_PORT="${MYCASA_API_PORT:-6709}"
UI_PORT="${MYCASA_UI_PORT:-3000}"
BIND_HOST="${MYCASA_BIND_HOST:-0.0.0.0}"

export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://${PUBLIC_HOST}:${API_PORT}}"

if [ ! -d "node_modules" ]; then
  npm install
fi

exec npm run dev -- --hostname "$BIND_HOST" --port "$UI_PORT"
