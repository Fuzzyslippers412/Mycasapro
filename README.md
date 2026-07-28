# MyCasaPro

MyCasaPro gives homeowners and contractors one clear record for repair work—from the first issue through estimates, scheduling, invoices, and payment history.

## What works today

### Homeowners

- secure account registration and sign-in
- private property records
- repair requests with photos and PDFs
- expiring, revocable links for contractors who are not registered
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

## Verify

```bash
make test
make build
```

## Repository

- `app/` — Go API, domain logic, persistence, private file storage, and SQL migrations
- `web/` — homeowner, contractor, and no-account estimate interfaces
- `infra/` — local PostgreSQL infrastructure
- `docs/` — active product, design, build, and deployment decisions

## Invitation security

Contractor share links use 256-bit random tokens. Only SHA-256 token hashes are stored. Public task views omit street addresses and homeowner identifiers, attachment access remains token-scoped, request logs redact tokens, and every invitation expires after seven days unless the homeowner revokes it earlier.

## Production status

This is active production-oriented development, not a hosted public release yet. Remaining launch work includes managed deployment, email delivery, private object storage, monitoring, backups, and live payment processing. See `docs/github-and-production-deployment.md` and `docs/mycasapro-premium-home-and-pro-plan.md`.
