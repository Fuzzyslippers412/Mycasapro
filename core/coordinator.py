"""
MyCasa Pro - Agent Coordination Layer
Implements the "Soccer Team" coordination architecture for inter-agent communication.
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import uuid
import logging

from core.events import (
    EventType, AgentState, get_event_bus, emit
)

logger = logging.getLogger("mycasa.coordinator")


# ═══════════════════════════════════════════════════════════════════════════════
# Extended Event Types for Coordination
# ═══════════════════════════════════════════════════════════════════════════════

class CoordinationEventType(Enum):
    """Extended event types for agent coordination"""
    # Task handoff
    TASK_HANDOFF_REQUEST = "task_handoff_request"
    TASK_HANDOFF_ACCEPTED = "task_handoff_accepted"
    TASK_HANDOFF_REJECTED = "task_handoff_rejected"
    
    # Cost approval
    COST_APPROVAL_REQUEST = "cost_approval_request"
    COST_APPROVAL_GRANTED = "cost_approval_granted"
    COST_APPROVAL_DENIED = "cost_approval_denied"
    
    # Status updates
    STATUS_BROADCAST = "status_broadcast"
    
    # Alerts & escalation
    ESCALATION_TO_MANAGER = "escalation_to_manager"
    ESCALATION_TO_USER = "escalation_to_user"
    
    # Heartbeat
    HEARTBEAT = "heartbeat"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    
    # Query/response
    QUERY_REQUEST = "query_request"
    QUERY_RESPONSE = "query_response"


# ═══════════════════════════════════════════════════════════════════════════════
# Communication Matrix - Who can talk to whom
# ═══════════════════════════════════════════════════════════════════════════════

COMMUNICATION_MATRIX = {
    "manager": ["finance", "maintenance", "contractors", "projects", "security", "janitor"],
    "finance": ["manager", "maintenance", "contractors", "projects", "janitor"],
    "maintenance": ["manager", "finance", "contractors", "projects"],
    "contractors": ["manager", "finance", "projects"],
    "projects": ["manager", "finance", "maintenance", "contractors"],
    "security": ["manager", "janitor"],
    "janitor": ["manager", "finance", "security"]
}

# Actions that require Finance approval
FINANCE_APPROVAL_REQUIRED = {
    "contractor_job_create": True,
    "task_with_cost": True,
    "project_expense": True,
    "budget_allocation": True
}

# Actions that require escalation to Manager
MANAGER_ESCALATION_REQUIRED = {
    "external_message": True,
    "user_notification_high": True,
    "schedule_change_impact": True,
    "new_vendor": True,
    "incident_p0_p1": True
}

# Actions requiring user confirmation (via Manager)
USER_CONFIRMATION_REQUIRED = {
    "irreversible_action": True,
    "cost_over_500": True,
    "new_vendor_introduction": True,
    "schedule_disruption": True,
    "contract_operations": True,
    "permission_changes": True
}


# ═══════════════════════════════════════════════════════════════════════════════
# Coordination Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskHandoff:
    """Represents a task being passed between agents"""
    handoff_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: str = ""
    to_agent: str = ""
    task_type: str = ""
    task_data: Dict[str, Any] = field(default_factory=dict)
    priority: str = "medium"
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_ms: int = 30000
    status: str = "pending"  # pending, accepted, rejected, timeout
    response_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "task_type": self.task_type,
            "task_data": self.task_data,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "timeout_ms": self.timeout_ms,
            "status": self.status,
            "response_data": self.response_data
        }


@dataclass
class ApprovalRequest:
    """Request for cost/action approval"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    requester_agent: str = ""
    approver_agent: str = "finance"  # Default to finance for cost approvals
    approval_type: str = ""  # cost, action, vendor, etc.
    amount_usd: Optional[float] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_ms: int = 60000
    status: str = "pending"  # pending, approved, denied, timeout
    response_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester_agent": self.requester_agent,
            "approver_agent": self.approver_agent,
            "approval_type": self.approval_type,
            "amount_usd": self.amount_usd,
            "description": self.description,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "timeout_ms": self.timeout_ms,
            "status": self.status,
            "response_reason": self.response_reason
        }


@dataclass
class AgentHeartbeat:
    """Agent health heartbeat"""
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    state: AgentState = AgentState.IDLE
    current_task: Optional[str] = None
    queue_depth: int = 0
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def is_stale(self, timeout_seconds: int = 60) -> bool:
        """Check if heartbeat is older than timeout"""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state.value,
            "current_task": self.current_task,
            "queue_depth": self.queue_depth,
            "last_error": self.last_error,
            "metrics": self.metrics
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Coordinator
# ═══════════════════════════════════════════════════════════════════════════════

class AgentCoordinator:
    """
    Central coordinator for inter-agent communication.
    Implements the "Soccer Team" coordination architecture.
    
    All agent-to-agent communication goes through this coordinator
    to ensure proper authority boundaries and audit trails.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._event_bus = get_event_bus()
        self._pending_handoffs: Dict[str, TaskHandoff] = {}
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._agent_heartbeats: Dict[str, AgentHeartbeat] = {}
        self._handoff_handlers: Dict[str, Callable] = {}
        self._approval_handlers: Dict[str, Callable] = {}
        self._response_events: Dict[str, threading.Event] = {}
        self._response_data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._initialized = True
        
        logger.info("AgentCoordinator initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Agent Registration
    # ═══════════════════════════════════════════════════════════════════════════
    
    def register_agent(self, agent_id: str, 
                      handoff_handler: Callable = None,
                      approval_handler: Callable = None) -> None:
        """Register an agent with its handlers"""
        with self._lock:
            if handoff_handler:
                self._handoff_handlers[agent_id] = handoff_handler
            if approval_handler:
                self._approval_handlers[agent_id] = approval_handler
            
            # Initialize heartbeat
            self._agent_heartbeats[agent_id] = AgentHeartbeat(agent_id=agent_id)
        
        logger.info(f"Agent registered: {agent_id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        with self._lock:
            self._handoff_handlers.pop(agent_id, None)
            self._approval_handlers.pop(agent_id, None)
            self._agent_heartbeats.pop(agent_id, None)
        
        logger.info(f"Agent unregistered: {agent_id}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Communication Validation
    # ═══════════════════════════════════════════════════════════════════════════
    
    def can_communicate(self, from_agent: str, to_agent: str) -> bool:
        """Check if from_agent can initiate communication with to_agent"""
        allowed = COMMUNICATION_MATRIX.get(from_agent, [])
        return to_agent in allowed
    
    def requires_finance_approval(self, action: str) -> bool:
        """Check if action requires Finance approval"""
        return FINANCE_APPROVAL_REQUIRED.get(action, False)
    
    def requires_manager_escalation(self, action: str) -> bool:
        """Check if action requires Manager escalation"""
        return MANAGER_ESCALATION_REQUIRED.get(action, False)
    
    def requires_user_confirmation(self, action: str, amount_usd: float = 0) -> bool:
        """Check if action requires user confirmation"""
        if USER_CONFIRMATION_REQUIRED.get(action, False):
            return True
        if amount_usd >= 500:
            return True
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Task Handoff
    # ═══════════════════════════════════════════════════════════════════════════
    
    def handoff_task(self, from_agent: str, to_agent: str, 
                     task_type: str, task_data: Dict[str, Any],
                     priority: str = "medium",
                     timeout_ms: int = 30000,
                     wait_for_response: bool = True) -> TaskHandoff:
        """
        Hand off a task from one agent to another.
        
        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID
            task_type: Type of task being handed off
            task_data: Task details
            priority: Task priority (low, medium, high, urgent)
            timeout_ms: Timeout for response
            wait_for_response: Whether to wait for acceptance
        
        Returns:
            TaskHandoff with status
        """
        # Validate communication
        if not self.can_communicate(from_agent, to_agent):
            logger.warning(f"Communication not allowed: {from_agent} -> {to_agent}")
            handoff = TaskHandoff(
                from_agent=from_agent,
                to_agent=to_agent,
                task_type=task_type,
                task_data=task_data,
                status="rejected",
                response_data={"error": "Communication not allowed"}
            )
            return handoff
        
        # Create handoff
        handoff = TaskHandoff(
            from_agent=from_agent,
            to_agent=to_agent,
            task_type=task_type,
            task_data=task_data,
            priority=priority,
            timeout_ms=timeout_ms
        )
        
        with self._lock:
            self._pending_handoffs[handoff.handoff_id] = handoff
            if wait_for_response:
                self._response_events[handoff.handoff_id] = threading.Event()
        
        # Emit handoff event
        emit(
            EventType.INFO,
            title="Task handoff requested",
            message=f"{from_agent} -> {to_agent}: {task_type}",
            agent_id=from_agent,
            metadata={
                "coordination_event": CoordinationEventType.TASK_HANDOFF_REQUEST.value,
                "handoff": handoff.to_dict()
            }
        )
        
        # Notify target agent
        handler = self._handoff_handlers.get(to_agent)
        if handler:
            try:
                # Run handler in thread to not block
                def run_handler():
                    try:
                        result = handler(handoff)
                        self._handle_handoff_response(handoff.handoff_id, result)
                    except Exception as e:
                        logger.error(f"Handoff handler error: {e}")
                        self._handle_handoff_response(
                            handoff.handoff_id, 
                            {"accepted": False, "error": str(e)}
                        )
                
                threading.Thread(target=run_handler, daemon=True).start()
            except Exception as e:
                logger.error(f"Failed to invoke handoff handler: {e}")
                handoff.status = "rejected"
                handoff.response_data = {"error": str(e)}
        else:
            logger.warning(f"No handoff handler for agent: {to_agent}")
            # For agents without handlers, auto-accept for now
            handoff.status = "accepted"
        
        # Wait for response if requested
        if wait_for_response and handoff.handoff_id in self._response_events:
            event = self._response_events[handoff.handoff_id]
            if event.wait(timeout=timeout_ms / 1000):
                with self._lock:
                    handoff = self._pending_handoffs.get(handoff.handoff_id, handoff)
            else:
                handoff.status = "timeout"
            
            # Cleanup
            with self._lock:
                self._response_events.pop(handoff.handoff_id, None)
                self._pending_handoffs.pop(handoff.handoff_id, None)
        
        return handoff
    
    def _handle_handoff_response(self, handoff_id: str, result: Dict[str, Any]) -> None:
        """Process handoff response from target agent"""
        with self._lock:
            handoff = self._pending_handoffs.get(handoff_id)
            if not handoff:
                return
            
            handoff.status = "accepted" if result.get("accepted", False) else "rejected"
            handoff.response_data = result
            
            # Signal waiting thread
            event = self._response_events.get(handoff_id)
            if event:
                event.set()
        
        # Emit response event
        emit(
            EventType.INFO,
            title=f"Task handoff {handoff.status}",
            message=f"{handoff.to_agent} {handoff.status} task from {handoff.from_agent}",
            agent_id=handoff.to_agent,
            metadata={
                "coordination_event": (
                    CoordinationEventType.TASK_HANDOFF_ACCEPTED.value 
                    if handoff.status == "accepted" 
                    else CoordinationEventType.TASK_HANDOFF_REJECTED.value
                ),
                "handoff": handoff.to_dict()
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Cost/Action Approval
    # ═══════════════════════════════════════════════════════════════════════════
    
    def request_approval(self, requester_agent: str, 
                        approval_type: str,
                        amount_usd: float = None,
                        description: str = "",
                        details: Dict[str, Any] = None,
                        timeout_ms: int = 60000,
                        wait_for_response: bool = True) -> ApprovalRequest:
        """
        Request approval for a cost or action.
        
        Args:
            requester_agent: Agent requesting approval
            approval_type: Type of approval (cost, action, vendor, etc.)
            amount_usd: Cost amount if applicable
            description: Human-readable description
            details: Additional details
            timeout_ms: Timeout for response
            wait_for_response: Whether to wait for approval
        
        Returns:
            ApprovalRequest with status
        """
        # Determine approver
        approver = "finance" if approval_type in ["cost", "budget", "expense"] else "manager"
        
        # Check if user confirmation needed
        needs_user = self.requires_user_confirmation(approval_type, amount_usd or 0)
        if needs_user:
            approver = "manager"  # Manager routes to user
        
        request = ApprovalRequest(
            requester_agent=requester_agent,
            approver_agent=approver,
            approval_type=approval_type,
            amount_usd=amount_usd,
            description=description,
            details=details or {},
            timeout_ms=timeout_ms
        )
        
        with self._lock:
            self._pending_approvals[request.request_id] = request
            if wait_for_response:
                self._response_events[request.request_id] = threading.Event()
        
        # Emit approval request event
        emit(
            EventType.INFO,
            title="Approval requested",
            message=f"{requester_agent} requests {approval_type} approval: {description}",
            agent_id=requester_agent,
            cost_usd=amount_usd,
            metadata={
                "coordination_event": CoordinationEventType.COST_APPROVAL_REQUEST.value,
                "approval_request": request.to_dict()
            }
        )
        
        # Notify approver
        handler = self._approval_handlers.get(approver)
        if handler:
            try:
                def run_handler():
                    try:
                        result = handler(request)
                        self._handle_approval_response(request.request_id, result)
                    except Exception as e:
                        logger.error(f"Approval handler error: {e}")
                        self._handle_approval_response(
                            request.request_id,
                            {"approved": False, "reason": str(e)}
                        )
                
                threading.Thread(target=run_handler, daemon=True).start()
            except Exception as e:
                logger.error(f"Failed to invoke approval handler: {e}")
                request.status = "denied"
                request.response_reason = str(e)
        else:
            # No handler - auto-approve for small amounts, deny for large
            if amount_usd and amount_usd <= 100:
                logger.info(f"Auto-approving small request: ${amount_usd}")
                request.status = "approved"
                request.response_reason = "Auto-approved (small amount)"
            else:
                logger.warning(f"No approval handler for: {approver}")
                request.status = "pending"
        
        # Wait for response if requested
        if wait_for_response and request.request_id in self._response_events:
            event = self._response_events[request.request_id]
            if event.wait(timeout=timeout_ms / 1000):
                with self._lock:
                    request = self._pending_approvals.get(request.request_id, request)
            else:
                request.status = "timeout"
            
            # Cleanup
            with self._lock:
                self._response_events.pop(request.request_id, None)
                self._pending_approvals.pop(request.request_id, None)
        
        return request
    
    def _handle_approval_response(self, request_id: str, result: Dict[str, Any]) -> None:
        """Process approval response"""
        with self._lock:
            request = self._pending_approvals.get(request_id)
            if not request:
                return
            
            request.status = "approved" if result.get("approved", False) else "denied"
            request.response_reason = result.get("reason", "")
            
            event = self._response_events.get(request_id)
            if event:
                event.set()
        
        emit(
            EventType.INFO,
            title=f"Approval {request.status}",
            message=f"{request.approver_agent} {request.status}: {request.description}",
            agent_id=request.approver_agent,
            metadata={
                "coordination_event": (
                    CoordinationEventType.COST_APPROVAL_GRANTED.value
                    if request.status == "approved"
                    else CoordinationEventType.COST_APPROVAL_DENIED.value
                ),
                "approval_request": request.to_dict()
            }
        )
    
    def grant_approval(self, request_id: str, reason: str = "") -> bool:
        """Grant a pending approval (called by approver)"""
        self._handle_approval_response(request_id, {"approved": True, "reason": reason})
        return True
    
    def deny_approval(self, request_id: str, reason: str = "") -> bool:
        """Deny a pending approval (called by approver)"""
        self._handle_approval_response(request_id, {"approved": False, "reason": reason})
        return True
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Heartbeat System
    # ═══════════════════════════════════════════════════════════════════════════
    
    def heartbeat(self, agent_id: str, 
                  state: AgentState = AgentState.IDLE,
                  current_task: str = None,
                  queue_depth: int = 0,
                  metrics: Dict[str, Any] = None) -> None:
        """
        Record agent heartbeat.
        
        Args:
            agent_id: Agent sending heartbeat
            state: Current agent state
            current_task: Currently executing task if any
            queue_depth: Number of pending tasks
            metrics: Additional metrics
        """
        hb = AgentHeartbeat(
            agent_id=agent_id,
            state=state,
            current_task=current_task,
            queue_depth=queue_depth,
            metrics=metrics or {}
        )
        
        with self._lock:
            self._agent_heartbeats[agent_id] = hb
        
        # Emit heartbeat event (low priority, not always needed)
        emit(
            EventType.INFO,
            title="Heartbeat",
            agent_id=agent_id,
            state=state.value,
            metadata={
                "coordination_event": CoordinationEventType.HEARTBEAT.value,
                "heartbeat": hb.to_dict()
            }
        )
    
    def get_agent_health(self, agent_id: str = None, timeout_seconds: int = 60) -> Dict[str, Any]:
        """
        Get health status for one or all agents.
        
        Args:
            agent_id: Specific agent or None for all
            timeout_seconds: Seconds before heartbeat considered stale
        
        Returns:
            Health status dictionary
        """
        with self._lock:
            if agent_id:
                hb = self._agent_heartbeats.get(agent_id)
                if not hb:
                    return {"agent_id": agent_id, "status": "unknown"}
                return {
                    "agent_id": agent_id,
                    "status": "healthy" if not hb.is_stale(timeout_seconds) else "stale",
                    "state": hb.state.value,
                    "last_heartbeat": hb.timestamp.isoformat(),
                    "current_task": hb.current_task,
                    "queue_depth": hb.queue_depth
                }
            else:
                result = {}
                for aid, hb in self._agent_heartbeats.items():
                    result[aid] = {
                        "status": "healthy" if not hb.is_stale(timeout_seconds) else "stale",
                        "state": hb.state.value,
                        "last_heartbeat": hb.timestamp.isoformat()
                    }
                return result
    
    def get_failed_agents(self, timeout_seconds: int = 60) -> List[str]:
        """Get list of agents with stale heartbeats"""
        with self._lock:
            return [
                aid for aid, hb in self._agent_heartbeats.items()
                if hb.is_stale(timeout_seconds)
            ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Status & Broadcast
    # ═══════════════════════════════════════════════════════════════════════════
    
    def broadcast_status(self, agent_id: str, status: Dict[str, Any]) -> None:
        """Broadcast status update from an agent to all interested parties"""
        emit(
            EventType.INFO,
            title="Status broadcast",
            message=f"{agent_id} status update",
            agent_id=agent_id,
            metadata={
                "coordination_event": CoordinationEventType.STATUS_BROADCAST.value,
                "status": status
            }
        )
    
    def escalate_to_manager(self, agent_id: str, issue: str, 
                           priority: str = "high",
                           details: Dict[str, Any] = None) -> None:
        """Escalate an issue to the Manager agent"""
        emit(
            EventType.WARNING,
            title="Escalation to Manager",
            message=issue,
            agent_id=agent_id,
            metadata={
                "coordination_event": CoordinationEventType.ESCALATION_TO_MANAGER.value,
                "priority": priority,
                "details": details or {}
            }
        )
        
        # Also handoff to manager
        self.handoff_task(
            from_agent=agent_id,
            to_agent="manager",
            task_type="escalation",
            task_data={"issue": issue, "priority": priority, "details": details or {}},
            priority=priority,
            wait_for_response=False
        )
    
    def escalate_to_user(self, agent_id: str, message: str,
                        requires_response: bool = False,
                        options: List[str] = None) -> None:
        """Escalate to user (via Manager)"""
        emit(
            EventType.WARNING,
            title="User escalation",
            message=message,
            agent_id=agent_id,
            metadata={
                "coordination_event": CoordinationEventType.ESCALATION_TO_USER.value,
                "requires_response": requires_response,
                "options": options or []
            }
        )
        
        # Route through manager
        self.handoff_task(
            from_agent=agent_id,
            to_agent="manager",
            task_type="user_notification",
            task_data={
                "message": message,
                "requires_response": requires_response,
                "options": options or []
            },
            priority="high",
            wait_for_response=False
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Pending Items
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_pending_handoffs(self, agent_id: str = None) -> List[TaskHandoff]:
        """Get pending task handoffs"""
        with self._lock:
            handoffs = list(self._pending_handoffs.values())
        
        if agent_id:
            handoffs = [h for h in handoffs if h.to_agent == agent_id]
        
        return [h for h in handoffs if h.status == "pending"]
    
    def get_pending_approvals(self, agent_id: str = None) -> List[ApprovalRequest]:
        """Get pending approval requests"""
        with self._lock:
            approvals = list(self._pending_approvals.values())
        
        if agent_id:
            approvals = [a for a in approvals if a.approver_agent == agent_id]
        
        return [a for a in approvals if a.status == "pending"]
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """Get summary of coordination state"""
        with self._lock:
            pending_handoffs = len([h for h in self._pending_handoffs.values() if h.status == "pending"])
            pending_approvals = len([a for a in self._pending_approvals.values() if a.status == "pending"])
            
            agent_states = {}
            for aid, hb in self._agent_heartbeats.items():
                agent_states[aid] = {
                    "state": hb.state.value,
                    "healthy": not hb.is_stale(60)
                }
        
        return {
            "pending_handoffs": pending_handoffs,
            "pending_approvals": pending_approvals,
            "registered_agents": list(self._handoff_handlers.keys()),
            "agent_states": agent_states,
            "failed_agents": self.get_failed_agents()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level convenience functions
# ═══════════════════════════════════════════════════════════════════════════════

_coordinator: AgentCoordinator = None


def get_coordinator() -> AgentCoordinator:
    """Get the global agent coordinator"""
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator


def register_agent(agent_id: str, handoff_handler: Callable = None, 
                   approval_handler: Callable = None) -> None:
    """Register an agent with the coordinator"""
    get_coordinator().register_agent(agent_id, handoff_handler, approval_handler)


def handoff_task(from_agent: str, to_agent: str, task_type: str, 
                task_data: Dict[str, Any], **kwargs) -> TaskHandoff:
    """Hand off a task between agents"""
    return get_coordinator().handoff_task(from_agent, to_agent, task_type, task_data, **kwargs)


def request_approval(requester_agent: str, approval_type: str, **kwargs) -> ApprovalRequest:
    """Request approval for a cost or action"""
    return get_coordinator().request_approval(requester_agent, approval_type, **kwargs)


def heartbeat(agent_id: str, **kwargs) -> None:
    """Send agent heartbeat"""
    get_coordinator().heartbeat(agent_id, **kwargs)


def escalate_to_manager(agent_id: str, issue: str, **kwargs) -> None:
    """Escalate issue to manager"""
    get_coordinator().escalate_to_manager(agent_id, issue, **kwargs)


def escalate_to_user(agent_id: str, message: str, **kwargs) -> None:
    """Escalate to user via manager"""
    get_coordinator().escalate_to_user(agent_id, message, **kwargs)
