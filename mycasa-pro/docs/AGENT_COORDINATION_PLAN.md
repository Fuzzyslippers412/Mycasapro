# MyCasa Pro Agent Coordination Plan
## "The Soccer Team" Architecture

> **Goal:** Each agent operates independently with clear responsibilities, but coordinates seamlessly like a world-class soccer team — passing work, covering positions, and winning together.

---

## 1. Agent Roles & Positions (Soccer Metaphor)

```
                    ┌─────────────────────────────────────────┐
                    │              USER (Coach)                │
                    └────────────────┬────────────────────────┘
                                     │
                    ┌────────────────▼────────────────────────┐
                    │     MANAGER (Galidima) — GOALKEEPER     │
                    │   Last line of defense, sees everything │
                    │   Routes all plays, makes final calls   │
                    └────────────────┬────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼───────┐          ┌────────▼────────┐          ┌────────▼───────┐
│   SECURITY    │          │     JANITOR     │          │    FINANCE     │
│   MANAGER     │          │                 │          │    MANAGER     │
│  (Sweeper)    │          │  (Defensive     │          │  (Defensive    │
│               │          │   Midfielder)   │          │   Midfielder)  │
│ Last defense  │          │ Cleans up,      │          │ Controls money │
│ before breach │          │ monitors health │          │ flow & limits  │
└───────────────┘          └─────────────────┘          └────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼───────┐          ┌────────▼────────┐          ┌────────▼───────┐
│  MAINTENANCE  │          │   PROJECTS      │          │  CONTRACTORS   │
│    AGENT      │          │    AGENT        │          │     AGENT      │
│  (Winger)     │          │  (Central       │          │   (Striker)    │
│               │          │   Midfielder)   │          │                │
│ Fast execution│          │ Coordinates     │          │ Scores goals   │
│ of daily ops  │          │ long-term work  │          │ (gets work     │
└───────────────┘          └─────────────────┘          │  done)         │
                                                        └────────────────┘
```

### Position Definitions

| Agent | Position | Zone | Primary Function |
|-------|----------|------|------------------|
| **Manager (Galidima)** | Goalkeeper | Full field visibility | Routes all plays, final authority, user interface |
| **Security Manager** | Sweeper/Libero | Defensive third | Last line before breach, protects all agents |
| **Janitor** | Defensive Midfielder | Middle third | Cleans up, monitors health, cost telemetry |
| **Finance Manager** | Defensive Midfielder | Middle third | Controls money flow, enforces guardrails |
| **Projects Agent** | Central Midfielder | Middle third | Coordinates long-term multi-agent work |
| **Maintenance Agent** | Winger | Attacking third | Fast execution of daily operations |
| **Contractors Agent** | Striker | Attacking third | Scores goals — gets external work done |

---

## 2. Communication Protocol

### 2.1 Event-Driven Message Bus

All agents communicate through the **Event Bus** — no direct agent-to-agent calls.

```python
# Standard event format
{
    "event_id": "uuid",
    "event_type": "task_handoff | cost_approval | status_update | alert",
    "timestamp": "ISO8601",
    "source_agent": "contractors",
    "target_agent": "finance | manager | broadcast",
    "payload": { ... },
    "requires_response": true/false,
    "timeout_ms": 30000
}
```

### 2.2 Communication Matrix

Who can initiate communication with whom:

| From ↓ / To → | Manager | Finance | Maintenance | Contractors | Projects | Security | Janitor |
|---------------|---------|---------|-------------|-------------|----------|----------|---------|
| **Manager**   | —       | ✓       | ✓           | ✓           | ✓        | ✓        | ✓       |
| **Finance**   | ✓       | —       | ✓ (cost)    | ✓ (approval)| ✓ (cost) | ✗        | ✓       |
| **Maintenance**| ✓      | ✓ (cost)| —           | ✓ (handoff) | ✓        | ✗        | ✗       |
| **Contractors**| ✓      | ✓ (cost)| ✗           | —           | ✓        | ✗        | ✗       |
| **Projects**  | ✓       | ✓ (cost)| ✓ (tasks)   | ✓ (jobs)    | —        | ✗        | ✗       |
| **Security**  | ✓ (alert)| ✗      | ✗           | ✗           | ✗        | —        | ✓ (alert)|
| **Janitor**   | ✓ (report)| ✓ (cost)| ✗          | ✗           | ✗        | ✓        | —       |

**Legend:**
- ✓ = Can initiate
- ✓ (type) = Can initiate only for that purpose
- ✗ = Cannot initiate (must go through Manager)

### 2.3 Message Types

1. **task_handoff** — One agent passes work to another
2. **cost_approval_request** — Request Finance approval for spending
3. **cost_approval_response** — Finance responds with approval/rejection
4. **status_update** — Broadcast current state
5. **alert** — Security or health concern
6. **query** — Request information from another agent
7. **report** — Janitor's telemetry and audit reports

---

## 3. Authority Boundaries

### 3.1 Autonomous Actions (No approval needed)

| Agent | Can Do Autonomously |
|-------|---------------------|
| **Manager** | Route messages, aggregate status, notify user |
| **Finance** | Track spending, update budgets, record costs |
| **Maintenance** | Create tasks, update task status, log readings |
| **Contractors** | Create job records, update job details, record evidence |
| **Projects** | Create milestones, update project status |
| **Security** | Monitor, log incidents, update baseline |
| **Janitor** | Record costs, generate reports, audit logs |

### 3.2 Requires Escalation to Manager

| Action | Agent | Escalate When |
|--------|-------|---------------|
| External messaging | All | Always (Manager routes to Galidima) |
| User notification | All | Priority >= high |
| Schedule change | Maintenance | Impacts other agents or user |
| Job creation | Contractors | Cost > $0 |
| New vendor | Contractors | Always |
| Incident response | Security | Severity P0 or P1 |
| Persona change | Janitor | Recommendation only; Manager decides |

### 3.3 Requires Finance Approval

| Action | Agent | Threshold |
|--------|-------|-----------|
| Contractor job | Contractors | All jobs with cost |
| Task with cost | Maintenance | Cost > $0 |
| Project expense | Projects | Any budget allocation |
| System cost | Janitor | Automatic tracking, alerts at thresholds |

### 3.4 Requires User Confirmation (via Manager)

- Irreversible actions
- Cost >= $500
- New vendor introduction
- Schedule disruption
- Contract/payment/credential operations
- Permission changes

---

## 4. Coordination Patterns

### 4.1 Task Handoff Chain

**Example: User requests faucet repair**

```
User → Manager → Maintenance (create task)
                      │
                      ▼
               Maintenance (needs contractor)
                      │
                      ▼
               Contractors (create job, PROPOSED)
                      │
                      ▼ (request details via Manager)
               Manager → External (Rakia/WhatsApp)
                      │
                      ▼ (receive details)
               Contractors (update job, PENDING)
                      │
                      ▼ (submit cost)
               Finance (review cost)
                      │
                      ├── APPROVED → Contractors (schedule job)
                      │                    │
                      │                    ▼
                      │              Manager → External (confirm)
                      │                    │
                      │                    ▼
                      │              Contractors (SCHEDULED → IN_PROGRESS → COMPLETED)
                      │                    │
                      │                    ▼
                      │              Janitor (record cost)
                      │
                      └── REJECTED → Contractors (BLOCKED)
                                          │
                                          ▼
                                    Manager → User (options)
```

### 4.2 Parallel Work Pattern

**Example: Monthly review**

```
Manager (initiates monthly review)
    │
    ├──→ Finance (run cost report)     ────┐
    │                                       │
    ├──→ Maintenance (overdue check)   ────┤
    │                                       │
    ├──→ Contractors (job summary)     ────┤
    │                                       │
    ├──→ Projects (status update)      ────┤
    │                                       │
    ├──→ Security (security posture)   ────┤
    │                                       │
    └──→ Janitor (system health)       ────┤
                                            │
                                            ▼
                                    Manager (aggregate & present)
                                            │
                                            ▼
                                         User
```

### 4.3 Blocking Dependency Pattern

**Example: Project with budget**

```
Projects (create project with $5000 budget)
    │
    ▼
Finance (allocate budget) ──── MUST COMPLETE BEFORE
    │
    ▼
Projects (create milestones)
    │
    ▼
Contractors (create jobs) ──── Each job requires:
    │                              Finance approval
    ▼
[Parallel job execution with individual Finance gates]
```

---

## 5. Shared Resources

### 5.1 Event Bus

- **Single instance** shared by all agents
- **Thread-safe** publish/subscribe
- **History buffer** of 1000 events
- **Agent activity tracking** built-in

```python
# Usage
from core.events import get_event_bus, emit, EventType

# Publish
emit(EventType.TASK_HANDOFF, agent_id="maintenance", ...)

# Subscribe
bus = get_event_bus()
bus.subscribe(EventType.COST_APPROVAL_REQUEST, my_handler)
```

### 5.2 Database Access

- **Each agent** has read/write access to its own tables
- **Manager** has read access to all tables
- **Janitor** has read access to all tables (audit)
- **Cross-agent queries** go through Manager

| Agent | Primary Tables | Can Read |
|-------|----------------|----------|
| Finance | bills, transactions, budgets, spend_entries, system_costs | All |
| Maintenance | maintenance_tasks, home_readings | contractors |
| Contractors | contractor_jobs, contractors | maintenance_tasks, projects |
| Projects | projects, project_milestones | contractor_jobs, maintenance_tasks |
| Security | (context files) | agent_logs |
| Janitor | system_cost_entries, agent_logs | All (audit) |

### 5.3 State Management

Each agent maintains state in:
1. **Database tables** — persistent structured data
2. **Context files** (`memory/agent/context/*.json`) — working state
3. **MEMORY.md** — long-term learnings

**Rule:** Agents MUST NOT directly modify another agent's context files.

---

## 6. Failure Handling

### 6.1 Agent Down Scenarios

| Failed Agent | Impact | Compensation |
|--------------|--------|--------------|
| **Manager** | Critical — no user interface | User contacts Galidima directly |
| **Finance** | Cost approvals blocked | Manager escalates to user |
| **Maintenance** | Tasks not tracked | Manual tracking until restored |
| **Contractors** | Jobs not progressing | Manager handles directly |
| **Projects** | Project updates delayed | Non-critical, can wait |
| **Security** | Monitoring gaps | Alert user immediately |
| **Janitor** | Cost tracking gaps | Finance can approximate |

### 6.2 Recovery Protocol

1. **Detection:** Event bus tracks agent heartbeats
2. **Notification:** Manager notified of agent failure
3. **Isolation:** Failed agent's pending work marked "blocked"
4. **Compensation:** Manager routes urgent work around failed agent
5. **Recovery:** On restart, agent processes backlog
6. **Reconciliation:** Janitor audits for missed events

### 6.3 Timeout & Retry Policy

```python
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds
MAX_RETRIES = 3
BACKOFF_BASE = 2  # Exponential backoff

# Retry on:
# - Timeout
# - Transient errors
# - Agent temporarily busy

# Fail immediately on:
# - Validation errors
# - Authorization denied
# - Agent explicitly rejects
```

---

## 7. Implementation Recommendations

### 7.1 New Interfaces Needed

#### AgentCoordinator (Middleware Layer)

```python
class AgentCoordinator:
    """
    Middleware that handles inter-agent coordination.
    All agent-to-agent communication goes through here.
    """
    
    def handoff_task(self, from_agent: str, to_agent: str, task: dict) -> str:
        """Transfer a task from one agent to another"""
        pass
    
    def request_approval(self, agent: str, approval_type: str, details: dict) -> dict:
        """Request approval from appropriate authority"""
        pass
    
    def broadcast_status(self, agent: str, status: dict) -> None:
        """Broadcast status update to interested agents"""
        pass
    
    def wait_for_dependency(self, task_id: str, dependency_id: str, timeout_ms: int) -> bool:
        """Wait for a dependency to complete"""
        pass
```

#### AgentHeartbeat System

```python
class HeartbeatMonitor:
    """
    Monitors agent health via periodic heartbeats.
    Detects failures and triggers recovery.
    """
    
    def register_agent(self, agent_id: str) -> None:
        pass
    
    def heartbeat(self, agent_id: str) -> None:
        pass
    
    def is_healthy(self, agent_id: str) -> bool:
        pass
    
    def get_failed_agents(self) -> List[str]:
        pass
```

### 7.2 Code Changes Required

1. **BaseAgent** — Add coordination methods:
   ```python
   def handoff_to(self, agent: str, task: dict) -> str
   def request_approval_from(self, agent: str, details: dict) -> dict
   def wait_for(self, dependency_id: str) -> bool
   ```

2. **EventBus** — Add response handling:
   ```python
   def publish_and_wait(self, event: SystemEvent, timeout_ms: int) -> SystemEvent
   ```

3. **Manager** — Add coordination routing:
   ```python
   def route_handoff(self, from_agent: str, to_agent: str, task: dict) -> str
   def mediate_approval(self, requester: str, approver: str, request: dict) -> dict
   ```

4. **All Agents** — Add heartbeat:
   ```python
   def heartbeat(self) -> dict:
       return {"agent": self.name, "state": "healthy", "current_task": ...}
   ```

### 7.3 Phased Implementation

**Phase 1: Event Bus Integration** (Week 1)
- [ ] Ensure all agents emit events for state changes
- [ ] Add event subscriptions for cross-agent awareness
- [ ] Implement heartbeat system

**Phase 2: Coordination Layer** (Week 2)
- [ ] Build AgentCoordinator middleware
- [ ] Implement task handoff protocol
- [ ] Add approval request/response flow

**Phase 3: Failure Handling** (Week 3)
- [ ] Implement failure detection
- [ ] Add compensation logic to Manager
- [ ] Build recovery and reconciliation

**Phase 4: Testing & Tuning** (Week 4)
- [ ] Integration tests for all coordination patterns
- [ ] Load testing for event bus
- [ ] Tune timeouts and retry policies

---

## 8. Success Metrics

The team is winning when:

1. **No dropped passes** — Every task handoff completes or fails cleanly
2. **No offsides** — Agents stay within authority boundaries
3. **No own goals** — No agent action harms another agent's work
4. **Good possession** — Events flow smoothly without bottlenecks
5. **Clean sheet** — Security detects all threats before breach
6. **Accurate scoreboard** — Manager can always answer "what's the status?"

---

## Summary

```
┌────────────────────────────────────────────────────────────────┐
│                     THE WINNING FORMULA                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Clear positions — Every agent knows their zone             │
│  2. Clean passes — Event bus for all communication             │
│  3. Defined plays — Handoff, parallel, blocking patterns       │
│  4. Authority lines — Who approves what                        │
│  5. Recovery drills — What happens when someone's down         │
│  6. One captain — Manager (Galidima) has final say             │
│                                                                │
│  RESULT: Independent agents working as one unit                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```
