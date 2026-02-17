"""
Memory API Routes - SecondBrain Enhanced Features
=================================================

Endpoints for preferences, patterns, relationships, transcripts, and agent workspaces.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from config.settings import DEFAULT_TENANT_ID
from core.secondbrain import SecondBrain
from core.secondbrain.models import PreferenceCategory, PatternType

router = APIRouter(prefix="/memory", tags=["memory"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class PreferenceRequest(BaseModel):
    key: str
    value: Any
    category: str = "general"
    context: Optional[str] = None
    learned_from: Optional[str] = None
    examples: Optional[List[str]] = None


class PatternRequest(BaseModel):
    name: str
    pattern_type: str
    behavior: str
    trigger: Optional[str] = None
    frequency: Optional[str] = None
    observations: Optional[List[str]] = None


class PersonRequest(BaseModel):
    name: str
    relation: Optional[str] = None
    context: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, str]] = None
    notes: Optional[List[str]] = None


class TranscriptRequest(BaseModel):
    session_id: str
    channel: str
    messages: List[Dict[str, Any]]
    summary: Optional[str] = None
    key_decisions: Optional[List[str]] = None
    action_items: Optional[List[str]] = None


class WorkspaceFileRequest(BaseModel):
    content: str


class RecallRequest(BaseModel):
    query: str
    include_preferences: bool = True
    include_patterns: bool = True
    include_relationships: bool = True
    include_transcripts: bool = False
    limit: int = 5


# ═══════════════════════════════════════════════════════════════════════════════
# PREFERENCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/preferences")
async def learn_preference(req: PreferenceRequest):
    """Learn a new preference."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        note_id = await sb.learn_preference(
            key=req.key,
            value=req.value,
            category=req.category,
            context=req.context,
            learned_from=req.learned_from,
            examples=req.examples,
        )
        return {"success": True, "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_preferences(category: Optional[str] = None):
    """Get all preferences."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        cat = PreferenceCategory(category) if category else None
        prefs = await sb.get_preferences(category=cat)
        return {"preferences": prefs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/patterns")
async def record_pattern(req: PatternRequest):
    """Record a behavioral pattern."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        note_id = await sb.record_pattern(
            name=req.name,
            pattern_type=req.pattern_type,
            behavior=req.behavior,
            trigger=req.trigger,
            frequency=req.frequency,
            observations=req.observations,
        )
        return {"success": True, "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_patterns(pattern_type: Optional[str] = None):
    """Get all patterns."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        pt = PatternType(pattern_type) if pattern_type else None
        patterns = await sb.get_patterns(pattern_type=pt)
        return {"patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/people")
async def remember_person(req: PersonRequest):
    """Remember information about a person."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        note_id = await sb.remember_person(
            name=req.name,
            relation=req.relation,
            context=req.context,
            contact_info=req.contact_info,
            preferences=req.preferences,
            notes=req.notes,
        )
        return {"success": True, "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/people/{name}")
async def get_person(name: str):
    """Get information about a person."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        person = await sb.get_person(name)
        if not person:
            raise HTTPException(status_code=404, detail=f"Person not found: {name}")
        return person
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSCRIPT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/transcripts")
async def save_transcript(req: TranscriptRequest):
    """Save a conversation transcript."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        note_id = await sb.save_transcript(
            session_id=req.session_id,
            channel=req.channel,
            messages=req.messages,
            summary=req.summary,
            key_decisions=req.key_decisions,
            action_items=req.action_items,
        )
        return {"success": True, "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcripts")
async def get_transcripts(channel: Optional[str] = None, limit: int = 10):
    """Get recent transcripts."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        transcripts = await sb.get_recent_transcripts(channel=channel, limit=limit)
        return {"transcripts": transcripts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT WORKSPACE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/agents/{agent_id}/workspace")
async def get_agent_workspace(agent_id: str):
    """Get an agent's workspace files."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        workspace = sb.get_agent_workspace(agent_id)
        return {
            "agent_id": workspace.agent_id,
            "files": workspace.to_files(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}/workspace/{filename}")
async def update_workspace_file(agent_id: str, filename: str, req: WorkspaceFileRequest):
    """Update a workspace file."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        workspace = sb.get_agent_workspace(agent_id)
        
        # Map filename to attribute
        file_map = {
            "SOUL.md": "soul",
            "IDENTITY.md": "identity",
            "TOOLS.md": "tools",
            "MEMORY.md": "memory",
            "HEARTBEAT.md": "heartbeat",
        }
        
        if filename not in file_map:
            raise HTTPException(status_code=400, detail=f"Invalid filename: {filename}")
        
        setattr(workspace, file_map[filename], req.content)
        sb.save_agent_workspace(workspace)
        
        return {"success": True, "filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/init")
async def init_agent_workspace(agent_id: str, name: str, description: str):
    """Initialize a new agent workspace."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        workspace = sb.init_agent_workspace(agent_id, name, description)
        return {
            "success": True,
            "agent_id": workspace.agent_id,
            "files": list(workspace.to_files().keys()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# RECALL ENDPOINT (Check memory before asking)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/recall")
async def recall_memories(req: RecallRequest):
    """
    Recall relevant memories for a query.
    Use this to check memory before asking the user to repeat themselves.
    """
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        results = await sb.recall(
            query=req.query,
            include_preferences=req.include_preferences,
            include_patterns=req.include_patterns,
            include_relationships=req.include_relationships,
            include_transcripts=req.include_transcripts,
            limit=req.limit,
        )
        
        # Add summary
        total = sum(len(v) for v in results.values())
        results["summary"] = {
            "total_results": total,
            "has_memories": total > 0,
        }
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{topic}")
async def has_memory(topic: str):
    """Quick check if we have memory of a topic."""
    try:
        sb = SecondBrain(tenant_id=DEFAULT_TENANT_ID)
        has_it = await sb.has_memory_of(topic)
        return {"topic": topic, "has_memory": has_it}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
