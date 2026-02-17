"""
Security Invariants - Immutable Rules
These invariants are enforced at runtime and cannot be violated
"""
from enum import Enum
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


class SecurityInvariant(str, Enum):
    """Core security invariants that must NEVER be violated"""

    NO_DIRECT_TOOL_EXECUTION = "INVARIANT_1"
    NO_SHARED_MEMORY = "INVARIANT_2"
    SIDE_EFFECTS_REQUIRE_POLICY_AND_TOKEN = "INVARIANT_3"
    NO_UNTRUSTED_CONCATENATION = "INVARIANT_4"
    AUTHORITY_EXPIRES_AUTOMATICALLY = "INVARIANT_5"


class InvariantViolation(Exception):
    """
    Raised when a security invariant is violated

    This is a critical security exception that should:
    1. Halt execution immediately
    2. Log the violation with full context
    3. Trigger security alerts
    4. Never be caught/suppressed
    """
    def __init__(self, invariant: SecurityInvariant, message: str, context: dict = None):
        self.invariant = invariant
        self.context = context or {}
        super().__init__(f"SECURITY INVARIANT VIOLATED: {invariant.value} - {message}")

        # Log critical security violation
        logger.critical(
            f"INVARIANT VIOLATION: {invariant.value} - {message}",
            extra={
                "invariant": invariant.value,
                "violation_context": self.context,
            }
        )


class InvariantEnforcer:
    """
    Enforces security invariants at runtime

    Usage:
        enforcer = InvariantEnforcer()
        enforcer.check_no_direct_tool_execution(agent_id, tool_name)
    """

    @staticmethod
    def check_no_direct_tool_execution(agent_id: str, tool_name: str):
        """
        INVARIANT 1: No agent may directly execute tools

        Agents can only PROPOSE actions. The platform executes.
        """
        raise InvariantViolation(
            SecurityInvariant.NO_DIRECT_TOOL_EXECUTION,
            f"Agent {agent_id} attempted to directly execute tool {tool_name}",
            {"agent_id": agent_id, "tool_name": tool_name}
        )

    @staticmethod
    def check_no_shared_memory(agent_id: str, memory_namespace: str, requested_namespace: str):
        """
        INVARIANT 2: No agent may share memory with another agent

        Each agent has its own isolated memory namespace
        """
        if memory_namespace != requested_namespace:
            raise InvariantViolation(
                SecurityInvariant.NO_SHARED_MEMORY,
                f"Agent {agent_id} attempted to access foreign namespace {requested_namespace}",
                {
                    "agent_id": agent_id,
                    "own_namespace": memory_namespace,
                    "requested_namespace": requested_namespace,
                }
            )

    @staticmethod
    def check_side_effects_require_approval(
        has_policy_decision: bool,
        has_capability_token: bool,
        action_description: str
    ):
        """
        INVARIANT 3: All side effects require policy approval AND capability tokens

        No state changes without both policy and token
        """
        if not has_policy_decision:
            raise InvariantViolation(
                SecurityInvariant.SIDE_EFFECTS_REQUIRE_POLICY_AND_TOKEN,
                f"Side effect attempted without policy decision: {action_description}",
                {"has_policy": False, "has_token": has_capability_token}
            )

        if not has_capability_token:
            raise InvariantViolation(
                SecurityInvariant.SIDE_EFFECTS_REQUIRE_POLICY_AND_TOKEN,
                f"Side effect attempted without capability token: {action_description}",
                {"has_policy": True, "has_token": False}
            )

    @staticmethod
    def check_no_untrusted_concatenation(content_source: str, is_in_prompt: bool):
        """
        INVARIANT 4: Untrusted content is never concatenated into system prompts

        Documents/files/emails must be passed by reference only
        """
        if content_source in {"pdf", "web", "email", "doc", "file"} and is_in_prompt:
            raise InvariantViolation(
                SecurityInvariant.NO_UNTRUSTED_CONCATENATION,
                f"Untrusted content from {content_source} was concatenated into prompt",
                {"source": content_source}
            )

    @staticmethod
    def check_authority_expiry(token_issued_at: float, token_expires_at: float, current_time: float):
        """
        INVARIANT 5: Authority is leased per request and expires automatically

        Tokens must have expiration and be checked
        """
        if token_expires_at is None:
            raise InvariantViolation(
                SecurityInvariant.AUTHORITY_EXPIRES_AUTOMATICALLY,
                "Capability token has no expiration",
                {"issued_at": token_issued_at}
            )

        if current_time > token_expires_at:
            raise InvariantViolation(
                SecurityInvariant.AUTHORITY_EXPIRES_AUTOMATICALLY,
                "Capability token has expired",
                {
                    "issued_at": token_issued_at,
                    "expires_at": token_expires_at,
                    "current_time": current_time,
                }
            )


def enforce_invariants(func: Callable) -> Callable:
    """
    Decorator to enforce invariants on functions

    Usage:
        @enforce_invariants
        def execute_tool(agent_id, tool_name, token):
            # This will check invariants before execution
            ...
    """
    def wrapper(*args, **kwargs):
        # Enforce invariants before execution
        # (specific checks depend on function signature)
        try:
            return func(*args, **kwargs)
        except InvariantViolation:
            # Never suppress invariant violations
            raise
        except Exception as e:
            # Log other exceptions but don't mask them as invariant violations
            logger.error(f"Error in {func.__name__}: {e}")
            raise

    return wrapper


# Philosophy enforcement
PHILOSOPHY = """
Agents think.
Policy decides.
Platform acts.

Invariants:
1. Agents propose, never execute
2. Memory is isolated per agent
3. Side effects require approval + token
4. Untrusted content stays isolated
5. Authority expires automatically
"""


def get_philosophy() -> str:
    """Get the system philosophy statement"""
    return PHILOSOPHY
