# Production deployment

This package runs a single-server MyCasaPro installation with automatic HTTPS, PostgreSQL, private attachment storage, and durable SMTP invitation delivery. Only Caddy exposes host ports; the database, API, and web process remain on the Docker network.

## Prerequisites

- a Linux server with Docker Engine and Compose v2
- ports 80 and 443 open
- an A/AAAA DNS record pointing a hostname to the server
- SMTP credentials for a transactional email provider
- at least 2 CPU cores, 4 GB RAM, and durable SSD storage

## First deployment

```bash
cd infra/production
cp .env.example .env
openssl rand -hex 32
# Edit .env and paste the generated database password.
./deploy.sh
```

Use a URL-safe hexadecimal database password because it is embedded in the PostgreSQL connection URL. The deployment script restricts `.env` to the current OS user. Do not commit it.

The API runs migrations before it becomes healthy. Caddy obtains and renews the TLS certificate automatically after DNS resolves and ports 80/443 are reachable.

## Upgrade

Set `MYCASAPRO_VERSION` in `.env` to a tested release tag, then run:

```bash
./deploy.sh
```

Create and verify a backup before every upgrade. Never deploy `latest` as an unattended production policy.

## Backup

```bash
./backup.sh
```

The backup contains a PostgreSQL custom-format dump, private uploads, and checksums. Encrypt it and copy it to a separate provider or physical location. A backup left only on the application server does not protect against server loss.

To restore, stop `app` and `web`, restore `database.dump` with `pg_restore` into an empty `mycasapro` database, extract `uploads.tar.gz` into the uploads volume, then start the stack and verify `/healthz`. Rehearse this procedure before launch.

## Operations

```bash
docker compose --env-file .env -f compose.yml ps
docker compose --env-file .env -f compose.yml logs -f --tail=100
docker compose --env-file .env -f compose.yml restart app web
```

Invitation emails are written to the database in the same transaction as their private link. The API worker retries temporary SMTP failures and marks terminal failures in invitation history after eight attempts.

This package is a durable single-server baseline, not a high-availability topology. Before serving critical or regulated workloads, move PostgreSQL and attachments to independently backed-up managed services and add external uptime, error-rate, disk, certificate, and backup-age monitoring.
