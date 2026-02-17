"""
MyCasa Pro Agents
Manager/persona agents for different domains
"""
from .base import BaseAgent
from .finance import FinanceAgent
from .maintenance import MaintenanceAgent
from .contractors import ContractorsAgent
from .projects import ProjectsAgent
from .security_manager import SecurityManagerAgent
from .janitor import JanitorAgent
from .manager import ManagerAgent
from .coordination import (
    AgentCoordinator,
    get_coordinator,
    EventType,
    Priority,
    Event,
    Workflow,
    WorkflowStep,
)
from .teams import (
    TeamOrchestrator,
    get_orchestrator,
    AgentTeam,
    TeamTask,
    TeamMode,
    PRESET_TEAMS,
    get_agent_instance,
)
from .security_integration import (
    SecureAgentCoordinator,
    get_secure_coordinator,
)

__all__ = [
    # Base
    "BaseAgent",

    # Domain Agents
    "FinanceAgent",
    "MaintenanceAgent",
    "ContractorsAgent",
    "ProjectsAgent",
    "SecurityManagerAgent",
    "JanitorAgent",
    "ManagerAgent",

    # Coordination
    "AgentCoordinator",
    "get_coordinator",
    "EventType",
    "Priority",
    "Event",
    "Workflow",
    "WorkflowStep",

    # Security Integration
    "SecureAgentCoordinator",
    "get_secure_coordinator",

    # Teams
    "TeamOrchestrator",
    "get_orchestrator",
    "AgentTeam",
    "TeamTask",
    "TeamMode",
    "PRESET_TEAMS",
    "get_agent_instance",
]
