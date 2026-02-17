# MyCasa Pro — Persona Architecture

## Core Principle

**Personas are first-class features in MyCasa Pro.**

Each persona represents a modular, replaceable capability with:
- A system prompt (policy + behavior) in `SOUL.md`
- Defined inputs/outputs
- Explicit authority boundaries
- Enable/disable lifecycle controls

## Key Properties

| Property | Description |
|----------|-------------|
| **Optional** | No persona is required for the system to function |
| **Composable** | Personas can work together or independently |
| **Reversible** | Any persona can be disabled or removed |
| **Versioned** | Changes create new versions; rollback is supported |
| **Auditable** | All persona actions are logged and traceable |

## Lifecycle States

```
PENDING → ACTIVE ↔ DISABLED → REMOVED
                ↘     ↗
                 (rollback)
```

| State | Description |
|-------|-------------|
| `PENDING` | Awaiting approval to activate |
| `ACTIVE` | Running and available |
| `DISABLED` | Paused but can be re-enabled |
| `REMOVED` | Archived (recoverable if archived=true) |

## Authority Model

### User (via Manager/Galidima)
- **Final authority** to add/remove personas
- Approves all persona lifecycle changes
- Sets policy thresholds

### Manager (Galidima)
- Executes persona lifecycle operations
- Enforces user policies
- Logs all changes

### Janitor
- **Authorized to audit** persona behavior and effectiveness
- **Recommends** adding, disabling, or removing personas
- **Flags** redundant, unsafe, or underperforming personas
- **Cannot** unilaterally change persona state

## File Structure

```
agents/
├── memory/
│   ├── {persona-id}/
│   │   ├── SOUL.md        # System prompt (policy + behavior)
│   │   ├── MEMORY.md      # Long-term memory
│   │   └── context/       # Runtime state
│   ├── persona_registry.json  # Central registry
│   └── _archive/          # Removed personas (if archived)
```

## API Reference

### Manager Methods

```python
# Query
manager.list_personas(include_disabled=False)
manager.get_persona(persona_id)
manager.get_active_personas()
manager.why_persona_active(persona_id)

# Lifecycle
manager.add_persona(persona_id, name, soul_md, ...)
manager.enable_persona(persona_id, reason)
manager.disable_persona(persona_id, reason)
manager.remove_persona(persona_id, reason, archive=True)

# Versioning
manager.update_persona(persona_id, soul_md, reason)
manager.rollback_persona(persona_id, to_version, reason)

# Audit
manager.get_persona_recommendations()
```

### Janitor Methods

```python
# Audit
janitor.audit_persona(persona_id)
janitor.audit_all_personas()
janitor.recommend_persona_action(persona_id)
```

## SOUL.md Requirements

Each persona's `SOUL.md` should include:

1. **## ROLE** — What the persona is and does
2. **## AUTHORITY** — What it may/must/must not do
3. **## OBJECTIVES** — Primary goals in order
4. **## COMMUNICATION** — Contracts with other personas
5. **## OPERATIONAL LOOP** — How it operates

## Audit Criteria

The Janitor evaluates personas on:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Activity | 20% | Is the persona being used? |
| Error Rate | 30% | Ratio of failed to successful actions |
| SOUL Completeness | 10% | Required sections present |
| Effectiveness | 40% | User-recorded outcomes |

### Scoring

| Score | Recommendation |
|-------|----------------|
| 0.8+ | Keep |
| 0.5-0.8 | Review |
| 0.3-0.5 | Disable |
| <0.3 | Remove |

## Example: Adding a New Persona

```python
# 1. Define the SOUL.md content
soul_md = """
# SOUL.md — My New Persona

## ROLE
You are MyCasa Pro — NewAgent, responsible for [capability].

## AUTHORITY
You MAY:
- [allowed actions]

You MUST escalate to Manager before:
- [restricted actions]

## OBJECTIVES
1. [primary objective]
2. [secondary objective]
"""

# 2. Add via Manager
manager.add_persona(
    persona_id="new-agent",
    name="My New Persona",
    soul_md=soul_md,
    description="Handles [capability]",
    auto_enable=False  # Start in PENDING state
)

# 3. Review and enable
manager.enable_persona("new-agent", reason="Approved after review")
```

## Example: Disabling a Persona

```python
# Janitor recommends disabling
recommendation = janitor.recommend_persona_action("underperforming-agent")
# → {"recommendation": "disable", "score": 0.4, ...}

# Manager approves and executes
manager.disable_persona(
    "underperforming-agent",
    reason="Low effectiveness score (0.4) - Janitor recommendation"
)
```

## Principles

1. **No persona is permanent** — All can be changed or removed
2. **User authority is supreme** — Manager acts on user's behalf
3. **Transparency** — All changes are logged and auditable
4. **Graceful degradation** — Disabling a persona doesn't crash the system
5. **Composability** — Personas should have minimal dependencies on each other
