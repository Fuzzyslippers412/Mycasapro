# MyCasa Pro - Error Log

---

## [ERR-20260129-001] inbox_messages_body_column

**Logged**: 2026-01-29T13:05:00-08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
Database schema mismatch: `backend/api/main.py` referenced `m.body` but SQLAlchemy model `InboxMessage` uses `preview` column.

### Error
```
(sqlite3.OperationalError) no such column: inbox_messages.body
[SQL: SELECT inbox_messages.body AS inbox_messages_body ...]
```

### Context
- The `InboxMessage` model in `database/models.py` uses `preview = Column(Text)` for message body
- The API endpoint at line 1422 of `backend/api/main.py` was incorrectly referencing `m.body`
- The Pydantic schema in `api/routes/inbox.py` uses `body` as the API field name (correct)
- The `mail_skill.py` agent correctly maps `preview` → `body` for its responses

### Fix Applied
Changed `m.body` to `m.preview` in `backend/api/main.py` line 1422.

### Suggested Future Prevention
- When model fields differ from API schema fields, add comments noting the mapping
- Consider using Pydantic `alias` or `Field(serialization_alias=)` to make mappings explicit

### Metadata
- Reproducible: yes
- Related Files: backend/api/main.py, database/models.py, api/routes/inbox.py

### Resolution
- **Resolved**: 2026-01-29T13:05:00-08:00
- **Notes**: Changed `m.body` to `m.preview` in backend/api/main.py

---

## [ERR-20260129-002] contractors_none_rating

**Logged**: 2026-01-29T13:05:00-08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
TypeError in Contractors page: `c.get("rating", 0)` doesn't handle `None` values stored in database.

### Error
```
TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
File "legacy/streamlit/4_👷_Contractors.py", line 49
avg_rating = sum(c.get("rating", 0) for c in contractors) / len(contractors)
```

### Context
- `dict.get("key", default)` returns `None` if key exists but value is `None`
- Database has contractors with `rating = NULL`
- The `or 0` pattern handles both missing keys AND `None` values

### Fix Applied
Changed `c.get("rating", 0)` to `c.get("rating") or 0` in line 49.

### Suggested Future Prevention
- Always use `value or default` pattern when database columns can be NULL
- Add data validation on insert to enforce non-null ratings

### Metadata
- Reproducible: yes
- Related Files: legacy/streamlit/4_👷_Contractors.py

### Resolution
- **Resolved**: 2026-01-29T13:05:00-08:00
- **Notes**: Changed to `or 0` pattern to handle None values

---

## [ERR-20260129-003] turbopack_sst_persistence

**Logged**: 2026-01-29T13:05:00-08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
Next.js Turbopack cache corruption: "Persisting failed: Unable to write SST file"

### Error
```
Persisting failed: Unable to write SST file 00005406.sst
Caused by: No such file or directory (os error 2)
```

### Context
- SST files are part of Turbopack's persistent caching system
- Directory or file may have been corrupted or deleted while Turbopack was running
- Common after system crashes, force kills, or disk issues

### Fix Applied
Cleared the cache directory: `rm -rf frontend/.next/cache`

### Suggested Future Prevention
- Add `frontend/.next/cache` cleanup to start script
- Consider disabling persistent cache in dev (`--turbo-no-persist`)

### Metadata
- Reproducible: intermittent
- Related Files: frontend/.next/cache/

### Resolution
- **Resolved**: 2026-01-29T13:05:00-08:00
- **Notes**: Cache cleared manually

---

## [ERR-20260129-004] streamlit_use_container_width_deprecated

**Logged**: 2026-01-29T13:05:00-08:00
**Priority**: low
**Status**: pending
**Area**: frontend

### Summary
Streamlit deprecation warning: `use_container_width` will be removed after 2025-12-31.

### Error
```
Please replace `use_container_width` with `width`.
For `use_container_width=True`, use `width='stretch'`.
For `use_container_width=False`, use `width='content'`.
```

### Context
- Multiple Streamlit components using deprecated parameter
- Needs to be updated before the parameter is removed

### Suggested Fix
Search and replace across all Streamlit files:
- `use_container_width=True` → `width='stretch'`
- `use_container_width=False` → `width='content'`

### Metadata
- Reproducible: yes
- Related Files: legacy/streamlit/*.py

---
## [ERR-20260205-001] settings_typed_pydantic_missing

**Logged**: 2026-02-05T00:00:00-08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Failed to update settings via Python because `pydantic` module not found in current environment.

### Error
```
ModuleNotFoundError: No module named 'pydantic'
```

### Context
- Command: python3 - <<'PY' ... import core.settings_typed ...
- Location: /Users/chefmbororo/clawd/apps/mycasa-pro
- Intended change: set all agent models to qwen

### Suggested Fix
Use the app's venv python or install deps; alternatively edit the persisted settings JSON directly via file ops.

### Metadata
- Reproducible: yes
- Related Files: core/settings_typed.py, data/system_state.json
- Tags: env, pydantic, settings
---
## [ERR-20260205-002] websockets_timeout_py314

**Logged**: 2026-02-05T00:00:00-08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
WebSocket handshake failed due to asyncio timeout bug in Python 3.14 / websockets legacy server.

### Error
```
RuntimeError: Timeout should be used inside a task
```

### Context
- Endpoint: /events websocket
- Server: api/main.py
- Environment: Python 3.14, websockets legacy server

### Suggested Fix
Add env toggle to disable WS or adjust server to avoid open_timeout; fallback to polling in frontend.

### Metadata
- Reproducible: yes
- Related Files: api/main.py, frontend/src/components/AgentActivityDashboard/AgentActivityDashboard.tsx
- Tags: websocket, python314, timeout
---
