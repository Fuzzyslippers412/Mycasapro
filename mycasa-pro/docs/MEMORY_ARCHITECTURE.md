# MyCasa Pro Memory Architecture
## Three-Layer Memory System with PARA Framework

**Version**: 1.0
**Date**: January 31, 2026
**Status**: Design Specification

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Layers](#architecture-layers)
3. [Directory Structure](#directory-structure)
4. [Atomic Fact Schema](#atomic-fact-schema)
5. [Memory Decay](#memory-decay)
6. [Heartbeat & Extraction](#heartbeat--extraction)
7. [Agent Integration](#agent-integration)
8. [Search & Retrieval](#search--retrieval)
9. [Error Handling](#error-handling)
10. [Implementation Plan](#implementation-plan)

---

## Overview

This memory system provides persistent, structured memory for AI agents using a three-layer architecture inspired by human memory:

- **Layer 1: Knowledge Graph (PARA)** - Declarative memory (facts about the world)
- **Layer 2: Daily Notes** - Episodic memory (what happened when)
- **Layer 3: Tacit Knowledge** - Procedural memory (how the user operates)

### Key Principles

1. **No Deletion** - Facts are superseded, not deleted (preserves history)
2. **Memory Decay** - Recent/frequent facts are more accessible (Hot/Warm/Cold tiers)
3. **Automated Extraction** - Facts extracted automatically via heartbeat process
4. **Per-Agent Context** - Each agent maintains specialized memory workspace
5. **Graceful Degradation** - Multiple fallback layers ensure no data loss

---

## Architecture Layers

### Layer 1: Knowledge Graph (PARA)

Organized using Tiago Forte's PARA method:

- **Projects** - Active work with clear goals/deadlines
- **Areas** - Ongoing responsibilities (no end date)
- **Resources** - Topics of interest, reference material
- **Archives** - Inactive items from other categories

Each entity has two files:
- `summary.md` - Concise overview (loaded first for quick context)
- `items.json` - Array of atomic facts (loaded on-demand for detail)

### Layer 2: Daily Notes

Chronological timeline in dated markdown files:
- `YYYY-MM-DD.md` format
- Raw, unstructured conversation logs
- Source of truth for "what happened when"
- Facts extracted into Layer 1 during heartbeat

### Layer 3: Tacit Knowledge

Single file capturing user patterns:
- `TACIT.md` in agent workspace
- Communication preferences
- Working style patterns
- Tool preferences and workflows
- Updates slowly when new patterns emerge

---

## Directory Structure

```
memory/
├── global/                    # Shared cross-agent memory
│   ├── life/                  # User's personal PARA
│   │   ├── projects/
│   │   │   └── <name>/
│   │   │       ├── summary.md
│   │   │       └── items.json
│   │   ├── areas/
│   │   │   ├── people/
│   │   │   │   └── <name>/
│   │   │   └── companies/
│   │   │       └── <name>/
│   │   ├── resources/
│   │   │   └── <topic>/
│   │   ├── archives/
│   │   ├── index.md
│   │   └── README.md
│   └── daily/                 # Global daily notes
│       └── YYYY-MM-DD.md
│
└── agents/                    # Per-agent workspaces
    ├── manager/
    │   ├── workspace/         # Agent-specific PARA
    │   │   ├── projects/
    │   │   ├── areas/
    │   │   ├── resources/
    │   │   └── archives/
    │   ├── daily/             # Agent-specific timeline
    │   │   └── YYYY-MM-DD.md
    │   ├── TACIT.md           # Agent behavioral patterns
    │   └── CONTEXT.md         # Current context snapshot
    │
    ├── finance/               # Mamadou
    ├── maintenance/           # Ousmane
    ├── security/              # Aïcha
    ├── contractors/           # Malik
    ├── projects/              # Zainab
    └── janitor/               # Salimata

backend/
└── storage/
    └── memory/                # Memory system implementation
        ├── __init__.py
        ├── manager.py         # Core MemoryManager class
        ├── para.py            # PARA operations
        ├── facts.py           # Atomic fact operations
        ├── decay.py           # Memory decay logic
        ├── heartbeat.py       # Extraction & synthesis
        ├── search.py          # Search/retrieval
        └── schemas.py         # Data schemas
```

---

## Atomic Fact Schema

Every fact in `items.json` follows this structure:

```json
{
  "id": "fact-uuid-001",
  "fact": "The actual fact content (clear, atomic statement)",
  "category": "relationship|milestone|status|preference|context",
  "timestamp": "2026-01-31T10:30:00Z",
  "source": "2026-01-31",
  "status": "active|superseded",
  "supersededBy": "fact-uuid-002",
  "relatedEntities": [
    "areas/people/jane",
    "projects/product-launch"
  ],
  "lastAccessed": "2026-01-31T15:45:00Z",
  "accessCount": 12,
  "confidence": 1.0,
  "agentId": "finance",
  "metadata": {
    "extractedFrom": "conversation-id-123",
    "verifiedBy": "user|agent|system"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (UUID) |
| `fact` | string | Yes | Atomic, clear statement |
| `category` | enum | Yes | Type classification |
| `timestamp` | ISO8601 | Yes | When fact was created |
| `source` | string | Yes | Original source (date or reference) |
| `status` | enum | Yes | active or superseded |
| `supersededBy` | string | No | ID of fact that replaced this one |
| `relatedEntities` | array | No | Cross-references to other entities |
| `lastAccessed` | ISO8601 | Yes | Last retrieval time |
| `accessCount` | integer | Yes | Total access count |
| `confidence` | float | No | Fact confidence (0-1) |
| `agentId` | string | No | Which agent created this |
| `metadata` | object | No | Additional context |

---

## Memory Decay

### Recency Tiers

Facts are categorized into three tiers based on `lastAccessed`:

| Tier | Condition | Summary Inclusion | Behavior |
|------|-----------|-------------------|----------|
| **Hot** | Accessed within 7 days | ✅ Prominently featured | First to load |
| **Warm** | Accessed 8-30 days ago | ✅ Lower priority | Still available |
| **Cold** | Not accessed in 30+ days | ❌ Omitted from summary | Searchable only |

### Frequency Resistance

Facts with high `accessCount` resist decay:

```python
def calculate_decay_tier(fact: Dict) -> str:
    days_since_access = (now - fact['lastAccessed']).days
    access_count = fact['accessCount']

    # Frequency resistance
    if access_count > 20:
        decay_threshold_hot = 14  # 2 weeks instead of 1
        decay_threshold_warm = 60  # 2 months instead of 1
    elif access_count > 10:
        decay_threshold_hot = 10
        decay_threshold_warm = 45
    else:
        decay_threshold_hot = 7
        decay_threshold_warm = 30

    if days_since_access <= decay_threshold_hot:
        return "hot"
    elif days_since_access <= decay_threshold_warm:
        return "warm"
    else:
        return "cold"
```

### Weekly Synthesis

Every Sunday at midnight (configurable):

1. Load all active facts from `items.json`
2. Calculate decay tier for each fact
3. Sort by tier (Hot → Warm → Cold), then by `accessCount` (descending)
4. Rewrite `summary.md` with Hot and Warm facts only
5. Cold facts remain in `items.json` for search retrieval

---

## Heartbeat & Extraction

### Heartbeat Process

Runs every 15 minutes (configurable):

```python
async def heartbeat():
    """
    Periodic memory maintenance:
    1. Extract facts from recent conversations
    2. Update daily notes
    3. Refresh summaries if needed
    4. Check for entity creation opportunities
    """
    try:
        # Get conversations since last heartbeat
        conversations = get_recent_conversations(since=last_heartbeat_time)

        for conv in conversations:
            # Extract durable facts
            facts = await extract_facts(conv)

            # Write to knowledge graph
            for fact in facts:
                await write_fact_to_entity(fact)

            # Update daily notes
            await append_to_daily_notes(conv, date=today())

            # Check entity creation heuristics
            await check_create_entities(facts)

        # Mark access for referenced facts
        await update_fact_access_times(conversations)

        last_heartbeat_time = now()

    except Exception as e:
        log_error("Heartbeat failed", e)
        # Continue on error - don't block operations
```

### Fact Extraction Logic

```python
async def extract_facts(conversation: Dict) -> List[Dict]:
    """
    Extract durable facts from conversation using LLM.

    Skip:
    - Casual chat, greetings, thanks
    - Transient requests (weather, time, calculations)
    - Already-captured information

    Extract:
    - Relationships (people, companies)
    - Status changes (project updates)
    - Milestones (deadlines, completions)
    - Decisions (choices made)
    - Preferences (how user likes things done)
    """
    prompt = f"""
    Extract durable facts from this conversation. Focus on:
    1. Relationships and people
    2. Project/task status changes
    3. Milestones and deadlines
    4. Decisions made
    5. User preferences revealed

    Skip casual chat and transient information.

    Conversation:
    {conversation['content']}

    Return JSON array of facts with category, fact, relatedEntities.
    """

    response = await llm.extract(prompt)
    return parse_facts(response)
```

### Entity Creation Heuristics

Create a new entity when:

1. **Mentioned 3+ times** across conversations
2. **Direct relationship** to user stated
3. **Significant project/company** in user's life
4. **Explicit user request** to track something

Otherwise, capture in daily notes only.

---

## Agent Integration

### Per-Agent Memory Workspace

Each agent gets:

```python
class AgentMemoryContext:
    """Memory context for a specific agent"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.workspace_path = f"memory/agents/{agent_id}"
        self.global_access = True  # Can read global memory

        # Agent-specific PARA
        self.para = PARAManager(f"{self.workspace_path}/workspace")

        # Agent daily notes
        self.daily_notes = DailyNotesManager(f"{self.workspace_path}/daily")

        # Agent tacit knowledge
        self.tacit = TacitKnowledge(f"{self.workspace_path}/TACIT.md")

        # Access to global memory (read-only for most agents)
        self.global_memory = MemoryManager("memory/global")

    async def get_context_for_chat(self) -> str:
        """
        Load relevant memory context for agent chat.
        Returns formatted context string to include in system prompt.
        """
        context_parts = []

        # Tacit knowledge (how this agent operates)
        tacit = await self.tacit.read()
        context_parts.append(f"## Your Patterns\n{tacit}")

        # Recent agent-specific activity
        recent_notes = await self.daily_notes.get_recent(days=7)
        context_parts.append(f"## Recent Activity\n{recent_notes}")

        # Relevant global facts (filtered by agent domain)
        relevant_facts = await self.global_memory.search(
            query=f"relevant to {self.agent_id}",
            limit=10,
            tiers=["hot", "warm"]
        )
        context_parts.append(f"## Relevant Knowledge\n{relevant_facts}")

        return "\n\n".join(context_parts)
```

### Integration with Agent Chat

```python
# In BaseAgent class
async def chat(self, message: str, conversation_history: List = None) -> str:
    """Enhanced chat with memory context"""

    # Load memory context for this agent
    memory_context = await self.memory.get_context_for_chat()

    # Build enhanced system prompt
    system_prompt = f"""
    You are {self.name} ({self.emoji}), {self.description}.

    {self.get_soul()}

    ## Memory Context
    {memory_context}

    ## Response Rules
    ...
    """

    # Chat with LLM
    response = await llm.chat(
        system_prompt=system_prompt,
        user_message=message,
        conversation_history=conversation_history
    )

    # Track this interaction for extraction
    await self.memory.record_interaction(message, response)

    return response
```

### Soul/Persona Integration

Each agent's SOUL.md is used as the base personality layer, with memory providing:

1. **Tacit knowledge** - Learned behavioral patterns specific to this agent
2. **Domain facts** - Knowledge relevant to agent's specialty
3. **Recent context** - What this agent has been working on

---

## Search & Retrieval

### Tiered Retrieval Strategy

```python
async def retrieve(self, query: str, max_context: int = 4000) -> str:
    """
    Tiered retrieval to optimize context window:

    1. Load relevant summaries first (cheap, high-level)
    2. If needed, load specific facts (expensive, detailed)
    3. Fall back to daily notes search (timeline context)
    """

    # Tier 1: Summary search (BM25 on summary.md files)
    summaries = await self.search_summaries(query, limit=5)

    context = "## Relevant Entities\n"
    for summary in summaries:
        context += f"\n### {summary['entity']}\n{summary['content']}\n"

    # Check context window usage
    if len(context) >= max_context:
        return context

    # Tier 2: Fact search (semantic search on items.json)
    if len(context) < max_context * 0.6:
        facts = await self.search_facts(query, limit=10)
        context += "\n## Specific Facts\n"
        for fact in facts:
            context += f"- {fact['fact']} ({fact['entity']})\n"

    # Tier 3: Timeline search (date-based if query has temporal aspect)
    if has_temporal_aspect(query):
        timeline = await self.search_daily_notes(query, limit=3)
        context += "\n## Timeline\n"
        for entry in timeline:
            context += f"**{entry['date']}**: {entry['content']}\n"

    return context
```

### Search Methods

```python
class MemorySearch:
    """Search interface for memory system"""

    async def search_summaries(self, query: str, limit: int = 5):
        """BM25 full-text search on summary.md files"""
        # Implementation using rank_bm25 or similar
        pass

    async def search_facts(self, query: str, limit: int = 10, tiers=["hot", "warm"]):
        """Semantic search on atomic facts"""
        # Implementation using sentence-transformers embeddings
        pass

    async def search_daily_notes(self, query: str, limit: int = 3):
        """Timeline search on daily notes"""
        # Date-aware search with recency weighting
        pass

    async def search_cross_entity(self, entity_id: str):
        """Find all facts related to an entity"""
        # Follow relatedEntities links
        pass
```

---

## Error Handling

### God-Level Error Handling Principles

1. **No Data Loss** - All operations are atomic with rollback
2. **Graceful Degradation** - System continues with reduced functionality
3. **Detailed Logging** - Every error logged with full context
4. **Auto-Recovery** - System attempts recovery before failing
5. **User Transparency** - Errors reported clearly to user

### Error Handling Patterns

```python
class MemoryManager:
    """Core memory manager with comprehensive error handling"""

    async def write_fact(self, entity_id: str, fact: Dict) -> Tuple[bool, str]:
        """
        Write a fact to an entity with full error handling.

        Returns:
            (success: bool, message: str)
        """
        backup_path = None

        try:
            # Validate inputs
            self._validate_entity_id(entity_id)
            self._validate_fact(fact)

            # Create backup before modification
            backup_path = await self._backup_entity(entity_id)

            # Load existing facts
            existing = await self._load_facts(entity_id)

            # Add new fact
            fact['id'] = self._generate_fact_id()
            fact['timestamp'] = datetime.now().isoformat()
            fact['lastAccessed'] = fact['timestamp']
            fact['accessCount'] = 0
            fact['status'] = 'active'

            existing.append(fact)

            # Write atomically
            await self._atomic_write(entity_id, existing)

            # Verify write
            verified = await self._verify_write(entity_id, fact['id'])
            if not verified:
                raise MemoryWriteError("Write verification failed")

            # Clean up backup
            if backup_path:
                os.remove(backup_path)

            self.log_action("fact_written", f"Entity: {entity_id}, Fact: {fact['id']}")
            return True, f"Fact written successfully: {fact['id']}"

        except EntityNotFoundError as e:
            # Create entity if it doesn't exist
            await self._create_entity(entity_id)
            return await self.write_fact(entity_id, fact)  # Retry

        except MemoryWriteError as e:
            # Restore from backup
            if backup_path and os.path.exists(backup_path):
                await self._restore_from_backup(entity_id, backup_path)

            error_msg = f"Failed to write fact: {str(e)}"
            self.log_error("fact_write_failed", error_msg, entity_id=entity_id)
            return False, error_msg

        except Exception as e:
            # Unexpected error - restore and report
            if backup_path and os.path.exists(backup_path):
                await self._restore_from_backup(entity_id, backup_path)

            error_msg = f"Unexpected error writing fact: {type(e).__name__}: {str(e)}"
            self.log_error("unexpected_error", error_msg, entity_id=entity_id, exception=e)
            return False, error_msg

    async def _atomic_write(self, entity_id: str, data: Any):
        """
        Atomic write operation - write to temp file, then rename.
        This ensures we never corrupt existing data.
        """
        entity_path = self._get_entity_path(entity_id)
        temp_path = f"{entity_path}.tmp"

        try:
            # Write to temp file
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))

            # Atomic rename
            os.rename(temp_path, entity_path)

        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise MemoryWriteError(f"Atomic write failed: {e}")
```

### Error Recovery Strategies

| Error Type | Recovery Strategy |
|------------|------------------|
| `EntityNotFoundError` | Auto-create entity if appropriate |
| `MemoryWriteError` | Restore from backup, retry once |
| `CorruptedDataError` | Restore from backup, report to Janitor |
| `SearchIndexError` | Rebuild index, use fallback search |
| `HeartbeatFailure` | Log, continue (non-blocking) |
| `ExtractionError` | Log, skip this extraction batch |

---

## Implementation Plan

### Phase 1: Core Infrastructure (Day 1)

- [ ] Create directory structure (`memory/global/`, `memory/agents/`)
- [ ] Implement `MemoryManager` base class
- [ ] Implement atomic fact schema and validation
- [ ] Implement atomic file operations with backup/restore
- [ ] Write comprehensive tests for core operations

### Phase 2: PARA Layer (Day 2)

- [ ] Implement `PARAManager` class
- [ ] Entity creation/update operations
- [ ] Summary.md generation from facts
- [ ] Entity lifecycle (Projects → Archives)
- [ ] Cross-entity relationship tracking

### Phase 3: Daily Notes & Tacit Knowledge (Day 2)

- [ ] Implement `DailyNotesManager`
- [ ] Timeline operations (append, search by date)
- [ ] Implement `TacitKnowledge` manager
- [ ] Pattern update logic

### Phase 4: Memory Decay (Day 3)

- [ ] Implement decay tier calculation
- [ ] Access tracking hooks
- [ ] Weekly synthesis process
- [ ] Summary rewriting logic

### Phase 5: Heartbeat & Extraction (Day 3-4)

- [ ] Implement heartbeat scheduler
- [ ] Fact extraction using LLM
- [ ] Entity creation heuristics
- [ ] Conversation tracking

### Phase 6: Agent Integration (Day 4-5)

- [ ] Create `AgentMemoryContext` class
- [ ] Per-agent workspace initialization
- [ ] Integrate with `BaseAgent.chat()`
- [ ] Soul/persona memory integration

### Phase 7: Search & Retrieval (Day 5-6)

- [ ] Implement tiered retrieval
- [ ] BM25 summary search
- [ ] Semantic fact search (sentence-transformers)
- [ ] Timeline search

### Phase 8: Janitor Integration (Day 6)

- [ ] Memory health checks
- [ ] Fact consistency validation
- [ ] Archive management
- [ ] Backup/restore commands

### Phase 9: Testing & Refinement (Day 7)

- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Error handling validation
- [ ] Documentation

---

## Success Metrics

1. **Zero Data Loss** - All operations are atomic and reversible
2. **Fast Retrieval** - < 100ms for summary retrieval, < 500ms for full search
3. **Context Efficiency** - Memory context stays under 4000 tokens
4. **Accurate Decay** - Hot/Warm/Cold classification reflects actual usage
5. **Autonomous Operation** - Heartbeat runs without manual intervention

---

## Next Steps

1. Review this architecture with team
2. Set up development environment
3. Begin Phase 1 implementation
4. Create test suite framework
5. Document API interfaces

---

**Status**: ✅ Architecture Complete - Ready for Implementation
