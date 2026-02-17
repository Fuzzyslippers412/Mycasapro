"""
Agent Coordination System
Handles inter-agent communication, task routing, workflow orchestration,
event-driven coordination, and safe editing protocols.

Enhanced with:
- Intent-based routing (not just keywords)
- Event bus for reactive coordination
- Workflow engine for multi-step tasks
- Shared context management
- Priority queues
"""
import os
import shutil
import json
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import subprocess
from collections import defaultdict


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class EventType(str, Enum):
    """Events that agents can subscribe to"""
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    MESSAGE_RECEIVED = "message_received"
    ALERT_TRIGGERED = "alert_triggered"
    BUDGET_WARNING = "budget_warning"
    SECURITY_INCIDENT = "security_incident"
    MAINTENANCE_DUE = "maintenance_due"
    CONTRACTOR_NEEDED = "contractor_needed"
    SYSTEM_HEALTH_CHANGE = "system_health_change"
    USER_REQUEST = "user_request"
    SCHEDULE_TRIGGER = "schedule_trigger"


@dataclass
class Event:
    """An event that can be published/subscribed"""
    id: str
    type: EventType
    source_agent: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: Priority = Priority.NORMAL
    consumed_by: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "type": self.type.value,
            "priority": self.priority.value,
        }


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    id: str
    agent_id: str
    action: str
    params: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 120
    retry_count: int = 0
    max_retries: int = 2
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """A multi-step workflow across agents"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"
    context: Dict[str, Any] = field(default_factory=dict)
    on_complete: Optional[str] = None  # Callback event type
    on_failure: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [asdict(s) for s in self.steps],
            "created_at": self.created_at,
            "status": self.status,
            "context": self.context,
        }


class AgentCoordinator:
    """
    Central coordinator for all agent interactions.
    
    Enhanced Features:
    - Intent-based smart routing
    - Event bus (pub/sub)
    - Workflow orchestration
    - Shared context management
    - Priority message queues
    - Circuit breaker for failing agents
    """
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Message queue with priority support
        self._message_queue: List[Dict[str, Any]] = []
        
        # Agent registry
        self._agents: Dict[str, Any] = {}
        
        # Edit history for rollback
        self._edit_history: List[Dict[str, Any]] = []
        
        # Event bus - subscriptions by event type
        self._event_subscriptions: Dict[EventType, Set[str]] = defaultdict(set)
        self._event_history: List[Event] = []
        
        # Workflow engine
        self._active_workflows: Dict[str, Workflow] = {}
        self._workflow_history: List[Dict[str, Any]] = []
        
        # Shared context - accessible by all agents
        self._shared_context: Dict[str, Any] = {}
        
        # Circuit breaker - tracks agent failures
        self._agent_failures: Dict[str, List[datetime]] = defaultdict(list)
        self._circuit_open: Set[str] = set()  # Agents in "fail" state
        
        # Load persisted state
        self._load_full_state()
    
    def _load_full_state(self):
        """Load all persisted coordinator state"""
        state_file = self.data_dir / "coordinator_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    self._message_queue = state.get("message_queue", [])[-1000:]
                    self._edit_history = state.get("edit_history", [])[-500:]
                    self._shared_context = state.get("shared_context", {})
                    self._workflow_history = state.get("workflow_history", [])[-200:]
                    
                    # Restore event subscriptions
                    for evt_type, agents in state.get("subscriptions", {}).items():
                        try:
                            self._event_subscriptions[EventType(evt_type)] = set(agents)
                        except ValueError:
                            pass
            except Exception as e:
                print(f"[Coordinator] Failed to load state: {e}")
    
    def _save_full_state(self):
        """Persist all coordinator state"""
        state_file = self.data_dir / "coordinator_state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    "message_queue": self._message_queue[-1000:],
                    "edit_history": self._edit_history[-500:],
                    "shared_context": self._shared_context,
                    "workflow_history": self._workflow_history[-200:],
                    "subscriptions": {
                        evt.value: list(agents) 
                        for evt, agents in self._event_subscriptions.items()
                    },
                    "last_saved": datetime.now().isoformat(),
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[Coordinator] Failed to save state: {e}")
    
    # ==================== AGENT REGISTRY ====================
    
    def register_agent(self, agent_id: str, agent_instance):
        """Register an agent with the coordinator"""
        self._agents[agent_id] = agent_instance
        print(f"[Coordinator] Registered agent: {agent_id}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            # Unsubscribe from all events
            for subscribers in self._event_subscriptions.values():
                subscribers.discard(agent_id)
    
    def get_agent(self, agent_id: str):
        """Get a registered agent"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[str]:
        """List all registered agent IDs"""
        return list(self._agents.keys())
    
    def is_agent_healthy(self, agent_id: str) -> bool:
        """Check if an agent is healthy (not circuit-broken)"""
        return agent_id not in self._circuit_open
    
    # ==================== CIRCUIT BREAKER ====================
    
    def record_agent_failure(self, agent_id: str):
        """Record an agent failure for circuit breaker"""
        now = datetime.now()
        self._agent_failures[agent_id].append(now)
        
        # Keep only failures from last 5 minutes
        cutoff = now - timedelta(minutes=5)
        self._agent_failures[agent_id] = [
            t for t in self._agent_failures[agent_id] if t > cutoff
        ]
        
        # Open circuit if 3+ failures in 5 minutes
        if len(self._agent_failures[agent_id]) >= 3:
            self._circuit_open.add(agent_id)
            print(f"[Coordinator] Circuit OPEN for {agent_id} - too many failures")
    
    def record_agent_success(self, agent_id: str):
        """Record agent success - helps close circuit"""
        if agent_id in self._circuit_open:
            self._agent_failures[agent_id].clear()
            self._circuit_open.discard(agent_id)
            print(f"[Coordinator] Circuit CLOSED for {agent_id} - recovered")
    
    # ==================== INTER-AGENT MESSAGING ====================
    
    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
        priority: str = "normal",
        reply_to: str = None,
        ttl_seconds: int = None,
    ) -> str:
        """
        Send a message from one agent to another.
        
        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID (or "broadcast" for all)
            message_type: Type of message
            content: Message payload
            priority: normal/high/critical/low
            reply_to: Original message ID if this is a reply
            ttl_seconds: Time-to-live (auto-expire)
        
        Returns message_id for tracking.
        """
        # Check circuit breaker
        if to_agent != "broadcast" and not self.is_agent_healthy(to_agent):
            print(f"[Coordinator] Message to {to_agent} blocked - circuit open")
            return None
        
        message_id = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._message_queue)}"
        
        message = {
            "id": message_id,
            "from": from_agent,
            "to": to_agent,
            "type": message_type,
            "content": content,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "reply_to": reply_to,
            "expires_at": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat() if ttl_seconds else None,
        }
        
        # Insert based on priority (critical/high at front)
        if priority in ["critical", "high"]:
            # Find insertion point after other critical/high
            insert_idx = 0
            for i, msg in enumerate(self._message_queue):
                if msg["status"] == "pending" and msg["priority"] in ["critical", "high"]:
                    insert_idx = i + 1
                elif msg["status"] == "pending":
                    break
            self._message_queue.insert(insert_idx, message)
        else:
            self._message_queue.append(message)
        
        self._save_full_state()
        
        # Broadcast: send to all registered agents
        if to_agent == "broadcast":
            for agent_id, agent in self._agents.items():
                if agent_id != from_agent and hasattr(agent, 'receive_message'):
                    try:
                        agent.receive_message(message)
                    except Exception as e:
                        print(f"[Coordinator] Broadcast to {agent_id} failed: {e}")
        else:
            # Direct message: notify target agent
            target = self._agents.get(to_agent)
            if target and hasattr(target, 'receive_message'):
                try:
                    target.receive_message(message)
                except Exception as e:
                    self.record_agent_failure(to_agent)
                    print(f"[Coordinator] Message delivery to {to_agent} failed: {e}")
        
        return message_id
    
    def get_messages(
        self, 
        agent_id: str, 
        status: str = None,
        message_type: str = None,
        since: str = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get messages for an agent with flexible filtering"""
        now = datetime.now()
        messages = []
        
        for m in self._message_queue:
            # Filter by recipient
            if m["to"] != agent_id and m["to"] != "broadcast":
                continue
            
            # Filter by status
            if status and m["status"] != status:
                continue
            
            # Filter by type
            if message_type and m["type"] != message_type:
                continue
            
            # Filter by time
            if since:
                msg_time = datetime.fromisoformat(m["timestamp"])
                since_time = datetime.fromisoformat(since)
                if msg_time < since_time:
                    continue
            
            # Check TTL
            if m.get("expires_at"):
                exp_time = datetime.fromisoformat(m["expires_at"])
                if now > exp_time:
                    m["status"] = "expired"
                    continue
            
            messages.append(m)
            
            if len(messages) >= limit:
                break
        
        return messages
    
    def mark_message_processed(self, message_id: str, result: Dict[str, Any] = None):
        """Mark a message as processed"""
        for msg in self._message_queue:
            if msg["id"] == message_id:
                msg["status"] = "processed"
                msg["processed_at"] = datetime.now().isoformat()
                if result:
                    msg["result"] = result
                break
        self._save_full_state()
    
    def reply_to_message(
        self,
        original_message_id: str,
        from_agent: str,
        content: Dict[str, Any],
    ) -> str:
        """Reply to a specific message"""
        # Find original message
        original = None
        for msg in self._message_queue:
            if msg["id"] == original_message_id:
                original = msg
                break
        
        if not original:
            return None
        
        return self.send_message(
            from_agent=from_agent,
            to_agent=original["from"],  # Reply to sender
            message_type=f"reply_{original['type']}",
            content=content,
            reply_to=original_message_id,
        )
    
    # ==================== EVENT BUS (PUB/SUB) ====================
    
    def subscribe(self, agent_id: str, event_type: EventType):
        """Subscribe an agent to an event type"""
        self._event_subscriptions[event_type].add(agent_id)
        print(f"[Coordinator] {agent_id} subscribed to {event_type.value}")
        self._save_full_state()
    
    def unsubscribe(self, agent_id: str, event_type: EventType):
        """Unsubscribe an agent from an event type"""
        self._event_subscriptions[event_type].discard(agent_id)
        self._save_full_state()
    
    def publish_event(
        self,
        event_type: EventType,
        source_agent: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
    ) -> Event:
        """
        Publish an event to all subscribers.
        Returns the created Event.
        """
        event_id = f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._event_history)}"
        
        event = Event(
            id=event_id,
            type=event_type,
            source_agent=source_agent,
            payload=payload,
            priority=priority,
        )
        
        self._event_history.append(event)
        
        # Notify subscribers
        subscribers = self._event_subscriptions.get(event_type, set())
        for agent_id in subscribers:
            if agent_id == source_agent:
                continue  # Don't notify self
            
            agent = self._agents.get(agent_id)
            if agent and hasattr(agent, 'handle_event'):
                try:
                    agent.handle_event(event)
                    event.consumed_by.append(agent_id)
                except Exception as e:
                    print(f"[Coordinator] Event delivery to {agent_id} failed: {e}")
                    self.record_agent_failure(agent_id)
        
        # Keep history bounded
        if len(self._event_history) > 500:
            self._event_history = self._event_history[-300:]
        
        self._save_full_state()
        return event
    
    def get_recent_events(
        self,
        event_type: EventType = None,
        limit: int = 50,
    ) -> List[Event]:
        """Get recent events, optionally filtered by type"""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:][::-1]
    
    # ==================== SHARED CONTEXT ====================
    
    def set_context(self, key: str, value: Any, source_agent: str = None):
        """Set a shared context value"""
        self._shared_context[key] = {
            "value": value,
            "updated_by": source_agent,
            "updated_at": datetime.now().isoformat(),
        }
        self._save_full_state()
    
    def get_context(self, key: str) -> Any:
        """Get a shared context value"""
        entry = self._shared_context.get(key)
        return entry["value"] if entry else None
    
    def get_full_context(self) -> Dict[str, Any]:
        """Get all shared context"""
        return {k: v["value"] for k, v in self._shared_context.items()}
    
    def clear_context(self, key: str = None):
        """Clear shared context (specific key or all)"""
        if key:
            self._shared_context.pop(key, None)
        else:
            self._shared_context.clear()
        self._save_full_state()
    
    # ==================== WORKFLOW ENGINE ====================
    
    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
        on_complete: EventType = None,
        on_failure: EventType = None,
    ) -> Workflow:
        """
        Create a new workflow.
        
        Steps format:
        [
            {"id": "step1", "agent_id": "finance", "action": "analyze_budget", "params": {...}},
            {"id": "step2", "agent_id": "maintenance", "action": "prioritize_repairs", 
             "params": {...}, "depends_on": ["step1"]},
        ]
        """
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._workflow_history)}"
        
        workflow_steps = [
            WorkflowStep(
                id=s.get("id", f"step_{i}"),
                agent_id=s["agent_id"],
                action=s["action"],
                params=s.get("params", {}),
                depends_on=s.get("depends_on", []),
                timeout_seconds=s.get("timeout_seconds", 120),
                max_retries=s.get("max_retries", 2),
            )
            for i, s in enumerate(steps)
        ]
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps,
            context=context or {},
            on_complete=on_complete.value if on_complete else None,
            on_failure=on_failure.value if on_failure else None,
        )
        
        self._active_workflows[workflow_id] = workflow
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a workflow, respecting dependencies"""
        workflow = self._active_workflows.get(workflow_id)
        if not workflow:
            return {"error": f"Workflow not found: {workflow_id}"}
        
        workflow.status = "running"
        completed_steps = set()
        
        while True:
            # Find executable steps (dependencies met, not done)
            executable = []
            for step in workflow.steps:
                if step.status in ["completed", "failed"]:
                    continue
                if all(dep in completed_steps for dep in step.depends_on):
                    executable.append(step)
            
            if not executable:
                # Check if we're done or stuck
                all_done = all(s.status in ["completed", "failed"] for s in workflow.steps)
                if all_done:
                    break
                else:
                    # Stuck - some steps failed and blocked others
                    workflow.status = "failed"
                    break
            
            # Execute executable steps (could be parallel)
            for step in executable:
                step.status = "running"
                try:
                    result = await self._execute_workflow_step(step, workflow)
                    step.result = result
                    step.status = "completed"
                    completed_steps.add(step.id)
                    
                    # Add result to workflow context
                    workflow.context[f"step_{step.id}_result"] = result
                    
                except Exception as e:
                    step.error = str(e)
                    step.retry_count += 1
                    
                    if step.retry_count <= step.max_retries:
                        step.status = "pending"  # Will retry
                        print(f"[Coordinator] Step {step.id} failed, retrying ({step.retry_count}/{step.max_retries})")
                    else:
                        step.status = "failed"
                        print(f"[Coordinator] Step {step.id} failed permanently: {e}")
        
        # Determine final status
        failed_steps = [s for s in workflow.steps if s.status == "failed"]
        if failed_steps:
            workflow.status = "failed"
            if workflow.on_failure:
                self.publish_event(
                    EventType(workflow.on_failure),
                    "coordinator",
                    {"workflow_id": workflow_id, "failed_steps": [s.id for s in failed_steps]},
                )
        else:
            workflow.status = "completed"
            if workflow.on_complete:
                self.publish_event(
                    EventType(workflow.on_complete),
                    "coordinator",
                    {"workflow_id": workflow_id, "context": workflow.context},
                )
        
        # Archive workflow
        self._archive_workflow(workflow)
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "steps": [{"id": s.id, "status": s.status, "result": s.result, "error": s.error} for s in workflow.steps],
            "context": workflow.context,
        }
    
    async def _execute_workflow_step(self, step: WorkflowStep, workflow: Workflow) -> Any:
        """Execute a single workflow step"""
        agent = self._agents.get(step.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {step.agent_id}")
        
        # Check circuit breaker
        if not self.is_agent_healthy(step.agent_id):
            raise RuntimeError(f"Agent {step.agent_id} is unhealthy (circuit open)")
        
        # Build action context
        action_context = {
            **workflow.context,
            **step.params,
            "_workflow_id": workflow.id,
            "_step_id": step.id,
        }
        
        # Check if agent has the action method
        if hasattr(agent, step.action):
            method = getattr(agent, step.action)
            if asyncio.iscoroutinefunction(method):
                result = await method(**action_context)
            else:
                result = method(**action_context)
        elif hasattr(agent, 'chat'):
            # Fallback: use chat with action description
            prompt = f"Execute action '{step.action}' with context: {json.dumps(action_context, default=str)}"
            result = await agent.chat(prompt)
        else:
            raise ValueError(f"Agent {step.agent_id} has no action '{step.action}' or chat method")
        
        self.record_agent_success(step.agent_id)
        return result
    
    def _archive_workflow(self, workflow: Workflow):
        """Archive a completed/failed workflow"""
        if workflow.id in self._active_workflows:
            del self._active_workflows[workflow.id]
        
        self._workflow_history.append(workflow.to_dict())
        self._save_full_state()
    
    def get_active_workflows(self) -> List[Workflow]:
        """Get all active workflows"""
        return list(self._active_workflows.values())
    
    def get_workflow_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get workflow history"""
        return self._workflow_history[-limit:][::-1]
    
    # ==================== INTENT-BASED TASK ROUTING ====================
    
    # Intent patterns - more sophisticated than keyword matching
    INTENT_PATTERNS = {
        "finance": {
            "keywords": ["budget", "bill", "money", "cost", "portfolio", "spending", "payment", 
                        "expense", "income", "savings", "investment", "stock", "crypto",
                        "bank", "transaction", "financial", "afford", "price", "pay"],
            "phrases": [
                r"how much (do|did|will|would|can) .* cost",
                r"can (i|we) afford",
                r"what('s| is) (my|our|the) (balance|budget)",
                r"track (my|our)? (spending|expenses)",
                r"(review|analyze|check) (my|our|the)? (finances?|portfolio|investments?)",
            ],
            "priority": 0.8,  # Base priority when matched
        },
        "maintenance": {
            "keywords": ["repair", "fix", "broken", "maintenance", "task", "leak", "damage",
                        "replace", "clean", "hvac", "appliance", "plumbing", "electrical",
                        "roof", "floor", "wall", "door", "window", "yard", "lawn"],
            "phrases": [
                r"(something|.+) (is|was|has been) broken",
                r"need(s)? (to be )?(fixed|repaired|replaced)",
                r"not working",
                r"schedule (a )?(maintenance|repair|cleaning)",
                r"when (was|is) .* (last )?(serviced|maintained|checked)",
            ],
            "priority": 0.7,
        },
        "security": {
            "keywords": ["security", "incident", "alarm", "camera", "access", "lock", "breach",
                        "intruder", "suspicious", "theft", "vandalism", "monitor", "sensor",
                        "motion", "alert", "safeguard", "protect"],
            "phrases": [
                r"(saw|noticed|heard) (something|someone) suspicious",
                r"(check|review|show) (the )?(cameras?|footage|recordings?)",
                r"(who|when|what) (was|is) .* (at|near|around) (the )?(door|entrance|gate)",
                r"arm|disarm (the )?(alarm|system)",
                r"security (report|status|check)",
            ],
            "priority": 0.9,  # Security is high priority
        },
        "contractors": {
            "keywords": ["contractor", "hire", "plumber", "electrician", "service", "handyman",
                        "provider", "worker", "quote", "estimate", "professional", "technician",
                        "roofer", "painter", "landscaper", "cleaner"],
            "phrases": [
                r"(find|get|need) (a|an|some) (contractor|plumber|electrician|handyman)",
                r"who (can|should|could) (fix|repair|install|do)",
                r"(get|request) (a )?quote",
                r"(recommend|suggest) .* (service|contractor|provider)",
                r"(call|contact|schedule) .* (service|contractor)",
            ],
            "priority": 0.6,
        },
        "projects": {
            "keywords": ["project", "renovation", "improvement", "upgrade", "remodel", 
                        "addition", "construction", "design", "plan", "blueprint",
                        "permit", "timeline", "milestone"],
            "phrases": [
                r"(start|plan|begin) (a )?(new )?(project|renovation|remodel)",
                r"(project|renovation) (status|progress|update)",
                r"how (long|much) (will|would) .* (take|cost)",
                r"(phase|stage|milestone) .* (complete|done|finished)",
                r"(what|which) (projects?|renovations?) .* (planned|scheduled|pending)",
            ],
            "priority": 0.5,
        },
        "janitor": {
            "keywords": ["system", "audit", "health", "backup", "cleanup", "debug", "error",
                        "log", "status", "performance", "memory", "disk", "database"],
            "phrases": [
                r"(check|run|perform) (a )?(system )?(health|audit|check|scan)",
                r"(backup|restore) .* (data|files|database)",
                r"(clean|clear) .* (cache|logs|temp)",
                r"(system|app) (is )?(slow|unresponsive|not working)",
                r"(show|check|review) (the )?(logs?|errors?|status)",
            ],
            "priority": 0.4,
        },
    }
    
    # Routing history for learning (track what worked)
    _routing_history: List[Dict[str, Any]] = []
    
    def route_request(
        self, 
        message: str, 
        from_agent: str = "manager",
        context: Dict[str, Any] = None,
    ) -> Optional[str]:
        """
        Smart intent-based routing.
        
        Uses:
        1. Keyword matching (fast path)
        2. Phrase pattern matching (regex)
        3. Context awareness (recent conversation)
        4. Multi-agent detection (complex requests)
        
        Returns agent_id or None if should stay with manager.
        """
        message_lower = message.lower()
        scores: Dict[str, float] = {}
        
        # Score each agent
        for agent_id, patterns in self.INTENT_PATTERNS.items():
            score = 0.0
            
            # Keyword matching
            keywords_found = sum(1 for kw in patterns["keywords"] if kw in message_lower)
            if keywords_found > 0:
                score += 0.3 * min(keywords_found, 3)  # Cap at 3 keywords
            
            # Phrase pattern matching
            for phrase in patterns["phrases"]:
                if re.search(phrase, message_lower):
                    score += 0.4
                    break
            
            # Apply base priority
            score *= patterns["priority"]
            
            if score > 0:
                scores[agent_id] = score
        
        # Context boost - if recent messages were about same topic
        if context and context.get("recent_agent"):
            recent = context["recent_agent"]
            if recent in scores:
                scores[recent] *= 1.2  # 20% boost for continuity
        
        # Check for multi-agent need (complex request)
        if len(scores) >= 2:
            # Multiple domains detected - might need team coordination
            top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if top_scores[0][1] - top_scores[1][1] < 0.2:
                # Close scores - suggest team handling
                self._log_routing_decision(message, None, scores, "multi_agent_detected")
                return None  # Manager will coordinate
        
        # Return highest scoring agent (if score is significant)
        if scores:
            best_agent, best_score = max(scores.items(), key=lambda x: x[1])
            if best_score >= 0.2:  # Minimum confidence threshold
                self._log_routing_decision(message, best_agent, scores, "routed")
                return best_agent
        
        self._log_routing_decision(message, None, scores, "no_match")
        return None
    
    def route_with_team_suggestion(
        self,
        message: str,
        from_agent: str = "manager",
    ) -> Dict[str, Any]:
        """
        Enhanced routing that also suggests teams for complex requests.
        
        Returns:
        {
            "primary_agent": "finance" or None,
            "suggested_team": "budget_decision" or None,
            "confidence": 0.8,
            "all_scores": {...},
        }
        """
        message_lower = message.lower()
        scores: Dict[str, float] = {}
        
        # Score each agent (same as route_request)
        for agent_id, patterns in self.INTENT_PATTERNS.items():
            score = 0.0
            keywords_found = sum(1 for kw in patterns["keywords"] if kw in message_lower)
            if keywords_found > 0:
                score += 0.3 * min(keywords_found, 3)
            
            for phrase in patterns["phrases"]:
                if re.search(phrase, message_lower):
                    score += 0.4
                    break
            
            score *= patterns["priority"]
            if score > 0:
                scores[agent_id] = score
        
        # Determine result
        result = {
            "primary_agent": None,
            "suggested_team": None,
            "confidence": 0.0,
            "all_scores": scores,
        }
        
        if not scores:
            return result
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_agent, best_score = sorted_scores[0]
        result["confidence"] = best_score
        
        # Single dominant agent
        if len(sorted_scores) == 1 or (len(sorted_scores) > 1 and best_score - sorted_scores[1][1] > 0.3):
            result["primary_agent"] = best_agent
            return result
        
        # Multiple agents involved - suggest team
        involved_agents = [a for a, s in sorted_scores if s > 0.15]
        
        # Match to preset teams
        from .teams import PRESET_TEAMS
        for team_id, team in PRESET_TEAMS.items():
            # Check if involved agents overlap with team members
            overlap = set(involved_agents) & set(team.members)
            if len(overlap) >= 2:
                result["suggested_team"] = team_id
                result["primary_agent"] = team.leader
                break
        
        if not result["suggested_team"]:
            result["primary_agent"] = best_agent
        
        return result
    
    def _log_routing_decision(
        self, 
        message: str, 
        routed_to: str, 
        scores: Dict[str, float],
        reason: str,
    ):
        """Log routing decisions for analysis and learning"""
        self._routing_history.append({
            "timestamp": datetime.now().isoformat(),
            "message_preview": message[:100],
            "routed_to": routed_to,
            "scores": scores,
            "reason": reason,
        })
        
        # Keep history bounded
        if len(self._routing_history) > 500:
            self._routing_history = self._routing_history[-300:]
    
    # ==================== SAFE EDITING PROTOCOL ====================
    
    def safe_edit_file(
        self,
        file_path: str,
        new_content: str,
        requesting_agent: str,
        reason: str,
        validator: Callable[[str], bool] = None
    ) -> Dict[str, Any]:
        """
        Safely edit a file with backup and validation.
        
        Protocol:
        1. Create backup of original
        2. Write to staged file
        3. Validate staged file (optional)
        4. Replace original with staged
        5. Log the change
        
        Returns dict with success status and details.
        """
        file_path = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        result = {
            "success": False,
            "file": str(file_path),
            "agent": requesting_agent,
            "reason": reason,
            "timestamp": timestamp,
        }
        
        try:
            # Step 1: Create backup
            if file_path.exists():
                backup_path = self.backup_dir / f"{file_path.name}.backup.{timestamp}"
                shutil.copy2(file_path, backup_path)
                result["backup_path"] = str(backup_path)
            else:
                result["backup_path"] = None
                result["is_new_file"] = True
            
            # Step 2: Write to staged file
            staged_path = file_path.parent / f"{file_path.name}.staged.{timestamp}"
            with open(staged_path, 'w') as f:
                f.write(new_content)
            result["staged_path"] = str(staged_path)
            
            # Step 3: Validate if validator provided
            if validator:
                try:
                    is_valid = validator(str(staged_path))
                    if not is_valid:
                        os.remove(staged_path)
                        result["error"] = "Validation failed"
                        result["validation_passed"] = False
                        return result
                    result["validation_passed"] = True
                except Exception as e:
                    os.remove(staged_path)
                    result["error"] = f"Validation error: {str(e)}"
                    result["validation_passed"] = False
                    return result
            
            # Step 4: Replace original with staged
            shutil.move(staged_path, file_path)
            result["success"] = True
            
            # Step 5: Log the change
            self._log_edit(result)
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            # Cleanup staged file if it exists
            if 'staged_path' in result:
                try:
                    os.remove(result["staged_path"])
                except Exception as e:
                    pass
            return result
    
    def _log_edit(self, edit_result: Dict[str, Any]):
        """Log an edit operation"""
        self._edit_history.append(edit_result)
        
        # Save edit history
        history_file = self.data_dir / "edit_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self._edit_history[-500:], f, indent=2, default=str)
        except Exception as e:
            print(f"[Coordinator] Failed to save edit history: {e}")
    
    def rollback_edit(self, timestamp: str) -> Dict[str, Any]:
        """
        Rollback an edit by timestamp.
        Finds the backup and restores it.
        """
        # Find the edit in history
        for edit in self._edit_history:
            if edit.get("timestamp") == timestamp:
                backup_path = edit.get("backup_path")
                file_path = edit.get("file")
                
                if not backup_path:
                    return {"success": False, "error": "No backup found for this edit"}
                
                if not Path(backup_path).exists():
                    return {"success": False, "error": "Backup file no longer exists"}
                
                # Restore the backup
                shutil.copy2(backup_path, file_path)
                
                return {
                    "success": True,
                    "restored_from": backup_path,
                    "restored_to": file_path,
                }
        
        return {"success": False, "error": "Edit not found in history"}
    
    def get_edit_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent edit history"""
        return self._edit_history[-limit:][::-1]
    
    # ==================== PYTHON FILE VALIDATION ====================
    
    @staticmethod
    def validate_python_syntax(file_path: str) -> bool:
        """Validate Python file syntax"""
        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", file_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def validate_json(file_path: str) -> bool:
        """Validate JSON file"""
        try:
            with open(file_path) as f:
                json.load(f)
            return True
        except Exception:
            return False


# Global coordinator instance
_coordinator = None

def get_coordinator() -> AgentCoordinator:
    """Get or create the global coordinator instance"""
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator
