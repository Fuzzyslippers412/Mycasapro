#!/bin/bash

#!/bin/bash

set -e

# Kill any existing backend
pkill -f "uvicorn.*api.main" 2>/dev/null || true

cd ~/clawd/apps/mycasa-pro

# Activate venv if present
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

# Align defaults with start_all.sh
BIND_HOST="${MYCASA_BIND_HOST:-127.0.0.1}"
API_PORT="${MYCASA_API_PORT:-6709}"
DATA_DIR="${MYCASA_DATA_DIR:-$PWD/data}"
if [ -z "$MYCASA_DATA_DIR" ]; then
  if [ -f "/tmp/mycasa-data/mycasa.db" ] && [ ! -f "$DATA_DIR/mycasa.db" ]; then
    echo "⚠ Migrating DB from /tmp/mycasa-data to ${DATA_DIR}..."
    cp /tmp/mycasa-data/mycasa.db "$DATA_DIR/mycasa.db"
  fi
fi
mkdir -p "$DATA_DIR"
export MYCASA_DATA_DIR="${DATA_DIR}"
export MYCASA_DATABASE_URL="${MYCASA_DATABASE_URL:-sqlite:///$DATA_DIR/mycasa.db}"
export DATABASE_URL="${DATABASE_URL:-$MYCASA_DATABASE_URL}"

echo "Starting MyCasa Pro Backend..."
echo "URL: http://${BIND_HOST}:${API_PORT}"
echo "Docs: http://${BIND_HOST}:${API_PORT}/docs"
echo "DB: ${MYCASA_DATABASE_URL}"
echo ""

uvicorn api.main:app --host "$BIND_HOST" --port "$API_PORT" --reload
