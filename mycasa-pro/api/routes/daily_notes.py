"""
Daily Notes & Tacit Knowledge API Routes
=========================================

Endpoints for managing daily notes and tacit knowledge.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from pathlib import Path

from core.secondbrain import DailyNotesManager, TacitKnowledge, get_timeline

router = APIRouter(prefix="/daily", tags=["daily-notes"])


# Helper to get memory base path
def get_memory_base() -> Path:
    """Get memory base path"""
    return Path.home() / "clawd" / "apps" / "mycasa-pro" / "memory"


# Request Models
class AddEntryRequest(BaseModel):
    entry_type: str  # "event", "decision", "conversation", "learning"
    content: str
    agent: Optional[str] = None
    tags: Optional[List[str]] = None
    date: Optional[str] = None  # YYYY-MM-DD format


class AddTacitKnowledgeRequest(BaseModel):
    category: str  # "preference", "pattern", "insight", "heuristic"
    content: str
    confidence: float = 0.7
    examples: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class UpdateTacitKnowledgeRequest(BaseModel):
    confidence: Optional[float] = None
    add_examples: Optional[List[str]] = None
    add_tags: Optional[List[str]] = None


# Daily Notes Endpoints

@router.post("/notes/entry")
async def add_daily_entry(
    req: AddEntryRequest,
    scope: str = "global",
    agent_id: Optional[str] = None
):
    """Add an entry to today's daily note"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        note_date = None
        if req.date:
            note_date = date.fromisoformat(req.date)

        note_path = manager.add_entry(
            entry_type=req.entry_type,
            content=req.content,
            agent=req.agent,
            tags=req.tags,
            note_date=note_date,
        )

        return {
            "success": True,
            "note_path": note_path,
            "entry_type": req.entry_type,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{note_date}")
async def get_daily_note(
    note_date: str,
    scope: str = "global",
    agent_id: Optional[str] = None
):
    """Get a specific daily note"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        note_date_obj = date.fromisoformat(note_date)
        content = manager.get_daily_note(note_date_obj)

        if not content:
            raise HTTPException(status_code=404, detail=f"Note not found for date: {note_date}")

        return {
            "date": note_date,
            "content": content,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes")
async def list_daily_notes(
    scope: str = "global",
    agent_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 30
):
    """List daily notes within a date range"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None

        notes = manager.list_daily_notes(
            start_date=start,
            end_date=end,
            limit=limit,
        )

        return {
            "notes": notes,
            "count": len(notes),
            "scope": scope,
            "agent_id": agent_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline_view(
    start_date: str,
    end_date: str,
    scope: str = "global",
    agent_id: Optional[str] = None
):
    """Get timeline of events across daily notes"""
    try:
        memory_base = get_memory_base()

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        timeline = get_timeline(memory_base, start, end, scope, agent_id)

        return {
            "timeline": timeline,
            "start_date": start_date,
            "end_date": end_date,
            "scope": scope,
            "total_days": len(timeline),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Tacit Knowledge Endpoints

@router.post("/tacit")
async def add_tacit(
    req: AddTacitKnowledgeRequest,
    scope: str = "global",
    agent_id: Optional[str] = None
):
    """Add tacit knowledge"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        knowledge_id = manager.add_tacit_knowledge(
            category=req.category,
            content=req.content,
            confidence=req.confidence,
            examples=req.examples,
            tags=req.tags,
        )

        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "category": req.category,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tacit")
async def get_tacit(
    scope: str = "global",
    agent_id: Optional[str] = None,
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    tags: Optional[str] = None  # Comma-separated
):
    """Get tacit knowledge with optional filters"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        tag_list = tags.split(",") if tags else None

        knowledge_list = manager.get_tacit_knowledge(
            category=category,
            min_confidence=min_confidence,
            tags=tag_list,
        )

        return {
            "knowledge": [k.dict() for k in knowledge_list],
            "count": len(knowledge_list),
            "scope": scope,
            "agent_id": agent_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tacit/{knowledge_id}")
async def update_tacit(
    knowledge_id: str,
    req: UpdateTacitKnowledgeRequest,
    scope: str = "global",
    agent_id: Optional[str] = None
):
    """Update tacit knowledge"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        success = manager.update_tacit_knowledge(
            knowledge_id=knowledge_id,
            confidence=req.confidence,
            add_examples=req.add_examples,
            add_tags=req.add_tags,
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Knowledge not found: {knowledge_id}")

        return {
            "success": True,
            "knowledge_id": knowledge_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tacit/decay")
async def decay_tacit(
    scope: str = "global",
    agent_id: Optional[str] = None,
    days_threshold: int = 30,
    decay_factor: float = 0.05
):
    """Decay confidence of stale tacit knowledge"""
    try:
        memory_base = get_memory_base()
        manager = DailyNotesManager(memory_base, scope, agent_id)

        decayed_count = manager.decay_tacit_knowledge(
            days_threshold=days_threshold,
            decay_factor=decay_factor,
        )

        return {
            "success": True,
            "decayed_count": decayed_count,
            "days_threshold": days_threshold,
            "decay_factor": decay_factor,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
