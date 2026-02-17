# MyCasa Pro Agent Audit Report

**Date:** 2026-01-28
**Auditor:** Galidima
**Status:** ✅ REMEDIATED

---

## Executive Summary

**ISSUES FIXED:**
- ✅ **Janitor** - Rewritten to match SOUL (reliability + debugging + cost + contract verification)
- ✅ **Backup-Recovery** - Full implementation created
- ✅ **Mail-Skill** - SOUL written, defined as attached capability to Manager
- ✅ **Supervisor** - Removed (was redundant with Manager)
- 🟡 **Security-Manager** - Partial implementation (scanning methods still stubs)

---

## Agent-by-Agent Audit

### 1. Manager ✅ MOSTLY ALIGNED

**SOUL Says:**
- Single user-facing coordinator
- All agents report here
- Quick/Full/Audit reporting modes
- Cross-agent coordination
- External comms (Gmail, WhatsApp)

**CODE Does:**
- ✅ Lazy-loads sub-agents
- ✅ Agent health tracking
- ✅ Quick status implemented
- ✅ Full system report implemented
- ⚠️ Audit trace mode - PARTIAL (no deep traceability)
- ⚠️ External comms - Referenced but not directly integrated

**GAPS:**
- Need `audit_trace()` method for "why" questions
- Need direct Gmail/WhatsApp integration methods

---

### 2. Finance ✅ WELL ALIGNED

**SOUL Says:**
- Bill tracking, budget management
- Portfolio tracking
- Spend analysis with 3-layer model (source/rail/category)
- Week 1 baseline capture mode
- Friction-based controls

**CODE Does:**
- ✅ Bill management (1228 lines of code)
- ✅ Budget tracking
- ✅ Portfolio tracking with yfinance
- ✅ Spending model persistence
- ⚠️ Week 1 baseline mode - needs verification
- ⚠️ Friction controls - not found

**GAPS:**
- Implement friction-based spending prompts
- Verify baseline capture mode works

---

### 3. Maintenance ✅ ALIGNED

**SOUL Says:**
- Track/schedule/execute maintenance tasks
- Coordinate with Contractors
- Evidence-based completion
- Recurring task management

**CODE Does:**
- ✅ Task CRUD operations
- ✅ Status tracking
- ✅ Overdue detection
- ✅ Contractor coordination hooks
- ⚠️ Evidence requirements - schema exists but not enforced

**GAPS:**
- Enforce `evidence_required` field before completion

---

### 4. Contractors ✅ ALIGNED

**SOUL Says:**
- Job lifecycle management
- Finance approval flow
- Communication logging
- Evidence on completion

**CODE Does:**
- ✅ Full job model (832 lines)
- ✅ JobStatus enum matches soul
- ✅ CostStatus for finance approval
- ✅ Evidence fields

**GAPS:**
- Minor: Verify Finance integration is wired up

---

### 5. Projects ✅ ALIGNED

**SOUL Says:**
- Multi-phase project tracking
- Milestone management
- Budget tracking per project

**CODE Does:**
- ✅ Project CRUD
- ✅ Milestone tracking
- ✅ Budget monitoring
- ✅ Overdue milestone detection

**GAPS:**
- None significant

---

### 6. Janitor 🔴 MAJOR MISMATCH

**SOUL Says:**
- Debugging + Security + Repair Orchestrator
- Audit agents, tools, workflows
- Detect anomalies
- Reproduce and diagnose faults
- Quarantine misbehaving services
- Coordinate with Coding Agent
- Invariant enforcement

**CODE Does:**
- ❌ ONLY cost tracking (token usage, daily/monthly costs)
- ❌ No audit capability
- ❌ No anomaly detection
- ❌ No quarantine/repair
- ❌ No invariant checking

**ASSESSMENT:**
The Janitor code is a **Cost Telemetry Agent**, NOT the debugging/repair orchestrator described in the SOUL. The SOUL describes a critical infrastructure component that doesn't exist.

**REQUIRED ACTION:**
Either:
1. Rename current code to `CostAgent` and write real Janitor
2. Update SOUL to match actual cost-tracking role

---

### 7. Security-Manager 🟡 PARTIAL

**SOUL Says:**
- Secure communications audit
- Network listener/port scanning
- Credential protection
- Dependency vulnerability scanning
- Egress allowlist enforcement
- Supply-chain integrity

**CODE Does:**
- ✅ EGRESS_ALLOWLIST defined
- ✅ SECRET_PATTERNS for detection
- ⚠️ `get_security_metrics()` referenced but not fully implemented
- ❌ No active port scanning
- ❌ No dependency scanning
- ❌ No actual egress enforcement

**GAPS:**
- Implement `scan_listeners()` method
- Implement `check_dependencies()` method
- Add actual secret scanning in logs

---

### 8. Backup-Recovery 🔴 NO CODE

**SOUL Says:**
- Create/manage system backups
- Restore from known-good state
- Preserve user preferences
- Verify integrity
- Full/incremental/config-only backups

**CODE:**
- ❌ **NO IMPLEMENTATION EXISTS**
- Only SOUL.md in `agents/memory/backup-recovery/`

**REQUIRED ACTION:**
Create `backup_recovery.py` with actual backup functionality

---

### 9. Mail-Skill 🔴 NO SOUL

**SOUL:**
- Empty file: `<!-- Define persona here -->`

**CODE Does:**
- ✅ Gmail ingestion via gog
- ✅ WhatsApp ingestion via wacli
- ✅ Message normalization
- ✅ Deduplication

**REQUIRED ACTION:**
Write actual SOUL.md defining the agent's role and boundaries

---

### 10. Supervisor (Legacy?)

**SOUL:** None found

**CODE:**
- Appears to be older version of Manager
- Directly instantiates MaintenanceAgent and FinanceAgent
- May be deprecated?

**REQUIRED ACTION:**
Confirm if deprecated, if so remove or archive

---

## Priority Fix List

### P0 (Critical)
1. **Janitor** - Either rewrite to match SOUL or rename/update SOUL
2. **Backup-Recovery** - Create actual implementation

### P1 (High)
3. **Mail-Skill** - Write proper SOUL.md
4. **Security-Manager** - Complete scanning implementations

### P2 (Medium)
5. **Manager** - Add audit trace method
6. **Finance** - Verify friction controls
7. **Supervisor** - Deprecate if redundant with Manager

---

## Recommendations

### Option A: Minimal Fixes (Ship Current)
- Update Janitor SOUL to "Cost Telemetry Agent"
- Remove Backup-Recovery SOUL (no implementation)
- Write Mail-Skill SOUL to match actual behavior
- Accept Security-Manager as "advisory only"

### Option B: Full Implementation (Match Souls)
- Implement real Janitor (debugging/repair/audit)
- Implement Backup-Recovery agent
- Complete Security-Manager scanning
- Add Manager audit traces

**Recommended:** Option A for now, Option B as follow-up project

---

## Files to Update

| File | Action |
|------|--------|
| `agents/memory/janitor/SOUL.md` | Rewrite to "Cost Telemetry" OR implement real janitor |
| `agents/memory/backup-recovery/SOUL.md` | Delete OR create backup_recovery.py |
| `agents/memory/mail-skill/SOUL.md` | Write actual persona |
| `agents/security_manager.py` | Add scanning methods |
| `agents/supervisor.py` | Mark deprecated or remove |

---

*Audit complete. Awaiting direction on Option A vs Option B.*
