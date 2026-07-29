#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
if [ ! -f .env ]; then
  echo "Missing $SCRIPT_DIR/.env" >&2
  exit 1
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
destination=${1:-"$SCRIPT_DIR/backups/$timestamp"}
mkdir -p "$destination"
chmod 700 "$destination"
COMPOSE="docker compose --env-file .env -f compose.yml"

$COMPOSE exec -T postgres pg_dump --format=custom --no-owner --no-acl -U mycasapro mycasapro > "$destination/database.dump"
$COMPOSE exec -T app tar -C /data/uploads -czf - . > "$destination/uploads.tar.gz"

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$destination" && sha256sum database.dump uploads.tar.gz > SHA256SUMS)
else
  (cd "$destination" && shasum -a 256 database.dump uploads.tar.gz > SHA256SUMS)
fi

echo "Backup written to $destination"
echo "Encrypt it and copy it off this server before treating it as durable."
