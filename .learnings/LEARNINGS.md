# MyCasa Pro - Learnings

---

## [LRN-20260129-001] best_practice

**Logged**: 2026-01-29T13:06:00-08:00
**Priority**: medium
**Status**: promoted
**Area**: backend

### Summary
When SQLAlchemy model fields differ from API schema fields, the mapping must be explicit and consistent.

### Details
The InboxMessage model uses `preview` column, but the API exposes it as `body`. This caused a bug where `backend/api/main.py` accessed `m.body` directly (SQLAlchemy attribute) instead of `m.preview`.

The correct approach used by `agents/mail_skill.py`:
```python
"body": msg.preview or "",  # Map DB field to API field
```

The incorrect approach in `backend/api/main.py`:
```python
"body": m.body or "",  # Wrong - body doesn't exist on model
```

### Suggested Action
1. Add comment in model indicating API mapping: `preview = Column(Text)  # API: body`
2. Consider using a consistent pattern like `@property` or serialization method
3. Update CLAUDE.md with this convention

### Metadata
- Source: error
- Related Files: database/models.py, backend/api/main.py
- Tags: sqlalchemy, api, naming
- Promoted: CLAUDE.md

---

## [LRN-20260129-002] best_practice

**Logged**: 2026-01-29T13:06:00-08:00
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
Python `dict.get(key, default)` vs `value or default` for handling None

### Details
`dict.get("key", 0)` returns 0 only if key is MISSING.
If key exists but value is `None`, it returns `None`.

For database rows where columns can be NULL:
```python
# WRONG - returns None if rating exists but is None
c.get("rating", 0)

# CORRECT - handles both missing and None
c.get("rating") or 0

# ALSO CORRECT - explicit None check
c.get("rating", 0) if c.get("rating") is not None else 0
```

### Suggested Action
Use `value or default` pattern consistently when dealing with nullable database fields.

### Metadata
- Source: error
- Related Files: legacy/streamlit/4_👷_Contractors.py
- Tags: python, dict, null-handling

---

## [LRN-20260129-003] best_practice

**Logged**: 2026-01-29T13:15:00-08:00
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
Setup wizards must include OAuth credential configuration for external services like Google.

### Details
The MyCasa Pro setup wizard was missing the Google/gog OAuth setup step. Users need to:
1. Upload credentials.json from Google Cloud Console
2. Authenticate their Google account
3. Verify the connection works

This is a common pattern for any service requiring OAuth:
- Check if credentials exist
- Allow upload of OAuth client credentials
- Initiate OAuth flow
- Verify authentication succeeded

### Suggested Action
When adding new integrations that require OAuth:
1. Add credential check endpoint (`/api/{service}/credentials/check`)
2. Add credential upload endpoint (`/api/{service}/credentials/upload`)
3. Add auth initiation endpoint (`/api/{service}/auth/add`)
4. Add verification endpoint (`/api/{service}/auth/verify`)
5. Add setup wizard step with these flows

### Metadata
- Source: user_feedback
- Related Files: api/routes/google.py, frontend/src/components/SetupWizard/SetupWizard.tsx
- Tags: oauth, wizard, setup, gog

---
