"""
MyCasa Pro - Tenant Context & Isolation
Manages per-tenant context for multi-tenant operations
"""
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import uuid


class TenantContextError(Exception):
    """Raised when tenant context is missing or invalid"""


# Context variable for current tenant
_current_tenant: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)
_tenant_context: ContextVar[Optional['TenantContext']] = ContextVar('tenant_context', default=None)


@dataclass
class TenantContext:
    """Rich tenant context with metadata"""
    tenant_id: str
    name: str
    timezone: str = "UTC"
    locale: str = "en-US"
    created_at: datetime = None
    
    # Feature flags
    features_enabled: dict = None
    
    # Quotas
    quota_limits: dict = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.features_enabled is None:
            self.features_enabled = {}
        if self.quota_limits is None:
            self.quota_limits = {}


def get_current_tenant() -> str:
    """
    Get current tenant ID from context.
    Raises TenantContextError if not in tenant scope.
    """
    tenant_id = _current_tenant.get()
    if tenant_id is None:
        raise TenantContextError(
            "No tenant in context. Wrap operation in tenant_scope() or set_current_tenant()"
        )
    return tenant_id


def get_current_tenant_or_none() -> Optional[str]:
    """Get current tenant ID or None if not set"""
    return _current_tenant.get()


def get_tenant_context() -> Optional[TenantContext]:
    """Get full tenant context if available"""
    return _tenant_context.get()


def set_current_tenant(tenant_id: str, context: TenantContext = None) -> None:
    """
    Set current tenant for this context.
    Typically called at request/session start.
    """
    _current_tenant.set(tenant_id)
    if context:
        _tenant_context.set(context)


def clear_current_tenant() -> None:
    """Clear tenant context"""
    _current_tenant.set(None)
    _tenant_context.set(None)


@contextmanager
def tenant_scope(tenant_id: str, context: TenantContext = None) -> Generator[str, None, None]:
    """
    Context manager for tenant-scoped operations.
    
    Usage:
        with tenant_scope("tenant-123"):
            # All operations here are scoped to tenant-123
            data = get_tenant_data()
    """
    previous_tenant = _current_tenant.get()
    previous_context = _tenant_context.get()
    
    token_tenant = _current_tenant.set(tenant_id)
    token_context = _tenant_context.set(context) if context else None
    
    try:
        yield tenant_id
    finally:
        _current_tenant.reset(token_tenant)
        if token_context:
            _tenant_context.reset(token_context)


def generate_tenant_id() -> str:
    """Generate a new unique tenant ID"""
    return str(uuid.uuid4())


def is_valid_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format"""
    if not tenant_id or not isinstance(tenant_id, str):
        return False
    try:
        uuid.UUID(tenant_id)
        return True
    except ValueError:
        return len(tenant_id) >= 8 and tenant_id.replace('-', '').isalnum()


# ============ Tenant Registry ============

class TenantRegistry:
    """
    Registry for tenant metadata and lookup.
    Backed by database in production.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tenants = {}
        return cls._instance
    
    def register(self, context: TenantContext) -> None:
        """Register a tenant"""
        self._tenants[context.tenant_id] = context
    
    def get(self, tenant_id: str) -> Optional[TenantContext]:
        """Get tenant context by ID"""
        return self._tenants.get(tenant_id)
    
    def exists(self, tenant_id: str) -> bool:
        """Check if tenant exists"""
        return tenant_id in self._tenants
    
    def list_all(self) -> list:
        """List all tenant IDs"""
        return list(self._tenants.keys())
    
    def remove(self, tenant_id: str) -> bool:
        """Remove a tenant (soft delete in production)"""
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            return True
        return False


def get_tenant_registry() -> TenantRegistry:
    """Get the global tenant registry"""
    return TenantRegistry()


# ============ Default Tenant (for single-tenant mode) ============

DEFAULT_TENANT_ID = "default"

def ensure_default_tenant() -> TenantContext:
    """
    Ensure default tenant exists (for single-tenant/local mode).
    Returns the default tenant context.
    """
    registry = get_tenant_registry()
    
    if not registry.exists(DEFAULT_TENANT_ID):
        context = TenantContext(
            tenant_id=DEFAULT_TENANT_ID,
            name="Default Household",
            timezone="America/Los_Angeles",
            locale="en-US"
        )
        registry.register(context)
        return context
    
    return registry.get(DEFAULT_TENANT_ID)
