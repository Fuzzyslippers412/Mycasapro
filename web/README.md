# Web

Next.js frontend for the MyCasaPro homeowner and contractor experiences.

## Run

```bash
cd web
npm ci
npm run dev
```

Set `NEXT_PUBLIC_APP_URL` when the API is not available at `http://localhost:8081`.

Account identity comes from the secure backend session. The frontend does not accept demo user IDs or seed fake dashboard records.
