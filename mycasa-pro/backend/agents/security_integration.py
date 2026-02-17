"""
Security Integration for Agent Coordination
Bridges the security layer with agent coordination system
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from security import (
    ActionIntent, ActionType, PolicyDecision, PolicyResult,
    RiskLevel, get_policy_engine, get_tool_runner, get_evidence_manager
)
from .coordination import get_coordinator, Event, EventType, Priority


logger = logging.getLogger(__name__)


class SecureAgentCoordinator:
    """
    Security-enhanced coordinator wrapper

    Provides secure tool execution with ActionIntent/PolicyDecision flow
    """

    def __init__(self):
        self.coordinator = get_coordinator()
        self.policy_engine = get_policy_engine()
        self.tool_runner = get_tool_runner()
        self.evidence_manager = get_evidence_manager()

        # Subscribe to security events
        self.coordinator.subscribe("security", EventType.SECURITY_INCIDENT)

        logger.info("SecureAgentCoordinator initialized")

    async def request_tool_execution(
        self,
        agent_id: str,
        session_id: str,
        action_type: ActionType,
        target: str,
        parameters: Dict[str, Any] = None,
        rationale: str = "",
        risk_level: RiskLevel = RiskLevel.LOW,
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Request tool execution with security validation

        Flow:
        1. Create ActionIntent
        2. Get PolicyDecision
        3. Execute with CapabilityToken if allowed
        4. Audit log the operation

        Args:
            agent_id: Requesting agent
            session_id: Session ID
            action_type: Type of action (READ_FILE, WRITE_FILE, etc.)
            target: Target of action (file path, API URL, etc.)
            parameters: Action parameters
            rationale: Why this action is needed
            risk_level: Assessed risk level

        Returns:
            (success: bool, result: Any, error: Optional[str])
        """
        # Step 1: Create ActionIntent
        intent = ActionIntent(
            action_type=action_type,
            target=target,
            parameters=parameters or {},
            rationale=rationale,
            risk_level=risk_level,
            requesting_agent=agent_id,
            session_id=session_id,
        )

        logger.info(f"[Security] Intent created: {intent.id} by {agent_id} for {action_type.value}")

        # Step 2: Get PolicyDecision
        decision = await self.policy_engine.evaluate(intent)

        logger.info(f"[Security] Policy decision: {decision.result.value} for intent {intent.id}")

        # Step 3: Handle decision
        if decision.result == PolicyResult.DENY:
            logger.warning(f"[Security] Action DENIED: {decision.denied_reasons}")
            # Publish security event
            self.coordinator.publish_event(
                EventType.SECURITY_INCIDENT,
                agent_id,
                {
                    "intent_id": intent.id,
                    "action_type": action_type.value,
                    "target": target,
                    "denied_reasons": decision.denied_reasons,
                },
                Priority.HIGH,
            )
            return False, None, f"Access denied: {'; '.join(decision.denied_reasons)}"

        elif decision.result == PolicyResult.ESCALATE:
            logger.info(f"[Security] Action ESCALATED: {decision.escalation_reason}")
            # For now, treat escalation as denial
            # In production, this would request human approval
            return False, None, f"Requires approval: {decision.escalation_reason}"

        elif decision.result == PolicyResult.SANITIZE:
            logger.info(f"[Security] Action SANITIZE: content will be sanitized")
            # Mark for sanitization
            intent.parameters['sanitize'] = True

        # Step 4: Execute with token
        if not decision.capability_token:
            logger.error(f"[Security] No capability token for allowed action")
            return False, None, "Internal error: No capability token"

        result = await self.tool_runner.execute(intent, decision.capability_token)

        if result.success:
            logger.info(f"[Security] Tool execution SUCCESS: {intent.id}")
            self.coordinator.record_agent_success(agent_id)
            return True, result.output, None
        else:
            logger.error(f"[Security] Tool execution FAILED: {result.error}")
            self.coordinator.record_agent_failure(agent_id)
            return False, None, result.error

    async def secure_file_read(
        self,
        agent_id: str,
        session_id: str,
        file_path: str,
        rationale: str = "Reading file for agent task",
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Securely read a file with policy enforcement

        Returns:
            (success: bool, content: Optional[str], error: Optional[str])
        """
        return await self.request_tool_execution(
            agent_id=agent_id,
            session_id=session_id,
            action_type=ActionType.READ_FILE,
            target=file_path,
            rationale=rationale,
            risk_level=RiskLevel.LOW,
        )

    async def secure_file_write(
        self,
        agent_id: str,
        session_id: str,
        file_path: str,
        content: str,
        rationale: str = "Writing file for agent task",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Securely write a file with policy enforcement

        Returns:
            (success: bool, message: Optional[str], error: Optional[str])
        """
        return await self.request_tool_execution(
            agent_id=agent_id,
            session_id=session_id,
            action_type=ActionType.WRITE_FILE,
            target=file_path,
            parameters={'content': content},
            rationale=rationale,
            risk_level=risk_level,
        )

    async def secure_command_execution(
        self,
        agent_id: str,
        session_id: str,
        command: str,
        rationale: str = "Executing command for agent task",
        risk_level: RiskLevel = RiskLevel.HIGH,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Securely execute a command with policy enforcement

        Returns:
            (success: bool, output: Optional[str], error: Optional[str])
        """
        return await self.request_tool_execution(
            agent_id=agent_id,
            session_id=session_id,
            action_type=ActionType.EXECUTE_COMMAND,
            target=command,
            parameters={'command': command},
            rationale=rationale,
            risk_level=risk_level,
        )

    async def secure_memory_read(
        self,
        agent_id: str,
        session_id: str,
        entity_id: str,
        rationale: str = "Reading memory for agent task",
    ) -> Tuple[bool, Optional[list], Optional[str]]:
        """
        Securely read from memory with policy enforcement

        Returns:
            (success: bool, facts: Optional[list], error: Optional[str])
        """
        return await self.request_tool_execution(
            agent_id=agent_id,
            session_id=session_id,
            action_type=ActionType.READ_MEMORY,
            target=entity_id,
            rationale=rationale,
            risk_level=RiskLevel.LOW,
        )

    async def secure_memory_write(
        self,
        agent_id: str,
        session_id: str,
        entity_id: str,
        fact: Dict[str, Any],
        rationale: str = "Writing memory for agent task",
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Securely write to memory with policy enforcement

        Returns:
            (success: bool, message: Optional[str], error: Optional[str])
        """
        return await self.request_tool_execution(
            agent_id=agent_id,
            session_id=session_id,
            action_type=ActionType.WRITE_MEMORY,
            target=entity_id,
            parameters={'fact': fact},
            rationale=rationale,
            risk_level=RiskLevel.MEDIUM,
        )

    async def secure_api_call(
        self,
        agent_id: str,
        session_id: str,
        url: str,
        method: str = "GET",
        headers: Dict[str, str] = None,
        data: Dict[str, Any] = None,
        rationale: str = "Making API call for agent task",
        risk_level: RiskLevel = RiskLevel.HIGH,
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Securely make an API call with policy enforcement

        Returns:
            (success: bool, response: Optional[Any], error: Optional[str])
        """
        return await self.request_tool_execution(
            agent_id=agent_id,
            session_id=session_id,
            action_type=ActionType.CALL_API,
            target=url,
            parameters={
                'method': method,
                'headers': headers or {},
                'data': data,
            },
            rationale=rationale,
            risk_level=risk_level,
        )

    def create_evidence_bundle(
        self,
        session_id: str,
        agent_id: str,
    ) -> str:
        """
        Create an evidence bundle for isolated document storage

        Returns:
            bundle_id: str
        """
        bundle = self.evidence_manager.create_bundle(session_id, agent_id)
        logger.info(f"[Security] Evidence bundle created: {bundle.id}")
        return bundle.id

    def add_evidence(
        self,
        bundle_id: str,
        content: str,
        source: str,
        content_type: str = "text/plain",
    ) -> Optional[str]:
        """
        Add evidence to bundle

        Returns:
            evidence_id: Optional[str]
        """
        evidence_id = self.evidence_manager.add_evidence(
            bundle_id,
            content,
            source,
            content_type,
        )

        if evidence_id:
            logger.info(f"[Security] Evidence added: {evidence_id} to bundle {bundle_id}")

        return evidence_id

    def get_evidence_references(self, bundle_id: str) -> list:
        """
        Get evidence references (not content) for prompts

        Returns:
            List of references (id, source, content_type)
        """
        return self.evidence_manager.get_references(bundle_id)

    def get_evidence_content(
        self,
        bundle_id: str,
        evidence_id: str,
    ) -> Optional[str]:
        """
        Get evidence content by ID (only when explicitly needed)

        Returns:
            content: Optional[str]
        """
        return self.evidence_manager.get_evidence(bundle_id, evidence_id)

    def get_audit_log(
        self,
        agent_id: str = None,
        limit: int = 100,
    ) -> list:
        """
        Get audit log entries

        Args:
            agent_id: Filter by agent (optional)
            limit: Max entries to return

        Returns:
            List of audit log entries
        """
        # Get from both policy engine and tool runner
        policy_log = self.policy_engine.get_audit_log(limit)
        tool_log = self.tool_runner.get_audit_log(limit)

        # Combine and sort by timestamp
        all_logs = policy_log + tool_log
        all_logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Filter by agent if specified
        if agent_id:
            all_logs = [log for log in all_logs if log.agent_id == agent_id]

        return all_logs[:limit]

    def get_security_summary(self) -> Dict[str, Any]:
        """
        Get security summary statistics

        Returns:
            Dict with security metrics
        """
        policy_log = self.policy_engine.get_audit_log(1000)
        tool_log = self.tool_runner.get_audit_log(1000)

        # Count results
        allowed = sum(1 for log in policy_log if log.result == "allow")
        denied = sum(1 for log in policy_log if log.result == "deny")
        sanitized = sum(1 for log in policy_log if log.result == "sanitize")
        escalated = sum(1 for log in policy_log if log.result == "escalate")

        # Count tool execution outcomes
        successful_executions = sum(1 for log in tool_log if log.result == "success")
        failed_executions = sum(1 for log in tool_log if log.result == "failure")

        # Count by risk level
        critical_actions = sum(1 for log in policy_log if log.risk_level == RiskLevel.CRITICAL)
        high_risk_actions = sum(1 for log in policy_log if log.risk_level == RiskLevel.HIGH)

        return {
            "total_policy_decisions": len(policy_log),
            "allowed": allowed,
            "denied": denied,
            "sanitized": sanitized,
            "escalated": escalated,
            "total_tool_executions": len(tool_log),
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "critical_actions": critical_actions,
            "high_risk_actions": high_risk_actions,
            "denial_rate": denied / len(policy_log) if policy_log else 0,
            "success_rate": successful_executions / len(tool_log) if tool_log else 0,
        }


# Global secure coordinator instance
_secure_coordinator: Optional[SecureAgentCoordinator] = None


def get_secure_coordinator() -> SecureAgentCoordinator:
    """Get global secure coordinator instance"""
    global _secure_coordinator
    if _secure_coordinator is None:
        _secure_coordinator = SecureAgentCoordinator()
    return _secure_coordinator
