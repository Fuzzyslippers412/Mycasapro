#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT/infra/docker-compose.local.yml"
MYCASAPRO_PORT="${MYCASAPRO_PORT:-33210}"
MYCASAPRO_VERSION="${MYCASAPRO_VERSION:-latest}"
MYCASAPRO_DB_PASSWORD="${MYCASAPRO_DB_PASSWORD:-smoke-test-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ}"
export MYCASAPRO_PORT MYCASAPRO_VERSION MYCASAPRO_DB_PASSWORD

compose() {
  docker compose --project-name mycasapro-smoke -f "$COMPOSE_FILE" "$@"
}

cleanup() {
  exit_code=$?
  trap - EXIT HUP INT TERM
  if [ "$exit_code" -ne 0 ]; then
    echo "MyCasaPro smoke test failed. Container logs:" >&2
    compose logs --no-color --tail 300 >&2 || true
  fi
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
  exit "$exit_code"
}
trap cleanup EXIT HUP INT TERM

wait_for_health() {
  attempts=0
  while [ "$attempts" -lt 90 ]; do
    if curl -fsS "http://127.0.0.1:$MYCASAPRO_PORT/healthz" >/tmp/mycasapro-smoke-health.json 2>/dev/null; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 2
  done
  echo "MyCasaPro did not become healthy within 180 seconds." >&2
  return 1
}

echo "Pulling MyCasaPro $MYCASAPRO_VERSION images..."
compose pull
compose up -d --remove-orphans
wait_for_health

python3 - <<'PY'
import json
with open('/tmp/mycasapro-smoke-health.json', encoding='utf-8') as handle:
    health = json.load(handle)
assert health['ok'] is True
assert health['database'] is True
assert health['store_backend'] == 'postgres'
PY

curl -fsS "http://127.0.0.1:$MYCASAPRO_PORT/" >/tmp/mycasapro-smoke-home.html
email="smoke-$(date +%s)-$$@example.test"
curl -fsS \
  -c /tmp/mycasapro-smoke-cookies.txt \
  -H 'Content-Type: application/json' \
  --data "{\"email\":\"$email\",\"password\":\"reliable-smoke-password\",\"display_name\":\"Smoke Homeowner\",\"role\":\"homeowner\"}" \
  "http://127.0.0.1:$MYCASAPRO_PORT/api/v1/auth/register" \
  >/tmp/mycasapro-smoke-register.json

python3 - "$email" <<'PY'
import json
import sys
with open('/tmp/mycasapro-smoke-register.json', encoding='utf-8') as handle:
    payload = json.load(handle)
assert payload['user']['email'] == sys.argv[1]
assert payload['user']['role'] == 'homeowner'
PY

echo "Restarting the appliance to verify durable database and session state..."
compose restart
wait_for_health
curl -fsS \
  -b /tmp/mycasapro-smoke-cookies.txt \
  "http://127.0.0.1:$MYCASAPRO_PORT/api/v1/auth/me" \
  >/tmp/mycasapro-smoke-session.json

python3 - "$email" <<'PY'
import json
import sys
with open('/tmp/mycasapro-smoke-session.json', encoding='utf-8') as handle:
    payload = json.load(handle)
assert payload['user']['email'] == sys.argv[1]
PY

echo "MyCasaPro appliance smoke test passed."
