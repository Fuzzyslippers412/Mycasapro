"""
MyCasa Pro Backend API
RESTful API + WebSocket for real-time updates

Endpoints:
- /status (quick)
- /status/full (full system report)
- /tasks (list + create)
- /events (WebSocket stream)
- /portfolio (ingest + view)
- /security (posture + incidents)

All data flows through Galidima (Manager) as single source of truth.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime
import math
import re
import time
from pathlib import Path
import asyncio
import json
import sys
from dotenv import load_dotenv
import os
import httpx

# Load environment variables from .env file for API key
load_dotenv()

# Add parent to path for agent imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import configuration system
from core.config import get_config

from agents.manager import ManagerAgent
from agents.janitor import JanitorAgent
from agents.security_manager import SecurityManagerAgent
from agents.mail_skill import MailSkillAgent
from agents.scheduler import get_scheduler, ScheduleFrequency
from agents.heartbeat_checker import HouseholdHeartbeatChecker
from core.system_state import get_state_manager
from api.routes.secondbrain import router as secondbrain_router
from api.routes.settings import router as settings_router
from api.routes.llm_auth import router as llm_auth_router
from api.routes.auth import router as auth_router
from api.routes.admin import router as admin_router
from api.routes.audit import router as audit_router
from api.routes.approvals import router as approvals_router
from api.routes.backup import router as backup_router
from api.middleware.errors import setup_error_handlers
from api.routes.agent_context import router as agent_context_router

from starlette.types import ASGIApp, Receive, Send, Scope

from auth.middleware import AuthMiddleware
from auth.dependencies import require_auth
import uuid


class RequestIDMiddleware:
    """Add X-Request-Id header to all responses.

    Pure ASGI middleware implementation to avoid anyio compatibility issues.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get request ID from headers or generate one
        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode("utf-8", errors="ignore")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in scope state for potential use by other middleware/handlers
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add X-Request-Id header to response
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)




# Event queue for real-time updates
class EventBroker:
    """Enhanced event broker for WebSocket clients with agent-specific support"""

    def __init__(self):
        self.clients: List[WebSocket] = []
        self._event_queue: Optional[asyncio.Queue] = None
        # Track which agents each client is interested in
        self.client_interests: Dict[WebSocket, set] = {}

    @property
    def event_queue(self) -> asyncio.Queue:
        """Lazy initialization of asyncio.Queue - only create when event loop is running"""
        if self._event_queue is None:
            self._event_queue = asyncio.Queue()
        return self._event_queue
    
    async def connect(self, websocket: WebSocket):
        # Avoid handshake timeout bug in websockets 12 + Python 3.14 by
        # accepting immediately and not using open_timeout logic.
        await websocket.accept()
        self.clients.append(websocket)
        self.client_interests[websocket] = set()  # Initially interested in all events
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)
        if websocket in self.client_interests:
            del self.client_interests[websocket]
    
    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast event to all connected clients"""
        await self._send_to_interested_clients(event, interested_agents=None)
    
    async def broadcast_to_agent(self, agent_id: str, event: Dict[str, Any]):
        """Broadcast event to clients interested in a specific agent"""
        await self._send_to_interested_clients(event, interested_agents={agent_id})
    
    async def _send_to_interested_clients(self, event: Dict[str, Any], interested_agents: Optional[set] = None):
        """Send event to clients based on their interests"""
        message = json.dumps(event, default=str)
        disconnected = []
        
        for client in self.clients:
            # Check if client is interested in this agent
            client_interests = self.client_interests.get(client, set())
            
            # If interested_agents is specified, only send to clients interested in those agents
            # If interested_agents is None, send to all clients
            should_send = interested_agents is None or \
                         len(interested_agents) == 0 or \
                         len(client_interests) == 0 or \
                         any(agent in client_interests for agent in interested_agents)
            
            if should_send:
                try:
                    await client.send_text(message)
                except Exception:
                    disconnected.append(client)
        
        for client in disconnected:
            self.disconnect(client)
    
    async def register_client_interest(self, websocket: WebSocket, agent_ids: List[str]):
        """Register that a client is interested in specific agents"""
        if websocket in self.client_interests:
            self.client_interests[websocket] = set(agent_ids)
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to the broker"""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        await self.broadcast(event)
    
    async def emit_agent_activity(self, agent_id: str, activity_data: Dict[str, Any]):
        """Emit agent activity event to interested clients"""
        event = {
            "type": "agent_activity",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": activity_data
        }
        await self.broadcast_to_agent(agent_id, event)


# Global instances
event_broker = EventBroker()
WS_ENABLED = False
_manager: Optional[ManagerAgent] = None
_janitor: Optional[JanitorAgent] = None
_security: Optional[SecurityManagerAgent] = None


def get_manager() -> ManagerAgent:
    global _manager
    if _manager is None:
        _manager = ManagerAgent()
    return _manager


def get_janitor() -> JanitorAgent:
    global _janitor
    if _janitor is None:
        _janitor = JanitorAgent()
    return _janitor


def get_security() -> SecurityManagerAgent:
    global _security
    if _security is None:
        _security = SecurityManagerAgent()
    return _security


_mail_skill: Optional[MailSkillAgent] = None

def get_mail_skill() -> MailSkillAgent:
    global _mail_skill
    if _mail_skill is None:
        _mail_skill = MailSkillAgent()
    return _mail_skill


def _ensure_scheduler_job(scheduler, name: str, **kwargs):
    if any(job.name == name for job in scheduler.jobs.values()):
        return
    scheduler.create_job(name=name, **kwargs)


async def _run_scheduled_agent(agent: str, task: str, config: Optional[Dict[str, Any]] = None):
    config = config or {}
    manager = get_manager()

    if config.get("endpoint"):
        base_url = get_config().API_BASE_URL.rstrip("/")
        url = f"{base_url}{config['endpoint']}"
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(url)
            res.raise_for_status()
            return res.json()

    action = config.get("action") or agent
    if action in {"heartbeat", "household_heartbeat"}:
        checker = HouseholdHeartbeatChecker(manager.tenant_id)
        result = await checker.run_heartbeat()
        return result.to_dict()
    if action == "memory_consolidation":
        checker = HouseholdHeartbeatChecker(manager.tenant_id)
        return await checker.run_memory_consolidation()

    alias_map = {
        "security": "security_manager",
        "backup": "backup_recovery",
        "mail": "mail_skill",
    }
    attr = alias_map.get(agent, agent)
    agent_obj = manager if agent == "manager" else getattr(manager, attr, None)
    if agent_obj and hasattr(agent_obj, "chat"):
        return await agent_obj.chat(task, context={"source": "scheduler"})
    if agent_obj and hasattr(agent_obj, "get_status"):
        return agent_obj.get_status()

    return await manager.chat(task, context={"source": "scheduler"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("[API] Starting MyCasa Pro API...")
    get_manager()  # Initialize manager
    
    # Auto-start lifecycle manager so agents show as active
    from core.lifecycle import get_lifecycle_manager
    lifecycle = get_lifecycle_manager()
    startup_result = lifecycle.startup()
    print(f"[API] Lifecycle started: {startup_result.get('agents_started', [])}")

    # Record lifecycle start in persistent state for UI visibility
    try:
        state_mgr = get_state_manager()
        state_mgr.startup()
    except Exception:
        pass

    # Start scheduler with real agent runner + default heartbeat jobs
    try:
        scheduler = get_scheduler()
        scheduler.agent_runner = _run_scheduled_agent
        _ensure_scheduler_job(
            scheduler,
            name="Household Heartbeat",
            agent="heartbeat",
            task="Run household heartbeat checks and record findings.",
            frequency=ScheduleFrequency.HOURLY,
            description="Proactive checks for inbox, calendar, bills, maintenance, security.",
            minute=5,
        )
        _ensure_scheduler_job(
            scheduler,
            name="Memory Consolidation",
            agent="heartbeat",
            task="Consolidate recent daily notes into MEMORY.md.",
            frequency=ScheduleFrequency.DAILY,
            description="Append recent daily notes into long-term memory.",
            hour=2,
            minute=15,
            config={"action": "memory_consolidation"},
        )
        scheduler.start()
    except Exception as exc:
        print(f"[API] Scheduler init failed: {exc}")
    
    await event_broker.emit("system", {"status": "api_started"})
    
    yield
    
    # Shutdown
    print("[API] Shutting down MyCasa Pro API...")
    lifecycle.shutdown()
    await event_broker.emit("system", {"status": "api_stopped"})


# Create FastAPI app
app = FastAPI(
    title="MyCasa Pro API",
    description="Backend API for MyCasa Pro Home Operating System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Use configuration system for allowed origins
config = get_config()
cors_kwargs = {
    "allow_origins": config.CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if config.CORS_ORIGIN_REGEX:
    cors_kwargs["allow_origin_regex"] = config.CORS_ORIGIN_REGEX
elif config.CORS_ALLOW_LAN:
    # Allow LAN devices during development without manually listing each IP.
    cors_kwargs["allow_origin_regex"] = r"^https?://(localhost|127\\.0\\.0\\.1|\\d{1,3}(?:\\.\\d{1,3}){3})(?::\\d+)?$"

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Setup standardized error handlers
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)
setup_error_handlers(app)

# Include SecondBrain routes
app.include_router(secondbrain_router, prefix="/api")

# Include Settings routes (with wizard)
app.include_router(settings_router, prefix="/api")
app.include_router(llm_auth_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(backup_router, prefix="/api")

# Messaging routes
from api.routes.messaging import router as messaging_router
app.include_router(messaging_router, prefix="/api")

# Chat routes
from api.routes.chat import router as chat_router
app.include_router(chat_router, prefix="/api")

# System lifecycle routes (startup/shutdown)
from api.routes.system import router as system_router
app.include_router(system_router, prefix="/api")

# Live system status routes
from api.routes.system_live import router as system_live_router
app.include_router(system_live_router, prefix="/api")

# Connector Marketplace routes
from api.routes.connectors import router as connectors_router
app.include_router(connectors_router, prefix="/api")

# Finance routes (portfolio recommendations, etc.)
from api.routes.finance import router as finance_router
app.include_router(finance_router, prefix="/api")

# Inbox routes (replaces inline inbox endpoints)
from api.routes.inbox import router as inbox_router
app.include_router(inbox_router, prefix="/api")

# Tasks routes  
from api.routes.tasks import router as tasks_router
app.include_router(tasks_router, prefix="/api")

# Projects routes
from api.routes.projects import router as projects_router
app.include_router(projects_router, prefix="/api")

# Contractors + jobs routes
from api.routes.contractors import router as contractors_router
app.include_router(contractors_router, prefix="/api")

# Janitor routes (health, audits, costs)
from api.routes.janitor import router as janitor_router
app.include_router(janitor_router, prefix="/api")

# Clawdbot session routes
from api.routes.clawdbot import router as clawdbot_router
app.include_router(clawdbot_router, prefix="/api")

# Telemetry routes
from api.routes.telemetry import router as telemetry_router
app.include_router(telemetry_router, prefix="/api")

# Agent Activity routes (HYPERCONTEXT-style tracking)
from api.routes.agent_activity import router as agent_activity_router
app.include_router(agent_activity_router)

# Scheduler routes (scheduled agent runs)
from api.routes.scheduler import router as scheduler_router
app.include_router(scheduler_router, prefix="/api")

# Google/gog OAuth routes
from api.routes.google import router as google_router
app.include_router(google_router, prefix="/api")

# Clawdbot import routes
from api.routes.clawdbot_import import router as clawdbot_import_router
app.include_router(clawdbot_import_router, prefix="/api")

# Reminders routes (bill & task alerts)
from api.routes.reminders import router as reminders_router
from api.routes.memory import router as memory_router
from api.routes.agent_chat import router as agent_chat_router
from api.routes.para import router as para_router
from api.routes.daily_notes import router as daily_notes_router
from api.routes.heartbeat import router as heartbeat_router
from api.routes.identity import router as identity_router
app.include_router(reminders_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(agent_chat_router, prefix="/api")
app.include_router(para_router, prefix="/api")
app.include_router(daily_notes_router, prefix="/api")
app.include_router(heartbeat_router, prefix="/api")
app.include_router(identity_router, prefix="/api")
app.include_router(agent_context_router, prefix="/api")

# Edge Lab routes (financial prediction system)
from api.routes.edgelab import router as edgelab_router
app.include_router(edgelab_router, prefix="/api")

# Data Management routes (clean slate, clear data)
from api.routes.data_management import router as data_management_router
app.include_router(data_management_router, prefix="/api")

# Fleet Management routes (agent orchestration)
from api.routes.fleet import router as fleet_router
app.include_router(fleet_router, prefix="/api")


# ============ MANAGER CHAT ENDPOINT ============

class ManagerChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    conversation_id: Optional[str] = None


def _extract_llm_error(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    prefix = "LLM_ERROR:"
    if text.startswith(prefix):
        return text[len(prefix):].strip() or "LLM error"
    return None


def _estimate_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _strip_cot_format(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    import re
    final_pattern = re.compile(r"(?:^|\n)\s*(?:\*\*|__)?\s*final answer\s*(?:\*\*|__)?\s*:?\s*", re.IGNORECASE)
    match = final_pattern.search(text)
    if match:
        return text[match.end():].strip()
    cot_patterns = [
        r'^\s*(?:\*\*|__)?\s*Thought\s*(?:\*\*|__)?\s*:?.*$',
        r'^\s*(?:\*\*|__)?\s*Action\s*(?:\*\*|__)?\s*:?.*$',
        r'^\s*(?:\*\*|__)?\s*Observation\s*(?:\*\*|__)?\s*:?.*$',
        r'^\s*(?:\*\*|__)?\s*Final Answer\s*(?:\*\*|__)?\s*:?.*$',
    ]
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if any(re.match(p, line.strip(), re.IGNORECASE) for p in cot_patterns):
            continue
        cleaned_lines.append(line)
    cleaned = '\n'.join(cleaned_lines).strip()
    return cleaned if cleaned else text


@app.post("/manager/chat", tags=["Manager"])
async def manager_chat(
    request: ManagerChatRequest,
    http_request: Request,
    user: dict = Depends(require_auth),
    background_tasks: BackgroundTasks = None,
):
    """
    Chat directly with Galidima (Manager agent).
    This is the main chat endpoint used by the bottom chat widget.
    
    The Manager can:
    - Answer questions directly
    - Delegate to specialist agents (Finance, Maintenance, Security, etc.)
    - Coordinate multi-agent workflows
    """
    try:
        from database import get_db
        from core.chat_store import get_or_create_conversation, add_message, get_history
        manager = get_manager()
        request_id = getattr(http_request.state, "request_id", None)
        with get_db() as db:
            conversation = get_or_create_conversation(
                db, user_id=user["id"], agent_name="manager", conversation_id=request.conversation_id
            )
            conversation_id = conversation.id
            history_messages = get_history(db, conversation_id, limit=20)
            history_payload = [
                {"role": msg.role, "content": msg.content} for msg in history_messages
            ]
            history_tokens_est = sum(_estimate_tokens(msg.content) for msg in history_messages)
            input_tokens_est = history_tokens_est + _estimate_tokens(request.message)
            add_message(db, conversation, "user", request.message)

            # Fast-path: create real maintenance tasks for reminders/tasks
            try:
                maintenance = manager.maintenance or manager.get_agent_by_id("maintenance")
                if maintenance and hasattr(maintenance, "create_task_from_message"):
                    msg_lower = (request.message or "").lower()
                    delete_match = re.search(
                        r"(?:delete|remove|cancel)\s+(?:task|reminder)\s*(?:#|id\s*)?(\d+)",
                        request.message or "",
                        re.IGNORECASE,
                    )
                    if delete_match:
                        try:
                            task_id = int(delete_match.group(1))
                        except Exception:
                            task_id = None
                        if task_id is not None:
                            removed = maintenance.remove_task(task_id)
                            if not removed or removed.get("error"):
                                response = f"Sorry — I couldn’t delete task #{task_id}. {removed.get('error', 'Task not found')}."
                                add_message(db, conversation, "assistant", response)
                                return {
                                    "response": response,
                                    "timestamp": datetime.now().isoformat(),
                                    "agent": "manager",
                                    "agent_name": "Galidima",
                                    "conversation_id": conversation_id,
                                    "input_tokens_est": input_tokens_est,
                                    "output_tokens_est": _estimate_tokens(response),
                                    "latency_ms": 0,
                                    "error": removed.get("error", "Task not found"),
                                }
                            title = (removed.get("task") or {}).get("title") or f"Task #{task_id}"
                            response = f"Task \"{title}\" removed."
                            add_message(db, conversation, "assistant", response)
                            return {
                                "response": response,
                                "timestamp": datetime.now().isoformat(),
                                "agent": "manager",
                                "agent_name": "Galidima",
                                "conversation_id": conversation_id,
                                "input_tokens_est": input_tokens_est,
                                "output_tokens_est": _estimate_tokens(response),
                                "latency_ms": 0,
                                "routed_to": "maintenance",
                            }
                    if re.search(r"(?:delete|remove|cancel)\s+(?:task|reminder)", msg_lower):
                        try:
                            tasks = maintenance.get_pending_tasks()
                        except Exception:
                            tasks = []
                        matches = []
                        for t in tasks:
                            title = (t.get("title") or "").lower()
                            if title and title in msg_lower:
                                matches.append(t)
                        if len(matches) == 1:
                            task_id = matches[0].get("id")
                            removed = maintenance.remove_task(int(task_id))
                            if removed and not removed.get("error"):
                                title = (removed.get("task") or {}).get("title") or matches[0].get("title") or f"Task #{task_id}"
                                response = f"Task \"{title}\" removed."
                                add_message(db, conversation, "assistant", response)
                                return {
                                    "response": response,
                                    "timestamp": datetime.now().isoformat(),
                                    "agent": "manager",
                                    "agent_name": "Galidima",
                                    "conversation_id": conversation_id,
                                    "input_tokens_est": input_tokens_est,
                                    "output_tokens_est": _estimate_tokens(response),
                                    "latency_ms": 0,
                                    "routed_to": "maintenance",
                                }
                        elif len(matches) > 1:
                            response = "Multiple tasks match that description. Please specify the task id."
                            add_message(db, conversation, "assistant", response)
                            return {
                                "response": response,
                                "timestamp": datetime.now().isoformat(),
                                "agent": "manager",
                                "agent_name": "Galidima",
                                "conversation_id": conversation_id,
                                "input_tokens_est": input_tokens_est,
                                "output_tokens_est": _estimate_tokens(response),
                                "latency_ms": 0,
                            }
                        elif "delete" in msg_lower or "remove" in msg_lower or "cancel" in msg_lower:
                            response = "Tell me the task id to delete."
                            add_message(db, conversation, "assistant", response)
                            return {
                                "response": response,
                                "timestamp": datetime.now().isoformat(),
                                "agent": "manager",
                                "agent_name": "Galidima",
                                "conversation_id": conversation_id,
                                "input_tokens_est": input_tokens_est,
                                "output_tokens_est": _estimate_tokens(response),
                                "latency_ms": 0,
                            }
                    intent_keywords = [
                        "remind",
                        "reminder",
                        "add a task",
                        "add task",
                        "schedule",
                        "task reminder",
                        "clean",
                        "fix",
                        "repair",
                        "maintenance",
                    ]
                    is_task_intent = any(k in msg_lower for k in intent_keywords)
                    task_result = maintenance.create_task_from_message(request.message, conversation_id=conversation_id)
                    if task_result:
                        if not task_result.get("success", True):
                            response = f"Sorry — I couldn’t create that task. {task_result.get('error', 'Please try again.')}"
                            add_message(db, conversation, "assistant", response)
                            return {
                                "response": response,
                                "timestamp": datetime.now().isoformat(),
                                "agent": "manager",
                                "agent_name": "Galidima",
                                "conversation_id": conversation_id,
                                "input_tokens_est": input_tokens_est,
                                "output_tokens_est": _estimate_tokens(response),
                                "latency_ms": 0,
                                "task_created": {
                                    "task_id": task_result.get("task_id"),
                                    "title": task_result.get("title"),
                                    "due_date": task_result.get("due_date"),
                                    "scheduled_date": task_result.get("scheduled_date"),
                                },
                                "error": task_result.get("error"),
                            }
                        # Verify task exists before claiming success
                        task_id = task_result.get("task_id")
                        if task_id and hasattr(maintenance, "get_task"):
                            try:
                                verified = maintenance.get_task(int(task_id))
                                if not verified:
                                    response = "I couldn't verify the task in the system. Please try again."
                                    add_message(db, conversation, "assistant", response)
                                    return {
                                        "response": response,
                                        "timestamp": datetime.now().isoformat(),
                                        "agent": "manager",
                                        "agent_name": "Galidima",
                                        "conversation_id": conversation_id,
                                        "input_tokens_est": input_tokens_est,
                                        "output_tokens_est": _estimate_tokens(response),
                                        "latency_ms": 0,
                                        "error": "task_verification_failed",
                                    }
                            except Exception:
                                pass

                        response = (
                            f"Task \"{task_result['title']}\" scheduled for {task_result.get('due_date')}."
                            if task_result.get("due_date")
                            else f"Task \"{task_result['title']}\" added."
                        )
                        add_message(db, conversation, "assistant", response)
                        if background_tasks:
                            background_tasks.add_task(
                                event_broker.emit,
                                "task_created",
                                {"task_id": task_result.get("task_id"), "title": task_result.get("title")}
                            )
                        return {
                            "response": response,
                            "timestamp": datetime.now().isoformat(),
                            "agent": "manager",
                            "agent_name": "Galidima",
                            "conversation_id": conversation_id,
                            "input_tokens_est": input_tokens_est,
                            "output_tokens_est": _estimate_tokens(response),
                            "latency_ms": 0,
                            "task_created": task_result,
                            "routed_to": "maintenance",
                            "delegation_note": "Maintenance queued the task. You can review it in the Maintenance list.",
                        }
                    if is_task_intent and not task_result:
                        response = "I couldn’t parse that into a task. Try: “Add a task to clean the garage by Friday.”"
                        add_message(db, conversation, "assistant", response)
                        return {
                            "response": response,
                            "timestamp": datetime.now().isoformat(),
                            "agent": "manager",
                            "agent_name": "Galidima",
                            "conversation_id": conversation_id,
                            "input_tokens_est": input_tokens_est,
                            "output_tokens_est": _estimate_tokens(response),
                            "latency_ms": 0,
                            "error": "task_parse_failed",
                        }
            except Exception as exc:
                response = f"Sorry — I couldn’t create that task. {str(exc)}"
                add_message(db, conversation, "assistant", response)
                return {
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "agent": "manager",
                    "agent_name": "Galidima",
                    "conversation_id": conversation_id,
                    "input_tokens_est": input_tokens_est,
                    "output_tokens_est": _estimate_tokens(response),
                    "latency_ms": 0,
                    "error": str(exc),
                }
            start_time = time.perf_counter()
            response = await manager.chat(request.message, conversation_history=history_payload)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response = _strip_cot_format(response)
            error_message = _extract_llm_error(response)
            if error_message:
                response = f"Warning: {error_message}"
            add_message(db, conversation, "assistant", response)
        
        return {
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "agent": "manager",
            "agent_name": "Galidima",
            "conversation_id": conversation_id,
            "input_tokens_est": input_tokens_est,
            "output_tokens_est": _estimate_tokens(response),
            "latency_ms": latency_ms,
            "error": error_message,
        }
    except Exception as e:
        return {
            "response": f"I encountered an issue: {str(e)}. Please try again.",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ============ STATUS ENDPOINTS ============

@app.get("/status", tags=["Status"])
async def get_quick_status():
    """
    Quick Status (default)
    Minimal data for dashboard - no heavy computation
    """
    manager = get_manager()
    result = manager.quick_status()

    # Normalize agent status using lifecycle as source of truth
    try:
        from core.lifecycle import get_lifecycle_manager

        lifecycle = get_lifecycle_manager()
        status = lifecycle.get_status()
        agents_enabled = status.get("agents_enabled", {})
        agents_data = status.get("agents", {})

        merged_agents = {}
        existing_agents = result.get("facts", {}).get("agents", {}) if isinstance(result, dict) else {}

        for agent_id, enabled in agents_enabled.items():
            agent_info = agents_data.get(agent_id, {})
            is_running = agent_info.get("running", False)
            state = "running" if is_running else ("idle" if enabled else "offline")
            doing = existing_agents.get(agent_id, {}).get("doing")
            skills = existing_agents.get(agent_id, {}).get("skills")
            if skills is None:
                try:
                    from core.agent_skills import get_agent_skills

                    skills = get_agent_skills(agent_id)
                except Exception:
                    skills = []
            merged_agents[agent_id] = {
                "state": state,
                "doing": doing,
                "skills": skills,
            }

        if isinstance(result, dict):
            result.setdefault("facts", {})
            result["facts"]["agents"] = merged_agents
    except Exception:
        pass

    return result


@app.get("/status/full", tags=["Status"])
async def get_full_status():
    """
    Full System Report
    Complete status with all sections
    """
    manager = get_manager()
    return manager.full_report()


@app.get("/status/audit", tags=["Status"])
async def get_audit_trace(query: Optional[str] = None, action_id: Optional[str] = None):
    """
    Audit Trace
    Traceability for "why" questions
    """
    manager = get_manager()
    return manager.audit_trace(action_id=action_id, query=query)


# ============ TASKS ENDPOINTS ============

@app.get("/tasks", tags=["Tasks"])
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50
):
    """List maintenance tasks"""
    manager = get_manager()
    maintenance = manager.maintenance
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")

    tasks = maintenance.get_tasks_from_db()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]

    return {"tasks": tasks[:limit], "total": len(tasks)}


@app.post("/tasks", tags=["Tasks"])
async def create_task(task: Dict[str, Any], background_tasks: BackgroundTasks):
    """Create a new maintenance task"""
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.create_task(
        title=task.get("title", "New Task"),
        category=task.get("category", "general"),
        priority=task.get("priority", "medium"),
        scheduled_date=task.get("scheduled_date"),
        due_date=task.get("due_date"),
        description=task.get("description", ""),
        conversation_id=task.get("conversation_id"),
    )
    
    # Emit event
    background_tasks.add_task(
        event_broker.emit,
        "task_created",
        {"task_id": (result.get("task") or {}).get("id"), "title": task.get("title")}
    )
    
    return result


@app.patch("/tasks/{task_id}/complete", tags=["Tasks"])
async def complete_task(task_id: int, evidence: Optional[str] = None, background_tasks: BackgroundTasks = None):
    """Mark a task as complete"""
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.complete_task(task_id, evidence=evidence or "Completed via API")
    
    # Emit event
    if background_tasks:
        background_tasks.add_task(
            event_broker.emit,
            "task_completed",
            {"task_id": task_id}
        )

    try:
        if isinstance(result, dict) and result.get("conversation_id"):
            from database import get_db
            from database.models import ChatConversation
            from core.chat_store import add_message

            conversation_id = result.get("conversation_id")
            title = result.get("title") or f"Task #{task_id}"
            with get_db() as db:
                conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
                if conversation:
                    add_message(db, conversation, "assistant", f"✅ {title} marked complete.")
    except Exception:
        pass
    
    return result


@app.delete("/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: int, background_tasks: BackgroundTasks = None):
    """Delete a maintenance task"""
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.remove_task(task_id)
    
    if not result or result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("error", "Task not found"))

    try:
        task_payload = result.get("task") if isinstance(result, dict) else None
        conversation_id = task_payload.get("conversation_id") if isinstance(task_payload, dict) else None
        title = task_payload.get("title") if isinstance(task_payload, dict) else f"Task #{task_id}"
        if conversation_id:
            from database import get_db
            from database.models import ChatConversation
            from core.chat_store import add_message
            with get_db() as db:
                conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
                if conversation:
                    add_message(db, conversation, "assistant", f"🗑️ {title} removed.")
    except Exception:
        pass
    
    if background_tasks:
        background_tasks.add_task(
            event_broker.emit,
            "task_deleted",
            {"task_id": task_id}
        )
    
    return result


# ============ PORTFOLIO ENDPOINTS ============

@app.get("/portfolio", tags=["Portfolio"])
async def get_portfolio():
    """Get portfolio summary (cached)"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    return finance.get_portfolio_summary()


class HoldingRequest(BaseModel):
    ticker: str
    shares: float
    asset_type: str = "Other"


class CashRequest(BaseModel):
    amount: float


@app.post("/portfolio/holdings", tags=["Portfolio"])
async def add_holding(req: HoldingRequest):
    """Add or update a portfolio holding (upsert - no duplicates)"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    if req.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")
    
    if not req.ticker or len(req.ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")
    
    result = finance.add_holding(
        ticker=req.ticker.upper().strip(),
        shares=req.shares,
        asset_type=req.asset_type
    )
    return result


@app.delete("/portfolio/holdings/{ticker}", tags=["Portfolio"])
async def remove_holding(ticker: str):
    """Remove a holding from the portfolio"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    result = finance.remove_holding(ticker.upper().strip())
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Holding not found"))
    
    return result


@app.put("/portfolio/cash", tags=["Portfolio"])
async def update_cash(req: CashRequest):
    """Update cash holdings"""
    from database.models import CashHolding
    from database import get_db
    
    if req.amount < 0:
        raise HTTPException(status_code=400, detail="Cash cannot be negative")
    
    with get_db() as db:
        # Upsert cash holding
        existing = db.query(CashHolding).filter(CashHolding.account_name == "JPM").first()
        if existing:
            existing.amount = req.amount
        else:
            db.add(CashHolding(account_name="JPM", amount=req.amount))
        db.commit()
    
    return {"success": True, "amount": req.amount}


@app.delete("/portfolio/clear", tags=["Portfolio"])
async def clear_portfolio():
    """Clear all portfolio holdings and cash"""
    from database.models import PortfolioHolding, CashHolding
    from database import get_db
    
    with get_db() as db:
        deleted_holdings = db.query(PortfolioHolding).delete()
        deleted_cash = db.query(CashHolding).delete()
        db.commit()
    
    return {"success": True, "deleted_count": deleted_holdings + deleted_cash}


@app.get("/bills", tags=["Finance"])
async def list_bills(include_paid: bool = False):
    """List bills"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    return {"bills": finance.get_bills(include_paid=include_paid)}


@app.patch("/bills/{bill_id}/pay", tags=["Finance"])
async def pay_bill(bill_id: int, background_tasks: BackgroundTasks):
    """Mark a bill as paid"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    result = finance.pay_bill(bill_id)
    
    # Emit event
    background_tasks.add_task(
        event_broker.emit,
        "bill_paid",
        {"bill_id": bill_id}
    )
    
    return result


# ============ SPEND TRACKING ENDPOINTS ============

@app.post("/spend", tags=["Spend Tracking"])
async def add_spend(
    amount: float,
    merchant: Optional[str] = None,
    description: Optional[str] = None,
    funding_source: Optional[str] = None,
    payment_rail: Optional[str] = None,
    category: Optional[str] = None,
    is_internal_transfer: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Add a spend entry with three-layer classification.
    
    - **amount**: Dollar amount (required)
    - **merchant**: Where the money went
    - **funding_source**: Bank account, card, cash (Chase Checking, Chase Freedom, etc.)
    - **payment_rail**: How money moved (direct, apple_cash, zelle, venmo, ach)
    - **category**: Consumption category (dining, groceries, housing, etc.)
    - **is_internal_transfer**: If True, excluded from consumption totals
    """
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    result = finance.add_spend_entry(
        amount=amount,
        merchant=merchant,
        description=description,
        funding_source=funding_source,
        payment_rail=payment_rail,
        consumption_category=category,
        is_internal_transfer=is_internal_transfer
    )
    
    if background_tasks:
        background_tasks.add_task(
            event_broker.emit,
            "spend_added",
            {"amount": amount, "category": category}
        )
    
    return result


@app.get("/spend/summary", tags=["Spend Tracking"])
async def get_spend_summary(days: int = 7):
    """Get spending summary for the last N days"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    return finance.get_spend_summary(days=days)


@app.get("/spend/baseline", tags=["Spend Tracking"])
async def get_baseline_status():
    """Get spending baseline status"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    return finance.get_baseline_status()


@app.post("/spend/baseline/complete", tags=["Spend Tracking"])
async def complete_baseline():
    """Complete baseline week and calculate insights"""
    manager = get_manager()
    finance = manager.finance
    
    if not finance:
        raise HTTPException(status_code=503, detail="Finance agent not available")
    
    return finance.complete_baseline()


# ============ INBOX / MESSAGES ENDPOINTS ============

@app.post("/inbox/ingest", tags=["Inbox"])
async def ingest_messages(background_tasks: BackgroundTasks):
    """
    Fetch and ingest messages from Gmail + WhatsApp.
    Mail Skill Agent handles ingestion, Manager handles routing.
    """
    mail_skill = get_mail_skill()
    result = mail_skill.ingest_all()
    
    if result.get("new_messages", 0) > 0:
        background_tasks.add_task(
            event_broker.emit,
            "messages_ingested",
            {"new": result.get("new_messages")}
        )
    
    return result


@app.get("/inbox/messages", tags=["Inbox"])
async def get_inbox_messages(
    source: Optional[str] = None,
    domain: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50
):
    """
    Get inbox messages with optional filters.
    
    - **source**: gmail, whatsapp
    - **domain**: maintenance, finance, contractors, projects, unknown
    - **unread_only**: Only return unread messages
    """
    mail_skill = get_mail_skill()
    messages = mail_skill.get_inbox_messages(
        source=source,
        domain=domain,
        unread_only=unread_only,
        limit=limit
    )
    return {"messages": messages, "count": len(messages)}


@app.get("/inbox/unread-count", tags=["Inbox"])
async def get_unread_count():
    """Get unread message counts by source"""
    mail_skill = get_mail_skill()
    status = mail_skill.get_status()
    metrics = status.get("metrics", {})
    
    return {
        "total": metrics.get("unread_total", 0),
        "gmail": metrics.get("unread_gmail", 0),
        "whatsapp": metrics.get("unread_whatsapp", 0)
    }


@app.patch("/inbox/messages/{message_id}/read", tags=["Inbox"])
async def mark_message_read(message_id: int):
    """Mark a message as read"""
    mail_skill = get_mail_skill()
    return mail_skill.mark_read(message_id)


@app.patch("/inbox/messages/{message_id}/link", tags=["Inbox"])
async def link_message_to_task(message_id: int, task_id: int):
    """Link a message to a task (1-click linking)"""
    mail_skill = get_mail_skill()
    return mail_skill.link_to_task(message_id, task_id)


@app.patch("/inbox/messages/{message_id}/assign", tags=["Inbox"])
async def assign_message_to_agent(message_id: int, agent: str):
    """Assign a message to an agent"""
    mail_skill = get_mail_skill()
    return mail_skill.assign_to_agent(message_id, agent)


# ============ SECURITY ENDPOINTS ============

@app.get("/security", tags=["Security"])
async def get_security_status():
    """Get security posture (quick)"""
    security = get_security()
    return security.quick_status()


@app.get("/security/full", tags=["Security"])
async def get_security_full():
    """Get full security report"""
    security = get_security()
    return security.full_report()


@app.get("/security/incidents", tags=["Security"])
async def list_incidents(active_only: bool = True):
    """List security incidents"""
    security = get_security()
    incidents = security.get_context("incidents") or {"active": [], "resolved": []}
    
    if active_only:
        return {"incidents": incidents.get("active", [])}
    return incidents


# ============ PERSONAS ENDPOINTS ============

@app.get("/personas", tags=["Personas"])
async def list_personas(include_disabled: bool = False):
    """List all personas"""
    manager = get_manager()
    return {"personas": manager.list_personas(include_disabled=include_disabled)}


@app.get("/personas/{persona_id}", tags=["Personas"])
async def get_persona(persona_id: str):
    """Get persona details"""
    manager = get_manager()
    return manager.get_persona(persona_id)


@app.patch("/personas/{persona_id}/enable", tags=["Personas"])
async def enable_persona(persona_id: str, reason: str = "Enabled via API"):
    """Enable a persona"""
    manager = get_manager()
    return manager.enable_persona(persona_id, reason=reason)


@app.patch("/personas/{persona_id}/disable", tags=["Personas"])
async def disable_persona(persona_id: str, reason: str = "Disabled via API"):
    """Disable a persona"""
    manager = get_manager()
    return manager.disable_persona(persona_id, reason=reason)


# ============ WEBSOCKET EVENTS ============

if WS_ENABLED:
    @app.websocket("/events")
    async def websocket_events(websocket: WebSocket):
        """
        WebSocket endpoint for real-time events
        
        Event types:
        - system: API lifecycle events
        - agent_heartbeat: Agent status updates
        - task_created, task_completed: Task events
        - bill_paid: Finance events
        - incident_created: Security events
        - portfolio_updated: Portfolio changes
        - agent_activity: Agent-specific activity updates
        """
        await event_broker.connect(websocket)
        
        # Send initial status
        manager = get_manager()
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now().isoformat(),
            "data": manager.quick_status()
        })
        
        try:
            while True:
                # Keep connection alive, handle incoming messages
                data = await websocket.receive_text()
                
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                
                # Handle status request
                elif data == "status":
                    await websocket.send_json({
                        "type": "status",
                        "timestamp": datetime.now().isoformat(),
                        "data": manager.quick_status()
                    })
                
                # Handle agent subscription
                elif data.startswith("subscribe:"):
                    agent_ids = data.split(":", 1)[1].split(",")
                    await event_broker.register_client_interest(websocket, agent_ids)
                    await websocket.send_text(f"subscribed:{','.join(agent_ids)}")
                
                # Handle unsubscribe
                elif data == "unsubscribe_all":
                    await event_broker.register_client_interest(websocket, [])
                    await websocket.send_text("unsubscribed_all")
        
        except WebSocketDisconnect:
            event_broker.disconnect(websocket)

# ============ SYSTEM STATE ENDPOINTS ============

@app.get("/system/status", tags=["System"])
async def get_system_status():
    """Get system running state"""
    state_mgr = get_state_manager()
    state = state_mgr.get_state()
    try:
        from core.settings_typed import get_settings_store
        settings_enabled = get_settings_store().get().get_enabled_agents()
        # keep state in sync
        if state.get("agents_enabled") != settings_enabled:
            state["agents_enabled"] = settings_enabled
            state_mgr.save_state(state)
    except Exception:
        settings_enabled = state.get("agents_enabled", {})
    return {
        "running": state.get("running", False),
        "last_shutdown": state.get("last_shutdown"),
        "last_startup": state.get("last_startup"),
        "last_backup": state.get("last_backup"),
        "agents_enabled": settings_enabled,
    }


@app.post("/system/startup", tags=["System"])
async def system_startup(background_tasks: BackgroundTasks):
    """
    Start the system
    - Restores previous state
    - Starts all enabled agents
    - Marks system as running
    """
    from core.lifecycle import get_lifecycle_manager
    
    # Start via lifecycle manager (which handles agent startup)
    lifecycle = get_lifecycle_manager()
    lifecycle_result = lifecycle.startup()
    
    # Also update the state manager for persistence
    state_mgr = get_state_manager()
    state_result = state_mgr.startup()
    
    # Merge results
    result = {
        **state_result,
        "agents_started": lifecycle_result.get("agents_started", []),
        "lifecycle_state": lifecycle_result.get("state", {}),
    }
    
    if result.get("success"):
        background_tasks.add_task(
            event_broker.emit,
            "system",
            {"status": "started", "timestamp": result["timestamp"]}
        )
    
    return result


@app.post("/system/shutdown", tags=["System"])
async def system_shutdown(
    settings: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Graceful system shutdown
    - Saves current state
    - Creates automatic backup
    - Marks system as stopped
    """
    state_mgr = get_state_manager()
    result = state_mgr.shutdown(save_settings=settings)
    
    if result.get("success") and background_tasks:
        background_tasks.add_task(
            event_broker.emit,
            "system",
            {"status": "shutdown", "timestamp": result["timestamp"]}
        )
    
    return result


@app.get("/system/monitor", tags=["System"])
async def system_monitor():
    """Get system monitoring data"""
    from core.lifecycle import get_lifecycle_manager
    
    state_mgr = get_state_manager()
    state = state_mgr.get_state()
    db_stats = state_mgr.get_database_stats()
    
    # Get actual agent status from lifecycle manager
    lifecycle = get_lifecycle_manager()
    lifecycle_status = lifecycle.get_status()
    
    agents_enabled = state.get("agents_enabled", {})
    agents_data = lifecycle_status.get("agents", {})
    agents_running = sum(1 for name, status in agents_data.items() 
                        if status.get("running", False))
    agents_total = len(agents_enabled)
    
    # Build processes array for frontend AgentManager
    processes = []
    for agent_name, enabled in agents_enabled.items():
        agent_status = agents_data.get(agent_name, {})
        is_running = agent_status.get("running", False)
        processes.append({
            "id": agent_name,
            "name": agent_name.replace("-", " ").replace("_", " ").title() + " Agent",
            "state": "running" if is_running else ("idle" if enabled else "stopped"),
            "uptime": 0,
            "memory_mb": 0,
            "cpu_percent": 0,
            "pending_tasks": 0,
            "error_count": 0,
            "last_heartbeat": agent_status.get("last_heartbeat", "never"),
        })
    
    return {
        "running": lifecycle_status.get("running", state.get("running", False)),
        "database": db_stats,
        "agents_enabled": agents_enabled,
        "last_activity": state.get("last_startup") or state.get("last_shutdown"),
        # Add resources structure that frontend expects
        "resources": {
            "agents_active": agents_running,
            "agents_total": agents_total,
        },
        "processes": processes,
    }


# ============ BACKUP ENDPOINTS ============

@app.post("/backup/export", tags=["Backup"])
async def export_backup():
    """Create a backup of the database and state"""
    state_mgr = get_state_manager()
    return state_mgr.create_backup()


@app.get("/backup/list", tags=["Backup"])
async def list_backups():
    """List all available backups"""
    state_mgr = get_state_manager()
    return {"backups": state_mgr.list_backups()}


@app.post("/backup/restore/{backup_name}", tags=["Backup"])
async def restore_backup(backup_name: str):
    """Restore from a specific backup"""
    state_mgr = get_state_manager()
    return state_mgr.restore_backup(backup_name)


# ============ DATABASE ENDPOINTS ============

@app.get("/database/stats", tags=["Database"])
async def get_database_stats():
    """Get database statistics"""
    state_mgr = get_state_manager()
    return state_mgr.get_database_stats()


@app.post("/database/clear", tags=["Database"])
async def clear_database():
    """Clear all data (creates backup first)"""
    from database import get_db
    from database.models import Base
    
    # Create backup first
    state_mgr = get_state_manager()
    backup_result = state_mgr.create_backup()
    
    # Clear tables
    try:
        with get_db() as db:
            # Delete all data but keep tables
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
        
        return {
            "success": True,
            "message": "All data cleared",
            "backup": backup_result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/database/reset", tags=["Database"])
async def reset_database():
    """Reset database to factory defaults (creates backup first)"""
    from database import engine
    from database.models import Base
    
    # Create backup first
    state_mgr = get_state_manager()
    backup_result = state_mgr.create_backup()
    
    try:
        # Drop and recreate all tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        return {
            "success": True,
            "message": "Database reset to factory defaults",
            "backup": backup_result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ INBOX SYNC STATUS ============

@app.get("/inbox/sync-status", tags=["Inbox"])
async def get_inbox_sync_status():
    """Get inbox sync status"""
    state_mgr = get_state_manager()
    state = state_mgr.get_state()
    
    return {
        "enabled": state.get("running", False),
        "last_sync": state.get("settings", {}).get("last_inbox_sync"),
    }


@app.post("/inbox/stop", tags=["Inbox"])
async def stop_inbox_sync():
    """Stop inbox sync"""
    state_mgr = get_state_manager()
    state = state_mgr.get_state()
    state["settings"] = state.get("settings", {})
    state["settings"]["inbox_sync_enabled"] = False
    state_mgr.save_state(state)
    return {"success": True, "message": "Inbox sync stopped"}


# ============ HEALTH CHECK ============

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    state_mgr = get_state_manager()
    state = state_mgr.get_state()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "system_running": state.get("running", False)
    }


# Run with: uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
