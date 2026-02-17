# MyCasa Pro - Agent Coordination Matrix

**Updated:** 2026-01-28

This document defines the official coordination relationships between all agents.

---

## Coordination Matrix

| Agent | Reports To | Coordinates With | Receives From |
|-------|-----------|------------------|---------------|
| **Manager (Galidima)** | User | All agents | Status reports, escalations |
| **Finance** | Manager | Contractors, Projects, Maintenance, Janitor | Cost requests, budget queries |
| **Maintenance** | Manager | Contractors, Finance, Projects, Janitor, Security | Task delegation, contractor info |
| **Contractors** | Manager | Finance, Maintenance, Projects, Janitor, Security | Job requests, cost approvals |
| **Projects** | Manager | Finance, Maintenance, Contractors, Janitor | Budget, task spawning |
| **Janitor** | Manager | Finance, Security, Backup-Recovery, All agents | Logs, telemetry, incidents |
| **Security-Manager** | Manager | Janitor | Scan results, containment |
| **Backup-Recovery** | Manager | Janitor, Security | Backup requests, validations |
| **Mail-Skill** | Manager (attached) | None (capability only) | Fetch requests |

---

## Communication Flows

### Manager → Sub-agents
- Task delegation
- Policy updates
- Priority changes
- Approval decisions

### Sub-agents → Manager
- Status reports
- Escalations
- Approval requests
- Incident alerts

### Cross-Agent (Direct)

| From | To | Purpose |
|------|-----|---------|
| Maintenance | Contractors | Job requests |
| Contractors | Finance | Cost approval |
| Projects | Maintenance | Spawn tasks |
| Projects | Finance | Budget tracking |
| Janitor | All agents | Audit, verification |
| Security | Janitor | Containment coordination |

---

## Escalation Paths

```
Any Agent → Manager → User (if needed)
         ↓
      Janitor (for verification)
```

### P0/P1 Incidents
```
Detecting Agent → Manager (immediate)
               → Janitor (containment)
               → Security (if security-related)
```

---

## Authority Boundaries

### Auto-Execute (No Approval)
- Janitor: Cost telemetry, audits
- Finance: Price updates, calculations
- Maintenance: Routine task scheduling
- Backup: Scheduled backups

### Requires Manager Approval
- Contractors: Confirm jobs
- Projects: Mark at-risk
- Finance: High alerts
- Security: Permission changes

### Requires User Approval
- Any external communication
- Payments > threshold
- Irreversible actions
- New vendor introduction

---

## Agent SOULs Checklist

All agents have `COORDINATES WITH` or `COMMUNICATION CONTRACTS` section:

- [x] Manager (`agents/memory/manager/SOUL.md`)
- [x] Finance (`agents/memory/finance/SOUL.md`)
- [x] Maintenance (`agents/memory/maintenance/SOUL.md`)
- [x] Contractors (`agents/memory/contractors/SOUL.md`)
- [x] Projects (`agents/memory/projects/SOUL.md`)
- [x] Janitor (`agents/memory/janitor/SOUL.md`)
- [x] Security-Manager (`agents/memory/security-manager/SOUL.md`)
- [x] Backup-Recovery (`agents/memory/backup-recovery/SOUL.md`)
- [x] Mail-Skill (`agents/memory/mail-skill/SOUL.md`) — attached to Manager

---

## Validation

Janitor agent loads all SOUL.md files on startup and can verify agent actions against their defined coordination contracts.

```python
janitor.verify_agent_contract(agent_id, action, context)
```

Any agent acting outside its defined coordination scope triggers a P1 incident.
