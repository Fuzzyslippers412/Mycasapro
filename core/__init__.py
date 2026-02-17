"""
MyCasa Pro - Core Infrastructure
Tenant isolation, settings, encryption, quotas, events, coordination
"""
from .tenant import (
    get_current_tenant,
    set_current_tenant,
    tenant_scope,
    TenantContext,
    TenantContextError
)
from .settings import (
    SettingsRegistry,
    get_setting,
    set_setting,
    export_settings,
    import_settings
)
from .events import (
    EventBus,
    get_event_bus,
    emit,
    emit_task_started,
    emit_task_completed,
    emit_cost,
    EventType,
    SystemEvent,
    AgentState
)
from .coordinator import (
    AgentCoordinator,
    get_coordinator,
    register_agent,
    handoff_task,
    request_approval,
    heartbeat,
    escalate_to_manager,
    escalate_to_user,
    TaskHandoff,
    ApprovalRequest,
    AgentHeartbeat,
    CoordinationEventType,
    COMMUNICATION_MATRIX
)

__all__ = [
    # Tenant
    'get_current_tenant',
    'set_current_tenant', 
    'tenant_scope',
    'TenantContext',
    'TenantContextError',
    # Settings
    'SettingsRegistry',
    'get_setting',
    'set_setting',
    'export_settings',
    'import_settings',
    # Events
    'EventBus',
    'get_event_bus',
    'emit',
    'emit_task_started',
    'emit_task_completed',
    'emit_cost',
    'EventType',
    'SystemEvent',
    'AgentState',
    # Coordination
    'AgentCoordinator',
    'get_coordinator',
    'register_agent',
    'handoff_task',
    'request_approval',
    'heartbeat',
    'escalate_to_manager',
    'escalate_to_user',
    'TaskHandoff',
    'ApprovalRequest',
    'AgentHeartbeat',
    'CoordinationEventType',
    'COMMUNICATION_MATRIX'
]
