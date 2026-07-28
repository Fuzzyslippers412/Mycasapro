# App

Go monolith for the home maintenance product.

## Current scope

- production-oriented HTTP server
- health and product metadata endpoints
- credentialed CORS and security middleware
- registration, login, logout, HTTP-only sessions, and role-scoped authorization
- homeowner APIs for:
  - property creation and listing
  - work request creation and listing
  - private repair photo and PDF upload/download
  - expiring, revocable guest estimate invitations
  - guest estimate collection and homeowner review
  - dashboard summary aggregation
- contractor APIs for:
  - organization creation and listing
  - dashboard summary aggregation
  - converting open homeowner requests into projects
- assigned and open-request attachment access with server-side authorization
- shared project workflows for estimates, appointments, invoices, payments, and messages
- PostgreSQL migrations for:
  - users
  - sessions
  - organizations
  - organization memberships
  - properties
  - work requests
  - attachments
  - projects
  - activity events

## Run

```bash
cd app
go run ./cmd/server
```

## Environment

- `APP_ADDR`
- `APP_ENV`
- `APP_PUBLIC_URL`
- `APP_WEB_URL`
- `APP_DATABASE_URL`
- `APP_STORE_BACKEND`
- `APP_AUTO_MIGRATE`
- `APP_MIGRATIONS_DIR`
- `APP_UPLOAD_DIR`
- `APP_ALLOWED_ORIGINS`

PostgreSQL is the standard persistent store. The in-memory store must be selected explicitly and is rejected in production. `APP_UPLOAD_DIR` must point to durable private storage in production; uploaded files are never served as public static assets.

## Postgres dev flow

```bash
cd /path/to/Mycasapro
make run-db
make run-app
```

The example environment file is `app/.env.example`.

## Endpoints

- `GET /healthz`
- `GET /api/v1/meta`
- `GET /api/v1/homeowners/{homeownerID}/dashboard`
- `GET /api/v1/homeowners/{homeownerID}/properties`
- `POST /api/v1/homeowners/{homeownerID}/properties`
- `GET /api/v1/homeowners/{homeownerID}/work-requests`
- `POST /api/v1/homeowners/{homeownerID}/work-requests`
- `GET|POST /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/attachments`
- `GET /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/attachments/{attachmentID}`
- `GET|POST /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/invites`
- `POST /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/invites/{inviteID}/revoke`
- `GET /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/guest-estimates`
- `GET /api/v1/invites/{token}`
- `POST /api/v1/invites/{token}/estimates`
- `GET /api/v1/invites/{token}/attachments/{attachmentID}`
- `GET /api/v1/contractors/{contractorID}/dashboard`
- `GET /api/v1/contractors/{contractorID}/work-requests/{workRequestID}/attachments/{attachmentID}`
- `GET /api/v1/contractors/{contractorID}/organizations`
- `POST /api/v1/contractors/{contractorID}/organizations`
- `POST /api/v1/contractors/{contractorID}/organizations/{organizationID}/projects`

Attachment uploads accept up to five files per repair request. Supported formats are JPEG, PNG, WebP, HEIC, and PDF, with a 10 MB limit per file. File bytes are stored under opaque keys with private permissions; access always passes through an authenticated API route.

Invitation tokens contain 256 bits of randomness. Only their SHA-256 hashes are stored. Public invitation responses omit the street address and homeowner identifiers, attachment access remains token-scoped, request logs redact tokens, and links expire after seven days unless revoked earlier.
