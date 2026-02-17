# MyCasa Pro - Janitor Audit Report

**Date:** 2026-01-29 17:51 PST  
**Files Checked:** 136  
**Duration:** 4.9 seconds

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 0 |
| 🟠 High | 1 |
| 🟡 Medium | 100 |
| 🟢 Low | 32 |
| ℹ️ Info | 17 |

---

## 🟠 HIGH Priority (Fix Now)

### 1. Next.js Dev Lock File
- **Status:** ✅ FIXED
- **Issue:** `frontend/.next/dev/lock` existed
- **Action:** Removed lock file

---

## 🟡 MEDIUM Priority (Should Fix)

### 1. Missing YAML Frontmatter (30 files)
Agent workspace files missing `---` delimited YAML header:
- `agents/security/*.md` (5 files)
- `agents/projects/*.md` (5 files)
- `agents/janitor/*.md` (5 files)
- `agents/finance/*.md` (5 files)
- `agents/maintenance/*.md` (5 files)
- `agents/contractors/*.md` (5 files)

**Fix:** Add frontmatter to each file:
```yaml
---
type: workspace
agent: <agent_id>
---
```

### 2. Bare `except:` Clauses (2 files)
- `backend/agents/coordination.py:1012`
- `backend/api/main.py:1568`

**Fix:** Change `except:` to `except Exception as e:`

### 3. Hardcoded Values (20+ occurrences)
- Hardcoded localhost URLs (should use config)
- Hardcoded tenant IDs (should be dynamic)
- Potential API key patterns detected (false positives - they're variable names)

### 4. Null Safety Issues (25+ occurrences)
Index `[0]` access without length check:
- `install.py:73`
- `agents/janitor_debugger.py:353, 843, 1127, 1130`
- `agents/security_manager.py:231`
- `agents/mail_skill.py:131, 301`
- `backend/api/main.py:630, 699, 1123, 1981, 1993, 2053, 2111, 2143, 2324, 2453, 2466, 2564, 2661, 2739, 3149`
- And others...

**Fix:** Add `if list_var:` or `if len(list_var) > 0:` before access

### 5. SetupWizard / Backend Field Mismatch
- `whatsappNumber` in backend but not frontend
- `enableWhatsapp` in backend but not frontend

---

## 🟢 LOW Priority (Nice to Have)

### 1. Missing Required Fields in SecondBrain Notes
- `inbox/sb_20260129194217_ce114e.md` - missing `tenant`
- `conversations/conv_main.md` - missing `type`, `tenant`, `agent`, `created_at`
- `conversations/conv_test_api_conv.md` - missing same fields

### 2. Unused Imports (9 files)
- `database/models.py:5` - `Index`
- `api/routes/memory.py:11` - `datetime`
- `api/routes/agent_chat.py:12` - `asyncio`
- `backend/agents/teams.py:8` - `Callable`, `Literal`
- `backend/agents/janitor.py:5, 8` - `Callable`, `subprocess`
- `backend/api/routes/teams.py:8` - `datetime`
- `backend/api/routes/chat.py:5, 6` - `Form`, `Field`

### 3. Hardcoded Tenant IDs
- `config/settings.py:9`
- `core/secondbrain/__init__.py:11`
- `connectors/whatsapp/connector.py:249`
- And others...

---

## ℹ️ INFO (For Reference)

### TODO/FIXME Markers Found
- `agents/backup_recovery.py:231, 378, 403` - Pull from settings, apply patterns, integrate scheduler
- `agents/manager.py:331, 425, 427` - Missed run detection, trigger tracking, rollback options
- `api/routes/connectors.py:310` - Actually save config to settings
- `api/routes/inbox.py:246` - Track last sync time
- `connectors/whatsapp/connector.py:175` - Implement wacli integration

---

## ✅ Passing Checks

- **TypeScript:** Compiles clean (0 errors)
- **API Endpoints:** All 8 tested endpoints respond correctly
- **Database:** Exists and valid (232K)
- **Health Check:** OK
- **SecondBrain:** 24 notes indexed
- **Agent Activity API:** Working

---

## Recommended Fix Order

1. ~~Remove Next.js lock file~~ ✅ DONE
2. ~~Create .env from example~~ ✅ DONE  
3. Fix bare `except:` clauses (2 files) - prevents hidden bugs
4. Add null safety checks to high-traffic paths (backend/api/main.py)
5. Add YAML frontmatter to agent workspace files
6. Clean up unused imports
7. Address TODO items based on priority

---

## API Endpoints Verified Working

| Endpoint | Status |
|----------|--------|
| `/health` | ✅ OK |
| `/status` | ✅ OK |
| `/portfolio` | ✅ OK (0 holdings) |
| `/system/monitor` | ✅ OK |
| `/api/secondbrain/stats` | ✅ OK (24 notes) |
| `/api/agent-activity/manager/activity` | ✅ OK |
| `/inbox/unread-count` | ✅ OK |
| `/api/settings` | ✅ OK |
