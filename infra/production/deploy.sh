#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine with Compose v2 is required." >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for the deployment health check." >&2
  exit 1
fi
if [ ! -f .env ]; then
  echo "Missing $SCRIPT_DIR/.env. Start from .env.example and add production values." >&2
  exit 1
fi

chmod 600 .env
COMPOSE="docker compose --env-file .env -f compose.yml"
$COMPOSE config --quiet
web_url=$($COMPOSE config | awk '$1 == "APP_WEB_URL:" { print $2; exit }')
MYCASAPRO_DOMAIN=${web_url#https://}

case "${MYCASAPRO_DOMAIN:-}" in
  ""|http://*|https://*|*/*|*:*|*" "*)
    echo "MYCASAPRO_DOMAIN must be a bare public hostname, such as repairs.example.com." >&2
    exit 1
    ;;
esac

$COMPOSE pull
$COMPOSE up -d --remove-orphans

health_url="https://${MYCASAPRO_DOMAIN}/healthz"
echo "Waiting for TLS and application health at $health_url ..."
attempt=0
until curl --fail --silent --show-error --max-time 8 "$health_url" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 45 ]; then
    echo "Deployment did not become healthy. Recent service status:" >&2
    $COMPOSE ps >&2
    $COMPOSE logs --tail=80 caddy app web >&2
    exit 1
  fi
  sleep 4
done

$COMPOSE ps
echo "MyCasaPro is healthy at https://${MYCASAPRO_DOMAIN}"
