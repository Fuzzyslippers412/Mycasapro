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
import math
import time
from threading import Lock
import re

from config.settings import DEFAULT_TENANT_ID
from auth.dependencies import require_auth
from database.connection import get_db
from database.models import ChatConversation, ChatMessage, AgentLog, Notification
from core.chat_store import get_or_create_conversation, add_message, get_history
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
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
    task_created: Optional[Dict[str, Any]] = None
    routed_to: Optional[str] = None
    delegation_note: Optional[str] = None
    input_tokens_est: Optional[int] = None
    output_tokens_est: Optional[int] = None
    latency_ms: Optional[int] = None


class AgentLogRequest(BaseModel):
    action: str
    details: Optional[str] = None
    status: Optional[str] = "success"


class AgentNotifyRequest(BaseModel):
    message: str
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = "medium"


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None


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


def _estimate_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _extract_task_delete_id(message: str) -> Optional[int]:
    if not message:
        return None
    match = re.search(r"(?:delete|remove|cancel)\s+(?:task|reminder)\s*(?:#|id\s*)?(\d+)", message, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return None
    return None


def _is_task_intent(message: str) -> bool:
    if not message:
        return False
    msg_lower = message.lower()
    keywords = [
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
    return any(k in msg_lower for k in keywords)


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
    from agents.mail_skill import MailSkillAgent
    from agents.backup_recovery import BackupRecoveryAgent

    agent_map = {
        "finance": FinanceAgent,
        "maintenance": MaintenanceAgent,
        "security-manager": SecurityManagerAgent,
        "contractors": ContractorsAgent,
        "projects": ProjectsAgent,
        "janitor": JanitorAgent,
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
        if canonical_id == "manager":
            return None
        AgentClass = _get_agent_class(canonical_id)
        if AgentClass:
            agent = AgentClass()

    if agent is None:
        return None

    with _agent_cache_lock:
        _agent_instances.setdefault(canonical_id, agent)
    return agent


async def get_agent_response(
    agent_id: str,
    message: str,
    context: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a response from the actual agent using the configured LLM (Kimi K2.5, Claude, etc.)
    Ensures task/reminder actions are executed before replying.
    """
    agent = _get_cached_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found or not loaded")
    canonical_id = _canonical_agent_id(agent_id)

    # Action-first: attempt real task creation/deletion, then let the LLM respond.
    task_created = None
    routed_to = None
    delegation_note = None
    action_error = None
    action_results: List[Dict[str, Any]] = []
    try:
        delete_id = _extract_task_delete_id(message)
        if delete_id is not None:
            target_agent = agent
            if not hasattr(target_agent, "remove_task"):
                target_agent = _get_cached_agent("maintenance")
            if not target_agent or not hasattr(target_agent, "remove_task"):
                action_error = "Maintenance agent not available"
                action_results.append({
                    "id": "task-delete",
                    "content": f"delete_task failed: maintenance_unavailable (task_id={delete_id})",
                })
            else:
                result = target_agent.remove_task(delete_id)
                if not result or result.get("error"):
                    action_error = result.get("error", "Task not found")
                    action_results.append({
                        "id": "task-delete",
                        "content": f"delete_task failed: {action_error} (task_id={delete_id})",
                    })
                else:
                    routed_to = "maintenance" if canonical_id == "manager" else canonical_id
                    action_results.append({
                        "id": "task-delete",
                        "content": f"delete_task success (task_id={delete_id})",
                    })
        task_intent = _is_task_intent(message)
        if task_intent and hasattr(agent, "create_task_from_message"):
            task_result = agent.create_task_from_message(message, conversation_id=conversation_id)
            if task_result:
                if not task_result.get("success", True):
                    action_error = task_result.get("error") or "task_create_failed"
                    action_results.append({
                        "id": "task-create",
                        "content": f"task_create failed: {action_error}",
                    })
                else:
                    task_created = task_result
                    routed_to = canonical_id
                    delegation_note = f"{agent.name} queued the task. You can track it in the Maintenance list."
                    action_results.append({
                        "id": "task-create",
                        "content": f"task_create success: {task_result.get('title', 'Task')}",
                    })
        # If not maintenance, route task intents through maintenance when available.
        if task_intent and canonical_id != "maintenance" and not task_created:
            maintenance_agent = _get_cached_agent("maintenance")
            if maintenance_agent and hasattr(maintenance_agent, "create_task_from_message"):
                task_result = maintenance_agent.create_task_from_message(message, conversation_id=conversation_id)
                if task_result:
                    if not task_result.get("success", True):
                        action_error = task_result.get("error") or "task_create_failed"
                        action_results.append({
                            "id": "task-create",
                            "content": f"task_create failed: {action_error}",
                        })
                    else:
                        task_created = task_result
                        routed_to = "maintenance"
                        delegation_note = f"{maintenance_agent.name} queued the task in Maintenance. You can track it in the Maintenance list."
                        action_results.append({
                            "id": "task-create",
                            "content": f"task_create success: {task_result.get('title', 'Task')}",
                        })
    except Exception as exc:
        action_error = str(exc)
        action_results.append({"id": "task-error", "content": f"task_error: {action_error}"})

    response_text = await agent.chat(
        message,
        context={"tool_results": action_results} if action_results else None,
    )

    return {
        "agent_id": agent_id,
        "response": response_text,
        "timestamp": datetime.now().isoformat(),
        "grounded_in": 0,
        "task_created": task_created,
        "routed_to": routed_to,
        "delegation_note": delegation_note,
        "error": action_error,
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
        history_messages = get_history(db, conversation.id, limit=20)
        history_payload = [
            {"id": msg.id, "role": msg.role, "content": msg.content} for msg in history_messages
        ]
        history_tokens_est = sum(_estimate_tokens(msg.content) for msg in history_messages)
        input_tokens_est = history_tokens_est + _estimate_tokens(req.message)
        add_message(db, conversation, "user", req.message)

        # Get real agent and call its chat method
        agent = _get_real_agent(agent_id)
        grounded_in = 0
        task_created = None
        routed_to = None
        delegation_note = None
        action_error = None

        if agent:
            action_results: List[Dict[str, Any]] = []
            task_created = None
            routed_to = None
            delegation_note = None
            action_error = None

            delete_id = _extract_task_delete_id(req.message)
            if delete_id is not None:
                target_agent = agent
                if not hasattr(target_agent, "remove_task"):
                    target_agent = _get_cached_agent("maintenance")
                if not target_agent or not hasattr(target_agent, "remove_task"):
                    action_error = "Maintenance agent not available"
                    action_results.append({
                        "id": "task-delete",
                        "content": f"delete_task failed: maintenance_unavailable (task_id={delete_id})",
                    })
                else:
                    try:
                        result = target_agent.remove_task(delete_id)
                        if not result or result.get("error"):
                            action_error = result.get("error", "Task not found")
                            action_results.append({
                                "id": "task-delete",
                                "content": f"delete_task failed: {action_error} (task_id={delete_id})",
                            })
                        else:
                            routed_to = "maintenance" if canonical_id == "manager" else canonical_id
                            action_results.append({
                                "id": "task-delete",
                                "content": f"delete_task success (task_id={delete_id})",
                            })
                            try:
                                from core.events_v2 import emit_sync, EventType
                                emit_sync(EventType.TASK_DELETED, {"user_id": user.get("id"), "task_id": delete_id})
                            except Exception:
                                pass
                    except Exception as exc:
                        action_error = str(exc)
                        action_results.append({"id": "task-delete", "content": f"delete_task error: {action_error}"})
            elif re.search(r"(?:delete|remove|cancel)\s+(?:task|reminder)", req.message or "", re.IGNORECASE):
                maintenance_agent = _get_cached_agent("maintenance")
                matches = []
                if maintenance_agent and hasattr(maintenance_agent, "get_pending_tasks"):
                    try:
                        tasks = maintenance_agent.get_pending_tasks()
                    except Exception:
                        tasks = []
                    for t in tasks:
                        title = (t.get("title") or "").lower()
                        if title and title in (req.message or "").lower():
                            matches.append({"id": t.get("id"), "title": t.get("title")})
                action_error = "task_id_required"
                action_results.append({
                    "id": "task-delete",
                    "content": f"delete_task requires id; matches={matches}",
                })

            task_intent = _is_task_intent(req.message)
            if task_intent and canonical_id == "manager":
                maintenance_agent = _get_cached_agent("maintenance")
                if maintenance_agent and hasattr(maintenance_agent, "create_task_from_message"):
                    try:
                        task_result = maintenance_agent.create_task_from_message(req.message, conversation_id=conversation.id)
                        if task_result:
                            if not task_result.get("success", True):
                                action_error = task_result.get("error") or "task_create_failed"
                                action_results.append({"id": "task-create", "content": f"task_create failed: {action_error}"})
                            else:
                                task_created = task_result
                                routed_to = "maintenance"
                                delegation_note = f"{maintenance_agent.name} queued the task in Maintenance. You can track it in the Maintenance list."
                                action_results.append({
                                    "id": "task-create",
                                    "content": f"task_create success: {task_result.get('title', 'Task')}",
                                })
                    except Exception as exc:
                        action_error = str(exc)
                        action_results.append({"id": "task-create", "content": f"task_create error: {action_error}"})
            elif task_intent and hasattr(agent, "create_task_from_message"):
                try:
                    task_result = agent.create_task_from_message(req.message, conversation_id=conversation.id)
                    if task_result:
                        if not task_result.get("success", True):
                            action_error = task_result.get("error") or "task_create_failed"
                            action_results.append({"id": "task-create", "content": f"task_create failed: {action_error}"})
                        else:
                            task_created = task_result
                            routed_to = canonical_id
                            delegation_note = f"{agent.name} queued the task. You can track it in the Maintenance list."
                            action_results.append({
                                "id": "task-create",
                                "content": f"task_create success: {task_result.get('title', 'Task')}",
                            })
                except Exception as exc:
                    action_error = str(exc)
                    action_results.append({"id": "task-create", "content": f"task_create error: {action_error}"})
            elif task_intent and canonical_id != "maintenance" and not task_created:
                maintenance_agent = _get_cached_agent("maintenance")
                if maintenance_agent and hasattr(maintenance_agent, "create_task_from_message"):
                    try:
                        task_result = maintenance_agent.create_task_from_message(req.message, conversation_id=conversation.id)
                        if task_result:
                            if not task_result.get("success", True):
                                action_error = task_result.get("error") or "task_create_failed"
                                action_results.append({"id": "task-create", "content": f"task_create failed: {action_error}"})
                            else:
                                task_created = task_result
                                routed_to = "maintenance"
                                delegation_note = f"{maintenance_agent.name} queued the task in Maintenance. You can track it in the Maintenance list."
                                action_results.append({
                                    "id": "task-create",
                                    "content": f"task_create success: {task_result.get('title', 'Task')}",
                                })
                    except Exception as exc:
                        action_error = str(exc)
                        action_results.append({"id": "task-create", "content": f"task_create error: {action_error}"})
            request_id = getattr(http_request.state, "request_id", None)
            start_time = time.perf_counter()
            tool_results = list(action_results)
            if canonical_id in {"manager", "maintenance"}:
                try:
                    maintenance_agent = _get_cached_agent("maintenance")
                    if maintenance_agent and hasattr(maintenance_agent, "get_pending_tasks"):
                        pending_tasks = maintenance_agent.get_pending_tasks()
                        pending_titles = [t.get("title") for t in pending_tasks[:3] if t.get("title")]
                        summary = f"pending_tasks={len(pending_tasks)}; next={', '.join(pending_titles) or 'none'}"
                        tool_results.append({"id": "tasks_snapshot", "content": summary})
                except Exception:
                    pass
            response_text = await agent.chat(
                req.message,
                context={
                    "history": history_payload,
                    "request_id": request_id,
                    "tool_results": tool_results,
                },
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            thinking_trace = None  # Real agents handle their own reasoning
        else:
            # Fallback to template responses for unknown agents
            result = await get_agent_response(
                agent_id,
                req.message,
                req.context,
                req.conversation_id,
            )
            response_text = result["response"]
            thinking_trace = result.get("thinking")
            grounded_in = result.get("grounded_in", 0)
            latency_ms = 0
        
        error_message = _extract_llm_error(response_text)
        if error_message:
            response_text = ""
        else:
            try:
                from core.response_formatting import normalize_agent_response
                response_text = normalize_agent_response(canonical_id, response_text)
            except Exception:
                pass

        # Add agent response to history (include thinking for auditability)
        assistant_msg = None
        if response_text:
            assistant_msg = add_message(db, conversation, "assistant", response_text)
        
        return AgentResponse(
            agent_id=agent_id,
            response=response_text,
            timestamp=assistant_msg.created_at.isoformat() if assistant_msg else datetime.now().isoformat(),
            thinking=thinking_trace,  # Include thinking trace in response
            conversation_id=conversation.id,
            error=error_message or action_error,
            task_created=task_created,
            routed_to=routed_to,
            delegation_note=delegation_note,
            input_tokens_est=input_tokens_est,
            output_tokens_est=_estimate_tokens(response_text),
            latency_ms=latency_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/conversations")
async def list_agent_conversations(
    agent_id: str,
    limit: int = 12,
    include_archived: bool = False,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List recent chat sessions for an agent."""
    canonical_id = _canonical_agent_id(agent_id)
    query = (
        db.query(ChatConversation)
        .filter(ChatConversation.user_id == user["id"], ChatConversation.agent_name == canonical_id)
    )
    if not include_archived:
        query = query.filter(ChatConversation.archived_at.is_(None))
    conversations = (
        query.order_by(ChatConversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for convo in conversations:
        last_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == convo.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        message_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == convo.id)
            .count()
        )
        items.append(
            {
                "id": convo.id,
                "title": convo.title,
                "created_at": convo.created_at.isoformat() if convo.created_at else None,
                "updated_at": convo.updated_at.isoformat() if convo.updated_at else None,
                "archived_at": convo.archived_at.isoformat() if convo.archived_at else None,
                "message_count": message_count,
                "last_message": last_message.content if last_message else None,
            }
        )
    return {"agent_id": agent_id, "conversations": items}


@router.patch("/{agent_id}/conversations/{conversation_id}/archive")
async def archive_agent_conversation(
    agent_id: str,
    conversation_id: str,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Archive a chat session for an agent."""
    canonical_id = _canonical_agent_id(agent_id)
    convo = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user["id"],
            ChatConversation.agent_name == canonical_id,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo.archived_at = datetime.utcnow()
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return {"success": True, "conversation_id": convo.id, "archived_at": convo.archived_at.isoformat()}


@router.patch("/{agent_id}/conversations/{conversation_id}/restore")
async def restore_agent_conversation(
    agent_id: str,
    conversation_id: str,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Restore an archived chat session."""
    canonical_id = _canonical_agent_id(agent_id)
    convo = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user["id"],
            ChatConversation.agent_name == canonical_id,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo.archived_at = None
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return {"success": True, "conversation_id": convo.id, "archived_at": None}

@router.delete("/{agent_id}/conversations/{conversation_id}")
async def delete_agent_conversation(
    agent_id: str,
    conversation_id: str,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a chat session and its messages for an agent."""
    canonical_id = _canonical_agent_id(agent_id)
    convo = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user["id"],
            ChatConversation.agent_name == canonical_id,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    for _ in range(3):
        try:
            db.query(ChatMessage).filter(ChatMessage.conversation_id == convo.id).delete()
            db.delete(convo)
            db.commit()
            break
        except OperationalError as exc:
            db.rollback()
            if "locked" not in str(exc).lower():
                raise
            time.sleep(0.2)

    if agent_id in _agent_conversations:
        _agent_conversations[agent_id] = []

    return {"success": True, "conversation_id": conversation_id}


@router.post("/{agent_id}/conversations")
async def create_agent_conversation(
    agent_id: str,
    payload: ConversationCreateRequest,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new chat session for an agent."""
    canonical_id = _canonical_agent_id(agent_id)
    conversation = ChatConversation(
        user_id=user["id"],
        agent_name=canonical_id,
        title=payload.title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {
        "agent_id": agent_id,
        "conversation_id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
    }


@router.patch("/{agent_id}/conversations/{conversation_id}")
async def update_agent_conversation(
    agent_id: str,
    conversation_id: str,
    payload: ConversationUpdateRequest,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update metadata for a chat session (title)."""
    canonical_id = _canonical_agent_id(agent_id)
    convo = (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user["id"],
            ChatConversation.agent_name == canonical_id,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if payload.title is not None:
        title = payload.title.strip()
        convo.title = title[:200] if title else None
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return {
        "success": True,
        "conversation_id": convo.id,
        "title": convo.title,
        "updated_at": convo.updated_at.isoformat() if convo.updated_at else None,
    }


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
    conversation = None
    if conversation_id:
        conversation = (
            db.query(ChatConversation)
            .filter(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user["id"],
                ChatConversation.agent_name == canonical_id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = (
            db.query(ChatConversation)
            .filter(ChatConversation.user_id == user["id"], ChatConversation.agent_name == canonical_id)
            .order_by(ChatConversation.updated_at.desc())
            .first()
        )
        if not conversation:
            return {
                "agent_id": agent_id,
                "conversation_id": None,
                "messages": [],
                "total": 0,
            }
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
        for _ in range(3):
            try:
                cleared = (
                    db.query(ChatMessage)
                    .filter(ChatMessage.conversation_id == conversation.id)
                    .delete()
                )
                db.delete(conversation)
                db.commit()
                break
            except OperationalError as exc:
                db.rollback()
                if "locked" not in str(exc).lower():
                    raise
                time.sleep(0.2)

    if agent_id in _agent_conversations:
        _agent_conversations[agent_id] = []

    return {"success": True, "agent_id": agent_id, "cleared": cleared, "conversation_id": conversation.id if conversation else None}


@router.get("/{agent_id}/activity")
async def get_agent_activity(
    agent_id: str,
    limit: int = 30,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Return recent activity logs for a specific agent."""
    canonical_id = _canonical_agent_id(agent_id)
    logs = (
        db.query(AgentLog)
        .filter(AgentLog.agent == canonical_id)
        .order_by(AgentLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "agent_id": canonical_id,
        "activity": [
            {
                "timestamp": log.created_at.isoformat(),
                "action": log.action,
                "details": log.details,
            }
            for log in logs
        ],
    }


@router.post("/{agent_id}/log")
async def log_agent_action(
    agent_id: str,
    req: AgentLogRequest,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Write an agent log entry (used by Setup Wizard and system tooling)."""
    canonical_id = _canonical_agent_id(agent_id)
    agent = _get_real_agent(canonical_id)
    status = req.status or "success"
    if agent and hasattr(agent, "log_action"):
        agent.log_action(req.action, req.details, status=status)
    else:
        entry = AgentLog(agent=canonical_id, action=req.action, details=req.details, status=status)
        db.add(entry)
        db.commit()
    return {"success": True}


@router.post("/{agent_id}/notify")
async def notify_agent(
    agent_id: str,
    req: AgentNotifyRequest,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a notification attributed to an agent."""
    canonical_id = _canonical_agent_id(agent_id)
    agent = _get_real_agent(canonical_id)
    title = req.title or "Setup Wizard"
    category = req.category or canonical_id
    priority = req.priority or "medium"
    if agent and hasattr(agent, "create_notification"):
        agent.create_notification(title=title, message=req.message, category=category, priority=priority)
    else:
        db.add(Notification(title=title, message=req.message, category=category, priority=priority))
        db.commit()
    return {"success": True}


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
