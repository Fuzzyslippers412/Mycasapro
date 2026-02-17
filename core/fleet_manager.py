"""
Agent Fleet Manager for MyCasa Pro.

Provides centralized management for all AI agents including:
- Agent lifecycle (spawn, stop, restart)
- Status monitoring and health checks
- Cost tracking and budget enforcement
- Performance metrics and optimization
- Load balancing and request routing
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost_usd: float = 0.0
    avg_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    requests_by_tier: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def record_request(
        self,
        success: bool,
        response_time_ms: float,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0.0,
        tier: str = "medium",
        error: Optional[str] = None,
    ):
        """Record a request's metrics."""
        self.total_requests += 1
        self.last_request_time = datetime.now()
        self.requests_by_tier[tier] += 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append({
                    "time": datetime.now().isoformat(),
                    "error": error[:200],
                })
                # Keep only last 10 errors
                self.errors = self.errors[-10:]

        self.total_tokens_input += tokens_input
        self.total_tokens_output += tokens_output
        self.total_cost_usd += cost_usd

        # Update rolling average response time
        if self.total_requests == 1:
            self.avg_response_time_ms = response_time_ms
        else:
            self.avg_response_time_ms = (
                self.avg_response_time_ms * 0.9 + response_time_ms * 0.1
            )


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    id: str
    name: str
    description: str = ""
    enabled: bool = True
    max_concurrent_requests: int = 5
    timeout_seconds: int = 60
    default_model: Optional[str] = None
    max_tier: str = "reasoning"  # Maximum allowed tier
    context_strategy: str = "adaptive"
    cost_limit_daily_usd: float = 10.0
    cost_limit_monthly_usd: float = 100.0
    priority: int = 5  # 1-10, higher = more priority


@dataclass
class AgentInstance:
    """Runtime instance of an agent."""
    config: AgentConfig
    state: AgentState = AgentState.IDLE
    metrics: AgentMetrics = field(default_factory=AgentMetrics)
    current_requests: int = 0
    last_health_check: Optional[datetime] = None
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def is_available(self) -> bool:
        """Check if agent can accept new requests."""
        return (
            self.config.enabled
            and self.state in [AgentState.IDLE, AgentState.RUNNING]
            and self.current_requests < self.config.max_concurrent_requests
        )

    def is_within_budget(self) -> bool:
        """Check if agent is within daily cost limits."""
        # Calculate today's cost (simplified - in production would use proper date filtering)
        return self.metrics.total_cost_usd < self.config.cost_limit_daily_usd


class FleetManager:
    """
    Manages the fleet of AI agents.

    Responsibilities:
    - Track agent states and health
    - Route requests to appropriate agents
    - Enforce cost budgets
    - Collect and report metrics
    - Handle agent lifecycle
    """

    # Default agent configurations
    DEFAULT_AGENTS = {
        "manager": AgentConfig(
            id="manager",
            name="Galidima",
            description="Orchestrator agent - coordinates all other agents",
            max_tier="reasoning",
            priority=10,
            cost_limit_daily_usd=20.0,
        ),
        "finance": AgentConfig(
            id="finance",
            name="Mamadou",
            description="Finance agent - manages budgets, investments, bills",
            max_tier="complex",
            priority=8,
            cost_limit_daily_usd=15.0,
        ),
        "maintenance": AgentConfig(
            id="maintenance",
            name="Ousmane",
            description="Maintenance agent - tracks tasks, schedules repairs",
            max_tier="medium",
            priority=6,
            cost_limit_daily_usd=5.0,
        ),
        "contractors": AgentConfig(
            id="contractors",
            name="Malik",
            description="Contractors agent - manages service providers",
            max_tier="medium",
            priority=5,
            cost_limit_daily_usd=5.0,
        ),
        "projects": AgentConfig(
            id="projects",
            name="Zainab",
            description="Projects agent - tracks home improvement projects",
            max_tier="complex",
            priority=6,
            cost_limit_daily_usd=10.0,
        ),
        "security-manager": AgentConfig(
            id="security-manager",
            name="Aicha",
            description="Security agent - monitors threats, manages access",
            max_tier="complex",
            priority=9,
            cost_limit_daily_usd=10.0,
        ),
        "janitor": AgentConfig(
            id="janitor",
            name="Sule",
            description="Janitor agent - system health, cleanup, telemetry",
            max_tier="simple",
            priority=3,
            cost_limit_daily_usd=2.0,
        ),
        "backup-recovery": AgentConfig(
            id="backup-recovery",
            name="Backup",
            description="Backup agent - data backup and recovery",
            max_tier="simple",
            priority=4,
            cost_limit_daily_usd=2.0,
            enabled=True,
        ),
        "mail-skill": AgentConfig(
            id="mail-skill",
            name="Amina",
            description="Mail agent - inbox triage and communication",
            max_tier="medium",
            priority=6,
            cost_limit_daily_usd=5.0,
        ),
    }

    def __init__(self):
        self._agents: Dict[str, AgentInstance] = {}
        self._lock = threading.Lock()
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._started = False
        self._health_check_task: Optional[asyncio.Task] = None

        # Initialize default agents
        for agent_id, config in self.DEFAULT_AGENTS.items():
            self._agents[agent_id] = AgentInstance(config=config)

    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        """Get an agent instance by ID."""
        return self._agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, AgentInstance]:
        """Get all agent instances."""
        return dict(self._agents)

    def get_enabled_agents(self) -> Dict[str, AgentInstance]:
        """Get only enabled agent instances."""
        return {
            k: v for k, v in self._agents.items()
            if v.config.enabled
        }

    def get_available_agents(self) -> Dict[str, AgentInstance]:
        """Get agents that can accept requests."""
        return {
            k: v for k, v in self._agents.items()
            if v.is_available() and v.is_within_budget()
        }

    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        with agent._lock:
            agent.config.enabled = True
            agent.state = AgentState.IDLE
            self._emit_event("agent_enabled", agent_id=agent_id)
        return True

    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        with agent._lock:
            agent.config.enabled = False
            agent.state = AgentState.DISABLED
            self._emit_event("agent_disabled", agent_id=agent_id)
        return True

    def update_agent_config(self, agent_id: str, **kwargs) -> bool:
        """Update agent configuration."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        with agent._lock:
            for key, value in kwargs.items():
                if hasattr(agent.config, key):
                    setattr(agent.config, key, value)
            self._emit_event("agent_config_updated", agent_id=agent_id, changes=kwargs)
        return True

    def register_agent(self, config: AgentConfig) -> AgentInstance:
        """Register a new agent with the fleet."""
        with self._lock:
            if config.id in self._agents:
                # Update existing
                self._agents[config.id].config = config
            else:
                self._agents[config.id] = AgentInstance(config=config)
            self._emit_event("agent_registered", agent_id=config.id)
        return self._agents[config.id]

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the fleet."""
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                self._emit_event("agent_unregistered", agent_id=agent_id)
                return True
        return False

    async def request_start(self, agent_id: str) -> bool:
        """
        Signal that an agent is starting a request.
        Returns False if agent can't accept requests.
        """
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        with agent._lock:
            if not agent.is_available():
                return False
            if not agent.is_within_budget():
                self._emit_event("agent_budget_exceeded", agent_id=agent_id)
                return False

            agent.current_requests += 1
            if agent.state == AgentState.IDLE:
                agent.state = AgentState.RUNNING
            if agent.current_requests >= agent.config.max_concurrent_requests:
                agent.state = AgentState.BUSY

        return True

    async def request_end(
        self,
        agent_id: str,
        success: bool = True,
        response_time_ms: float = 0,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0,
        tier: str = "medium",
        error: Optional[str] = None,
    ):
        """Signal that an agent has completed a request."""
        agent = self._agents.get(agent_id)
        if not agent:
            return

        with agent._lock:
            agent.current_requests = max(0, agent.current_requests - 1)

            # Record metrics
            agent.metrics.record_request(
                success=success,
                response_time_ms=response_time_ms,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                tier=tier,
                error=error,
            )

            # Update state
            if agent.current_requests == 0:
                agent.state = AgentState.IDLE if success else AgentState.ERROR
            elif agent.current_requests < agent.config.max_concurrent_requests:
                agent.state = AgentState.RUNNING

            if not success:
                agent.last_error = error

        self._emit_event(
            "request_completed",
            agent_id=agent_id,
            success=success,
            response_time_ms=response_time_ms,
            tier=tier,
        )

    def get_fleet_status(self) -> Dict[str, Any]:
        """Get comprehensive fleet status."""
        agents_status = {}
        total_requests = 0
        total_cost = 0.0
        agents_by_state = defaultdict(int)

        for agent_id, agent in self._agents.items():
            agents_status[agent_id] = {
                "name": agent.config.name,
                "state": agent.state.value,
                "enabled": agent.config.enabled,
                "default_model": agent.config.default_model,
                "current_requests": agent.current_requests,
                "max_concurrent": agent.config.max_concurrent_requests,
                "max_tier": agent.config.max_tier,
                "priority": agent.config.priority,
                "metrics": {
                    "total_requests": agent.metrics.total_requests,
                    "success_rate": (
                        agent.metrics.successful_requests / agent.metrics.total_requests
                        if agent.metrics.total_requests > 0 else 1.0
                    ),
                    "avg_response_time_ms": round(agent.metrics.avg_response_time_ms, 2),
                    "total_cost_usd": round(agent.metrics.total_cost_usd, 4),
                    "requests_by_tier": dict(agent.metrics.requests_by_tier),
                },
                "cost_limit_daily": agent.config.cost_limit_daily_usd,
                "within_budget": agent.is_within_budget(),
                "last_request": (
                    agent.metrics.last_request_time.isoformat()
                    if agent.metrics.last_request_time else None
                ),
                "last_error": agent.last_error,
            }
            total_requests += agent.metrics.total_requests
            total_cost += agent.metrics.total_cost_usd
            agents_by_state[agent.state.value] += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "fleet_size": len(self._agents),
            "enabled_count": len(self.get_enabled_agents()),
            "available_count": len(self.get_available_agents()),
            "agents_by_state": dict(agents_by_state),
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 4),
            "agents": agents_status,
        }

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific agent."""
        status = self.get_fleet_status()
        return status["agents"].get(agent_id)

    def select_agent_for_task(
        self,
        task_type: str,
        required_tier: str = "medium",
        preferred_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Select the best available agent for a task.

        Args:
            task_type: Type of task (for routing)
            required_tier: Minimum tier required
            preferred_agent: Preferred agent ID if any

        Returns:
            Agent ID or None if no suitable agent available
        """
        # Tier ordering
        tier_order = {"simple": 0, "medium": 1, "complex": 2, "reasoning": 3}
        required_level = tier_order.get(required_tier, 1)

        # Check preferred agent first
        if preferred_agent:
            agent = self._agents.get(preferred_agent)
            if agent and agent.is_available() and agent.is_within_budget():
                agent_max = tier_order.get(agent.config.max_tier, 1)
                if agent_max >= required_level:
                    return preferred_agent

        # Find best available agent
        candidates = []
        for agent_id, agent in self._agents.items():
            if not agent.is_available() or not agent.is_within_budget():
                continue

            agent_max = tier_order.get(agent.config.max_tier, 1)
            if agent_max < required_level:
                continue

            # Score based on: priority, current load, success rate
            load_factor = agent.current_requests / agent.config.max_concurrent_requests
            success_rate = (
                agent.metrics.successful_requests / agent.metrics.total_requests
                if agent.metrics.total_requests > 0 else 1.0
            )
            score = (
                agent.config.priority * 10
                + (1 - load_factor) * 5
                + success_rate * 3
            )
            candidates.append((agent_id, score))

        if not candidates:
            return None

        # Return highest scoring agent
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self._event_handlers[event_type].append(handler)

    def _emit_event(self, event_type: str, **kwargs):
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event_type=event_type, **kwargs)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def start_health_checks(self, interval_seconds: int = 30):
        """Start periodic health checks."""
        async def check_loop():
            while self._started:
                await self._run_health_checks()
                await asyncio.sleep(interval_seconds)

        self._started = True
        self._health_check_task = asyncio.create_task(check_loop())

    async def stop_health_checks(self):
        """Stop health checks."""
        self._started = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def _run_health_checks(self):
        """Run health checks on all agents."""
        now = datetime.now()
        for agent_id, agent in self._agents.items():
            agent.last_health_check = now

            # Check for stuck agents (no response in timeout period)
            if agent.current_requests > 0 and agent.metrics.last_request_time:
                elapsed = (now - agent.metrics.last_request_time).total_seconds()
                if elapsed > agent.config.timeout_seconds * 2:
                    logger.warning(f"Agent {agent_id} appears stuck")
                    agent.state = AgentState.ERROR
                    self._emit_event("agent_stuck", agent_id=agent_id)

            # Check for high error rates
            if agent.metrics.total_requests > 10:
                error_rate = agent.metrics.failed_requests / agent.metrics.total_requests
                if error_rate > 0.3:
                    logger.warning(f"Agent {agent_id} has high error rate: {error_rate:.2%}")
                    self._emit_event("agent_high_error_rate", agent_id=agent_id, rate=error_rate)

    def reset_metrics(self, agent_id: Optional[str] = None):
        """Reset metrics for one or all agents."""
        if agent_id:
            agent = self._agents.get(agent_id)
            if agent:
                agent.metrics = AgentMetrics()
        else:
            for agent in self._agents.values():
                agent.metrics = AgentMetrics()

    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis."""
        return {
            "exported_at": datetime.now().isoformat(),
            "agents": {
                agent_id: {
                    "config": {
                        "id": agent.config.id,
                        "name": agent.config.name,
                        "enabled": agent.config.enabled,
                        "max_tier": agent.config.max_tier,
                        "priority": agent.config.priority,
                    },
                    "metrics": {
                        "total_requests": agent.metrics.total_requests,
                        "successful_requests": agent.metrics.successful_requests,
                        "failed_requests": agent.metrics.failed_requests,
                        "total_tokens_input": agent.metrics.total_tokens_input,
                        "total_tokens_output": agent.metrics.total_tokens_output,
                        "total_cost_usd": agent.metrics.total_cost_usd,
                        "avg_response_time_ms": agent.metrics.avg_response_time_ms,
                        "requests_by_tier": dict(agent.metrics.requests_by_tier),
                        "recent_errors": agent.metrics.errors,
                    },
                }
                for agent_id, agent in self._agents.items()
            },
        }


# Singleton instance
_fleet_manager: Optional[FleetManager] = None


def get_fleet_manager() -> FleetManager:
    """Get the singleton FleetManager instance."""
    global _fleet_manager
    if _fleet_manager is None:
        _fleet_manager = FleetManager()
    return _fleet_manager
