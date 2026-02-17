"""
MyCasa Pro - Event Bus
Real-time event streaming for system observability
"""
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque
import threading
import uuid
import logging

logger = logging.getLogger("mycasa.events")


class EventType(Enum):
    """System event types"""
    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_STATE_CHANGED = "agent_state_changed"
    
    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # Prompt/AI operations
    PROMPT_STARTED = "prompt_started"
    PROMPT_COMPLETED = "prompt_completed"
    
    # Cost tracking
    COST_RECORDED = "cost_recorded"
    COST_THRESHOLD_WARNING = "cost_threshold_warning"
    
    # Connector events
    CONNECTOR_SYNC_STARTED = "connector_sync_started"
    CONNECTOR_SYNC_COMPLETED = "connector_sync_completed"
    CONNECTOR_ERROR = "connector_error"
    
    # Security
    INCIDENT_CREATED = "incident_created"
    ALERT_TRIGGERED = "alert_triggered"
    
    # System
    SYSTEM_STARTED = "system_started"
    SYSTEM_HEALTH_CHECK = "system_health_check"
    
    # Generic
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AgentState(Enum):
    """Agent operational states"""
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class SystemEvent:
    """
    Unified event model for all system activity.
    All significant actions emit events in this format.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: EventType = EventType.INFO
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Source
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Task context
    task_id: Optional[str] = None
    task_type: Optional[str] = None
    
    # Content
    title: str = ""
    message: str = ""
    
    # State
    state: Optional[str] = None  # For state change events
    progress: Optional[float] = None  # 0-100 for progress events
    duration_ms: Optional[int] = None
    
    # Cost tracking
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    cost_confidence: str = "estimated"  # exact, estimated, unknown
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "title": self.title,
            "message": self.message,
            "state": self.state,
            "progress": self.progress,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "cost_confidence": self.cost_confidence,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SystemEvent':
        data = data.copy()
        data['event_type'] = EventType(data['event_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class AgentActivity:
    """Current activity state for an agent"""
    agent_id: str
    state: AgentState = AgentState.IDLE
    current_task_id: Optional[str] = None
    current_task_type: Optional[str] = None
    current_task_started: Optional[datetime] = None
    last_completed_task: Optional[str] = None
    last_completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def elapsed_ms(self) -> Optional[int]:
        if self.current_task_started:
            delta = datetime.utcnow() - self.current_task_started
            return int(delta.total_seconds() * 1000)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "current_task_id": self.current_task_id,
            "current_task_type": self.current_task_type,
            "current_task_started": self.current_task_started.isoformat() if self.current_task_started else None,
            "elapsed_ms": self.elapsed_ms(),
            "last_completed_task": self.last_completed_task,
            "last_completed_at": self.last_completed_at.isoformat() if self.last_completed_at else None,
            "last_error": self.last_error
        }


class EventBus:
    """
    Central event bus for system-wide event streaming.
    
    Features:
    - Publish/subscribe pattern
    - Event history buffer
    - Agent activity tracking
    - Thread-safe
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
        
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._all_subscribers: List[Callable] = []
        self._event_history: deque = deque(maxlen=1000)
        self._agent_activity: Dict[str, AgentActivity] = {}
        self._last_event_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self._initialized = True
    
    def subscribe(self, event_type: EventType, callback: Callable[[SystemEvent], None]) -> None:
        """Subscribe to a specific event type"""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def subscribe_all(self, callback: Callable[[SystemEvent], None]) -> None:
        """Subscribe to all events"""
        with self._lock:
            self._all_subscribers.append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe from an event type"""
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type] if cb != callback
                ]
    
    def publish(self, event: SystemEvent) -> None:
        """Publish an event to all subscribers"""
        with self._lock:
            # Store in history
            self._event_history.append(event)
            self._last_event_time = event.timestamp
            
            # Update agent activity if applicable
            if event.agent_id:
                self._update_agent_activity(event)
            
            # Get subscribers
            type_subscribers = self._subscribers.get(event.event_type, [])
            all_subs = list(self._all_subscribers)
        
        # Notify subscribers (outside lock)
        for callback in type_subscribers + all_subs:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")
    
    def _update_agent_activity(self, event: SystemEvent) -> None:
        """Update agent activity based on event"""
        agent_id = event.agent_id
        
        if agent_id not in self._agent_activity:
            self._agent_activity[agent_id] = AgentActivity(agent_id=agent_id)
        
        activity = self._agent_activity[agent_id]
        
        if event.event_type == EventType.TASK_STARTED:
            activity.state = AgentState.RUNNING
            activity.current_task_id = event.task_id
            activity.current_task_type = event.task_type
            activity.current_task_started = event.timestamp
        
        elif event.event_type == EventType.TASK_COMPLETED:
            activity.state = AgentState.IDLE
            activity.last_completed_task = event.task_type or event.task_id
            activity.last_completed_at = event.timestamp
            activity.current_task_id = None
            activity.current_task_type = None
            activity.current_task_started = None
        
        elif event.event_type == EventType.TASK_FAILED:
            activity.state = AgentState.ERROR
            activity.last_error = event.message
            activity.current_task_id = None
            activity.current_task_type = None
            activity.current_task_started = None
        
        elif event.event_type == EventType.AGENT_STATE_CHANGED:
            try:
                activity.state = AgentState(event.state)
            except ValueError:
                pass
    
    def get_recent_events(self, limit: int = 50, event_types: List[EventType] = None) -> List[SystemEvent]:
        """Get recent events from history"""
        with self._lock:
            events = list(self._event_history)
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        return events[-limit:]
    
    def get_agent_activity(self, agent_id: str = None) -> Dict[str, AgentActivity]:
        """Get current agent activity"""
        with self._lock:
            if agent_id:
                activity = self._agent_activity.get(agent_id)
                return {agent_id: activity} if activity else {}
            return dict(self._agent_activity)
    
    def get_active_agents(self) -> List[AgentActivity]:
        """Get agents currently running tasks"""
        with self._lock:
            return [
                a for a in self._agent_activity.values()
                if a.state == AgentState.RUNNING
            ]
    
    def get_last_event_time(self) -> Optional[datetime]:
        """Get timestamp of last event"""
        return self._last_event_time
    
    def is_system_active(self) -> bool:
        """Check if any agent is actively working"""
        return len(self.get_active_agents()) > 0
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get live system status summary"""
        with self._lock:
            active_count = sum(1 for a in self._agent_activity.values() if a.state == AgentState.RUNNING)
            idle_count = sum(1 for a in self._agent_activity.values() if a.state == AgentState.IDLE)
            error_count = sum(1 for a in self._agent_activity.values() if a.state == AgentState.ERROR)
            
            recent = list(self._event_history)[-10:]
        
        return {
            "is_active": active_count > 0,
            "active_agents": active_count,
            "idle_agents": idle_count,
            "error_agents": error_count,
            "last_event_time": self._last_event_time.isoformat() if self._last_event_time else None,
            "recent_events": [e.to_dict() for e in recent]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level convenience functions
# ═══════════════════════════════════════════════════════════════════════════════

_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get the global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def emit(
    event_type: EventType,
    title: str = "",
    message: str = "",
    agent_id: str = None,
    task_id: str = None,
    task_type: str = None,
    **kwargs
) -> SystemEvent:
    """Emit an event to the event bus"""
    event = SystemEvent(
        event_type=event_type,
        title=title,
        message=message,
        agent_id=agent_id,
        task_id=task_id,
        task_type=task_type,
        **kwargs
    )
    get_event_bus().publish(event)
    return event


def emit_task_started(agent_id: str, task_type: str, task_id: str = None, **kwargs) -> SystemEvent:
    """Convenience: emit task started event"""
    return emit(
        EventType.TASK_STARTED,
        title=f"{task_type} started",
        agent_id=agent_id,
        task_id=task_id or str(uuid.uuid4())[:8],
        task_type=task_type,
        **kwargs
    )


def emit_task_completed(agent_id: str, task_type: str, task_id: str, duration_ms: int = None, **kwargs) -> SystemEvent:
    """Convenience: emit task completed event"""
    return emit(
        EventType.TASK_COMPLETED,
        title=f"{task_type} completed",
        agent_id=agent_id,
        task_id=task_id,
        task_type=task_type,
        duration_ms=duration_ms,
        **kwargs
    )


def emit_cost(
    agent_id: str,
    cost_usd: float,
    tokens_used: int = None,
    confidence: str = "estimated",
    description: str = "",
    **kwargs
) -> SystemEvent:
    """Emit a cost recording event"""
    return emit(
        EventType.COST_RECORDED,
        title="Cost recorded",
        message=description,
        agent_id=agent_id,
        cost_usd=cost_usd,
        tokens_used=tokens_used,
        cost_confidence=confidence,
        **kwargs
    )
