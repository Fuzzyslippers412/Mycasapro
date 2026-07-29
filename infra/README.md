# Infrastructure

Local PostgreSQL, complete Docker appliance, and public single-server deployment infrastructure for MyCasaPro.

```bash
make run-db
make run-app
```

Stop the local database with `make stop-db`. Production must use managed PostgreSQL and durable private attachment storage.

Build and run the complete appliance from source:

```bash
make local-up
```

Open `http://127.0.0.1:3210`. Stop it with `make local-down`. The published-image definition in `docker-compose.local.yml` is embedded in the `mycasapro` CLI and must remain byte-for-byte identical.

Run the same published-appliance integration test used by release automation:

```bash
MYCASAPRO_VERSION=latest ./infra/smoke-test.sh
```

It verifies PostgreSQL migrations, the web-to-API proxy, account creation, container restart, and durable session state, then removes its isolated test volumes.

For a public HTTPS deployment with PostgreSQL, private uploads, SMTP invitations, and backup tooling, use `infra/production/` and follow `infra/production/README.md`.
