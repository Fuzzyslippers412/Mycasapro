"""
PARA Knowledge Graph - Layer 1
================================

Implements Projects, Areas, Resources, Archives (PARA) methodology for agent memory.

Entity Structure:
- Each entity has a folder: {category}/{entity_name}/
- summary.md: Human-readable overview, updated on every change
- items.json: Append-only fact list with superseding logic
- relationships.json: Links to other entities

Fact Superseding Rules:
- Never delete facts
- Mark facts as superseded with new_fact_id
- Query interface returns only current (non-superseded) facts

Entity Lifecycle:
- Projects can move to Archives when completed
- Areas are ongoing (never archived)
- Resources can move to Archives when obsolete
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class PARACategory(str, Enum):
    """PARA categories"""
    PROJECTS = "projects"
    AREAS = "areas"
    RESOURCES = "resources"
    ARCHIVES = "archives"


class FactStatus(str, Enum):
    """Status of a fact"""
    CURRENT = "current"
    SUPERSEDED = "superseded"


class Fact(BaseModel):
    """A single fact about an entity"""
    fact_id: str
    content: str
    added_at: str
    added_by: str  # Agent name
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    source: Optional[str] = None
    status: FactStatus = FactStatus.CURRENT
    superseded_by: Optional[str] = None  # fact_id that supersedes this


class Relationship(BaseModel):
    """Relationship to another entity"""
    target_entity: str  # Entity ID
    rel_type: str  # "depends_on", "related_to", "child_of", etc.
    added_at: str
    notes: Optional[str] = None


class EntityMetadata(BaseModel):
    """Metadata for a PARA entity"""
    entity_id: str
    name: str
    category: PARACategory
    created_at: str
    updated_at: str
    created_by: str
    tags: List[str] = Field(default_factory=list)
    status: str = "active"  # active, completed, archived


class PARAEntity:
    """
    Represents a PARA entity (Project, Area, Resource, or Archive)
    """

    def __init__(self, base_path: Path, category: PARACategory, entity_id: str):
        self.base_path = base_path
        self.category = category
        self.entity_id = entity_id
        self.entity_path = base_path / category.value / entity_id

    def exists(self) -> bool:
        """Check if entity exists"""
        return self.entity_path.exists()

    def create(self, name: str, created_by: str, tags: List[str] = None) -> None:
        """Create a new entity"""
        if self.exists():
            raise ValueError(f"Entity already exists: {self.entity_id}")

        # Create directory
        self.entity_path.mkdir(parents=True, exist_ok=True)

        # Initialize metadata
        metadata = EntityMetadata(
            entity_id=self.entity_id,
            name=name,
            category=self.category,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            created_by=created_by,
            tags=tags or [],
        )

        # Write initial files
        self._write_metadata(metadata)
        self._write_items([])
        self._write_relationships([])
        self._update_summary(metadata, [], [])

    def add_fact(
        self,
        content: str,
        added_by: str,
        confidence: float = 0.8,
        source: Optional[str] = None,
        supersedes: Optional[str] = None
    ) -> str:
        """
        Add a new fact to the entity.

        Args:
            content: Fact content
            added_by: Agent name
            confidence: Confidence level (0-1)
            source: Optional source reference
            supersedes: Optional fact_id to supersede

        Returns:
            fact_id of the new fact
        """
        if not self.exists():
            raise ValueError(f"Entity does not exist: {self.entity_id}")

        # Generate fact ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        fact_id = f"fact_{timestamp}"

        # Load existing items
        items = self._read_items()

        # If superseding, mark old fact as superseded
        if supersedes:
            for item in items:
                if item.fact_id == supersedes:
                    item.status = FactStatus.SUPERSEDED
                    item.superseded_by = fact_id
                    break

        # Create new fact
        fact = Fact(
            fact_id=fact_id,
            content=content,
            added_at=datetime.now().isoformat(),
            added_by=added_by,
            confidence=confidence,
            source=source,
        )

        items.append(fact)

        # Write updated items
        self._write_items(items)

        # Update summary and metadata
        metadata = self._read_metadata()
        metadata.updated_at = datetime.now().isoformat()
        self._write_metadata(metadata)

        relationships = self._read_relationships()
        self._update_summary(metadata, items, relationships)

        return fact_id

    def get_current_facts(self) -> List[Fact]:
        """Get all current (non-superseded) facts"""
        if not self.exists():
            return []

        items = self._read_items()
        return [f for f in items if f.status == FactStatus.CURRENT]

    def get_all_facts(self) -> List[Fact]:
        """Get all facts including superseded ones"""
        if not self.exists():
            return []

        return self._read_items()

    def add_relationship(
        self,
        target_entity: str,
        rel_type: str,
        notes: Optional[str] = None
    ) -> None:
        """Add a relationship to another entity"""
        if not self.exists():
            raise ValueError(f"Entity does not exist: {self.entity_id}")

        relationships = self._read_relationships()

        # Check if relationship already exists
        for rel in relationships:
            if rel.target_entity == target_entity and rel.rel_type == rel_type:
                return  # Already exists

        # Add new relationship
        rel = Relationship(
            target_entity=target_entity,
            rel_type=rel_type,
            added_at=datetime.now().isoformat(),
            notes=notes,
        )
        relationships.append(rel)

        self._write_relationships(relationships)

        # Update summary
        metadata = self._read_metadata()
        metadata.updated_at = datetime.now().isoformat()
        self._write_metadata(metadata)

        items = self._read_items()
        self._update_summary(metadata, items, relationships)

    def move_to_archive(self) -> "PARAEntity":
        """
        Move this entity to Archives.
        Only valid for Projects and Resources.

        Returns:
            New PARAEntity in archives
        """
        if not self.exists():
            raise ValueError(f"Entity does not exist: {self.entity_id}")

        if self.category == PARACategory.ARCHIVES:
            raise ValueError("Entity is already in archives")

        if self.category == PARACategory.AREAS:
            raise ValueError("Areas cannot be archived (they are ongoing)")

        # Create archive entity
        archive_entity = PARAEntity(
            self.base_path,
            PARACategory.ARCHIVES,
            self.entity_id
        )

        if archive_entity.exists():
            raise ValueError(f"Archive entity already exists: {self.entity_id}")

        # Move directory
        import shutil
        archive_entity.entity_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.entity_path), str(archive_entity.entity_path))

        # Update metadata
        metadata = archive_entity._read_metadata()
        metadata.category = PARACategory.ARCHIVES
        metadata.status = "archived"
        metadata.updated_at = datetime.now().isoformat()
        archive_entity._write_metadata(metadata)

        # Update summary
        items = archive_entity._read_items()
        relationships = archive_entity._read_relationships()
        archive_entity._update_summary(metadata, items, relationships)

        return archive_entity

    # Private methods

    def _read_metadata(self) -> EntityMetadata:
        """Read metadata from summary.md frontmatter"""
        summary_path = self.entity_path / "summary.md"
        if not summary_path.exists():
            raise ValueError(f"Metadata not found: {summary_path}")

        content = summary_path.read_text()

        # Extract frontmatter (between --- lines)
        lines = content.split("\n")
        if lines[0] == "---":
            end_idx = lines[1:].index("---") + 1
            frontmatter = "\n".join(lines[1:end_idx])

            # Parse YAML-like frontmatter
            metadata_dict = {}
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Parse lists
                    if value.startswith("["):
                        value = json.loads(value)
                    # Parse strings
                    elif value.startswith('"') or value.startswith("'"):
                        value = value.strip('"').strip("'")

                    metadata_dict[key] = value

            return EntityMetadata(**metadata_dict)

        raise ValueError("Invalid summary.md format")

    def _write_metadata(self, metadata: EntityMetadata) -> None:
        """Write metadata to summary.md frontmatter"""
        summary_path = self.entity_path / "summary.md"

        # Keep existing body if it exists
        body = ""
        if summary_path.exists():
            content = summary_path.read_text()
            lines = content.split("\n")
            if lines[0] == "---":
                end_idx = lines[1:].index("---") + 1
                body = "\n".join(lines[end_idx + 1:])

        # Write frontmatter
        frontmatter_lines = [
            "---",
            f'entity_id: "{metadata.entity_id}"',
            f'name: "{metadata.name}"',
            f'category: "{metadata.category.value}"',
            f'created_at: "{metadata.created_at}"',
            f'updated_at: "{metadata.updated_at}"',
            f'created_by: "{metadata.created_by}"',
            f'tags: {json.dumps(metadata.tags)}',
            f'status: "{metadata.status}"',
            "---",
        ]

        content = "\n".join(frontmatter_lines) + "\n" + body
        summary_path.write_text(content)

    def _read_items(self) -> List[Fact]:
        """Read items from items.json"""
        items_path = self.entity_path / "items.json"
        if not items_path.exists():
            return []

        data = json.loads(items_path.read_text())
        return [Fact(**item) for item in data]

    def _write_items(self, items: List[Fact]) -> None:
        """Write items to items.json"""
        items_path = self.entity_path / "items.json"
        data = [item.dict() for item in items]
        items_path.write_text(json.dumps(data, indent=2))

    def _read_relationships(self) -> List[Relationship]:
        """Read relationships from relationships.json"""
        rel_path = self.entity_path / "relationships.json"
        if not rel_path.exists():
            return []

        data = json.loads(rel_path.read_text())
        return [Relationship(**rel) for rel in data]

    def _write_relationships(self, relationships: List[Relationship]) -> None:
        """Write relationships to relationships.json"""
        rel_path = self.entity_path / "relationships.json"
        data = [rel.dict() for rel in relationships]
        rel_path.write_text(json.dumps(data, indent=2))

    def _update_summary(
        self,
        metadata: EntityMetadata,
        items: List[Fact],
        relationships: List[Relationship]
    ) -> None:
        """Regenerate summary.md body from current data"""
        # Count current facts
        current_facts = [f for f in items if f.status == FactStatus.CURRENT]

        body_lines = [
            "",
            f"# {metadata.name}",
            "",
            f"**Status:** {metadata.status}",
            f"**Category:** {metadata.category.value}",
            f"**Created:** {metadata.created_at} by {metadata.created_by}",
            f"**Last Updated:** {metadata.updated_at}",
            "",
        ]

        if metadata.tags:
            body_lines.append(f"**Tags:** {', '.join(metadata.tags)}")
            body_lines.append("")

        # Facts section
        body_lines.extend([
            "## Current Facts",
            "",
            f"Total: {len(current_facts)} facts",
            "",
        ])

        for fact in current_facts[-10:]:  # Last 10 facts
            body_lines.append(f"- [{fact.added_at}] {fact.content} (by {fact.added_by}, confidence: {fact.confidence})")

        if len(current_facts) > 10:
            body_lines.append(f"\n_...and {len(current_facts) - 10} more facts (see items.json)_")

        body_lines.append("")

        # Relationships section
        if relationships:
            body_lines.extend([
                "## Relationships",
                "",
            ])

            for rel in relationships:
                notes_str = f" - {rel.notes}" if rel.notes else ""
                body_lines.append(f"- **{rel.rel_type}**: [[{rel.target_entity}]]{notes_str}")

            body_lines.append("")

        # Update summary.md
        summary_path = self.entity_path / "summary.md"
        content = summary_path.read_text()

        # Keep frontmatter, replace body
        lines = content.split("\n")
        if lines[0] == "---":
            end_idx = lines[1:].index("---") + 1
            frontmatter = "\n".join(lines[:end_idx + 1])
            content = frontmatter + "\n" + "\n".join(body_lines)
        else:
            content = "\n".join(body_lines)

        summary_path.write_text(content)


class PARAKnowledgeGraph:
    """
    PARA Knowledge Graph manager
    """

    def __init__(self, agent_workspace_path: Path):
        """
        Initialize knowledge graph for an agent's workspace.

        Args:
            agent_workspace_path: Path to agent's workspace (contains projects/, areas/, etc.)
        """
        self.workspace_path = agent_workspace_path

        # Ensure PARA folders exist
        for category in PARACategory:
            (self.workspace_path / category.value).mkdir(parents=True, exist_ok=True)

    def create_entity(
        self,
        entity_id: str,
        name: str,
        category: PARACategory,
        created_by: str,
        tags: List[str] = None
    ) -> PARAEntity:
        """Create a new PARA entity"""
        entity = PARAEntity(self.workspace_path, category, entity_id)
        entity.create(name, created_by, tags)
        return entity

    def get_entity(self, entity_id: str, category: PARACategory) -> Optional[PARAEntity]:
        """Get an existing entity"""
        entity = PARAEntity(self.workspace_path, category, entity_id)
        if entity.exists():
            return entity
        return None

    def find_entity(self, entity_id: str) -> Optional[PARAEntity]:
        """Find an entity by ID across all categories"""
        for category in PARACategory:
            entity = self.get_entity(entity_id, category)
            if entity:
                return entity
        return None

    def list_entities(self, category: Optional[PARACategory] = None) -> List[str]:
        """List all entity IDs in a category or all categories"""
        categories = [category] if category else list(PARACategory)

        entity_ids = []
        for cat in categories:
            cat_path = self.workspace_path / cat.value
            if cat_path.exists():
                for entity_dir in cat_path.iterdir():
                    if entity_dir.is_dir():
                        entity_ids.append(entity_dir.name)

        return entity_ids

    def archive_project(self, entity_id: str) -> PARAEntity:
        """Archive a project (move to archives)"""
        entity = self.get_entity(entity_id, PARACategory.PROJECTS)
        if not entity:
            raise ValueError(f"Project not found: {entity_id}")

        return entity.move_to_archive()

    def archive_resource(self, entity_id: str) -> PARAEntity:
        """Archive a resource (move to archives)"""
        entity = self.get_entity(entity_id, PARACategory.RESOURCES)
        if not entity:
            raise ValueError(f"Resource not found: {entity_id}")

        return entity.move_to_archive()
