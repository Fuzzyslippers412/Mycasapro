"""
MyCasa Pro API - Inbox Routes
Unified inbox for Gmail and WhatsApp messages.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from api.helpers.auth import require_auth
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/inbox", tags=["Inbox"])


# ============ SCHEMAS ============

class MessageSource(str, Enum):
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    ALL = "all"


class MessageDomain(str, Enum):
    MAINTENANCE = "maintenance"
    FINANCE = "finance"
    CONTRACTORS = "contractors"
    PROJECTS = "projects"
    UNKNOWN = "unknown"


class MessageStatus(str, Enum):
    NEW = "new"
    READ = "read"
    TRIAGED = "triaged"
    DONE = "done"


class Message(BaseModel):
    id: int
    provider: str  # gmail, whatsapp
    external_id: str  # Provider's message ID for deduplication
    thread_id: Optional[str] = None
    sender: str
    sender_name: Optional[str] = None
    recipients: List[str] = []
    subject: Optional[str] = None
    body: str
    timestamp: datetime
    attachments: List[Dict[str, Any]] = []
    status: MessageStatus = MessageStatus.NEW
    domain: Optional[MessageDomain] = None
    tags: List[str] = []
    linked_task_id: Optional[int] = None
    assigned_agent: Optional[str] = None


class MessageListResponse(BaseModel):
    messages: List[Dict[str, Any]]
    count: int
    has_more: bool = False


class UnreadCountResponse(BaseModel):
    total: int
    gmail: int
    whatsapp: int


class MarkReadRequest(BaseModel):
    message_ids: Optional[List[int]] = None  # If None, mark all as read


class LinkTaskRequest(BaseModel):
    task_id: int


class AssignAgentRequest(BaseModel):
    agent: str  # finance, maintenance, contractors, projects


# ============ ROUTES ============

@router.post("/ingest")
async def ingest_messages(user: dict = Depends(require_auth), background_tasks: BackgroundTasks = None):
    """
    Fetch and ingest new messages from Gmail + WhatsApp.
    Deduplicates based on (provider, external_id).
    """
    from agents.mail_skill import MailSkillAgent
    from core.events_v2 import emit_sync, EventType
    
    mail_skill = MailSkillAgent()
    result = mail_skill.ingest_all()
    
    if result.get("new_messages", 0) > 0:
        emit_sync(EventType.MESSAGES_SYNCED, "api.inbox", {
            "new_messages": result.get("new_messages"),
            "gmail": result.get("gmail", 0),
            "whatsapp": result.get("whatsapp", 0),
        })

    # Optional: respond to WhatsApp messages when enabled
    try:
        from core.settings_typed import get_settings_store
        settings = get_settings_store().get()
        if settings.agents.mail.allow_whatsapp_replies:
            if background_tasks is not None:
                background_tasks.add_task(mail_skill.respond_to_whatsapp)
            else:
                await mail_skill.respond_to_whatsapp()
    except Exception:
        pass
    
    return result


@router.get("/messages", response_model=MessageListResponse)
async def get_messages(
    source: Optional[MessageSource] = None,
    domain: Optional[MessageDomain] = None,
    status: Optional[MessageStatus] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """
    Get inbox messages with filters.
    Returns unified, deduplicated, stable ordering (newest first).
    """
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    
    # Convert enum to string for agent call
    source_str = source.value if source and source != MessageSource.ALL else None
    domain_str = domain.value if domain else None
    
    messages = mail_skill.get_inbox_messages(
        source=source_str,
        domain=domain_str,
        unread_only=unread_only or (status == MessageStatus.NEW),
        limit=limit + 1,  # Get one extra to check has_more
    )
    
    # Apply offset
    messages = messages[offset:]
    
    # Check if there are more
    has_more = len(messages) > limit
    messages = messages[:limit]
    
    return MessageListResponse(
        messages=messages,
        count=len(messages),
        has_more=has_more,
    )


@router.get("/messages/{message_id}")
async def get_message(message_id: int):
    """Get a specific message by ID"""
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    messages = mail_skill.get_inbox_messages(limit=1000)  # Get all to find by ID
    
    for msg in messages:
        if msg.get("id") == message_id:
            return msg
    
    raise HTTPException(status_code=404, detail=f"Message {message_id} not found")


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count():
    """Get unread message counts by source"""
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    status = mail_skill.get_status()
    metrics = status.get("metrics", {})
    
    return UnreadCountResponse(
        total=metrics.get("unread_total", 0),
        gmail=metrics.get("unread_gmail", 0),
        whatsapp=metrics.get("unread_whatsapp", 0),
    )


@router.patch("/messages/{message_id}/read")
async def mark_message_read(message_id: int, user: dict = Depends(require_auth)):
    """Mark a single message as read"""
    from agents.mail_skill import MailSkillAgent
    from core.events_v2 import emit_sync, EventType
    
    mail_skill = MailSkillAgent()
    result = mail_skill.mark_read(message_id)
    
    emit_sync(EventType.MESSAGE_TRIAGED, "api.inbox", {
        "message_id": message_id,
        "action": "mark_read",
    })
    
    return result


@router.post("/messages/mark-read")
async def mark_messages_read(request: MarkReadRequest):
    """Mark multiple messages as read (or all if message_ids is None)"""
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    
    if request.message_ids:
        results = []
        for msg_id in request.message_ids:
            results.append(mail_skill.mark_read(msg_id))
        return {"marked": len(request.message_ids), "results": results}
    else:
        # Mark all as read
        return mail_skill.mark_all_read() if hasattr(mail_skill, 'mark_all_read') else {"message": "Not implemented"}


@router.post("/clear")
async def clear_messages(source: Optional[MessageSource] = None, user: dict = Depends(require_auth)):
    """Clear inbox messages, optionally filtered by source."""
    from database import get_db
    from database.models import InboxMessage

    with get_db() as db:
        query = db.query(InboxMessage)
        if source and source != MessageSource.ALL:
            query = query.filter(InboxMessage.source == source.value)
        count = query.delete(synchronize_session=False)
        db.commit()

    label = source.value if source and source != MessageSource.ALL else "all"
    return {
        "success": True,
        "cleared_count": count,
        "message": f"Cleared {count} {label} message(s)",
    }


@router.patch("/messages/{message_id}/link")
async def link_message_to_task(message_id: int, request: LinkTaskRequest, user: dict = Depends(require_auth)):
    """Link a message to a task (1-click linking)"""
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    return mail_skill.link_to_task(message_id, request.task_id)


@router.patch("/messages/{message_id}/assign")
async def assign_message_to_agent(message_id: int, request: AssignAgentRequest, user: dict = Depends(require_auth)):
    """Assign a message to an agent for handling"""
    from agents.mail_skill import MailSkillAgent
    
    valid_agents = ["finance", "maintenance", "contractors", "projects"]
    if request.agent not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent. Must be one of: {valid_agents}"
        )
    
    mail_skill = MailSkillAgent()
    return mail_skill.assign_to_agent(message_id, request.agent)


@router.get("/sync-status")
async def get_sync_status():
    """Get inbox sync status"""
    from core.lifecycle import get_lifecycle_manager
    
    lifecycle = get_lifecycle_manager()
    status = lifecycle.get_status()
    
    return {
        "enabled": status.get("running", False),
        "last_sync": None,  # TODO: Track last sync time
    }


@router.post("/launch")
async def launch_inbox_sync():
    """Launch inbox sync (one-time pull)"""
    return await ingest_messages(None)


@router.post("/stop")
async def stop_inbox_sync():
    """Stop continuous inbox sync"""
    return {"success": True, "message": "Inbox sync stopped"}


# ============ SEARCH ============

@router.get("/search")
async def search_messages(
    q: str,
    source: Optional[MessageSource] = None,
    limit: int = 20,
):
    """Search messages by query string"""
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    
    # Get all messages and filter (simple implementation)
    # In production, this should use full-text search in DB
    source_str = source.value if source and source != MessageSource.ALL else None
    all_messages = mail_skill.get_inbox_messages(source=source_str, limit=500)
    
    q_lower = q.lower()
    results = []
    
    for msg in all_messages:
        # Search in subject, body, sender
        searchable = " ".join([
            msg.get("subject", ""),
            msg.get("body", ""),
            msg.get("sender", ""),
            msg.get("sender_name", ""),
        ]).lower()
        
        if q_lower in searchable:
            results.append(msg)
            if len(results) >= limit:
                break
    
    return {
        "query": q,
        "results": results,
        "count": len(results),
    }


# ============ STATS ============

@router.get("/stats")
async def get_inbox_stats():
    """Get inbox statistics"""
    from agents.mail_skill import MailSkillAgent
    
    mail_skill = MailSkillAgent()
    status = mail_skill.get_status()
    
    return {
        "total_messages": status.get("metrics", {}).get("total_messages", 0),
        "unread": status.get("metrics", {}).get("unread_total", 0),
        "by_source": {
            "gmail": status.get("metrics", {}).get("total_gmail", 0),
            "whatsapp": status.get("metrics", {}).get("total_whatsapp", 0),
        },
        "by_domain": status.get("metrics", {}).get("by_domain", {}),
    }
