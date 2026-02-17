# MyCasa Pro - Architecture

> **Product Vision:** A packaged, installable Super Skill for any Clawdbot user.  
> Multi-tenant, pluggable connectors, modular managers, first-run wizard.

## Core Principles

1. **Install Once, Configure Per-Tenant** — Single skill install, tenant-specific data isolation
2. **Pluggable Everything** — Connectors, managers, agents are all adapters
3. **Sensible Defaults** — Works out of the box with minimal config
4. **Settings Hierarchy** — Global → Manager → Connector → Tenant overrides
5. **Audit Everything** — Full trail for billing, debugging, compliance

---

## Directory Structure

```
mycasa-pro/
├── SKILL.md                    # Clawdbot skill manifest
├── install.py                  # One-click installer
├── migrate.py                  # Schema migrations
├── CHANGELOG.md
│
├── core/
│   ├── __init__.py
│   ├── tenant.py               # Tenant context & isolation
│   ├── settings.py             # Settings registry & loader
│   ├── encryption.py           # Per-tenant key management
│   ├── quota.py                # Rate limits & usage tracking
│   └── events.py               # Event bus for cross-module comms
│
├── connectors/
│   ├── __init__.py
│   ├── base.py                 # Connector interface (abstract)
│   ├── registry.py             # Connector discovery & registration
│   ├── gmail/
│   │   ├── __init__.py
│   │   ├── connector.py
│   │   ├── auth.py
│   │   └── settings.py
│   ├── whatsapp/
│   ├── calendar/
│   ├── bank_import/
│   └── sms/
│
├── managers/
│   ├── __init__.py
│   ├── base.py                 # Manager interface (abstract)
│   ├── registry.py             # Manager discovery
│   ├── finance/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── settings.py
│   │   └── models.py
│   ├── maintenance/
│   ├── security/
│   ├── contractors/
│   └── projects/
│
├── database/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy models (multi-tenant)
│   ├── migrations/             # Alembic migrations
│   └── seeds/                  # Default data seeders
│
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── auth.py                 # Tenant auth middleware
│   └── routes/
│
├── ui/
│   ├── app.py                  # Streamlit entry
│   ├── pages/
│   └── components/
│
├── wizard/
│   ├── __init__.py
│   ├── intake.py               # First-run wizard logic
│   └── templates/              # Wizard step templates
│
├── templates/
│   ├── settings_export.json    # Settings schema
│   └── demo_dataset.json       # Quick-start sample data
│
└── docs/
    ├── INSTALL.md
    ├── CONNECTORS.md
    ├── QUICKSTART.md
    └── TROUBLESHOOTING.md
```

---

## Settings Architecture

### Hierarchy (lowest to highest priority)

```
1. Defaults (code)           — Shipped with skill
2. Global Settings           — Infrastructure-wide
3. Manager Settings          — Per-manager config
4. Connector Settings        — Per-connector config  
5. Tenant Settings           — Per-tenant overrides
6. Runtime Overrides         — Temporary/session
```

### Storage

```python
# settings table
class Setting(Base):
    __tablename__ = "settings"
    
    id: int
    tenant_id: str | None       # NULL = global
    scope: str                  # "global" | "manager" | "connector" | "tenant"
    namespace: str              # "finance" | "gmail" | "maintenance"
    key: str
    value: JSON
    encrypted: bool
    version: int
    created_at: datetime
    updated_at: datetime
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'scope', 'namespace', 'key'),
    )
```

### Export/Import Format

```json
{
  "version": "1.0.0",
  "exported_at": "2026-01-28T22:00:00Z",
  "settings": {
    "global": { ... },
    "managers": {
      "finance": { ... },
      "maintenance": { ... }
    },
    "connectors": {
      "gmail": { ... },
      "whatsapp": { ... }
    }
  }
}
```

---

## Connector Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime
from enum import Enum

class ConnectorStatus(Enum):
    DISABLED = "disabled"
    AUTHENTICATING = "authenticating"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

class BaseConnector(ABC):
    """Abstract base for all connectors"""
    
    connector_id: str           # "gmail", "whatsapp", etc.
    display_name: str
    description: str
    version: str
    
    @abstractmethod
    async def authenticate(self, tenant_id: str, credentials: Dict) -> bool:
        """Run auth flow, store tokens"""
        pass
    
    @abstractmethod
    async def health_check(self, tenant_id: str) -> ConnectorStatus:
        """Check connection health"""
        pass
    
    @abstractmethod
    async def sync(self, tenant_id: str, since: datetime = None) -> List[Dict]:
        """Pull new events/messages since timestamp"""
        pass
    
    @abstractmethod
    async def send(self, tenant_id: str, payload: Dict) -> Dict:
        """Send outbound message/action"""
        pass
    
    @abstractmethod
    def get_settings_schema(self) -> Dict:
        """Return JSON schema for connector settings"""
        pass
    
    # Built-in behaviors
    def get_retry_policy(self) -> Dict:
        return {
            "max_retries": 3,
            "backoff_base": 2,
            "backoff_max": 300
        }
    
    def get_sync_schedule(self) -> str:
        return "*/5 * * * *"  # Every 5 minutes default
```

---

## Multi-Tenant Isolation

### Tenant Context

```python
from contextvars import ContextVar
from functools import wraps

_current_tenant: ContextVar[str] = ContextVar('current_tenant', default=None)

def get_current_tenant() -> str:
    tenant = _current_tenant.get()
    if not tenant:
        raise TenantContextError("No tenant in context")
    return tenant

def tenant_scope(tenant_id: str):
    """Context manager for tenant operations"""
    token = _current_tenant.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant.reset(token)
```

### Database Isolation

All models include `tenant_id`:

```python
class TenantMixin:
    tenant_id = Column(String(36), nullable=False, index=True)
    
    @declared_attr
    def __table_args__(cls):
        return (
            Index(f'ix_{cls.__tablename__}_tenant', 'tenant_id'),
        )

# Automatic tenant filtering
class TenantQuery(Query):
    def filter_by_tenant(self):
        tenant_id = get_current_tenant()
        return self.filter_by(tenant_id=tenant_id)
```

### Per-Tenant Encryption

```python
class TenantKeyManager:
    def get_key(self, tenant_id: str) -> bytes:
        """Derive tenant-specific encryption key"""
        # Key derivation from master + tenant_id
        pass
    
    def encrypt(self, tenant_id: str, data: bytes) -> bytes:
        pass
    
    def decrypt(self, tenant_id: str, data: bytes) -> bytes:
        pass
```

---

## First-Run Wizard

### Steps

1. **Welcome** — What is MyCasa Pro, what it does
2. **Tenant Setup** — Name, timezone, locale
3. **Income Source** — Primary funding source (required)
4. **Budgets** — System cost cap, spend guardrails (with defaults)
5. **Connectors** — Enable Gmail, WhatsApp, etc. (optional, can skip)
6. **Notifications** — How to receive alerts
7. **Complete** — Summary + "Start Using"

### Wizard State

```python
class WizardState(Base):
    __tablename__ = "wizard_state"
    
    tenant_id: str (PK)
    current_step: int
    completed_steps: JSON        # List of step IDs
    step_data: JSON              # Collected data per step
    started_at: datetime
    completed_at: datetime | None
```

---

## Quota & Usage Tracking

```python
class UsageEntry(Base):
    __tablename__ = "usage_entries"
    
    id: int
    tenant_id: str
    category: str               # "ai_api", "connector_sync", "storage"
    metric: str                 # "tokens", "requests", "bytes"
    amount: float
    unit_cost: float | None
    timestamp: datetime
    metadata: JSON

class TenantQuota(Base):
    __tablename__ = "tenant_quotas"
    
    tenant_id: str (PK)
    category: str (PK)
    limit_value: float
    period: str                 # "day", "month"
    current_usage: float
    reset_at: datetime
```

---

## Installation Flow

```bash
# From Clawdbot
clawdbot skill install mycasa-pro

# Or from ClawdHub
clawdhub install mycasa-pro
```

### install.py

```python
def install():
    """One-click installation"""
    
    # 1. Validate environment
    check_python_version()
    check_dependencies()
    
    # 2. Create data directory
    ensure_data_dir()
    
    # 3. Initialize database
    init_database()
    run_migrations()
    
    # 4. Seed defaults
    seed_default_settings()
    seed_connector_stubs()
    
    # 5. Register with Clawdbot
    register_skill()
    
    # 6. Print success + next steps
    print_success_message()
```

---

## Versioning & Migrations

- **Semantic Versioning:** MAJOR.MINOR.PATCH
- **Database Migrations:** Alembic with auto-generation
- **Settings Migrations:** Version field + upgrade scripts
- **Breaking Changes:** MAJOR bump, migration guide required

```python
# migrate.py
def migrate():
    """Run pending migrations"""
    
    # 1. Backup current DB
    backup_database()
    
    # 2. Run Alembic migrations
    run_alembic_upgrade()
    
    # 3. Run settings migrations
    migrate_settings()
    
    # 4. Validate integrity
    validate_schema()
```

---

## API Endpoints (FastAPI)

```
# Tenant
POST   /api/tenant/setup          # First-run setup
GET    /api/tenant/status         # Tenant health

# Settings
GET    /api/settings              # Get all settings
PUT    /api/settings/{scope}/{ns} # Update settings
POST   /api/settings/export       # Export to JSON
POST   /api/settings/import       # Import from JSON

# Connectors
GET    /api/connectors            # List available
POST   /api/connectors/{id}/auth  # Start auth flow
GET    /api/connectors/{id}/status
POST   /api/connectors/{id}/sync  # Trigger sync

# Managers
GET    /api/managers              # List managers
GET    /api/managers/{id}/status

# Inbox (aggregated events)
GET    /api/inbox                 # All events from all connectors
POST   /api/inbox/{id}/action     # Take action on event

# Usage
GET    /api/usage                 # Current usage stats
GET    /api/usage/history         # Historical usage
```

---

## Agent Activity Dashboard (HYPERCONTEXT)

Real-time activity tracking for agents with visualization similar to HYPERCONTEXT.

### API Endpoints

```
# Agent Activity
POST   /api/agent-activity/{agent_id}/activity    # Record activity
GET    /api/agent-activity/{agent_id}/activity    # Get activity summary
GET    /api/agent-activity/{agent_id}/sessions    # List sessions
DELETE /api/agent-activity/{agent_id}/sessions/{session_id}  # Delete session
```

### Activity Schema

```python
{
    "agent_id": "manager",
    "session_id": "manager-20260129-174402",
    
    # Context tracking
    "context_percent": 37.5,
    "context_used": 75000,
    "context_limit": 200000,
    "runway_tokens": 125000,
    "velocity": 75000.0,
    
    # Files
    "total_files": 3,
    "files_modified": 1,
    "files_read": 2,
    "files_touched": [
        {"path": "/agents/coordinator.py", "action": "modified", "timestamp": "..."}
    ],
    
    # Tools
    "tool_usage": {"read": 8, "write": 4, "bash": 12, "edit": 2},
    
    # Systems
    "systems": {"Gmail": "ok", "WhatsApp": "ok", "Database": "ok"},
    
    # Decisions & Questions
    "decisions": ["Pure knowledge skill", "Recency heat model"],
    "questions": ["Visual vocabulary evolution?"],
    
    # Visualization
    "threads": [{"id": "agents", "name": "Agents", "status": "done", "children": [...]}],
    "heat_map": [{"topic": "agents", "score": 0.99, "color": "#ff4d4d"}]
}
```

### Frontend Components

- **AgentActivityDashboard** (`frontend/src/components/AgentActivityDashboard/`)
  - Dark theme with gradient background
  - Context usage progress bar
  - Velocity + runway display
  - Threads panel (✓ / ⏳ / 💡 status)
  - Heat map (red → stale)
  - Files touched (◆ modified / ◇ read)
  - Tools used bar chart
  - Systems badges
  - Decisions + Questions lists

### Integration Points

1. **System Page** → "Activity Map" tab (all agents)
2. **AgentManager Modal** → "Activity" tab per agent

---

## Next Steps

1. [x] Architecture document
2. [x] Core tenant/settings infrastructure
3. [x] Connector base class + registry
4. [x] Manager base class + registry
5. [x] Finance Manager implementation
6. [x] First-run wizard (SetupWizard)
7. [x] Settings export/import
8. [x] Multi-tenant database models
9. [x] Agent Activity Dashboard (HYPERCONTEXT-style)
10. [ ] Agent activity real-time WebSocket
11. [ ] Wire agents to automatically record activity
12. [ ] Installation script improvements
13. [ ] Documentation updates
