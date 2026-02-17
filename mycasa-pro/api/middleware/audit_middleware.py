from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from database import get_db
from database.models import EventLog
from datetime import datetime
import uuid
import json

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Skip audit for health checks and static files
        if request.url.path.endswith(('/health', '/metrics', '.css', '.js')):
            response = await call_next(request)
            return response
            
        # Get user info from request state if available
        user_info = getattr(request.state, 'user', None)
        user_id = user_info.get('id') if user_info else None
        
        # Process request
        response = await call_next(request)
        
        # Log the event
        try:
            with get_db() as db:
                # Capture request body if available
                request_body = None
                try:
                    # Attempt to read body if it hasn't been consumed
                    body_bytes = b""
                    async for chunk in request.stream():
                        body_bytes += chunk
                    if body_bytes:
                        request_body = body_bytes.decode('utf-8')
                except:
                    pass  # Body may have been consumed already
                
                event = EventLog(
                    event_id=request_id,
                    event_type=f"{request.method}_{response.status_code}",
                    source=f"{request.client.host}:{request.client.port}",
                    user_id=user_id,  # Add user ID to audit log
                    details={
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                        "user_agent": request.headers.get("user-agent"),
                        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                        "request_body_preview": str(request_body)[:500] if request_body else None,
                        "ip_address": request.client.host,
                        "user_is_admin": user_info.get('is_admin') if user_info else False
                    }
                )
                db.add(event)
                db.commit()
        except Exception as e:
            # Don't fail the request if audit fails
            print(f"Audit logging failed: {e}")
            
        return response
