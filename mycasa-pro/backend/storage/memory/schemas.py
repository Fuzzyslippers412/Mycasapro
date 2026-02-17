"""
Memory System Data Schemas
Defines all data structures for the three-layer memory system
"""
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime
from uuid import uuid4
import json


# Type aliases
FactCategory = Literal["relationship", "milestone", "status", "preference", "context"]
FactStatus = Literal["active", "superseded"]
DecayTier = Literal["hot", "warm", "cold"]
PARACategory = Literal["projects", "areas", "resources", "archives"]


@dataclass
class AtomicFact:
    """
    Atomic fact schema - single piece of information with full metadata
    """
    fact: str
    category: FactCategory
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""
    status: FactStatus = "active"
    lastAccessed: str = field(default_factory=lambda: datetime.now().isoformat())
    accessCount: int = 0
    id: str = field(default_factory=lambda: f"fact-{uuid4().hex[:12]}")
    supersededBy: Optional[str] = None
    relatedEntities: List[str] = field(default_factory=list)
    confidence: float = 1.0
    agentId: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AtomicFact':
        """Create from dictionary"""
        # Ensure all required fields exist
        required = {'fact', 'category'}
        if not required.issubset(data.keys()):
            missing = required - data.keys()
            raise ValueError(f"Missing required fields: {missing}")

        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def supersede(self, new_fact_id: str):
        """Mark this fact as superseded"""
        self.status = "superseded"
        self.supersededBy = new_fact_id

    def access(self):
        """Record an access"""
        self.lastAccessed = datetime.now().isoformat()
        self.accessCount += 1


@dataclass
class Entity:
    """
    Entity in the knowledge graph
    """
    id: str
    name: str
    category: PARACategory
    path: str
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    lastModified: str = field(default_factory=lambda: datetime.now().isoformat())
    factCount: int = 0
    relatedEntities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class MemoryContext:
    """
    Memory context for an agent or conversation
    """
    agentId: str
    summary: str = ""
    hotFacts: List[AtomicFact] = field(default_factory=list)
    warmFacts: List[AtomicFact] = field(default_factory=list)
    recentNotes: str = ""
    tacitKnowledge: str = ""
    tokenCount: int = 0

    def to_prompt_context(self) -> str:
        """Convert to formatted context for LLM prompt"""
        parts = []

        if self.tacitKnowledge:
            parts.append(f"## Your Operational Patterns\n{self.tacitKnowledge}")

        if self.summary:
            parts.append(f"## Relevant Knowledge\n{self.summary}")

        if self.hotFacts:
            parts.append("## Recently Active Facts")
            for fact in self.hotFacts[:10]:  # Limit to top 10
                parts.append(f"- {fact.fact}")

        if self.recentNotes:
            parts.append(f"## Recent Activity\n{self.recentNotes}")

        return "\n\n".join(parts)


@dataclass
class ConversationLog:
    """
    Log entry for a conversation
    """
    id: str = field(default_factory=lambda: f"conv-{uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agentId: str = ""
    userMessage: str = ""
    agentResponse: str = ""
    factsExtracted: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class MemoryException(Exception):
    """Base exception for memory system"""
    pass


class EntityNotFoundError(MemoryException):
    """Entity does not exist"""
    pass


class MemoryWriteError(MemoryException):
    """Failed to write to memory"""
    pass


class CorruptedDataError(MemoryException):
    """Data is corrupted"""
    pass


class ValidationError(MemoryException):
    """Data validation failed"""
    pass


class SearchIndexError(MemoryException):
    """Search index error"""
    pass


def validate_fact(fact: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a fact dictionary

    Returns:
        (valid: bool, error_message: str)
    """
    try:
        # Required fields
        if 'fact' not in fact or not fact['fact']:
            return False, "Missing or empty 'fact' field"

        if 'category' not in fact:
            return False, "Missing 'category' field"

        valid_categories = {"relationship", "milestone", "status", "preference", "context"}
        if fact['category'] not in valid_categories:
            return False, f"Invalid category: {fact['category']}"

        # Validate status if present
        if 'status' in fact:
            valid_statuses = {"active", "superseded"}
            if fact['status'] not in valid_statuses:
                return False, f"Invalid status: {fact['status']}"

        # Validate confidence if present
        if 'confidence' in fact:
            if not isinstance(fact['confidence'], (int, float)):
                return False, "confidence must be a number"
            if not 0 <= fact['confidence'] <= 1:
                return False, "confidence must be between 0 and 1"

        # Validate relatedEntities if present
        if 'relatedEntities' in fact:
            if not isinstance(fact['relatedEntities'], list):
                return False, "relatedEntities must be a list"

        return True, ""

    except Exception as e:
        return False, f"Validation exception: {str(e)}"


def validate_entity_id(entity_id: str) -> Tuple[bool, str]:
    """
    Validate an entity ID format

    Expected format: category/subcategory/name
    Examples: projects/product-launch, areas/people/jane, resources/python

    Returns:
        (valid: bool, error_message: str)
    """
    if not entity_id or not isinstance(entity_id, str):
        return False, "Entity ID must be a non-empty string"

    parts = entity_id.split('/')
    if len(parts) < 2:
        return False, f"Entity ID must have at least 2 parts: {entity_id}"

    valid_categories = {"projects", "areas", "resources", "archives"}
    if parts[0] not in valid_categories:
        return False, f"Invalid category: {parts[0]}"

    # Check for invalid characters
    for part in parts:
        if not part or part != part.strip():
            return False, f"Entity ID parts cannot be empty or have leading/trailing spaces: {entity_id}"

    return True, ""


def calculate_decay_tier(fact: AtomicFact) -> DecayTier:
    """
    Calculate the decay tier for a fact based on recency and frequency

    Args:
        fact: The atomic fact to evaluate

    Returns:
        Decay tier: "hot", "warm", or "cold"
    """
    try:
        last_accessed = datetime.fromisoformat(fact.lastAccessed)
        now = datetime.now()
        days_since_access = (now - last_accessed).days
        access_count = fact.accessCount

        # Frequency resistance - highly accessed facts decay slower
        if access_count > 20:
            hot_threshold = 14  # 2 weeks
            warm_threshold = 60  # 2 months
        elif access_count > 10:
            hot_threshold = 10  # 10 days
            warm_threshold = 45  # 45 days
        else:
            hot_threshold = 7   # 1 week
            warm_threshold = 30  # 1 month

        if days_since_access <= hot_threshold:
            return "hot"
        elif days_since_access <= warm_threshold:
            return "warm"
        else:
            return "cold"

    except Exception:
        # Default to warm on error
        return "warm"


# JSON encoder for dataclasses
class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        return super().default(o)
