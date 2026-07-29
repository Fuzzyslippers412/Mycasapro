# MyCasaPro

MyCasaPro gives homeowners and contractors one clear record for repair work—from the first issue through estimates, scheduling, invoices, and payment history.

## What works today

### Homeowners

- secure account registration and sign-in
- private property records
- repair requests with photos and PDFs
- expiring, revocable links for contractors who are not registered
- email delivery for private contractor invitations, with retry and delivery status
- guest estimate review with line-item pricing
- shared project timelines, messages, appointments, invoices, and payments

### Contractors

- contractor accounts and organizations
- live homeowner request inbox
- request-to-project conversion
- estimate, scheduling, message, and invoice workflows
- no-account estimate submission through a private homeowner invitation

## Technology

- Next.js 16 and React 19
- Go HTTP API
- PostgreSQL 16
- HTTP-only sessions and role-scoped authorization
- private, API-authorized attachment storage

## Run locally

### Personal installation

MyCasaPro can run as a private appliance on a macOS, Linux, or Windows computer. It binds only to `127.0.0.1`, stores its database and uploads in durable Docker volumes, and exposes one local web address.

macOS or Linux:

```bash
curl -fsSL https://www.mycasapro.com/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://www.mycasapro.com/install.ps1 | iex
```

Docker Desktop or Docker Engine with Compose is required. After setup, run `mycasapro` to start or open the app. Use `mycasapro help` for status, logs, upgrades, backup, restore, and uninstall commands.

### Source development

Requirements: Go 1.25+, Node.js 22+, npm, and Docker for PostgreSQL.

```bash
git clone https://github.com/Fuzzyslippers412/Mycasapro.git
cd Mycasapro
npm --prefix web ci
make run-db
```

In a second terminal:

```bash
make run-app
```

In a third terminal:

```bash
make run-web
```

Open `http://localhost:3000`.

For a temporary development run without PostgreSQL:

```bash
make run-app-memory
make run-web
```

The memory backend is blocked when `APP_ENV=production`.

## Deploy publicly

The production package runs the web app, API, PostgreSQL, private uploads, SMTP delivery, and automatic HTTPS on one Linux server:

```bash
cd infra/production
cp .env.example .env
# Configure the domain, database password, and SMTP provider in .env.
./deploy.sh
```

See `infra/production/README.md` for DNS, sizing, backups, upgrades, and operational limits.

## Verify

```bash
make test
make build
```

## Repository

- `app/` — Go API, domain logic, persistence, private file storage, and SQL migrations
- `cli/` — cross-platform local appliance lifecycle, diagnostics, and backups
- `web/` — homeowner, contractor, and no-account estimate interfaces
- `infra/` — PostgreSQL and complete local Docker appliance definitions
- `infra/production/` — hardened single-server deployment, HTTPS proxy, and backup tooling
- `docs/` — active product, design, build, and deployment decisions

## Invitation security

Contractor share links use 256-bit random tokens. Only SHA-256 token hashes are stored. Public task views omit street addresses and homeowner identifiers, attachment access remains token-scoped, request logs redact tokens, and every invitation expires after seven days unless the homeowner revokes it earlier. Email invitations are committed to a database outbox with the link, then delivered asynchronously with bounded retries so a temporary mail-provider outage cannot lose the invitation.

## Production status

The local appliance provides a complete private workflow without a hosted dependency. The repository also includes a real single-server public deployment baseline. A broader public launch still requires external monitoring, rehearsed off-server backups, managed/object storage for horizontal scaling, email-domain authentication, abuse controls, and live payment-provider integration. See `docs/github-and-production-deployment.md` and `docs/mycasapro-premium-home-and-pro-plan.md`.
