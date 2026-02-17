from fastapi import Request, HTTPException
import time
from collections import defaultdict

# Simple in-memory rate limiter (per IP+path)
WINDOW = 60
LIMITS = {
    "/api/auth/login": 20,
    "/api/auth/register": 10,
    "/api/auth/forgot-password": 8,
    "/api/auth/reset-password": 8,
    "/api/agents": 60,
    "/api/finance/spend/upload": 10,
}

_hits = defaultdict(list)

async def rate_limit(request: Request):
    path = request.url.path
    # apply to prefixes
    limit = None
    for prefix, lim in LIMITS.items():
        if path.startswith(prefix):
            limit = lim
            break
    if not limit:
        return
    key = f"{request.client.host}:{prefix}"
    now = time.time()
    window_start = now - WINDOW
    _hits[key] = [t for t in _hits[key] if t > window_start]
    if len(_hits[key]) >= limit:
        raise HTTPException(status_code=429, detail={"error": {"code": "RATE_LIMIT", "message": "Too many requests"}})
    _hits[key].append(now)
