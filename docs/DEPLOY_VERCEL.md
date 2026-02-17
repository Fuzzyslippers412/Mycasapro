# Deploy on Vercel (Frontend) + Hosted Backend

MyCasa Pro needs a long-running FastAPI backend for agents, scheduling, and webhooks. Deploy the frontend to Vercel and the backend to a separate host (Railway/Fly/Render/VM).

## Frontend (Vercel)
1) In Vercel, set **Root Directory** to `frontend`
2) Set environment variable:
   - `NEXT_PUBLIC_API_URL=https://YOUR_BACKEND_DOMAIN`
3) Build command:
   - `npm run build`
4) Output directory:
   - `.next`

## Backend (FastAPI host)
Set these environment variables on your backend host:
```
MYCASA_ENVIRONMENT=production
MYCASA_BACKEND_PORT=6709
MYCASA_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
MYCASA_FRONTEND_URL=https://YOUR_VERCEL_DOMAIN
MYCASA_CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN
MYCASA_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB
MYCASA_SECRET_KEY=your-strong-secret
```

Run:
```
pip install -r requirements.txt
python install.py install
python -m uvicorn api.main:app --host 0.0.0.0 --port 6709
```

## Notes
- SQLite is fine for local installs. For production (multi-user), use Postgres.
- Ensure your backend host allows outbound HTTPS for LLM providers.
