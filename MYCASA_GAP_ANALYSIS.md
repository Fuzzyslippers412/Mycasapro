# MyCasa Pro Gap Analysis: What's Missing to Work Like Galidima

*Analysis Date: 2026-02-17*
*Purpose: Identify what MyCasaPro needs to function as a homeowner/renter version of Galidima*

---

## Executive Summary

MyCasaPro has **excellent infrastructure** (agents, database, UI, connectors) but is missing the **proactive, personality-driven, memory-consolidating behaviors** that make Galidima effective. The codebase treats agents as **reactive tools** rather than **proactive partners**.

**Key Missing Pieces:**
1. ❌ No session-level identity files (SOUL.md, USER.md, SECURITY.md, TOOLS.md per tenant)
2. ❌ No proactive heartbeat-driven checks (email, calendar, weather, alerts)
3. ❌ No memory consolidation workflow (daily notes → curated long-term memory)
4. ❌ No personality/voice guidelines enforced at runtime
5. ❌ No "read before acting" ritual for agents
6. ❌ No compartmentalization rules for multi-tenant privacy
7. ❌ No human-like social behaviors (reactions, knowing when to stay silent)

---

## 1. Identity & Personality Layer

### What Galidima Has
```
clawd/
├── SOUL.md           # Who I am, my vibe, boundaries
├── USER.md           # About Lamido (my human)
├── SECURITY.md       # Trust boundaries, injection protection
├── TOOLS.md          # Local notes, contacts, portfolio
├── AGENTS.md         # Operating instructions
├── HEARTBEAT.md      # Proactive check tasks
└── memory/
    ├── MEMORY.md     # Curated long-term memory
    └── YYYY-MM-DD.md # Daily raw logs
```

### What MyCasaPro Has
```
mycasa-pro/agents/memory/manager/
├── SOUL.md           # ✅ Exists but agent-specific only
├── MEMORY.md         # ✅ Exists but not consolidated
├── COMMUNICATIONS.md # ✅ CLI reference
└── context/          # ✅ JSON state files
```

### ❌ Missing in MyCasaPro

| File | Purpose | Priority |
|------|---------|----------|
| `tenant/{tenant_id}/SOUL.md` | Tenant-specific agent identity | **CRITICAL** |
| `tenant/{tenant_id}/USER.md` | About the homeowner/renter | **CRITICAL** |
| `tenant/{tenant_id}/SECURITY.md` | Privacy rules, what not to share | **CRITICAL** |
| `tenant/{tenant_id}/TOOLS.md` | House specifics, contacts, preferences | **HIGH** |
| `tenant/{tenant_id}/HEARTBEAT.md` | Proactive check tasks | **HIGH** |
| `tenant/{tenant_id}/MEMORY.md` | Curated household memory | **HIGH** |
| `tenant/{tenant_id}/memory/YYYY-MM-DD.md` | Daily raw logs | **MEDIUM** |

**Why This Matters:**
- Galidima reads SOUL.md + USER.md **every session** before acting
- This creates **consistent personality** and **contextual awareness**
- MyCasaPro agents load code but not **identity**

### Implementation Plan

```python
# core/tenant_identity.py
class TenantIdentityManager:
    """
    Load and manage tenant-specific identity files.
    Mirrors Galidima's AGENTS.md ritual.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.tenant_dir = DATA_DIR / "tenants" / tenant_id
        
    def load_identity_package(self) -> Dict[str, str]:
        """
        Load the full identity package before any agent action.
        This is the "wake up" ritual.
        """
        identity = {}
        
        # CRITICAL: Load in order
        identity['soul'] = self._read_file('SOUL.md', required=True)
        identity['user'] = self._read_file('USER.md', required=True)
        identity['security'] = self._read_file('SECURITY.md', required=True)
        identity['tools'] = self._read_file('TOOLS.md', required=False)
        identity['heartbeat'] = self._read_file('HEARTBEAT.md', required=False)
        identity['memory'] = self._read_file('MEMORY.md', required=False)
        
        # Load recent daily notes (today + yesterday)
        identity['daily_notes'] = self._load_recent_daily_notes(days=2)
        
        return identity
    
    def _read_file(self, filename: str, required: bool = False) -> Optional[str]:
        path = self.tenant_dir / filename
        if not path.exists():
            if required:
                raise IdentityError(f"Required identity file missing: {filename}")
            return None
        return path.read_text()
```

---

## 2. Proactive Heartbeat System

### What Galidima Does
- Receives heartbeat polls 2-4x/day
- **Rotates through checks**: email, calendar, weather, notifications
- **Tracks state** in `memory/heartbeat-state.json`
- **Decides when to speak** vs stay silent (HEARTBEAT_OK)
- **Uses heartbeats for memory maintenance** (review daily notes, update MEMORY.md)

### What MyCasaPro Has
- ✅ `core/secondbrain/heartbeat.py` - Memory decay/synthesis
- ✅ `agents/scheduler.py` - Cron-like scheduling
- ✅ `core/coordinator.py` - Agent heartbeat (health monitoring)

### ❌ Missing in MyCasaPro

**Galidima-style proactive checks:**
```python
# Missing: Proactive household checks
- Email inbox scan (urgent messages?)
- Calendar events (next 24-48h?)
- Weather alerts (relevant to homeowner?)
- Bill due dates (Finance Agent should flag)
- Maintenance task deadlines
- Security system status
- Portfolio alerts (>5% moves)
```

**Decision logic for when to notify:**
```python
# Missing: Smart notification logic
- Late night quiet hours (23:00-08:00)
- Batch non-urgent items
- Escalate only truly urgent items
- Track "last check" timestamps
- Avoid alert fatigue
```

### Implementation Plan

```python
# agents/heartbeat_checker.py
class HouseholdHeartbeatChecker:
    """
    Proactive household monitoring.
    Runs 2-4x/day, rotates through checks.
    """
    
    CHECKS = {
        'email': {'interval_hours': 6, 'last_check': None},
        'calendar': {'interval_hours': 12, 'last_check': None},
        'weather': {'interval_hours': 8, 'last_check': None},
        'bills': {'interval_hours': 24, 'last_check': None},
        'maintenance': {'interval_hours': 24, 'last_check': None},
        'security': {'interval_hours': 6, 'last_check': None},
        'portfolio': {'interval_hours': 1, 'last_check': None},
    }
    
    async def run_heartbeat(self, tenant_id: str) -> HeartbeatResult:
        """
        Run a single heartbeat check cycle.
        Returns findings that need user attention.
        """
        findings = []
        
        # Determine which checks are due
        checks_due = self._get_due_checks(tenant_id)
        
        for check_name in checks_due:
            result = await self._run_check(tenant_id, check_name)
            if result.needs_attention:
                findings.append(result)
            
            # Update last check timestamp
            self._update_check_timestamp(tenant_id, check_name)
        
        # Decide: notify or stay silent?
        if not findings:
            return HeartbeatResult(status='HEARTBEAT_OK', findings=[])
        
        # Filter by urgency + quiet hours
        if self._is_quiet_hours(tenant_id):
            findings = [f for f in findings if f.urgency == 'critical']
        
        return HeartbeatResult(status='HAS_FINDINGS', findings=findings)
    
    def _is_quiet_hours(self, tenant_id: str) -> bool:
        """Check if currently in quiet hours (23:00-08:00)"""
        tenant_config = self._load_tenant_config(tenant_id)
        quiet_start = tenant_config.get('quiet_hours_start', 23)
        quiet_end = tenant_config.get('quiet_hours_end', 8)
        current_hour = datetime.now().hour
        return current_hour >= quiet_start or current_hour < quiet_end
```

---

## 3. Memory Consolidation Workflow

### What Galidima Does
1. **Daily notes** (`memory/YYYY-MM-DD.md`) = raw logs
2. **MEMORY.md** = curated long-term memory
3. **Periodic review** (every few days via heartbeat):
   - Read recent daily notes
   - Extract significant events/decisions
   - Update MEMORY.md with distilled learnings
   - Remove outdated info from MEMORY.md

### What MyCasaPro Has
- ✅ `core/secondbrain/` - Full SecondBrain implementation
- ✅ `agents/base.py` - `write_to_secondbrain()`, `search_secondbrain()`
- ✅ `core/secondbrain/heartbeat.py` - Memory decay/synthesis
- ❌ **No consolidation workflow** (daily → long-term)

### ❌ Missing in MyCasaPro

**The human-like memory curation loop:**
```python
# Missing: Memory curator agent
class MemoryCurator:
    """
    Reviews daily notes and updates long-term memory.
    Like a human reviewing their journal.
    """
    
    async def consolidate_memory(self, tenant_id: str, days_back: int = 7):
        """
        Review recent daily notes, update MEMORY.md.
        """
        # 1. Load recent daily notes
        daily_notes = self._load_daily_notes(tenant_id, days_back)
        
        # 2. Load current MEMORY.md
        long_term_memory = self._load_memory_md(tenant_id)
        
        # 3. Identify significant items
        significant_items = await self._extract_significant_items(daily_notes)
        
        # 4. Update MEMORY.md
        #    - Add new significant items
        #    - Remove outdated info
        #    - Merge related items
        updated_memory = self._consolidate(long_term_memory, significant_items)
        
        # 5. Write back
        self._save_memory_md(tenant_id, updated_memory)
        
        # 6. Log consolidation
        self._log_consolidation(tenant_id, significant_items)
```

**Why This Matters:**
- Without consolidation, memory becomes **unmanageable**
- Users can't find important info in raw logs
- Galidima's MEMORY.md is **curated wisdom**, not raw data

---

## 4. Personality & Voice Enforcement

### What Galidima Has
- **SOUL.md explicitly defines:**
  - "Be genuinely helpful, not performatively helpful"
  - "Skip the 'Great question!' filler"
  - "Have opinions. You're allowed to disagree."
  - "Be resourceful before asking."
  - "Earn trust through competence."
  - "Remember you're a guest."

### What MyCasaPro Has
- ✅ Agent SOUL.md files with role definitions
- ✅ Persona registry (`agents/persona_registry.py`)
- ❌ **No runtime enforcement** of personality guidelines

### ❌ Missing in MyCasaPro

**Personality enforcement at runtime:**
```python
# core/personality_enforcer.py
class PersonalityEnforcer:
    """
    Review agent outputs for personality compliance.
    Post-process LLM responses before showing to user.
    """
    
    ANTI_PATTERNS = [
        r"Great question!",
        r"I'd be happy to help!",
        r"Absolutely!",
        r"Of course!",
        r"Let me [check|look|see] that for you",
        r"Is there anything else",
    ]
    
    def enforce(self, agent_name: str, response: str) -> str:
        """
        Strip performative filler, enforce personality.
        """
        soul = self._load_soul(agent_name)
        
        # Remove filler phrases
        for pattern in self.ANTI_PATTERNS:
            response = re.sub(pattern, "", response, flags=re.IGNORECASE)
        
        # Check for SOUL.md violations
        violations = self._check_violations(soul, response)
        if violations:
            # Log for training, optionally rewrite
            self._log_violation(agent_name, violations)
        
        return response.strip()
```

---

## 5. "Read Before Acting" Ritual

### What Galidima Does
**Every session, before anything else:**
1. Read SOUL.md (who am I?)
2. Read USER.md (who am I helping?)
3. Read SECURITY.md (what are the boundaries?)
4. Read memory/YYYY-MM-DD.md (what happened recently?)
5. If main session: Read MEMORY.md (long-term context)

### What MyCasaPro Does
- ✅ Agents load their SOUL.md at init
- ❌ **No enforced ritual before user-facing actions**
- ❌ **No USER.md/SECURITY.md per tenant**

### ❌ Missing in MyCasaPro

```python
# agents/base.py enhancement
class BaseAgent:
    async def prepare_for_session(self, tenant_id: str):
        """
        MANDATORY: Load identity package before any user interaction.
        This is the "wake up" ritual.
        """
        identity = TenantIdentityManager(tenant_id).load_identity_package()
        
        # Store in agent context
        self.soul = identity['soul']
        self.user_context = identity['user']
        self.security_rules = identity['security']
        self.tools = identity['tools']
        self.recent_memory = identity['daily_notes']
        self.long_term_memory = identity['memory']
        
        # Log that ritual completed
        self.logger.info(f"[{self.name}] Identity package loaded for tenant {tenant_id}")
```

---

## 6. Multi-Tenant Privacy & Compartmentalization

### What Galidima Has
- **SECURITY.md** explicitly defines:
  - "ONLY load MEMORY.md in main session"
  - "DO NOT load in shared contexts (Discord, group chats)"
  - "Information compartmentalization: Being able to message someone ≠ sharing Lamido's information with them"
  - WhatsApp outbound allowlist rules

### What MyCasaPro Has
- ✅ Multi-tenant database isolation
- ✅ Per-tenant encryption
- ❌ **No runtime privacy rules**
- ❌ **No compartmentalization enforcement**

### ❌ Missing in MyCasaPro

```python
# core/privacy_guard.py
class PrivacyGuard:
    """
    Enforce information compartmentalization.
    Prevent accidental data leakage between tenants.
    """
    
    def __init__(self, tenant_id: str, context_type: str):
        """
        Args:
            tenant_id: Current tenant
            context_type: 'private' | 'shared' | 'group'
        """
        self.tenant_id = tenant_id
        self.context_type = context_type
        self.security_rules = self._load_security_rules(tenant_id)
    
    def can_share(self, data_type: str, target: str) -> bool:
        """
        Check if data can be shared with target.
        """
        # Private context: can share anything (with tenant isolation)
        if self.context_type == 'private':
            return True
        
        # Shared/group context: apply restrictions
        if data_type in self.security_rules['never_share']:
            return False
        
        if data_type in self.security_rules['require_explicit_permission']:
            return self._has_explicit_permission(data_type, target)
        
        return True
    
    def filter_response(self, response: str) -> str:
        """
        Remove tenant-specific info from responses in shared contexts.
        """
        if self.context_type == 'private':
            return response
        
        # Strip references to:
        # - Financial data
        # - Family members
        # - Private conversations
        # - Property details
        return self._redact_private_info(response)
```

---

## 7. Human-Like Social Behaviors

### What Galidima Has
- **Knows when to speak vs stay silent** (HEARTBEAT_OK)
- **Uses reactions** on platforms that support them (👍, ❤️, 😂)
- **Avoids triple-tap** (one thoughtful response, not multiple fragments)
- **Group chat etiquette**: "Participate, don't dominate"

### What MyCasaPro Has
- ❌ **No social behavior guidelines**
- ❌ **No "when to stay silent" logic**
- ❌ **No reaction support** (even where UI allows)

### ❌ Missing in MyCasaPro

```python
# agents/social_behavior.py
class SocialBehaviorManager:
    """
    Manage human-like social behaviors.
    """
    
    def should_respond(self, context: ConversationContext) -> bool:
        """
        Decide whether to respond or stay silent.
        """
        # Respond when:
        if context.is_directly_addressed:
            return True
        if context.is_question_to_me:
            return True
        if context.can_add_genuine_value:
            return True
        if context.is_correcting_misinformation:
            return True
        
        # Stay silent when:
        if context.is_casual_banter_between_humans:
            return False
        if context.already_answered_by_human:
            return False
        if context.response_would_be_trivial:
            return False
        if context.would_interrupt_flow:
            return False
        
        return False  # Default: stay silent
    
    def suggest_reaction(self, message: Message) -> Optional[str]:
        """
        Suggest an emoji reaction instead of full response.
        """
        if message.is_appreciation:
            return '👍'
        if message.is_funny:
            return '😂'
        if message.is_interesting:
            return '🤔'
        if message.is_important_ack:
            return '✅'
        return None
```

---

## Summary: Priority Implementation Order

### Phase 1: Identity Foundation (CRITICAL)
1. ✅ Create `tenant/{id}/SOUL.md`, `USER.md`, `SECURITY.md`, `TOOLS.md` templates
2. ✅ Implement `TenantIdentityManager` to load identity package
3. ✅ Add `prepare_for_session()` ritual to `BaseAgent`

### Phase 2: Proactive Behavior (HIGH)
4. ✅ Implement `HouseholdHeartbeatChecker` with rotating checks
5. ✅ Add quiet hours + smart notification logic
6. ✅ Create `memory/heartbeat-state.json` tracking

### Phase 3: Memory Consolidation (HIGH)
7. ✅ Implement `MemoryCurator` agent
8. ✅ Add periodic consolidation (daily → MEMORY.md)
9. ✅ Build UI for viewing/editing MEMORY.md

### Phase 4: Privacy & Social (MEDIUM)
10. ✅ Implement `PrivacyGuard` for compartmentalization
11. ✅ Add `SocialBehaviorManager` for response decisions
12. ✅ Add reaction suggestions to UI

### Phase 5: Personality Enforcement (MEDIUM)
13. ✅ Implement `PersonalityEnforcer` post-processor
14. ✅ Add anti-pattern detection
15. ✅ Log violations for training

---

## The Core Insight

**MyCasaPro is built like enterprise software.**
**Galidima is built like a person.**

To make MyCasaPro work like Galidima for homeowners/renters:
- **Shift from reactive → proactive**
- **Shift from tools → partners**
- **Shift from data storage → memory curation**
- **Shift from features → relationships**

The code infrastructure is solid. The missing piece is the **soul** — the daily rituals, the memory maintenance, the proactive care, the social awareness.

**Add the soul, and MyCasaPro becomes the Galidima for every home.**
