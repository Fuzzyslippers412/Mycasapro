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

Use GitHub for source control and CI. Deploy the web application to a managed Next.js host, deploy the Go service to a container host, use managed PostgreSQL, and store attachments in a private object bucket. `www.mycasapro.com` can then point to the web deployment while `api.mycasapro.com` points to the Go API.

## Required production checks before DNS cutover

- production-mode cookie and CORS verification
- database migrations through `000008_guest_invites`
- private object-storage authorization tests
- invitation-token log redaction verification
- backup and restore test
- email-domain authentication
- health checks and rollback path
- full homeowner invitation to guest estimate smoke test
