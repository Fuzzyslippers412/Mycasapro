"""
MyCasa Pro API - Telemetry Routes
Cost tracking, usage metrics, and system telemetry.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum



router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


# ============ SCHEMAS ============

class TelemetryCategory(str, Enum):
    AI_API = "ai_api"
    CONNECTOR_SYNC = "connector_sync"
    AGENT_TASK = "agent_task"
    DATABASE = "database"
    SYSTEM = "system"


class TelemetryEntry(BaseModel):
    """Single telemetry entry"""
    id: str
    category: TelemetryCategory
    source: str  # Agent or component name
    operation: str  # What was done
    timestamp: datetime
    duration_ms: Optional[int] = None
    
    # Cost tracking
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_estimate: Optional[float] = None
    
    # Status
    status: str = "success"  # success, error
    error: Optional[str] = None
    
    # Correlation
    correlation_id: Optional[str] = None
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecordTelemetryRequest(BaseModel):
    """Request to record telemetry"""
    category: TelemetryCategory
    source: str
    operation: str
    duration_ms: Optional[int] = None
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_estimate: Optional[float] = None
    status: str = "success"
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TelemetrySummary(BaseModel):
    """Summary of telemetry for a period"""
    period_start: datetime
    period_end: datetime
    total_entries: int
    total_cost: float
    total_tokens_in: int
    total_tokens_out: int
    by_category: Dict[str, Dict[str, Any]]
    by_source: Dict[str, Dict[str, Any]]
    by_model: Dict[str, Dict[str, Any]]
    errors: int


# ============ STORAGE (DB + IN-MEMORY FALLBACK) ============

_telemetry_log: List[TelemetryEntry] = []  # Fallback if DB unavailable
_max_entries = 10000
_db_available = False

try:
    _db_available = True
except ImportError:
    print("[Telemetry] Database not available, using in-memory storage")


def _add_entry(entry: TelemetryEntry):
    """Add telemetry entry to log (DB or in-memory)"""
    global _telemetry_log
    
    if _db_available:
        try:
            from database import get_db
            from database.models import TelemetryEvent
            import json
            
            with get_db() as db:
                db_entry = TelemetryEvent(
                    event_id=entry.id,
                    event_type='telemetry',
                    category=entry.category.value,
                    source=entry.source,
                    operation=entry.operation,
                    model=entry.model,
                    tokens_in=entry.tokens_in,
                    tokens_out=entry.tokens_out,
                    cost_estimate=entry.cost_estimate,
                    duration_ms=entry.duration_ms,
                    status=entry.status,
                    error=entry.error,
                    correlation_id=entry.correlation_id,
                    extra_data=json.dumps(entry.metadata) if entry.metadata else None,
                )
                db.add(db_entry)
            return
        except Exception as e:
            print(f"[Telemetry] DB write failed, using memory: {e}")
    
    # Fallback to in-memory
    _telemetry_log.append(entry)
    if len(_telemetry_log) > _max_entries:
        _telemetry_log = _telemetry_log[-_max_entries:]


def _get_entries(
    since: datetime = None,
    category: TelemetryCategory = None,
    source: str = None,
    limit: int = 100,
) -> List[TelemetryEntry]:
    """Query telemetry entries from DB or memory"""
    
    if _db_available:
        try:
            from database import get_db
            from database.models import TelemetryEvent
            
            with get_db() as db:
                query = db.query(TelemetryEvent)
                
                if since:
                    query = query.filter(TelemetryEvent.created_at >= since)
                if category:
                    query = query.filter(TelemetryEvent.category == category.value)
                if source:
                    query = query.filter(TelemetryEvent.source == source)
                
                query = query.order_by(TelemetryEvent.created_at.desc()).limit(limit)
                
                entries = []
                for row in query.all():
                    entries.append(TelemetryEntry(
                        id=row.event_id,
                        category=TelemetryCategory(row.category),
                        source=row.source,
                        operation=row.operation or "",
                        timestamp=row.created_at,
                        duration_ms=row.duration_ms,
                        model=row.model,
                        tokens_in=row.tokens_in,
                        tokens_out=row.tokens_out,
                        cost_estimate=row.cost_estimate,
                        status=row.status or "success",
                        error=row.error,
                        correlation_id=row.correlation_id,
                    ))
                return entries
        except Exception as e:
            print(f"[Telemetry] DB read failed, using memory: {e}")
    
    # Fallback to in-memory
    entries = _telemetry_log.copy()
    
    if since:
        entries = [e for e in entries if e.timestamp >= since]
    if category:
        entries = [e for e in entries if e.category == category]
    if source:
        entries = [e for e in entries if e.source == source]
    
    return entries[-limit:]


def _compute_summary(entries: List[TelemetryEntry]) -> Dict[str, Any]:
    """Compute summary statistics from entries"""
    if not entries:
        return {
            "total_entries": 0,
            "total_cost": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "by_category": {},
            "by_source": {},
            "by_model": {},
            "errors": 0,
        }
    
    total_cost = sum(e.cost_estimate or 0 for e in entries)
    total_tokens_in = sum(e.tokens_in or 0 for e in entries)
    total_tokens_out = sum(e.tokens_out or 0 for e in entries)
    errors = sum(1 for e in entries if e.status == "error")
    
    by_category = {}
    for e in entries:
        cat = e.category.value
        if cat not in by_category:
            by_category[cat] = {"count": 0, "cost": 0, "errors": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["cost"] += e.cost_estimate or 0
        if e.status == "error":
            by_category[cat]["errors"] += 1
    
    by_source = {}
    for e in entries:
        if e.source not in by_source:
            by_source[e.source] = {"count": 0, "cost": 0, "errors": 0}
        by_source[e.source]["count"] += 1
        by_source[e.source]["cost"] += e.cost_estimate or 0
        if e.status == "error":
            by_source[e.source]["errors"] += 1
    
    by_model = {}
    for e in entries:
        if e.model:
            if e.model not in by_model:
                by_model[e.model] = {"count": 0, "cost": 0, "tokens_in": 0, "tokens_out": 0}
            by_model[e.model]["count"] += 1
            by_model[e.model]["cost"] += e.cost_estimate or 0
            by_model[e.model]["tokens_in"] += e.tokens_in or 0
            by_model[e.model]["tokens_out"] += e.tokens_out or 0
    
    return {
        "total_entries": len(entries),
        "total_cost": round(total_cost, 4),
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "by_category": by_category,
        "by_source": by_source,
        "by_model": by_model,
        "errors": errors,
    }


# ============ ROUTES ============

@router.post("/record")
async def record_telemetry(request: RecordTelemetryRequest):
    """Record a telemetry entry"""
    import uuid
    
    entry = TelemetryEntry(
        id=str(uuid.uuid4()),
        category=request.category,
        source=request.source,
        operation=request.operation,
        timestamp=datetime.now(),
        duration_ms=request.duration_ms,
        model=request.model,
        tokens_in=request.tokens_in,
        tokens_out=request.tokens_out,
        cost_estimate=request.cost_estimate,
        status=request.status,
        error=request.error,
        correlation_id=request.correlation_id,
        metadata=request.metadata,
    )
    
    _add_entry(entry)
    
    return {"success": True, "entry_id": entry.id}


@router.get("/entries")
async def get_telemetry_entries(
    since_hours: int = 24,
    category: Optional[TelemetryCategory] = None,
    source: Optional[str] = None,
    limit: int = 100,
):
    """Get telemetry entries"""
    since = datetime.now() - timedelta(hours=since_hours)
    entries = _get_entries(since=since, category=category, source=source, limit=limit)
    
    return {
        "entries": [e.model_dump() for e in entries],
        "count": len(entries),
        "since": since.isoformat(),
    }


@router.get("/summary/today")
async def get_today_summary():
    """Get telemetry summary for today (Finance-readable)"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    entries = _get_entries(since=today_start, limit=10000)
    summary = _compute_summary(entries)
    
    return {
        "period": "today",
        "period_start": today_start.isoformat(),
        "period_end": datetime.now().isoformat(),
        **summary,
    }


@router.get("/summary/week")
async def get_week_summary():
    """Get telemetry summary for the past 7 days"""
    week_start = datetime.now() - timedelta(days=7)
    entries = _get_entries(since=week_start, limit=10000)
    summary = _compute_summary(entries)
    
    return {
        "period": "week",
        "period_start": week_start.isoformat(),
        "period_end": datetime.now().isoformat(),
        **summary,
    }


@router.get("/summary/month")
async def get_month_summary():
    """Get telemetry summary for the past 30 days"""
    month_start = datetime.now() - timedelta(days=30)
    entries = _get_entries(since=month_start, limit=10000)
    summary = _compute_summary(entries)
    
    return {
        "period": "month",
        "period_start": month_start.isoformat(),
        "period_end": datetime.now().isoformat(),
        **summary,
    }


@router.get("/cost/today")
async def get_cost_today():
    """Get cost for today (simple endpoint for Finance agent)"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    entries = _get_entries(since=today_start, limit=10000)
    total_cost = sum(e.cost_estimate or 0 for e in entries)
    
    return {
        "date": today_start.date().isoformat(),
        "cost": round(total_cost, 4),
        "entries": len(entries),
    }


@router.get("/cost/breakdown")
async def get_cost_breakdown(days: int = 7):
    """Get daily cost breakdown"""
    breakdown = []
    
    for i in range(days):
        day_start = (datetime.now() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_entries = [
            e for e in _telemetry_log
            if day_start <= e.timestamp < day_end
        ]
        
        day_cost = sum(e.cost_estimate or 0 for e in day_entries)
        
        breakdown.append({
            "date": day_start.date().isoformat(),
            "cost": round(day_cost, 4),
            "entries": len(day_entries),
        })
    
    return {
        "breakdown": breakdown,
        "total": round(sum(d["cost"] for d in breakdown), 4),
        "days": days,
    }


# ============ HELPER FUNCTION FOR AGENTS ============

def record_cost(
    source: str,
    operation: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_estimate: float,
    correlation_id: str = None,
):
    """
    Helper function for agents to record AI API costs.
    
    Usage:
        from api.routes.telemetry import record_cost
        record_cost(
            source="finance",
            operation="portfolio_analysis",
            model="claude-opus-4",
            tokens_in=1500,
            tokens_out=800,
            cost_estimate=0.05,
        )
    """
    import uuid
    
    entry = TelemetryEntry(
        id=str(uuid.uuid4()),
        category=TelemetryCategory.AI_API,
        source=source,
        operation=operation,
        timestamp=datetime.now(),
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_estimate=cost_estimate,
        correlation_id=correlation_id,
    )
    
    _add_entry(entry)
    return entry.id
