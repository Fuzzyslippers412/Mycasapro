"""
PARA Knowledge Graph API Routes
================================

Endpoints for managing Projects, Areas, Resources, and Archives (PARA).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from core.secondbrain import PARAKnowledgeGraph, PARACategory, Fact, Relationship, EntityMetadata
from config.settings import DEFAULT_TENANT_ID

router = APIRouter(prefix="/para", tags=["para"])


# Request Models
class CreateEntityRequest(BaseModel):
    entity_id: str
    name: str
    category: str  # "projects", "areas", "resources", "archives"
    created_by: str
    tags: Optional[List[str]] = None


class AddFactRequest(BaseModel):
    content: str
    added_by: str
    confidence: float = 0.8
    source: Optional[str] = None
    supersedes: Optional[str] = None


class AddRelationshipRequest(BaseModel):
    target_entity: str
    rel_type: str  # "depends_on", "related_to", "child_of", etc.
    notes: Optional[str] = None


# Helper to get agent workspace path
def get_agent_workspace(agent_id: str) -> Path:
    """Get agent workspace path"""
    memory_base = Path.home() / "clawd" / "apps" / "mycasa-pro" / "memory" / "agents"
    workspace_path = memory_base / agent_id / "workspace"

    if not workspace_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent workspace not found: {agent_id}")

    return workspace_path


# Entity Management Endpoints

@router.post("/agents/{agent_id}/entities")
async def create_entity(agent_id: str, req: CreateEntityRequest):
    """Create a new PARA entity"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        category = PARACategory(req.category)
        entity = kg.create_entity(
            entity_id=req.entity_id,
            name=req.name,
            category=category,
            created_by=req.created_by,
            tags=req.tags,
        )

        return {
            "success": True,
            "entity_id": entity.entity_id,
            "category": category.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/entities")
async def list_entities(agent_id: str, category: Optional[str] = None):
    """List all entities in an agent's workspace"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        cat = PARACategory(category) if category else None
        entity_ids = kg.list_entities(cat)

        return {
            "agent_id": agent_id,
            "category": category,
            "entities": entity_ids,
            "count": len(entity_ids),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/entities/{entity_id}")
async def get_entity(agent_id: str, entity_id: str, category: Optional[str] = None):
    """Get entity details"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        # Find entity
        if category:
            entity = kg.get_entity(entity_id, PARACategory(category))
        else:
            entity = kg.find_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Load data
        metadata_dict = entity._read_metadata().dict()
        current_facts = [f.dict() for f in entity.get_current_facts()]
        all_facts = [f.dict() for f in entity.get_all_facts()]
        relationships = [r.dict() for r in entity._read_relationships()]

        return {
            "entity_id": entity_id,
            "metadata": metadata_dict,
            "current_facts": current_facts,
            "all_facts": all_facts,
            "relationships": relationships,
            "current_fact_count": len(current_facts),
            "total_fact_count": len(all_facts),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Fact Management Endpoints

@router.post("/agents/{agent_id}/entities/{entity_id}/facts")
async def add_fact(agent_id: str, entity_id: str, req: AddFactRequest, category: Optional[str] = None):
    """Add a fact to an entity"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        # Find entity
        if category:
            entity = kg.get_entity(entity_id, PARACategory(category))
        else:
            entity = kg.find_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Add fact
        fact_id = entity.add_fact(
            content=req.content,
            added_by=req.added_by,
            confidence=req.confidence,
            source=req.source,
            supersedes=req.supersedes,
        )

        return {
            "success": True,
            "fact_id": fact_id,
            "entity_id": entity_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/entities/{entity_id}/facts")
async def get_facts(agent_id: str, entity_id: str, include_superseded: bool = False, category: Optional[str] = None):
    """Get facts for an entity"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        # Find entity
        if category:
            entity = kg.get_entity(entity_id, PARACategory(category))
        else:
            entity = kg.find_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Get facts
        if include_superseded:
            facts = entity.get_all_facts()
        else:
            facts = entity.get_current_facts()

        return {
            "entity_id": entity_id,
            "facts": [f.dict() for f in facts],
            "count": len(facts),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Relationship Management Endpoints

@router.post("/agents/{agent_id}/entities/{entity_id}/relationships")
async def add_relationship(agent_id: str, entity_id: str, req: AddRelationshipRequest, category: Optional[str] = None):
    """Add a relationship to another entity"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        # Find entity
        if category:
            entity = kg.get_entity(entity_id, PARACategory(category))
        else:
            entity = kg.find_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Add relationship
        entity.add_relationship(
            target_entity=req.target_entity,
            rel_type=req.rel_type,
            notes=req.notes,
        )

        return {
            "success": True,
            "entity_id": entity_id,
            "relationship": {
                "target": req.target_entity,
                "type": req.rel_type,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/entities/{entity_id}/relationships")
async def get_relationships(agent_id: str, entity_id: str, category: Optional[str] = None):
    """Get relationships for an entity"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        # Find entity
        if category:
            entity = kg.get_entity(entity_id, PARACategory(category))
        else:
            entity = kg.find_entity(entity_id)

        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")

        # Get relationships
        relationships = entity._read_relationships()

        return {
            "entity_id": entity_id,
            "relationships": [r.dict() for r in relationships],
            "count": len(relationships),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Lifecycle Endpoints

@router.post("/agents/{agent_id}/entities/{entity_id}/archive")
async def archive_entity(agent_id: str, entity_id: str):
    """Archive a project or resource"""
    try:
        workspace_path = get_agent_workspace(agent_id)
        kg = PARAKnowledgeGraph(workspace_path)

        # Try to find and archive
        entity = kg.get_entity(entity_id, PARACategory.PROJECTS)
        if entity:
            archived = entity.move_to_archive()
            return {
                "success": True,
                "entity_id": entity_id,
                "from_category": "projects",
                "to_category": "archives",
            }

        entity = kg.get_entity(entity_id, PARACategory.RESOURCES)
        if entity:
            archived = entity.move_to_archive()
            return {
                "success": True,
                "entity_id": entity_id,
                "from_category": "resources",
                "to_category": "archives",
            }

        raise HTTPException(status_code=404, detail=f"Entity not found or cannot be archived: {entity_id}")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
