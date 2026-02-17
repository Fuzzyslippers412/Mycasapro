from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from database import get_db
from database.models import SessionToken, User
from datetime import datetime
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public routes
        if request.url.path in ["/api/auth/login", "/api/auth/register", "/health"]:
            response = await call_next(request)
            return response
            
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        token_hash = hash_password(token)
        
        with get_db() as db:
            session = db.query(SessionToken).filter(SessionToken.token_hash == token_hash).first()
            if not session or session.expires_at < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Invalid or expired token")
                
            # Mark session as used
            session.last_used_at = datetime.utcnow()
            db.commit()
            
            # Attach user info to request
            request.state.user = {
                "id": session.user_id,
                "is_admin": session.user.is_admin
            }
        
        response = await call_next(request)
        return response
