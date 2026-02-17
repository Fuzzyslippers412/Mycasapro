# SecondBrain + ENSUE Integration Spec

> **Version:** 1.0.0
> **Status:** Specification
> **Date:** 2026-01-28

## Objective

Integrate Moltbot's SecondBrain skill and ENSUE API to implement an Obsidian-compatible, local-first vault that serves as the canonical long-term memory and knowledge graph for all MyCasa Pro agents.

## Non-Negotiables

| Requirement | Description |
|-------------|-------------|
| File-system based | Vault is markdown files, not a database |
| Obsidian compatible | Opens cleanly in Obsidian without adapters |
| Guarded writes | Agents NEVER write files directly |
| SecondBrain only | All writes go through SecondBrain skill |
| ENSUE indexing | API handles retrieval + graph construction |
| Append-only | No silent edits, no deletions |
| DB as index | Vault files are source of truth |

## Vault Architecture

### Location
```
~/moltbot/vaults/<tenant_id>/secondbrain/
```

### Directory Structure
```
secondbrain/
├── inbox/          # Incoming items to triage
├── memory/         # Processed memories
├── entities/       # People, places, organizations
├── projects/       # Project documentation
├── finance/        # Financial records, transactions
├── maintenance/    # Maintenance logs, readings
├── contractors/    # Contractor records
├── decisions/      # Decision logs
├── logs/           # System/telemetry logs
└── _index/         # Index files for Obsidian
```

### Note Format (Mandatory)

Every markdown note MUST include YAML frontmatter:

```yaml
---
id: sb_2026_01_28_001
type: decision
tenant: tenkiang_household
agent: finance
created_at: 2026-01-28T22:30:00Z
source: user
refs:
  - sb_2026_01_27_042
entities:
  - ent_contractor_juan
confidence: high
permissions: append_only
---

# Decision: Approve Roof Repair Quote

Approved Juan's quote of $4,500 for roof repair.

## Context
- Quote received 2026-01-26
- Compared against 2 other bids
- Best price with good warranty

## Outcome
Work scheduled for 2026-02-15.
```

### Type Taxonomy

| Type | Description | Primary Folder |
|------|-------------|----------------|
| `decision` | Choices made, approvals | `decisions/` |
| `event` | Things that happened | `memory/` |
| `entity` | People, orgs, things | `entities/` |
| `policy` | Rules, guidelines | `memory/` |
| `task` | Actionable items | `maintenance/`, `projects/` |
| `message` | Communications log | `memory/` |
| `telemetry` | System readings | `logs/` |

## SecondBrain Skill Interface

### Agent Write API

```python
# Create new note
secondbrain.write_note({
    "type": "decision",
    "folder": "decisions",
    "title": "Approve Roof Repair Quote",
    "body": "Approved Juan's quote...",
    "entities": ["ent_contractor_juan"],
    "refs": ["sb_2026_01_27_042"],
    "confidence": "high"
})

# Append to existing note
secondbrain.append(
    note_id="sb_2026_01_28_001",
    content="\n\n## Update 2026-01-29\nWork completed ahead of schedule."
)

# Create relationship
secondbrain.link(
    from_id="sb_2026_01_28_001",
    to_id="ent_contractor_juan",
    relation="APPROVED_BY"
)

# Search notes
results = secondbrain.search(
    query="roof repair",
    scope=["decisions", "projects"]
)

# Get entity with relationships
entity = secondbrain.get_entity("ent_contractor_juan")

# Traverse graph
graph = secondbrain.get_graph(
    seed_id="sb_2026_01_28_001",
    depth=2
)
```

### Skill Implementation Responsibilities

The SecondBrain skill MUST:

1. **Validate schema** — Reject malformed payloads
2. **Enforce permissions** — Only allow allowed operations per agent
3. **Generate IDs** — Create `sb_YYYY_MM_DD_NNN` format IDs
4. **Write markdown** — Create properly formatted files
5. **Emit ingest event** — Notify ENSUE of new content
6. **Return note_id** — Confirm successful write

## ENSUE API Integration

### Ingest Pipeline

```
[Vault Change] → [Watcher] → [Parser] → [Normalizer] → [ENSUE Index]
```

1. **Watch** — Monitor vault folders for changes (fsnotify or events)
2. **Parse** — Extract YAML frontmatter + markdown body
3. **Normalize** — Standardize entity references
4. **Index** — Store metadata + embeddings in ENSUE

### Retrieval

```python
# Keyword + semantic search
results = ensue.discover_memories({
    "query": "contractor roof repair",
    "filters": {
        "tenant": "tenkiang_household",
        "type": ["decision", "entity"]
    },
    "limit": 10
})

# Response includes citations
{
    "results": [
        {
            "note_id": "sb_2026_01_28_001",
            "file_path": "decisions/sb_2026_01_28_001.md",
            "relevance": 0.94,
            "snippet": "Approved Juan's quote of $4,500..."
        }
    ]
}
```

### Knowledge Graph

**Nodes:**
- Notes (by type)
- Entities
- Tasks
- Projects
- Decisions

**Edges:**
| Relation | Description |
|----------|-------------|
| `MENTIONS` | Note references entity |
| `OWNS` | Entity owns asset |
| `PAID` | Transaction record |
| `SCHEDULED` | Calendar/task relationship |
| `DECIDED` | Decision outcome |
| `APPROVED_BY` | Approval chain |
| `BLOCKED_BY` | Dependency |

## Agent Memory Policies

### Finance Agent
MUST reference:
- Finance policy notes
- Spending history notes
- Portfolio entity nodes

### Maintenance Agent
MUST reference:
- Task + project notes
- Vendor entity nodes
- Maintenance reading history

### Contractors Agent
MUST reference:
- Contractor entity nodes
- Work history notes
- Payment records

### Manager Agent
MUST reference:
- Cross-domain decision chains
- All entity types for context

### Janitor Agent
MUST reference:
- Telemetry notes
- Incident notes
- Audit logs

## Security & Integrity

| Rule | Implementation |
|------|----------------|
| No secrets in markdown | Pre-write validation |
| No PII without tagging | Required `pii: true` flag |
| Correlation IDs | Every write includes `correlation_id` |
| Audit trail | Janitor reviews all writes |
| Backup integrity | Vault + DB snapshot together |

## Recovery Procedure

```bash
# 1. Restore vault files
tar -xzf vault_backup_2026_01_28.tar.gz -C ~/moltbot/vaults/

# 2. Restore ENSUE index
ensue restore --backup index_backup_2026_01_28.db

# 3. Verify integrity
./scripts/verify_vault.sh
# Checks:
#   - Note count matches
#   - Checksum hashes valid
#   - Graph node/edge counts match
```

## Success Criteria

1. ✅ Vault opens cleanly in Obsidian
2. ✅ All agent memory operations use SecondBrain skill
3. ✅ ENSUE provides reliable retrieval + graph traversal
4. ✅ System is portable (no vendor lock-in)
5. ✅ Human can read/edit notes directly
6. ✅ Recovery restores full functionality

## Implementation Phases

### Phase 1: Foundation
- [ ] Create vault directory structure
- [ ] Implement SecondBrain skill write API
- [ ] Setup ENSUE ingest pipeline

### Phase 2: Agent Integration
- [ ] Wire Finance agent to SecondBrain
- [ ] Wire Maintenance agent
- [ ] Wire Contractors agent
- [ ] Wire Manager agent

### Phase 3: Graph & Search
- [ ] Build knowledge graph edges
- [ ] Implement graph traversal
- [ ] Add semantic search

### Phase 4: Hardening
- [ ] Add Janitor audit agent
- [ ] Implement backup/restore
- [ ] Obsidian compatibility testing
