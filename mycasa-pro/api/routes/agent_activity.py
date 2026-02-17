"""
MyCasa Pro - Agent Activity API
HYPERCONTEXT-style activity tracking for agents.

Tracks:
- Files touched (read/modified)
- Tools used (with counts)
- Systems accessed
- Decisions made
- Open questions
- Heat map (recency → stale)
- Thread progress
- Context usage
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import uuid

router = APIRouter(prefix="/api/agent-activity", tags=["Agent Activity"])


# ============ SCHEMAS ============

class FileAction(str, Enum):
    READ = "read"
    MODIFIED = "modified"
    CREATED = "created"
    DELETED = "deleted"


class ThreadStatus(str, Enum):
    DONE = "done"          # ✓
    IN_PROGRESS = "in_progress"  # ⏳
    IDEA = "idea"          # 💡
    BLOCKED = "blocked"    # ⛔


class FileTouch(BaseModel):
    """Record of a file being accessed"""
    path: str
    action: FileAction
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_id: str
    correlation_id: Optional[str] = None


class ToolUse(BaseModel):
    """Record of a tool being used"""
    tool: str  # bash, read, write, edit, glob, etc.
    count: int = 1
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None


class SystemAccess(BaseModel):
    """Record of external system access"""
    system: str  # Gmail, WhatsApp, Calendar, Database, etc.
    status: Literal["ok", "error", "pending"]
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Decision(BaseModel):
    """A decision made by an agent"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    resolved: bool = True


class OpenQuestion(BaseModel):
    """An unresolved question"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ThreadItem(BaseModel):
    """A thread/task being worked on"""
    id: str
    name: str
    status: ThreadStatus
    children: List["ThreadItem"] = Field(default_factory=list)


class HeatEntry(BaseModel):
    """Heat map entry showing recency"""
    topic: str
    last_touched: datetime
    activity_score: float  # 0.0 (stale) to 1.0 (hot)
    color: str  # CSS color


class AgentSession(BaseModel):
    """A complete agent working session"""
    session_id: str
    agent_id: str
    started_at: datetime
    
    # Context tracking
    context_used: int = 0  # tokens
    context_limit: int = 200000
    velocity: float = 0.0  # tokens per minute
    runway: int = 0  # estimated remaining tokens
    
    # Activity data
    files_touched: List[FileTouch] = Field(default_factory=list)
    tools_used: Dict[str, int] = Field(default_factory=dict)
    systems_accessed: List[SystemAccess] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    open_questions: List[OpenQuestion] = Field(default_factory=list)
    threads: List[ThreadItem] = Field(default_factory=list)
    heat_map: List[HeatEntry] = Field(default_factory=list)


class RecordActivityRequest(BaseModel):
    """Request to record agent activity"""
    agent_id: str
    session_id: Optional[str] = None
    
    # What happened
    files_touched: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: Dict[str, int] = Field(default_factory=dict)
    systems_accessed: List[Dict[str, Any]] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    
    # Context
    context_used: Optional[int] = None
    correlation_id: Optional[str] = None


class ActivitySummary(BaseModel):
    """Summary response for agent activity"""
    agent_id: str
    session_id: Optional[str]
    period_start: datetime
    period_end: datetime
    
    # Aggregates
    total_files: int
    files_modified: int
    files_read: int
    tool_usage: Dict[str, int]
    systems: Dict[str, str]  # system -> status
    decisions_count: int
    open_questions_count: int
    
    # Detail lists (for display)
    files_touched: List[Dict[str, Any]]
    decisions: List[str]
    questions: List[str]
    threads: List[Dict[str, Any]]
    heat_map: List[Dict[str, Any]]
    
    # Context
    context_percent: float
    runway_tokens: int


# ============ STORAGE ============

# In-memory storage (would be DB in production)
_sessions: Dict[str, AgentSession] = {}
_activity_log: List[Dict[str, Any]] = []
_max_log_size = 10000


def _get_or_create_session(agent_id: str, session_id: Optional[str] = None) -> AgentSession:
    """Get existing session or create new one"""
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    
    # Create new session
    new_id = session_id or f"{agent_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    session = AgentSession(
        session_id=new_id,
        agent_id=agent_id,
        started_at=datetime.now(),
        context_limit=200000,
    )
    _sessions[new_id] = session
    return session


def _get_api_app():
    """Helper to get the main API app instance for WebSocket access"""
    try:
        from main import event_broker
        return event_broker
    except ImportError:
        # Fallback - might be imported from different module
        try:
            from api.main import event_broker
            return event_broker
        except ImportError:
            return None


def _compute_heat_map(session: AgentSession) -> List[HeatEntry]:
    """Compute heat map from activity"""
    topics: Dict[str, datetime] = {}
    
    # Extract topics from files
    for f in session.files_touched:
        # Extract topic from path (simplified)
        parts = f.path.split("/")
        if len(parts) > 1:
            topic = parts[-2] if parts[-1].endswith((".py", ".ts", ".md")) else parts[-1]
            if topic not in topics or f.timestamp > topics[topic]:
                topics[topic] = f.timestamp
    
    # Extract topics from decisions
    for d in session.decisions:
        words = d.text.lower().split()
        for word in words[:3]:  # First 3 words as topic hint
            if len(word) > 4:
                if word not in topics:
                    topics[word] = d.timestamp
    
    # Convert to heat entries
    now = datetime.now()
    entries = []
    
    colors = ["#ff4d4d", "#ff8c42", "#ffb347", "#87ceeb", "#6b7a8a"]
    
    for topic, last_touched in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:8]:
        age_minutes = (now - last_touched).total_seconds() / 60
        score = max(0.0, 1.0 - (age_minutes / 60))  # 1 hour decay
        
        color_idx = min(int((1 - score) * len(colors)), len(colors) - 1)
        
        entries.append(HeatEntry(
            topic=topic,
            last_touched=last_touched,
            activity_score=score,
            color=colors[color_idx],
        ))
    
    return entries


def _compute_velocity(session: AgentSession) -> float:
    """Compute tokens per minute velocity"""
    if session.context_used == 0:
        return 0.0
    
    elapsed = (datetime.now() - session.started_at).total_seconds() / 60
    if elapsed < 1:
        return float(session.context_used)
    
    return session.context_used / elapsed


# ============ ROUTES ============

@router.post("/{agent_id}/activity")
async def record_activity(agent_id: str, request: RecordActivityRequest):
    """Record activity for an agent"""
    session = _get_or_create_session(agent_id, request.session_id)
    now = datetime.now()
    
    # Record files
    for f in request.files_touched:
        touch = FileTouch(
            path=f.get("path", "unknown"),
            action=FileAction(f.get("action", "read")),
            timestamp=now,
            agent_id=agent_id,
            correlation_id=request.correlation_id,
        )
        session.files_touched.append(touch)
    
    # Record tools
    for tool, count in request.tools_used.items():
        session.tools_used[tool] = session.tools_used.get(tool, 0) + count
    
    # Record systems
    for sys in request.systems_accessed:
        access = SystemAccess(
            system=sys.get("system", "unknown"),
            status=sys.get("status", "ok"),
            agent_id=agent_id,
            timestamp=now,
        )
        session.systems_accessed.append(access)
    
    # Record decisions
    for text in request.decisions:
        session.decisions.append(Decision(
            text=text,
            agent_id=agent_id,
            timestamp=now,
        ))
    
    # Record questions
    for text in request.open_questions:
        session.open_questions.append(OpenQuestion(
            text=text,
            agent_id=agent_id,
            timestamp=now,
        ))
    
    # Update context
    if request.context_used:
        session.context_used = request.context_used
        session.velocity = _compute_velocity(session)
        session.runway = max(0, session.context_limit - session.context_used)
    
    # Update heat map
    session.heat_map = _compute_heat_map(session)
    
    # Log activity
    _activity_log.append({
        "agent_id": agent_id,
        "session_id": session.session_id,
        "timestamp": now.isoformat(),
        "files": len(request.files_touched),
        "tools": sum(request.tools_used.values()),
    })
    
    if len(_activity_log) > _max_log_size:
        _activity_log.pop(0)
    
    # Broadcast real-time activity update via WebSocket
    try:
        event_broker = _get_api_app()
        if event_broker:
            # Prepare activity summary for real-time update
            activity_summary = {
                "agent_id": agent_id,
                "session_id": session.session_id,
                "timestamp": now.isoformat(),
                "files_touched_count": len(session.files_touched),
                "tools_used": dict(list(session.tools_used.items())[-5:]),  # Last 5 tools
                "systems_accessed_count": len(session.systems_accessed),
                "decisions_count": len(session.decisions),
                "open_questions_count": len(session.open_questions),
                "context_percent": round(session.context_used / session.context_limit * 100, 1),
                "velocity": session.velocity,
                "recent_files": [f"{ft.action.value}:{ft.path.split('/')[-1]}" for ft in session.files_touched[-3:]],
                "recent_decisions": [d.text[:50] + "..." if len(d.text) > 50 else d.text for d in session.decisions[-3:]]
            }
            
            await event_broker.emit_agent_activity(agent_id, activity_summary)
    except Exception as e:
        # Don't fail the request if WebSocket broadcast fails
        print(f"Warning: Could not broadcast activity update: {e}")
    
    return {
        "success": True,
        "session_id": session.session_id,
        "context_percent": round(session.context_used / session.context_limit * 100, 1),
    }


@router.get("/{agent_id}/activity")
async def get_activity(
    agent_id: str,
    session_id: Optional[str] = None,
    hours: int = 24,
):
    """Get agent activity summary (HYPERCONTEXT format)"""
    since = datetime.now() - timedelta(hours=hours)
    
    # Find session or aggregate all
    if session_id and session_id in _sessions:
        sessions = [_sessions[session_id]]
    else:
        sessions = [s for s in _sessions.values() 
                   if s.agent_id == agent_id and s.started_at >= since]
    
    if not sessions:
        # Return empty structure for no activity
        return ActivitySummary(
            agent_id=agent_id,
            session_id=None,
            period_start=since,
            period_end=datetime.now(),
            total_files=0,
            files_modified=0,
            files_read=0,
            tool_usage={},
            systems={},
            decisions_count=0,
            open_questions_count=0,
            files_touched=[],
            decisions=[],
            questions=[],
            threads=[],
            heat_map=[],
            context_percent=0,
            runway_tokens=200000,
        ).model_dump()
    
    # Aggregate across sessions
    all_files = []
    tool_usage = defaultdict(int)
    systems = {}
    all_decisions = []
    all_questions = []
    total_context = 0
    
    for session in sessions:
        for f in session.files_touched:
            all_files.append({
                "path": f.path,
                "action": f.action.value,
                "timestamp": f.timestamp.isoformat(),
            })
        
        for tool, count in session.tools_used.items():
            tool_usage[tool] += count
        
        for sys in session.systems_accessed:
            systems[sys.system] = sys.status
        
        for d in session.decisions:
            all_decisions.append(d.text)
        
        for q in session.open_questions:
            all_questions.append(q.text)
        
        total_context = max(total_context, session.context_used)
    
    # Count file actions
    files_modified = sum(1 for f in all_files if f["action"] in ["modified", "created"])
    files_read = sum(1 for f in all_files if f["action"] == "read")
    
    # Use most recent session for heat map
    latest_session = max(sessions, key=lambda s: s.started_at)
    heat_map = [
        {
            "topic": h.topic,
            "score": h.activity_score,
            "color": h.color,
        }
        for h in latest_session.heat_map
    ]
    
    # Build thread structure from files (simplified)
    threads = _build_threads_from_files(all_files)
    
    context_limit = 200000
    
    return {
        "agent_id": agent_id,
        "session_id": latest_session.session_id,
        "period_start": since.isoformat(),
        "period_end": datetime.now().isoformat(),
        "total_files": len(set(f["path"] for f in all_files)),
        "files_modified": files_modified,
        "files_read": files_read,
        "tool_usage": dict(tool_usage),
        "systems": systems,
        "decisions_count": len(all_decisions),
        "open_questions_count": len(all_questions),
        "files_touched": all_files[-50:],  # Last 50
        "decisions": all_decisions[-10:],  # Last 10
        "questions": all_questions,
        "threads": threads,
        "heat_map": heat_map,
        "context_percent": round(total_context / context_limit * 100, 1),
        "context_used": total_context,
        "context_limit": context_limit,
        "runway_tokens": context_limit - total_context,
        "velocity": latest_session.velocity,
    }


@router.get("/{agent_id}/sessions")
async def list_sessions(agent_id: str, limit: int = 10):
    """List recent sessions for an agent"""
    agent_sessions = [
        s for s in _sessions.values() 
        if s.agent_id == agent_id
    ]
    agent_sessions.sort(key=lambda s: s.started_at, reverse=True)
    
    return {
        "agent_id": agent_id,
        "sessions": [
            {
                "session_id": s.session_id,
                "started_at": s.started_at.isoformat(),
                "context_percent": round(s.context_used / s.context_limit * 100, 1),
                "files_touched": len(s.files_touched),
                "decisions_made": len(s.decisions),
            }
            for s in agent_sessions[:limit]
        ]
    }


@router.delete("/{agent_id}/sessions/{session_id}")
async def delete_session(agent_id: str, session_id: str):
    """Delete a session"""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"success": True}
    return {"success": False, "error": "Session not found"}


def _build_threads_from_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build thread structure from file activity"""
    # Group by directory
    dirs = defaultdict(list)
    for f in files:
        path = f["path"]
        parts = path.split("/")
        if len(parts) > 1:
            dir_name = parts[-2]
            dirs[dir_name].append(path.split("/")[-1])
    
    threads = []
    for dir_name, files in list(dirs.items())[:5]:
        children = [
            {"name": fname, "status": "done" if any(fname.endswith(ext) for ext in [".py", ".ts"]) else "in_progress"}
            for fname in list(set(files))[:5]
        ]
        threads.append({
            "id": dir_name,
            "name": dir_name.replace("_", " ").title(),
            "status": "done" if all(c["status"] == "done" for c in children) else "in_progress",
            "children": children,
        })
    
    return threads


# ============ HELPER FOR AGENTS ============

def record_agent_activity(
    agent_id: str,
    files: List[Dict[str, str]] = None,
    tools: Dict[str, int] = None,
    systems: List[Dict[str, str]] = None,
    decisions: List[str] = None,
    questions: List[str] = None,
    context_used: int = None,
    correlation_id: str = None,
):
    """
    Helper function for agents to record their activity.
    
    Usage:
        from api.routes.agent_activity import record_agent_activity
        record_agent_activity(
            agent_id="manager",
            files=[{"path": "/src/app.py", "action": "modified"}],
            tools={"read": 3, "write": 1},
            decisions=["Use async for API calls"],
        )
    """
    session = _get_or_create_session(agent_id)
    now = datetime.now()
    
    if files:
        for f in files:
            session.files_touched.append(FileTouch(
                path=f.get("path", "unknown"),
                action=FileAction(f.get("action", "read")),
                timestamp=now,
                agent_id=agent_id,
                correlation_id=correlation_id,
            ))
    
    if tools:
        for tool, count in tools.items():
            session.tools_used[tool] = session.tools_used.get(tool, 0) + count
    
    if systems:
        for sys in systems:
            session.systems_accessed.append(SystemAccess(
                system=sys.get("system", "unknown"),
                status=sys.get("status", "ok"),
                agent_id=agent_id,
                timestamp=now,
            ))
    
    if decisions:
        for text in decisions:
            session.decisions.append(Decision(text=text, agent_id=agent_id, timestamp=now))
    
    if questions:
        for text in questions:
            session.open_questions.append(OpenQuestion(text=text, agent_id=agent_id, timestamp=now))
    
    if context_used:
        session.context_used = context_used
        session.velocity = _compute_velocity(session)
        session.runway = max(0, session.context_limit - session.context_used)
    
    session.heat_map = _compute_heat_map(session)
    
    return session.session_id
