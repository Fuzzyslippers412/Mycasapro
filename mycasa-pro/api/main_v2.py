"""
MyCasa Pro Backend API v2
Clean architecture with separated routes and schemas.

Run with: uvicorn api.main_v2:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import traceback
import uuid
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import routes
from api.routes.system import router as system_router
from api.routes.telemetry import router as telemetry_router
from api.routes.tasks import router as tasks_router
from api.routes.finance import router as finance_router, legacy_router as finance_legacy_router
from api.routes.inbox import router as inbox_router
from api.routes.settings import router as settings_router

# Import core
from core.lifecycle import get_lifecycle_manager
from core.events_v2 import get_event_bus


# ============ LIFESPAN ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    print("[API] Starting MyCasa Pro API v2...")
    
    # Initialize lifecycle manager (loads state)
    lifecycle = get_lifecycle_manager()
    
    # Initialize event bus
    event_bus = get_event_bus()
    
    yield
    
    print("[API] Shutting down MyCasa Pro API v2...")


# ============ APP CREATION ============

app = FastAPI(
    title="MyCasa Pro API",
    description="Backend API for MyCasa Pro Home Operating System",
    version="2.0.0",
    lifespan=lifespan,
)


# ============ MIDDLEWARE ============

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests"""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


# Error handling middleware
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standard error response format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "error_code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler"""
    print(f"[API] Unhandled error: {exc}")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "detail": str(exc) if app.debug else None,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
            "timestamp": datetime.now().isoformat(),
        },
    )


# ============ ROUTES ============

# Include routers
app.include_router(system_router)
app.include_router(telemetry_router)
app.include_router(tasks_router)
app.include_router(finance_router)
app.include_router(finance_legacy_router)  # Legacy routes at /portfolio, /bills, /spend
app.include_router(inbox_router)
app.include_router(settings_router)


# Root endpoint
@app.get("/")
async def root():
    """API info"""
    return {
        "name": "MyCasa Pro API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/system/health",
    }


# Legacy health endpoint (for compatibility)
@app.get("/health")
async def health_check():
    """Legacy health check (redirects to /system/health)"""
    lifecycle = get_lifecycle_manager()
    status = lifecycle.get_status()
    
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "system_running": status.get("running", False),
    }


# ============ LEGACY ROUTE IMPORTS ============
# TODO: Migrate these to separate route files

# For now, import legacy routes from main.py
try:
    from api.main import (
        # Status routes
        get_quick_status, get_full_status, get_audit_trace,
        # Task routes
        list_tasks, create_task, complete_task,
        # Portfolio routes
        get_portfolio, list_bills, pay_bill,
        # Spend routes
        add_spend, get_spend_summary, get_baseline_status, complete_baseline,
        # Inbox routes
        ingest_messages, get_inbox_messages, get_unread_count,
        mark_message_read, link_message_to_task, assign_message_to_agent,
        # Security routes
        get_security_status, get_security_full, list_incidents,
        # Persona routes
        list_personas, get_persona, enable_persona, disable_persona,
        # WebSocket
        websocket_events,
    )
    
    # Re-register legacy routes
    app.get("/status", tags=["Legacy"])(get_quick_status)
    app.get("/status/full", tags=["Legacy"])(get_full_status)
    app.get("/status/audit", tags=["Legacy"])(get_audit_trace)
    
    app.get("/tasks", tags=["Legacy"])(list_tasks)
    app.post("/tasks", tags=["Legacy"])(create_task)
    app.patch("/tasks/{task_id}/complete", tags=["Legacy"])(complete_task)
    
    app.get("/portfolio", tags=["Legacy"])(get_portfolio)
    app.get("/bills", tags=["Legacy"])(list_bills)
    app.patch("/bills/{bill_id}/pay", tags=["Legacy"])(pay_bill)
    
    app.post("/spend", tags=["Legacy"])(add_spend)
    app.get("/spend/summary", tags=["Legacy"])(get_spend_summary)
    app.get("/spend/baseline", tags=["Legacy"])(get_baseline_status)
    app.post("/spend/baseline/complete", tags=["Legacy"])(complete_baseline)
    
    app.post("/inbox/ingest", tags=["Legacy"])(ingest_messages)
    app.get("/inbox/messages", tags=["Legacy"])(get_inbox_messages)
    app.get("/inbox/unread-count", tags=["Legacy"])(get_unread_count)
    app.patch("/inbox/messages/{message_id}/read", tags=["Legacy"])(mark_message_read)
    app.patch("/inbox/messages/{message_id}/link", tags=["Legacy"])(link_message_to_task)
    app.patch("/inbox/messages/{message_id}/assign", tags=["Legacy"])(assign_message_to_agent)
    
    app.get("/security", tags=["Legacy"])(get_security_status)
    app.get("/security/full", tags=["Legacy"])(get_security_full)
    app.get("/security/incidents", tags=["Legacy"])(list_incidents)
    
    app.get("/personas", tags=["Legacy"])(list_personas)
    app.get("/personas/{persona_id}", tags=["Legacy"])(get_persona)
    app.patch("/personas/{persona_id}/enable", tags=["Legacy"])(enable_persona)
    app.patch("/personas/{persona_id}/disable", tags=["Legacy"])(disable_persona)
    
    app.websocket("/events")(websocket_events)
    
    print("[API] Legacy routes imported successfully")
except ImportError as e:
    print(f"[API] Warning: Could not import legacy routes: {e}")
    print("[API] Running with new routes only")


# ============ RUN ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
