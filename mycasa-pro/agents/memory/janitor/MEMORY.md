---
type: workspace
agent: janitor
file: MEMORY
---
# MEMORY.md — Janitor Agent Long-Term Memory

## Detection Thresholds

### Correctness
- Repeated action threshold: 10 occurrences
- Evidence required for task completion: Yes

### Reliability  
- Failure rate threshold: 3 failures
- Stale notification threshold: 7 days
- Queue backlog threshold: 100 items

### Security
- Secret patterns: password, api_key, secret, token, credential
- Permission audit frequency: Daily

---

## Incident History

<!-- Append significant incidents for pattern detection -->

---

## False Positives

<!-- Track false positives to tune detection -->

---

_[2026-01-28T12:17:51.002989]_ Resolved 5 false positive P0 incidents - secret patterns were in detection documentation, not actual secrets

## Remediation Patterns

<!-- Track successful remediation approaches -->

---

## Audits

<!-- Audit summaries -->

---

_[2026-01-28T11:43:35.222516]_ Audit completed: 5 findings, 5 incidents

## Learnings

<!-- Insights from incident handling -->

### 2026-01-30: API Response Contract Bug (CRITICAL)

**Issue:** All agents showed as "offline" in the UI despite backend being healthy.

**Root Cause (Multi-layer):**
1. `/api/main.py` line ~811 had `"processes": []` hardcoded with comment "For future use"
2. `/system/startup` only called `SystemStateManager.startup()`, NOT `LifecycleManager.startup()` — agents never actually started
3. "manager" agent was missing from `AGENT_NAMES` in `core/lifecycle.py` and from `ManagerSettings` in `core/settings_typed.py`

**Frontend Contract:** AgentManager expects `/system/monitor` to return:
```json
{
  "processes": [
    {"id": "finance", "state": "running", ...},
    {"id": "manager", "state": "running", ...}
  ]
}
```
It maps `state === "running"` → "active" in UI. Empty `processes` → all agents "offline".

**Detection Gap:** This was a cross-layer bug:
- Backend health check passed ✓
- Database connected ✓
- System "running" flag was true ✓
- But `processes` was empty and lifecycle wasn't started

**New Check Added:** `_check_api_response_contracts()` in `janitor_debugger.py` now validates:
1. `/system/monitor` doesn't have hardcoded empty `processes`
2. `/system/startup` calls lifecycle manager
3. State values match frontend expectations ("running" not "active")

**Lesson:** Always validate API response shapes match frontend expectations. "For future use" TODOs in production code are bugs waiting to happen.

## Telemetry

_[2026-01-29T08:24:13.737517]_ **test_metric - 2026-01-29 08:24**
_[2026-01-29T08:24:54.850129]_ **system_audit - 2026-01-29 08:24**
## system_audit

```json
{
  "finding_count": 0,
  "severity_counts": {},
  "cost_pct": 0.0
}
```

## test_metric

```json
{
  "status": "ok",
  "value": 42
}
```
