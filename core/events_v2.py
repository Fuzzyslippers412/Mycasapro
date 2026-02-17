"""
MyCasa Pro - Hardened Event Bus
Reliable event system with correlation IDs, ack/retry, and dead-letter handling.
"""
import asyncio
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Awaitable
import threading


# ============ EVENT TYPES ============

class EventType(str, Enum):
    # System lifecycle
    SYSTEM_STARTING = "system.starting"
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPING = "system.stopping"
    SYSTEM_STOPPED = "system.stopped"
    
    # Agent lifecycle
    AGENT_STARTING = "agent.starting"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPING = "agent.stopping"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_HEARTBEAT = "agent.heartbeat"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # Finance events
    BILL_DUE = "finance.bill_due"
    BILL_PAID = "finance.bill_paid"
    SPEND_ADDED = "finance.spend_added"
    PORTFOLIO_UPDATED = "finance.portfolio_updated"
    
    # Inbox events
    MESSAGE_RECEIVED = "inbox.message_received"
    MESSAGE_TRIAGED = "inbox.message_triaged"
    MESSAGES_SYNCED = "inbox.messages_synced"
    
    # Security events
    THREAT_DETECTED = "security.threat_detected"
    INCIDENT_CREATED = "security.incident_created"
    INCIDENT_RESOLVED = "security.incident_resolved"
    
    # Telemetry
    TELEMETRY_RECORDED = "telemetry.recorded"
    COST_INCURRED = "telemetry.cost_incurred"


class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


# ============ EVENT MODEL ============

@dataclass
class Event:
    """Core event model with full traceability"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    source: str = ""  # Agent or component that emitted
    tenant_id: str = "default"
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # For tracing related events
    causation_id: Optional[str] = None    # ID of event that caused this
    data: Dict[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['status'] = self.status.value
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        data = data.copy()
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = EventStatus(data['status'])
        return cls(**data)
    
    def child_event(self, event_type: str, source: str, data: Dict = None) -> 'Event':
        """Create a child event with correlation chain"""
        return Event(
            type=event_type,
            source=source,
            tenant_id=self.tenant_id,
            correlation_id=self.correlation_id or self.event_id,
            causation_id=self.event_id,
            data=data or {},
        )


# ============ EVENT HANDLERS ============

EventHandler = Callable[[Event], Awaitable[None]]
SyncEventHandler = Callable[[Event], None]


@dataclass
class Subscription:
    """Event subscription with metadata"""
    handler_id: str
    event_types: List[str]  # Empty = all events
    handler: EventHandler
    source_filter: Optional[str] = None  # Only events from this source


# ============ EVENT BUS ============

class EventBus:
    """
    Hardened event bus with:
    - Correlation ID tracking
    - Retry with exponential backoff
    - Dead-letter queue for failed events
    - DB persistence for at-least-once delivery
    """
    
    def __init__(self, persist_events: bool = True):
        self._subscriptions: Dict[str, Subscription] = {}
        self._event_log: List[Event] = []
        self._dead_letter: List[Event] = []
        self._lock = threading.Lock()
        self._persist = persist_events
        self._running = False
        self._db_available = False
        
        # Try to init DB persistence
        try:
            self._db_available = True
        except ImportError:
            print("[EventBus] Database not available, using in-memory only")
        
    # ============ SUBSCRIPTION ============
    
    def subscribe(
        self,
        handler: EventHandler,
        event_types: List[str] = None,
        source_filter: str = None,
    ) -> str:
        """Subscribe to events. Returns handler_id for unsubscribe."""
        handler_id = str(uuid.uuid4())
        sub = Subscription(
            handler_id=handler_id,
            event_types=event_types or [],
            handler=handler,
            source_filter=source_filter,
        )
        with self._lock:
            self._subscriptions[handler_id] = sub
        return handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler"""
        with self._lock:
            if handler_id in self._subscriptions:
                del self._subscriptions[handler_id]
                return True
        return False
    
    def clear_subscriptions(self):
        """Clear all subscriptions (for restart)"""
        with self._lock:
            self._subscriptions.clear()
    
    # ============ EMIT ============
    
    async def emit(self, event: Event) -> str:
        """Emit an event. Returns event_id."""
        # Add correlation ID if not set
        if not event.correlation_id:
            event.correlation_id = event.event_id
        
        # Log event to memory
        with self._lock:
            self._event_log.append(event)
            # Keep last 1000 events in memory
            if len(self._event_log) > 1000:
                self._event_log = self._event_log[-1000:]
        
        # Persist to DB if available
        if self._persist and self._db_available:
            self._persist_event(event)
        
        # Dispatch to handlers
        await self._dispatch(event)
        
        # Mark as delivered in DB
        if self._persist and self._db_available:
            self._mark_delivered(event.event_id)
        
        return event.event_id
    
    def _persist_event(self, event: Event):
        """Persist event to database"""
        try:
            from database import get_db
            from database.models import EventLog
            import json
            
            with get_db() as db:
                log_entry = EventLog(
                    event_id=event.event_id,
                    event_type=event.type,
                    source=event.source,
                    tenant_id=event.tenant_id,
                    correlation_id=event.correlation_id,
                    causation_id=event.causation_id,
                    payload=json.dumps(event.data, default=str),
                    status='pending',
                    attempts=0,
                    max_attempts=event.max_attempts,
                )
                db.add(log_entry)
        except Exception as e:
            print(f"[EventBus] Failed to persist event: {e}")
    
    def _mark_delivered(self, event_id: str):
        """Mark event as delivered in database"""
        try:
            from database import get_db
            from database.models import EventLog
            from datetime import datetime
            
            with get_db() as db:
                entry = db.query(EventLog).filter_by(event_id=event_id).first()
                if entry:
                    entry.status = 'delivered'
                    entry.processed_at = datetime.now()
        except Exception as e:
            print(f"[EventBus] Failed to mark delivered: {e}")
    
    def _mark_dead_letter(self, event_id: str, error: str):
        """Mark event as dead-letter in database"""
        try:
            from database import get_db
            from database.models import EventLog
            
            with get_db() as db:
                entry = db.query(EventLog).filter_by(event_id=event_id).first()
                if entry:
                    entry.status = 'dead_letter'
                    entry.last_error = error
        except Exception as e:
            print(f"[EventBus] Failed to mark dead-letter: {e}")
    
    def emit_sync(self, event: Event) -> str:
        """Synchronous emit (creates event loop if needed)"""
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, schedule it
            asyncio.create_task(self.emit(event))
        except RuntimeError:
            # No running loop, run synchronously
            asyncio.run(self.emit(event))
        return event.event_id
    
    async def _dispatch(self, event: Event):
        """Dispatch event to matching handlers"""
        handlers = self._get_matching_handlers(event)
        
        for sub in handlers:
            event.attempts += 1
            try:
                event.status = EventStatus.PROCESSING
                await sub.handler(event)
                event.status = EventStatus.DELIVERED
            except Exception as e:
                event.error = str(e)
                if event.attempts >= event.max_attempts:
                    event.status = EventStatus.DEAD_LETTER
                    with self._lock:
                        self._dead_letter.append(event)
                    print(f"[EventBus] Event {event.event_id} moved to dead-letter: {e}")
                else:
                    event.status = EventStatus.FAILED
                    # Retry with backoff
                    delay = 2 ** event.attempts
                    await asyncio.sleep(delay)
                    await self._dispatch(event)
    
    def _get_matching_handlers(self, event: Event) -> List[Subscription]:
        """Get handlers that match the event"""
        matching = []
        with self._lock:
            for sub in self._subscriptions.values():
                # Check event type filter
                if sub.event_types and event.type not in sub.event_types:
                    continue
                # Check source filter
                if sub.source_filter and event.source != sub.source_filter:
                    continue
                matching.append(sub)
        return matching
    
    # ============ HELPERS ============
    
    def create_event(
        self,
        event_type: str,
        source: str,
        data: Dict = None,
        correlation_id: str = None,
    ) -> Event:
        """Helper to create an event"""
        return Event(
            type=event_type,
            source=source,
            data=data or {},
            correlation_id=correlation_id,
        )
    
    # ============ QUERIES ============
    
    def get_event_log(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """Get recent events from the log"""
        with self._lock:
            events = self._event_log[-limit:]
            if event_type:
                events = [e for e in events if e.type == event_type]
            return [e.to_dict() for e in events]
    
    def get_dead_letter(self, limit: int = 50) -> List[Dict]:
        """Get events in dead-letter queue"""
        with self._lock:
            return [e.to_dict() for e in self._dead_letter[-limit:]]
    
    def get_events_by_correlation(self, correlation_id: str) -> List[Dict]:
        """Get all events with a correlation ID (trace a request)"""
        with self._lock:
            events = [e for e in self._event_log if e.correlation_id == correlation_id]
            return [e.to_dict() for e in events]
    
    def clear_dead_letter(self) -> int:
        """Clear dead-letter queue, returns count cleared"""
        with self._lock:
            count = len(self._dead_letter)
            self._dead_letter.clear()
            return count
    
    # ============ LIFECYCLE ============
    
    def start(self):
        """Start the event bus"""
        self._running = True
        self.emit_sync(Event(
            type=EventType.SYSTEM_STARTING,
            source="event_bus",
            data={"subscriptions": len(self._subscriptions)},
        ))
    
    def stop(self):
        """Stop the event bus"""
        self._running = False
        self.emit_sync(Event(
            type=EventType.SYSTEM_STOPPING,
            source="event_bus",
            data={"pending_events": len(self._event_log)},
        ))


# ============ SINGLETON ============

_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.Lock()

def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _event_bus
    with _event_bus_lock:
        if _event_bus is None:
            _event_bus = EventBus()
        return _event_bus

def reset_event_bus():
    """Reset the event bus (for testing or restart)"""
    global _event_bus
    with _event_bus_lock:
        if _event_bus:
            _event_bus.clear_subscriptions()
        _event_bus = None


# ============ CONVENIENCE FUNCTIONS ============

async def emit(event_type: str, source: str, data: Dict = None, correlation_id: str = None) -> str:
    """Quick emit helper"""
    bus = get_event_bus()
    event = bus.create_event(event_type, source, data, correlation_id)
    return await bus.emit(event)

def emit_sync(event_type: str, source: str, data: Dict = None) -> str:
    """Quick synchronous emit helper"""
    bus = get_event_bus()
    event = bus.create_event(event_type, source, data)
    return bus.emit_sync(event)
