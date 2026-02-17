"""
MyCasa Pro Agents Module

Multi-agent system for home management:
- Manager: Orchestrates all sub-agents, maintains global context (user-facing)
- Maintenance: Home tasks, repairs, readings, preventive schedules
- Finance: Bills, budgets, portfolio, transactions
- Contractors: Vendor relationships, quotes, scheduling
- Projects: Renovations, improvements, multi-phase tracking
- Janitor: Internal debugging, reliability, and repair orchestrator (not user-facing)
- SecurityManager: Security control plane for comms, network, supply-chain (not user-facing)
"""

from agents.base import BaseAgent
from agents.manager import ManagerAgent, SupervisorAgent
from agents.maintenance import MaintenanceAgent
from agents.finance import FinanceAgent
from agents.contractors import ContractorsAgent
from agents.projects import ProjectsAgent
from agents.janitor import JanitorAgent
from agents.security_manager import SecurityManagerAgent

__all__ = [
    "BaseAgent",
    "ManagerAgent",
    "SupervisorAgent",  # Backwards compatibility alias
    "MaintenanceAgent",
    "FinanceAgent",
    "ContractorsAgent",
    "ProjectsAgent",
    "JanitorAgent",
    "SecurityManagerAgent",
]
