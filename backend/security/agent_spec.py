"""
Agent Specification System
Defines how agents are configured and constrained according to security invariants
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class AgentClass(str, Enum):
    """Agent class types"""
    CLAWDBOT = "clawdbot"


class RiskTolerance(str, Enum):
    """Risk tolerance levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ModelConfig:
    """LLM model configuration"""
    provider: str  # "anthropic", "venice", "openai"
    model: str  # "claude-sonnet-4", "llama-3.3-70b", etc.
    temperature: float = 0.0
    max_tokens: int = 4096

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        return cls(**data)


@dataclass
class IsolationConfig:
    """Agent isolation configuration"""
    memory_namespace: str  # e.g., "agent:finance", "agent:legal"
    network_access: bool = False
    filesystem_access: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IsolationConfig':
        return cls(**data)


@dataclass
class CapabilitiesConfig:
    """What the agent can do"""
    can_propose_actions: bool = True
    can_execute_actions: bool = False  # Should ALWAYS be False per INVARIANT_1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilitiesConfig':
        return cls(**data)


@dataclass
class PermissionsConfig:
    """Tool permissions"""
    tools_allowed: List[str] = field(default_factory=list)
    tools_forbidden: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PermissionsConfig':
        return cls(**data)


@dataclass
class PolicyConfig:
    """Policy requirements"""
    policy_agent_required: bool = True
    risk_tolerance: RiskTolerance = RiskTolerance.LOW

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['risk_tolerance'] = self.risk_tolerance.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicyConfig':
        if 'risk_tolerance' in data and isinstance(data['risk_tolerance'], str):
            data['risk_tolerance'] = RiskTolerance(data['risk_tolerance'])
        return cls(**data)


@dataclass
class AuditConfig:
    """Audit logging configuration"""
    snapshot_every_run: bool = True
    retention_days: int = 90

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditConfig':
        return cls(**data)


@dataclass
class LifecycleConfig:
    """Agent lifecycle configuration"""
    ephemeral: bool = True  # True = destroyed after request
    max_runtime_seconds: int = 300  # 5 minutes default

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LifecycleConfig':
        return cls(**data)


@dataclass
class AgentSpec:
    """
    Complete agent specification

    Defines all constraints and configuration for an agent
    """
    agent_id: str
    agent_class: AgentClass
    model: ModelConfig
    isolation: IsolationConfig
    capabilities: CapabilitiesConfig
    permissions: PermissionsConfig
    policy: PolicyConfig
    audit: AuditConfig
    lifecycle: LifecycleConfig

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "agent_id": self.agent_id,
            "agent_class": self.agent_class.value,
            "model": self.model.to_dict(),
            "isolation": self.isolation.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "permissions": self.permissions.to_dict(),
            "policy": self.policy.to_dict(),
            "audit": self.audit.to_dict(),
            "lifecycle": self.lifecycle.to_dict(),
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentSpec':
        """Deserialize from dictionary"""
        return cls(
            agent_id=data["agent_id"],
            agent_class=AgentClass(data["agent_class"]),
            model=ModelConfig.from_dict(data["model"]),
            isolation=IsolationConfig.from_dict(data["isolation"]),
            capabilities=CapabilitiesConfig.from_dict(data["capabilities"]),
            permissions=PermissionsConfig.from_dict(data["permissions"]),
            policy=PolicyConfig.from_dict(data["policy"]),
            audit=AuditConfig.from_dict(data["audit"]),
            lifecycle=LifecycleConfig.from_dict(data["lifecycle"]),
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'AgentSpec':
        """Deserialize from JSON"""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> tuple[bool, str]:
        """
        Validate agent spec against security invariants

        Returns:
            (valid: bool, error_message: str)
        """
        # INVARIANT_1: Agents cannot execute actions
        if self.capabilities.can_execute_actions:
            return False, "INVARIANT_1 VIOLATION: can_execute_actions must be False"

        # INVARIANT_2: Memory namespace must be unique
        if not self.isolation.memory_namespace.startswith(f"agent:{self.agent_id}"):
            return False, f"INVARIANT_2 VIOLATION: memory_namespace must be 'agent:{self.agent_id}:*'"

        # Agent ID must be valid
        import re
        if not re.match(r"^[a-z0-9_\-]+$", self.agent_id):
            return False, "agent_id must match pattern ^[a-z0-9_\\-]+$"

        # Model config validation
        if self.model.temperature < 0 or self.model.temperature > 1:
            return False, "temperature must be between 0 and 1"

        if self.model.max_tokens < 512:
            return False, "max_tokens must be >= 512"

        return True, ""


# ==================== PRE-CONFIGURED AGENT SPECS ====================

# Finance Agent Spec
FINANCE_AGENT_SPEC = AgentSpec(
    agent_id="finance",
    agent_class=AgentClass.CLAWDBOT,
    model=ModelConfig(
        provider="anthropic",
        model="claude-sonnet-4",
        temperature=0.0,
        max_tokens=4096,
    ),
    isolation=IsolationConfig(
        memory_namespace="agent:finance",
        network_access=True,  # Needs to fetch financial data
        filesystem_access=True,  # Needs to read/write financial docs
    ),
    capabilities=CapabilitiesConfig(
        can_propose_actions=True,
        can_execute_actions=False,  # INVARIANT_1
    ),
    permissions=PermissionsConfig(
        tools_allowed=["read_file", "write_file", "query_database", "call_api", "read_memory", "write_memory"],
        tools_forbidden=["execute_command", "send_message"],
    ),
    policy=PolicyConfig(
        policy_agent_required=True,
        risk_tolerance=RiskTolerance.LOW,  # Finance is high stakes
    ),
    audit=AuditConfig(
        snapshot_every_run=True,
        retention_days=365,  # Keep financial records 1 year
    ),
    lifecycle=LifecycleConfig(
        ephemeral=True,
        max_runtime_seconds=300,
    ),
)

# Security Agent Spec
SECURITY_AGENT_SPEC = AgentSpec(
    agent_id="security",
    agent_class=AgentClass.CLAWDBOT,
    model=ModelConfig(
        provider="anthropic",
        model="claude-sonnet-4",
        temperature=0.0,
        max_tokens=4096,
    ),
    isolation=IsolationConfig(
        memory_namespace="agent:security",
        network_access=False,  # Security agent doesn't need network
        filesystem_access=True,  # Needs to audit logs
    ),
    capabilities=CapabilitiesConfig(
        can_propose_actions=True,
        can_execute_actions=False,  # INVARIANT_1
    ),
    permissions=PermissionsConfig(
        tools_allowed=["read_file", "query_database", "read_memory"],  # Read-only mostly
        tools_forbidden=["execute_command", "call_api", "send_message"],
    ),
    policy=PolicyConfig(
        policy_agent_required=True,
        risk_tolerance=RiskTolerance.LOW,
    ),
    audit=AuditConfig(
        snapshot_every_run=True,
        retention_days=365,
    ),
    lifecycle=LifecycleConfig(
        ephemeral=True,
        max_runtime_seconds=300,
    ),
)

# Legal Analyzer Agent Spec
LEGAL_ANALYZER_SPEC = AgentSpec(
    agent_id="legal_analyzer",
    agent_class=AgentClass.CLAWDBOT,
    model=ModelConfig(
        provider="anthropic",
        model="claude-opus-4",  # Use Opus for complex legal analysis
        temperature=0.0,
        max_tokens=8192,
    ),
    isolation=IsolationConfig(
        memory_namespace="agent:legal_analyzer",
        network_access=True,  # Needs to fetch from sec.gov, irs.gov
        filesystem_access=True,
    ),
    capabilities=CapabilitiesConfig(
        can_propose_actions=True,
        can_execute_actions=False,  # INVARIANT_1
    ),
    permissions=PermissionsConfig(
        tools_allowed=["read_file", "call_api", "read_memory", "write_memory"],
        tools_forbidden=["write_file", "execute_command", "send_message"],
    ),
    policy=PolicyConfig(
        policy_agent_required=True,
        risk_tolerance=RiskTolerance.LOW,
    ),
    audit=AuditConfig(
        snapshot_every_run=True,
        retention_days=365,
    ),
    lifecycle=LifecycleConfig(
        ephemeral=True,
        max_runtime_seconds=600,  # Legal analysis can take longer
    ),
)


# Registry of all agent specs
AGENT_SPEC_REGISTRY: Dict[str, AgentSpec] = {
    "finance": FINANCE_AGENT_SPEC,
    "security": SECURITY_AGENT_SPEC,
    "legal_analyzer": LEGAL_ANALYZER_SPEC,
}


def get_agent_spec(agent_id: str) -> Optional[AgentSpec]:
    """Get agent spec by ID"""
    return AGENT_SPEC_REGISTRY.get(agent_id)


def register_agent_spec(spec: AgentSpec) -> None:
    """
    Register a new agent spec

    Validates the spec before registration
    """
    valid, error = spec.validate()
    if not valid:
        raise ValueError(f"Invalid agent spec: {error}")

    AGENT_SPEC_REGISTRY[spec.agent_id] = spec


def list_agent_specs() -> List[str]:
    """List all registered agent IDs"""
    return list(AGENT_SPEC_REGISTRY.keys())
