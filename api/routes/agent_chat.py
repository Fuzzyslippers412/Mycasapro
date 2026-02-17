"""
Agent Chat API - Route messages to specific agents
===================================================

Each agent is a separate entity that can process messages independently.

Based on LLM research:
- Chain-of-Thought (Wei et al., 2022): Step-by-step reasoning
- ReAct (Yao et al., 2022): Thought → Action → Observation
- RAG (Lewis et al., 2020): Ground in retrieved knowledge
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from threading import Lock

from config.settings import DEFAULT_TENANT_ID
from auth.dependencies import require_auth
from database.connection import get_db
from database.models import ChatConversation, ChatMessage
from core.chat_store import get_or_create_conversation, add_message, get_history
from sqlalchemy.orm import Session
from core.secondbrain import SecondBrain
from core.agent_prompts import get_agent_prompt

router = APIRouter(prefix="/agents", tags=["agents"])

# In-memory conversation history per agent
_agent_conversations: Dict[str, List[Dict[str, Any]]] = {}
_agent_instances: Dict[str, Any] = {}
_manager_instance: Optional[Any] = None
_manager_init_error: Optional[Exception] = None
_agent_cache_lock = Lock()

_AGENT_ALIASES = {
    "security": "security-manager",
    "mamadou": "finance",
    "mail": "mail-skill",
    "backup": "backup-recovery",
}


class AgentMessage(BaseModel):
    message: str
    context: Optional[str] = None
    conversation_id: Optional[str] = None


class AgentResponse(BaseModel):
    """
    Agent response with Chain-of-Thought reasoning trace.
    
    Follows ReAct pattern (Yao et al., 2022):
    - response: The final answer/action
    - thinking: The reasoning trace (Thought → Action → Observation)
    """
    agent_id: str
    response: str
    timestamp: str
    thinking: Optional[str] = None  # ReAct-style reasoning trace
    grounded_in: Optional[int] = None  # Number of RAG memories used
    conversation_id: Optional[str] = None
    error: Optional[str] = None


# Agent prompts are now imported from core.agent_prompts
# Uses Chain-of-Thought and ReAct patterns based on LLM research


def _canonical_agent_id(agent_id: str) -> str:
    key = (agent_id or "").strip().lower()
    return _AGENT_ALIASES.get(key, key)


def _extract_llm_error(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    prefix = "LLM_ERROR:"
    if text.startswith(prefix):
        return text[len(prefix):].strip() or "LLM error"
    return None


def _get_cached_manager():
    global _manager_instance, _manager_init_error
    if _manager_instance is not None:
        return _manager_instance
    if _manager_init_error is not None:
        return None
    with _agent_cache_lock:
        if _manager_instance is not None:
            return _manager_instance
        if _manager_init_error is not None:
            return None
        try:
            # Prefer the global manager from api.main to avoid multiple instances
            try:
                from api.main import get_manager as _get_global_manager
                _manager_instance = _get_global_manager()
                return _manager_instance
            except Exception:
                from backend.agents.manager import ManagerAgent
                _manager_instance = ManagerAgent()
            return _manager_instance
        except Exception as exc:
            _manager_init_error = exc
            return None


def _get_agent_class(agent_id: str):
    from backend.agents.finance import FinanceAgent
    from backend.agents.maintenance import MaintenanceAgent
    from backend.agents.security_manager import SecurityManagerAgent
    from backend.agents.contractors import ContractorsAgent
    from backend.agents.projects import ProjectsAgent
    from backend.agents.janitor import JanitorAgent
    from backend.agents.manager import ManagerAgent
    from agents.mail_skill import MailSkillAgent
    from agents.backup_recovery import BackupRecoveryAgent

    agent_map = {
        "finance": FinanceAgent,
        "maintenance": MaintenanceAgent,
        "security-manager": SecurityManagerAgent,
        "contractors": ContractorsAgent,
        "projects": ProjectsAgent,
        "janitor": JanitorAgent,
        "manager": ManagerAgent,
        "mail-skill": MailSkillAgent,
        "backup-recovery": BackupRecoveryAgent,
    }

    return agent_map.get(agent_id)


def _get_cached_agent(agent_id: str):
    canonical_id = _canonical_agent_id(agent_id)
    with _agent_cache_lock:
        cached = _agent_instances.get(canonical_id)
        if cached is not None:
            return cached

    agent = None
    manager = _get_cached_manager()
    if manager:
        if canonical_id == "manager":
            agent = manager
        elif hasattr(manager, "get_agent_by_id"):
            try:
                agent = manager.get_agent_by_id(canonical_id)
            except Exception:
                agent = None
        else:
            attr_map = {
                "finance": "finance",
                "maintenance": "maintenance",
                "security-manager": "security_manager",
                "contractors": "contractors",
                "projects": "projects",
                "janitor": "janitor",
            }
            attr = attr_map.get(canonical_id)
            if attr and hasattr(manager, attr):
                agent = getattr(manager, attr)

    if agent is None:
        AgentClass = _get_agent_class(canonical_id)
        if AgentClass:
            agent = AgentClass()

    if agent is None:
        return None

    with _agent_cache_lock:
        _agent_instances.setdefault(canonical_id, agent)
    return agent


async def get_agent_response(agent_id: str, message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a response from the actual agent using the configured LLM (Kimi K2.5, Claude, etc.)
    Ensures task/reminder actions are executed before replying.
    """
    agent = _get_cached_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found or not loaded")

    # Action-first: attempt real task creation for maintenance-style intents
    try:
        if hasattr(agent, "create_task_from_message"):
            task_result = agent.create_task_from_message(message)
            if task_result:
                if not task_result.get("success", True):
                    return {
                        "agent_id": agent_id,
                        "response": f"Sorry — I couldn’t create that task. {task_result.get('error', 'Please try again.')}",
                        "timestamp": datetime.now().isoformat(),
                        "grounded_in": 0,
                        "error": task_result.get("error"),
                        "task_created": task_result,
                    }
                due = task_result.get("due_date")
                response_text = (
                    f"Got it. I added the task \"{task_result.get('title', 'Task')}\" due {due}."
                    if due
                    else f"Got it. I added the task \"{task_result.get('title', 'Task')}\"."
                )
                return {
                    "agent_id": agent_id,
                    "response": response_text,
                    "timestamp": datetime.now().isoformat(),
                    "grounded_in": 0,
                    "task_created": task_result,
                }
    except Exception as exc:
        return {
            "agent_id": agent_id,
            "response": f"Sorry — I couldn’t create that task. {str(exc)}",
            "timestamp": datetime.now().isoformat(),
            "grounded_in": 0,
            "error": str(exc),
        }

    response_text = await agent.chat(message)

    return {
        "agent_id": agent_id,
        "response": response_text,
        "timestamp": datetime.now().isoformat(),
        "grounded_in": 0,
    }
    
    response_text = responses.get(agent_id, f"[{agent_id}] Message received: {message[:100]}")
    
    return {
        "response": response_text,
        "thinking": thinking_trace,
        "grounded_in": len(memories),
        "agent_prompt_version": "cot_react_v1"
    }


@router.get("/{agent_id}/status")
async def get_agent_status(
    agent_id: str,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get an agent's current status."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        workspace = sb.get_agent_workspace(agent_id)

        canonical_id = _canonical_agent_id(agent_id)
        conversation = (
            db.query(ChatConversation)
            .filter(ChatConversation.user_id == user["id"], ChatConversation.agent_name == canonical_id)
            .order_by(ChatConversation.updated_at.desc())
            .first()
        )
        message_count = 0
        if conversation:
            message_count = (
                db.query(ChatMessage)
                .filter(ChatMessage.conversation_id == conversation.id)
                .count()
            )
        
        return {
            "agent_id": agent_id,
            "status": "active",
            "has_workspace": bool(workspace.soul),
            "conversation_count": message_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_real_agent(agent_id: str):
    """Get the actual agent instance by ID (cached)."""
    return _get_cached_agent(agent_id)


@router.post("/{agent_id}/chat")
async def chat_with_agent(
    agent_id: str,
    req: AgentMessage,
    http_request: Request,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Send a message to a specific agent and get a response.
    
    Each agent is a real entity with its own:
    - SOUL.md (personality, objectives)
    - MEMORY.md (long-term memory)  
    - Domain expertise
    """
    try:
        canonical_id = _canonical_agent_id(agent_id)
        conversation = get_or_create_conversation(
            db, user_id=user["id"], agent_name=canonical_id, conversation_id=req.conversation_id
        )
        history_messages = get_history(db, conversation.id, limit=50)
        history_payload = [
            {"id": msg.id, "role": msg.role, "content": msg.content} for msg in history_messages
        ]
        add_message(db, conversation, "user", req.message)

        # Get real agent and call its chat method
        agent = _get_real_agent(agent_id)
        grounded_in = 0

        if agent:
            request_id = getattr(http_request.state, "request_id", None)
            response_text = await agent.chat(
                req.message,
                context={"history": history_payload, "request_id": request_id},
            )
            thinking_trace = None  # Real agents handle their own reasoning
        else:
            # Fallback to template responses for unknown agents
            result = await get_agent_response(agent_id, req.message, req.context)
            response_text = result["response"]
            thinking_trace = result.get("thinking")
            grounded_in = result.get("grounded_in", 0)
        
        error_message = _extract_llm_error(response_text)
        if error_message:
            response_text = f"⚠️ {error_message}"

        # Add agent response to history (include thinking for auditability)
        assistant_msg = add_message(db, conversation, "assistant", response_text)
        
        return AgentResponse(
            agent_id=agent_id,
            response=response_text,
            timestamp=assistant_msg.created_at.isoformat(),
            thinking=thinking_trace,  # Include thinking trace in response
            conversation_id=conversation.id,
            error=error_message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/history")
async def get_agent_history(
    agent_id: str,
    limit: int = 20,
    conversation_id: Optional[str] = None,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get conversation history with an agent."""
    canonical_id = _canonical_agent_id(agent_id)
    conversation = get_or_create_conversation(
        db, user_id=user["id"], agent_name=canonical_id, conversation_id=conversation_id
    )
    history = get_history(db, conversation.id, limit=limit)
    return {
        "agent_id": agent_id,
        "conversation_id": conversation.id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }
            for msg in history
        ],
        "total": len(history),
    }


@router.delete("/{agent_id}/history")
async def clear_agent_history(
    agent_id: str,
    conversation_id: Optional[str] = None,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Clear conversation history with an agent for the current user."""
    canonical_id = _canonical_agent_id(agent_id)
    query = db.query(ChatConversation).filter(
        ChatConversation.user_id == user["id"],
        ChatConversation.agent_name == canonical_id,
    )
    if conversation_id:
        query = query.filter(ChatConversation.id == conversation_id)
    conversation = query.order_by(ChatConversation.updated_at.desc()).first()

    cleared = 0
    if conversation:
        cleared = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .delete()
        )
        db.delete(conversation)
        db.commit()

    if agent_id in _agent_conversations:
        _agent_conversations[agent_id] = []

    return {"success": True, "agent_id": agent_id, "cleared": cleared, "conversation_id": conversation.id if conversation else None}


@router.get("/available")
async def list_agents(user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """List available agents (roster)."""
    agents = [
        {"id": "finance", "name": "Finance Manager", "status": "active"},
        {"id": "maintenance", "name": "Maintenance Manager", "status": "active"},
        {"id": "security", "name": "Security Manager", "status": "idle"},
        {"id": "contractors", "name": "Contractors", "status": "active"},
        {"id": "projects", "name": "Projects Manager", "status": "idle"},
        {"id": "reminders", "name": "Reminders", "status": "active"},
        {"id": "janitor", "name": "Janitor", "status": "active"},
    ]
    
    # Add conversation counts
    for agent in agents:
        canonical_id = _canonical_agent_id(agent["id"])
        conversation = (
            db.query(ChatConversation)
            .filter(ChatConversation.user_id == user["id"], ChatConversation.agent_name == canonical_id)
            .order_by(ChatConversation.updated_at.desc())
            .first()
        )
        if conversation:
            agent["message_count"] = (
                db.query(ChatMessage)
                .filter(ChatMessage.conversation_id == conversation.id)
                .count()
            )
        else:
            agent["message_count"] = 0
    
    return {"agents": agents}
