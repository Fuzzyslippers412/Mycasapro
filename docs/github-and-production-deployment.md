# GitHub and Production Deployment

## Repository cutover

The homeowner and contractor rebuild is published at `https://github.com/Fuzzyslippers412/Mycasapro`.

The repository's previous application is preserved in the remote branch `archive/pre-home-rebuild-2026-07-28`.

## Hosting boundary

GitHub Pages is static hosting. It cannot operate the authenticated MyCasaPro application because the product requires:

- a Next.js runtime for dynamic routes
- the Go API
- PostgreSQL
- durable private attachment storage
- secure environment variables and HTTP-only cookies

Use GitHub for source control and CI. `infra/production/` now provides the first public deployment topology: Caddy terminates HTTPS on one hostname and routes to isolated web and API containers, PostgreSQL remains unexposed, and private uploads live in a durable Docker volume. The API writes contractor email invitations to a PostgreSQL outbox and retries SMTP delivery asynchronously.

This topology is intentionally operable on one Linux server. It is not horizontally scalable or highly available. Move PostgreSQL to a managed service and attachments to a private object bucket before adding multiple API replicas or treating the server as failure-independent storage.

## Required production checks before DNS cutover

- production-mode cookie, same-origin, and CORS verification
- database migrations through `000009_email_outbox`
- private attachment authorization tests
- invitation-token log redaction verification
- off-server backup and restore rehearsal
- SPF, DKIM, and DMARC alignment for the invitation sender domain
- external health, disk, error-rate, certificate, and backup-age alerts
- release-pinned rollback rehearsal
- full homeowner email invitation to guest estimate smoke test against the deployed domain
