# Infrastructure

Local PostgreSQL and complete Docker appliance infrastructure for MyCasaPro.

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
