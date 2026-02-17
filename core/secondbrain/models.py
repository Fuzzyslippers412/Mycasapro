"""SecondBrain Data Models - Enhanced with Dumbo features"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import re


class NoteType(str, Enum):
    """Valid note types - Enhanced with Dumbo memory types"""
    # Core types
    DECISION = "decision"
    EVENT = "event"
    ENTITY = "entity"
    POLICY = "policy"
    TASK = "task"
    MESSAGE = "message"
    TELEMETRY = "telemetry"
    
    # Dumbo-inspired memory types
    PREFERENCE = "preference"      # Learns what you like over time
    PATTERN = "pattern"            # Documents recurring behaviors
    RELATIONSHIP = "relationship"  # Remembers people you mention
    TRANSCRIPT = "transcript"      # Saves conversations to prevent amnesia
    
    # Agent workspace types
    SOUL = "soul"                  # Agent personality/behavior
    IDENTITY = "identity"          # Agent role definition
    TOOLS = "tools"                # Agent tool notes
    MEMORY = "memory"              # Agent persistent learnings
    HEARTBEAT = "heartbeat"        # Agent periodic check config


class AgentType(str, Enum):
    """Valid agent types"""
    MANAGER = "manager"
    FINANCE = "finance"
    MAINTENANCE = "maintenance"
    CONTRACTORS = "contractors"
    PROJECTS = "projects"
    SECURITY = "security"
    JANITOR = "janitor"
    MAIL = "mail"
    BACKUP = "backup"
    REMINDERS = "reminders"


class SourceType(str, Enum):
    """Valid source types"""
    USER = "user"
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    SYSTEM = "system"
    API = "api"
    SESSION = "session"      # From conversation session
    LEARNING = "learning"    # Auto-learned


class Confidence(str, Enum):
    """Confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PreferenceCategory(str, Enum):
    """Categories for preferences"""
    COMMUNICATION = "communication"  # How user likes to be communicated with
    SCHEDULING = "scheduling"        # Time preferences
    FINANCE = "finance"              # Financial preferences
    STYLE = "style"                  # Formatting/output preferences
    PRIVACY = "privacy"              # Privacy preferences
    GENERAL = "general"


class PatternType(str, Enum):
    """Types of patterns"""
    ROUTINE = "routine"        # Regular activities
    TRIGGER = "trigger"        # What causes certain behaviors
    RESPONSE = "response"      # How user typically responds
    WORKFLOW = "workflow"      # Work patterns
    EXCEPTION = "exception"    # Exceptions to patterns


# Type to folder mapping
TYPE_FOLDER_MAP = {
    NoteType.DECISION: "decisions",
    NoteType.EVENT: "memory",
    NoteType.ENTITY: "entities",
    NoteType.POLICY: "memory",
    NoteType.TASK: "inbox",
    NoteType.MESSAGE: "memory",
    NoteType.TELEMETRY: "logs",
    # Dumbo types
    NoteType.PREFERENCE: "preferences",
    NoteType.PATTERN: "patterns",
    NoteType.RELATIONSHIP: "relationships",
    NoteType.TRANSCRIPT: "transcripts",
    # Workspace types go in agents/<agent_id>/
    NoteType.SOUL: "agents",
    NoteType.IDENTITY: "agents",
    NoteType.TOOLS: "agents",
    NoteType.MEMORY: "agents",
    NoteType.HEARTBEAT: "agents",
}


@dataclass
class NoteMetadata:
    """YAML frontmatter metadata"""
    id: str
    type: NoteType
    tenant: str
    agent: AgentType
    created_at: datetime
    source: SourceType = SourceType.SYSTEM
    refs: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    permissions: str = "append_only"
    correlation_id: Optional[str] = None
    pii: bool = False
    # New fields for enhanced types
    category: Optional[str] = None  # For preferences/patterns
    learned_from: Optional[str] = None  # Source of learning
    strength: float = 1.0  # How strong the preference/pattern is (0-1)
    last_confirmed: Optional[datetime] = None  # Last time this was confirmed
    
    def to_yaml(self) -> str:
        """Convert to YAML frontmatter string"""
        lines = [
            "---",
            f"id: {self.id}",
            f"type: {self.type.value}",
            f"tenant: {self.tenant}",
            f"agent: {self.agent.value}",
            f"created_at: {self.created_at.isoformat()}",
            f"source: {self.source.value}",
        ]
        
        if self.refs:
            lines.append("refs:")
            for ref in self.refs:
                lines.append(f"  - {ref}")
        
        if self.entities:
            lines.append("entities:")
            for ent in self.entities:
                lines.append(f"  - {ent}")
        
        lines.extend([
            f"confidence: {self.confidence.value}",
            f"permissions: {self.permissions}",
        ])
        
        if self.correlation_id:
            lines.append(f"correlation_id: {self.correlation_id}")
        
        if self.pii:
            lines.append("pii: true")
        
        if self.category:
            lines.append(f"category: {self.category}")
        
        if self.learned_from:
            lines.append(f"learned_from: {self.learned_from}")
        
        if self.strength != 1.0:
            lines.append(f"strength: {self.strength}")
        
        if self.last_confirmed:
            lines.append(f"last_confirmed: {self.last_confirmed.isoformat()}")
        
        lines.append("---")
        return "\n".join(lines)


@dataclass
class NotePayload:
    """Payload for creating a new note"""
    type: NoteType
    title: str
    body: str
    agent: AgentType
    source: SourceType = SourceType.SYSTEM
    folder: Optional[str] = None
    refs: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    correlation_id: Optional[str] = None
    pii: bool = False
    # Enhanced fields
    category: Optional[str] = None
    learned_from: Optional[str] = None
    strength: float = 1.0
    
    def get_folder(self) -> str:
        """Get target folder for this note"""
        if self.folder:
            return self.folder
        return TYPE_FOLDER_MAP.get(self.type, "memory")
    
    def validate(self) -> List[str]:
        """Validate payload, return list of errors"""
        errors = []
        
        if not self.title or not self.title.strip():
            errors.append("Title is required")
        
        if not self.body or not self.body.strip():
            errors.append("Body is required")
        
        # Check for secrets patterns
        secret_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',
            r'-----BEGIN.*KEY-----',
            r'password\s*[=:]\s*["\']?\S+',
            r'secret\s*[=:]\s*["\']?\S+',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, self.body, re.IGNORECASE):
                errors.append(f"Body may contain secrets (pattern: {pattern})")
        
        for ent in self.entities:
            if not ent.startswith("ent_"):
                errors.append(f"Invalid entity ID format: {ent}")
        
        for ref in self.refs:
            if not ref.startswith("sb_"):
                errors.append(f"Invalid ref format: {ref}")
        
        return errors


@dataclass 
class PreferenceNote:
    """Structured preference data"""
    key: str                           # e.g., "communication.tone"
    value: Any                         # The preference value
    category: PreferenceCategory
    context: Optional[str] = None      # When this preference applies
    learned_from: Optional[str] = None # How we learned this
    strength: float = 1.0              # Confidence (0-1)
    examples: List[str] = field(default_factory=list)  # Example situations
    
    def to_markdown(self) -> str:
        """Convert to markdown body"""
        lines = [
            f"**Key:** `{self.key}`",
            f"**Value:** {self.value}",
            f"**Category:** {self.category.value}",
            "",
        ]
        if self.context:
            lines.append(f"**Context:** {self.context}")
        if self.learned_from:
            lines.append(f"**Learned from:** {self.learned_from}")
        if self.examples:
            lines.append("\n**Examples:**")
            for ex in self.examples:
                lines.append(f"- {ex}")
        return "\n".join(lines)


@dataclass
class PatternNote:
    """Structured pattern data"""
    name: str
    pattern_type: PatternType
    trigger: Optional[str] = None      # What triggers this pattern
    behavior: str = ""                 # The pattern behavior
    frequency: Optional[str] = None    # How often it occurs
    confidence: float = 1.0
    observations: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Convert to markdown body"""
        lines = [
            f"**Pattern:** {self.name}",
            f"**Type:** {self.pattern_type.value}",
            "",
        ]
        if self.trigger:
            lines.append(f"**Trigger:** {self.trigger}")
        lines.append(f"**Behavior:** {self.behavior}")
        if self.frequency:
            lines.append(f"**Frequency:** {self.frequency}")
        if self.observations:
            lines.append("\n**Observations:**")
            for obs in self.observations:
                lines.append(f"- {obs}")
        return "\n".join(lines)


@dataclass
class RelationshipNote:
    """Structured relationship/person data"""
    name: str
    relation: Optional[str] = None     # e.g., "wife", "contractor", "friend"
    context: Optional[str] = None      # How we know them
    contact_info: Dict[str, str] = field(default_factory=dict)
    preferences: Dict[str, str] = field(default_factory=dict)  # Their preferences
    notes: List[str] = field(default_factory=list)
    last_interaction: Optional[datetime] = None
    
    def to_markdown(self) -> str:
        """Convert to markdown body"""
        lines = [f"# {self.name}", ""]
        if self.relation:
            lines.append(f"**Relation:** {self.relation}")
        if self.context:
            lines.append(f"**Context:** {self.context}")
        if self.contact_info:
            lines.append("\n## Contact Info")
            for k, v in self.contact_info.items():
                lines.append(f"- **{k}:** {v}")
        if self.preferences:
            lines.append("\n## Their Preferences")
            for k, v in self.preferences.items():
                lines.append(f"- **{k}:** {v}")
        if self.notes:
            lines.append("\n## Notes")
            for note in self.notes:
                lines.append(f"- {note}")
        if self.last_interaction:
            lines.append(f"\n*Last interaction: {self.last_interaction.isoformat()}*")
        return "\n".join(lines)


@dataclass
class TranscriptNote:
    """Structured transcript data"""
    session_id: str
    channel: str                       # whatsapp, telegram, etc.
    start_time: datetime
    end_time: Optional[datetime] = None
    message_count: int = 0
    summary: Optional[str] = None
    key_decisions: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Convert to markdown body"""
        lines = [
            f"**Session:** `{self.session_id}`",
            f"**Channel:** {self.channel}",
            f"**Started:** {self.start_time.isoformat()}",
        ]
        if self.end_time:
            lines.append(f"**Ended:** {self.end_time.isoformat()}")
        lines.append(f"**Messages:** {self.message_count}")
        
        if self.summary:
            lines.extend(["", "## Summary", self.summary])
        
        if self.key_decisions:
            lines.append("\n## Key Decisions")
            for d in self.key_decisions:
                lines.append(f"- {d}")
        
        if self.action_items:
            lines.append("\n## Action Items")
            for item in self.action_items:
                lines.append(f"- [ ] {item}")
        
        if self.messages:
            lines.append("\n## Transcript")
            for msg in self.messages[-50:]:  # Last 50 messages
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                ts = msg.get("timestamp", "")
                lines.append(f"\n**[{ts}] {role}:**\n{content}")
        
        return "\n".join(lines)


@dataclass
class AgentWorkspace:
    """Agent workspace configuration"""
    agent_id: str
    soul: str = ""        # SOUL.md content
    identity: str = ""    # IDENTITY.md content  
    tools: str = ""       # TOOLS.md content
    memory: str = ""      # MEMORY.md content
    heartbeat: str = ""   # HEARTBEAT.md content
    
    def to_files(self) -> Dict[str, str]:
        """Convert to file dict"""
        return {
            "SOUL.md": self.soul,
            "IDENTITY.md": self.identity,
            "TOOLS.md": self.tools,
            "MEMORY.md": self.memory,
            "HEARTBEAT.md": self.heartbeat,
        }


@dataclass
class SearchResult:
    """Search result from ENSUE"""
    note_id: str
    file_path: str
    relevance: float
    snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphNode:
    """Node in knowledge graph"""
    id: str
    type: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Edge in knowledge graph"""
    from_id: str
    to_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphResult:
    """Subgraph from traversal"""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
