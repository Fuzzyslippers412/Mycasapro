# Galidima Pattern Implementation Guide

*Making MyCasa Pro work like Galidima - a proactive, personality-driven partner for homeowners/renters*

---

## What I Found

Your MyCasaPro codebase has **excellent infrastructure**:
- ✅ Multi-agent architecture with personas
- ✅ Database with multi-tenant isolation
- ✅ SecondBrain memory system
- ✅ Connectors (Gmail, WhatsApp, Calendar)
- ✅ FastAPI backend + Next.js frontend
- ✅ Agent activity dashboard

**But it's missing the soul** — the proactive, personality-driven behaviors that make Galidima effective.

---

## What I Created

### 1. Gap Analysis Document
**File:** `MYCASA_GAP_ANALYSIS.md`

A comprehensive analysis comparing Galidima's setup vs MyCasaPro, identifying 7 key missing pieces:
1. Identity & Personality Layer
2. Proactive Heartbeat System
3. Memory Consolidation Workflow
4. Personality & Voice Enforcement
5. "Read Before Acting" Ritual
6. Multi-Tenant Privacy & Compartmentalization
7. Human-Like Social Behaviors

### 2. Tenant Identity Templates
**Location:** `templates/tenant_identity/`

Created template files that mirror Galidima's workspace structure:

```
templates/tenant_identity/
├── SOUL.md           # Agent identity, vibe, boundaries
├── USER.md           # About the homeowner/renter
├── SECURITY.md       # Trust boundaries, privacy rules
├── TOOLS.md          # House specifics, contacts, preferences
├── HEARTBEAT.md      # Proactive check tasks
└── MEMORY.md         # Curated household memory
```

### 3. Core Implementation Code

#### Tenant Identity Manager
**File:** `core/tenant_identity.py`

```python
# Usage in any agent:
from core.tenant_identity import TenantIdentityManager

identity = TenantIdentityManager(tenant_id).load_identity_package()

# Now you have:
# - identity['soul'] - Who the agent is
# - identity['user'] - Who they're helping
# - identity['security'] - Trust boundaries
# - identity['tools'] - Local notes
# - identity['memory'] - Long-term context
```

#### Household Heartbeat Checker
**File:** `agents/heartbeat_checker.py`

```python
# Proactive household monitoring:
checker = HouseholdHeartbeatChecker(tenant_id)
result = await checker.run_heartbeat()

if result.status == 'HEARTBEAT_OK':
    # Nothing needs attention
    pass
else:
    # Notify user of findings
    for finding in result.findings:
        notify_user(finding)
```

#### Base Agent Enhancement
**File:** `agents/base.py` (updated)

Added `prepare_for_session()` method that ALL agents must call before user-facing actions:

```python
# In any agent:
async def chat(self, message: str, context: Dict):
    # MANDATORY: Load identity first
    await self.prepare_for_session()
    
    # Now agent has soul, user context, security rules, etc.
    # ... rest of chat logic
```

---

## How This Makes MyCasaPro Like Galidima

### Before (Current State)
```
User: "What's going on?"
Agent: [Queries database, returns facts]
```

### After (With Galidima Pattern)
```
User: "What's going on?"
Agent: 
  1. Loads SOUL.md (knows its role)
  2. Loads USER.md (knows the homeowner)
  3. Loads MEMORY.md (remembers context)
  4. Checks daily notes (recent activity)
  5. Runs heartbeat checks (email, calendar, bills, security)
  6. Synthesizes complete, proactive report
  
"Here's what's happening:
- 2 bills due this week (electric, water)
- Contractor Juan confirmed for Thursday 9am
- Weather alert: Freeze warning tonight - I closed smart valves
- Calendar: HOA meeting tomorrow 7pm
- Portfolio: NVDA up 7% today

Anything you want me to handle?"
```

---

## Implementation Priority

### Phase 1: Identity Foundation (CRITICAL) - DO THIS FIRST

**Step 1:** Copy templates to tenant directory
```bash
cd /path/to/mycasa-pro
mkdir -p data/tenants/default

# Copy templates
cp templates/tenant_identity/*.md data/tenants/default/
mkdir -p data/tenants/default/memory

# Edit for your household
nano data/tenants/default/USER.md
nano data/tenants/default/TOOLS.md
nano data/tenants/default/HEARTBEAT.md
```

**Step 2:** Update agent initialization
In `agents/manager.py` (and all other agents), add to `__init__` or first user-facing method:

```python
async def prepare(self):
    """Load identity before any user interaction"""
    await self.prepare_for_session()
```

**Step 3:** Test identity loading
```python
from agents.manager import ManagerAgent
from core.tenant_identity import TenantIdentityManager

# Check identity status
status = TenantIdentityManager('default').get_identity_status()
print(status)

# Load identity
agent = ManagerAgent(tenant_id='default')
await agent.prepare_for_session()
print(f"Soul loaded: {agent.soul is not None}")
print(f"User context loaded: {agent.user_context is not None}")
```

### Phase 2: Proactive Heartbeat (HIGH)

**Step 1:** Integrate heartbeat checker into Manager Agent
```python
# In agents/manager.py
from agents.heartbeat_checker import HouseholdHeartbeatChecker

async def get_status_report(self):
    # Run heartbeat checks
    checker = HouseholdHeartbeatChecker(self.tenant_id)
    heartbeat_result = await checker.run_heartbeat()
    
    # Include findings in status report
    if heartbeat_result.findings:
        # Add to report
        pass
```

**Step 2:** Schedule heartbeat runs
Use the existing scheduler (`agents/scheduler.py`) to run heartbeat 2-4x/day:

```python
# Add scheduled job

```

---

## Expanded Implementation Roadmap (Detailed)

This is the end-to-end build plan to make MyCasaPro behave like Galidima.

### Phase 0 — Baseline Hygiene (Day 0)
1. Ensure tenant identity templates are installed on setup.
2. Ensure every agent calls `prepare_for_session()` before any user-facing action.
3. Confirm `data/tenants/<tenant>` exists and is per-user.
4. Add a CI-friendly sanity check (preflight) to verify templates exist.

### Phase 1 — Identity & Personality (Day 1)
**Goal:** Agents know who they are, who the user is, and the trust boundaries.

- Load `SOUL.md`, `USER.md`, `SECURITY.md` on every chat.
- Enforce a top-level “Identity Guard” system/developer prompt.
- Add a Settings → Identity page to edit templates.
- Add a “Last identity load time” indicator in System page.
- Log identity load failures to audit log (no silent failures).

### Phase 2 — Household Heartbeat (Day 2)
**Goal:** Proactive checks, not reactive chat.

- Implement `HouseholdHeartbeatChecker` with real DB checks.
- Run heartbeat hourly via scheduler; throttle by per-check intervals.
- Persist findings as `Notification` records.
- Add API: `/api/heartbeat/household/run` and `/api/heartbeat/household/status`.
- Display heartbeat findings on Dashboard + System Health.

### Phase 3 — Memory Consolidation (Day 3)
**Goal:** Curate long-term memory, avoid context drift.

- Add daily note ingestion (append raw observations).
- Nightly consolidation: summarize daily notes into `MEMORY.md`.
- Store last consolidation timestamp and show in Settings.
- Ensure SecondBrain writes for curated memory where possible.

### Phase 4 — Voice & Rituals (Day 4)
**Goal:** Consistent Galidima voice and behavior.

- Enforce “Read Before Acting” ritual: load identity + recent notes.
- Ban fabricated actions: actions must correspond to DB writes.
- Use deterministic formatting: status → actions → open questions.
- Add `VoicePolicy` guardrails (no chain-of-thought leaks).

### Phase 5 — Privacy & Multi-Tenant Integrity (Day 5)
**Goal:** Hard isolation between users.

- All queries must filter by `tenant_id`.
- Identity, memory, conversations, and backups are tenant-scoped.
- Add audit log for cross-tenant access attempts (blocked).

### Phase 6 — Social Behaviors (Day 6)
**Goal:** Human-like but reliable system behavior.

- Morning summary prompt with dynamic context.
- “It’s been a while” check-ins when idle > N days.
- Friendly check-ins with real facts (not placeholders).

### Phase 7 — QA & Verification (Day 7)
**Goal:** Ensure everything works before shipping.

- Add end-to-end scripted flow: signup → setup → heartbeat → task create.
- Verify tasks created by chat appear in UI.
- Validate no API endpoints return mock data.
job = ScheduledJob(
    id='household-heartbeat',
    name='Household Heartbeat Check',
    description='Proactive monitoring of household systems',
    agent='manager',
    task='run_heartbeat',
    frequency=ScheduleFrequency.DAILY,
    hour=9,  # 9am
    minute=0,
)
```

### Phase 3: Memory Consolidation (HIGH)

**Step 1:** Implement memory curator
The heartbeat checker has a placeholder for `run_memory_consolidation()`. Implement the logic:

```python
# In agents/heartbeat_checker.py
async def run_memory_consolidation(self):
    # 1. Load recent daily notes (last 7 days)
    # 2. Load MEMORY.md
    # 3. Use LLM to extract significant items
    # 4. Update MEMORY.md with distilled learnings
    # 5. Save consolidation timestamp
    pass
```

**Step 2:** Schedule weekly consolidation
```python
# Add to scheduler
job = ScheduledJob(
    id='memory-consolidation',
    name='Weekly Memory Consolidation',
    description='Review daily notes, update long-term memory',
    agent='manager',
    task='run_memory_consolidation',
    frequency=ScheduleFrequency.WEEKLY,
    day_of_week=6,  # Sunday
    hour=10,
    minute=0,
)
```

### Phase 4: Privacy & Social (MEDIUM)

See `MYCASA_GAP_ANALYSIS.md` for detailed implementation plans for:
- PrivacyGuard (compartmentalization)
- SocialBehaviorManager (when to speak vs stay silent)
- PersonalityEnforcer (remove filler phrases)

---

## Key Differences: Galidima vs MyCasaPro

| Aspect | Galidima | MyCasaPro (Before) | MyCasaPro (After) |
|--------|----------|-------------------|-------------------|
| **Identity** | SOUL.md + USER.md loaded every session | Agent personas in code only | Tenant-specific identity files |
| **Memory** | Daily notes → MEMORY.md consolidation | SecondBrain storage only | Curated long-term memory |
| **Proactive** | Heartbeat checks 2-4x/day | Reactive only | Proactive monitoring |
| **Personality** | Enforced via SOUL.md | Generic agent responses | Consistent voice per tenant |
| **Privacy** | SECURITY.md rules enforced | Database isolation only | Runtime privacy guards |
| **Social** | Knows when to stay silent | Always responds | Human-like judgment |

---

## Testing Checklist

### Identity Loading
- [ ] Create tenant directory with identity files
- [ ] Run `TenantIdentityManager.get_identity_status()` - should show all files present
- [ ] Call `agent.prepare_for_session()` - should load without errors
- [ ] Verify `agent.soul`, `agent.user_context`, etc. are populated

### Heartbeat Checks
- [ ] Run `checker.run_heartbeat()` - should complete without errors
- [ ] Verify `heartbeat-state.json` is created/updated
- [ ] Test quiet hours filtering (set time to 2am, verify only critical findings)
- [ ] Add mock findings and verify they're returned correctly

### Memory Consolidation
- [ ] Create daily notes for past 7 days
- [ ] Run `run_memory_consolidation()`
- [ ] Verify MEMORY.md is updated with significant items
- [ ] Check `lastConsolidation` timestamp is updated

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

---

## Next Steps

1. **Read** `MYCASA_GAP_ANALYSIS.md` for full details
2. **Review** the template files in `templates/tenant_identity/`
3. **Implement** Phase 1 (Identity Foundation) first
4. **Test** with your own tenant setup
5. **Iterate** based on what works/doesn't

Questions? The gap analysis doc has implementation details for each missing piece.
