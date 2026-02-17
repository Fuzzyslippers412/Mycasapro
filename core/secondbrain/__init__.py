"""
SecondBrain - Obsidian-Compatible Agent Memory System
=====================================================

Provides guarded write access to the vault for all MyCasa Pro agents.
Agents NEVER write files directly - only through this skill.

Usage:
    from core.secondbrain import SecondBrain
    
    sb = SecondBrain(tenant_id="tenkiang_household")
    
    # Write a note
    note_id = await sb.write_note(
        type="decision",
        title="Approve Roof Repair",
        body="Approved Juan's quote...",
        agent="finance",
        entities=["ent_contractor_juan"]
    )
    
    # Append to existing note
    await sb.append(note_id, "## Update\nWork completed.")
    
    # Search
    results = await sb.search("roof repair", scope=["decisions"])
"""

from .skill import SecondBrain
from .models import (
    NoteType, NotePayload, NoteMetadata,
    AgentType, SourceType, Confidence,
    SearchResult, GraphNode, GraphEdge, GraphResult
)
from .exceptions import (
    SecondBrainError, ValidationError, PermissionError, NoteNotFoundError, IndexError
)
from .para import (
    PARAKnowledgeGraph, PARAEntity, PARACategory,
    Fact, FactStatus, Relationship, EntityMetadata
)
from .daily_notes import (
    DailyNotesManager, DailyEntry, TacitKnowledge, get_timeline
)
from .heartbeat import (
    MemoryHeartbeat, RecencyTier, schedule_heartbeat
)

__all__ = [
    "SecondBrain",
    "NoteType",
    "NotePayload",
    "NoteMetadata",
    "AgentType",
    "SourceType",
    "Confidence",
    "SearchResult",
    "GraphNode",
    "GraphEdge",
    "GraphResult",
    "SecondBrainError",
    "ValidationError",
    "PermissionError",
    "NoteNotFoundError",
    "IndexError",
    "PARAKnowledgeGraph",
    "PARAEntity",
    "PARACategory",
    "Fact",
    "FactStatus",
    "Relationship",
    "EntityMetadata",
    "DailyNotesManager",
    "DailyEntry",
    "TacitKnowledge",
    "get_timeline",
    "MemoryHeartbeat",
    "RecencyTier",
    "schedule_heartbeat",
]
