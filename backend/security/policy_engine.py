"""
Policy Engine - Security Decision Making
Evaluates ActionIntents and produces PolicyDecisions with CapabilityTokens
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path

from .schemas import (
    ActionIntent, PolicyDecision, CapabilityToken,
    ActionType, PolicyResult, CapabilityScope, RiskLevel,
    AuditLogEntry
)


logger = logging.getLogger(__name__)


class SecurityPolicy:
    """
    Security policy definitions

    Defines what actions are allowed/denied and under what conditions
    """

    def __init__(self):
        # Default policies
        self.policies = {
            # File operations
            ActionType.READ_FILE: {
                'allowed_paths': [
                    'memory/',
                    'backend/agents/',
                    'docs/',
                ],
                'denied_paths': [
                    '.env',
                    'credentials.json',
                    '.ssh/',
                    '/etc/',
                ],
                'requires_sanitization': False,
                'max_risk': RiskLevel.MEDIUM,
            },
            ActionType.WRITE_FILE: {
                'allowed_paths': [
                    'memory/',
                    'logs/',
                ],
                'denied_paths': [
                    'backend/',
                    '.env',
                    'credentials.json',
                ],
                'requires_sanitization': True,
                'max_risk': RiskLevel.HIGH,
            },
            ActionType.EXECUTE_COMMAND: {
                'allowed_commands': [
                    'ls', 'pwd', 'cat', 'grep', 'find',
                    'git status', 'git diff', 'git log',
                ],
                'denied_commands': [
                    'rm -rf', 'sudo', 'chmod', 'chown',
                    'curl', 'wget', 'ssh', 'scp',
                ],
                'requires_approval': True,
                'max_risk': RiskLevel.CRITICAL,
            },
            ActionType.QUERY_DATABASE: {
                'allowed_operations': ['SELECT', 'INSERT', 'UPDATE'],
                'denied_operations': ['DELETE', 'DROP', 'ALTER'],
                'requires_sanitization': True,
                'max_risk': RiskLevel.MEDIUM,
            },
            ActionType.CALL_API: {
                'allowed_domains': [
                    'api.venice.ai',
                    'api.anthropic.com',
                ],
                'denied_domains': [
                    '*'  # Deny all by default
                ],
                'requires_sanitization': True,
                'max_risk': RiskLevel.HIGH,
            },
            ActionType.DELEGATE_TASK: {
                'allowed_agents': [
                    'manager', 'finance', 'maintenance',
                    'security', 'contractors', 'projects', 'janitor'
                ],
                'max_risk': RiskLevel.LOW,
            },
            ActionType.READ_MEMORY: {
                'max_risk': RiskLevel.LOW,
            },
            ActionType.WRITE_MEMORY: {
                'requires_sanitization': True,
                'max_risk': RiskLevel.MEDIUM,
            },
            ActionType.SEARCH_WEB: {
                'requires_approval': False,
                'max_risk': RiskLevel.LOW,
            },
            ActionType.SEND_MESSAGE: {
                'requires_approval': True,
                'max_risk': RiskLevel.HIGH,
            },
        }

    def evaluate_action(self, intent: ActionIntent) -> tuple[PolicyResult, List[str], Set[str]]:
        """
        Evaluate if an action should be allowed

        Args:
            intent: ActionIntent to evaluate

        Returns:
            (result: PolicyResult, reasons: List[str], capabilities: Set[str])
        """
        action_type = intent.action_type
        policy = self.policies.get(action_type, {})

        reasons = []
        capabilities = set()

        # Check risk level
        max_risk = policy.get('max_risk', RiskLevel.MEDIUM)
        if self._risk_exceeds(intent.risk_level, max_risk):
            reasons.append(f"Risk level {intent.risk_level.value} exceeds max {max_risk.value}")
            return PolicyResult.DENY, reasons, capabilities

        # Action-specific checks
        if action_type == ActionType.READ_FILE:
            return self._evaluate_read_file(intent, policy)
        elif action_type == ActionType.WRITE_FILE:
            return self._evaluate_write_file(intent, policy)
        elif action_type == ActionType.EXECUTE_COMMAND:
            return self._evaluate_execute_command(intent, policy)
        elif action_type == ActionType.QUERY_DATABASE:
            return self._evaluate_query_database(intent, policy)
        elif action_type == ActionType.CALL_API:
            return self._evaluate_call_api(intent, policy)
        elif action_type == ActionType.DELEGATE_TASK:
            return self._evaluate_delegate_task(intent, policy)
        elif action_type in [ActionType.READ_MEMORY, ActionType.WRITE_MEMORY]:
            return self._evaluate_memory_access(intent, policy)
        elif action_type in [ActionType.SEARCH_WEB, ActionType.SEND_MESSAGE]:
            return self._evaluate_external_action(intent, policy)
        else:
            reasons.append(f"Unknown action type: {action_type}")
            return PolicyResult.DENY, reasons, capabilities

    def _risk_exceeds(self, actual: RiskLevel, maximum: RiskLevel) -> bool:
        """Check if actual risk exceeds maximum"""
        risk_values = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        return risk_values.get(actual, 0) > risk_values.get(maximum, 0)

    def _evaluate_read_file(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate READ_FILE action"""
        target = intent.target
        reasons = []
        capabilities = {'read_file'}

        # Check denied paths
        for denied in policy.get('denied_paths', []):
            if denied in target or target.startswith(denied):
                reasons.append(f"File path matches denied pattern: {denied}")
                return PolicyResult.DENY, reasons, set()

        # Check allowed paths
        allowed = False
        for allowed_path in policy.get('allowed_paths', []):
            if target.startswith(allowed_path):
                allowed = True
                break

        if not allowed:
            reasons.append("File path not in allowed list")
            return PolicyResult.DENY, reasons, set()

        return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_write_file(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate WRITE_FILE action"""
        target = intent.target
        reasons = []
        capabilities = {'write_file'}

        # Check denied paths
        for denied in policy.get('denied_paths', []):
            if denied in target or target.startswith(denied):
                reasons.append(f"File path matches denied pattern: {denied}")
                return PolicyResult.DENY, reasons, set()

        # Check allowed paths
        allowed = False
        for allowed_path in policy.get('allowed_paths', []):
            if target.startswith(allowed_path):
                allowed = True
                break

        if not allowed:
            reasons.append("File path not in allowed list")
            return PolicyResult.DENY, reasons, set()

        # Sanitization required
        if policy.get('requires_sanitization', False):
            return PolicyResult.SANITIZE, reasons, capabilities

        return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_execute_command(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate EXECUTE_COMMAND action"""
        command = intent.parameters.get('command', intent.target)
        reasons = []
        capabilities = {'execute_command'}

        # Check denied commands
        for denied in policy.get('denied_commands', []):
            if denied in command:
                reasons.append(f"Command contains denied pattern: {denied}")
                return PolicyResult.DENY, reasons, set()

        # Check if command is in allowed list
        allowed = False
        for allowed_cmd in policy.get('allowed_commands', []):
            if command.startswith(allowed_cmd):
                allowed = True
                break

        if not allowed:
            reasons.append("Command not in allowed list")
            if policy.get('requires_approval', False):
                return PolicyResult.ESCALATE, reasons, set()
            return PolicyResult.DENY, reasons, set()

        return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_query_database(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate QUERY_DATABASE action"""
        query = intent.parameters.get('query', '')
        reasons = []
        capabilities = {'query_database'}

        # Check for denied operations
        query_upper = query.upper()
        for denied_op in policy.get('denied_operations', []):
            if denied_op in query_upper:
                reasons.append(f"Query contains denied operation: {denied_op}")
                return PolicyResult.DENY, reasons, set()

        # Sanitization required
        if policy.get('requires_sanitization', False):
            return PolicyResult.SANITIZE, reasons, capabilities

        return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_call_api(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate CALL_API action"""
        target = intent.target
        reasons = []
        capabilities = {'call_api'}

        # Check allowed domains
        allowed = False
        for domain in policy.get('allowed_domains', []):
            if domain in target:
                allowed = True
                break

        if not allowed:
            reasons.append("API domain not in allowed list")
            return PolicyResult.DENY, reasons, set()

        # Sanitization required
        if policy.get('requires_sanitization', False):
            return PolicyResult.SANITIZE, reasons, capabilities

        return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_delegate_task(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate DELEGATE_TASK action"""
        target_agent = intent.target
        reasons = []
        capabilities = {'delegate_task'}

        # Check allowed agents
        if target_agent not in policy.get('allowed_agents', []):
            reasons.append(f"Agent '{target_agent}' not in allowed list")
            return PolicyResult.DENY, reasons, set()

        return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_memory_access(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate memory access"""
        reasons = []

        if intent.action_type == ActionType.READ_MEMORY:
            capabilities = {'read_memory'}
            return PolicyResult.ALLOW, reasons, capabilities
        else:  # WRITE_MEMORY
            capabilities = {'write_memory'}
            if policy.get('requires_sanitization', False):
                return PolicyResult.SANITIZE, reasons, capabilities
            return PolicyResult.ALLOW, reasons, capabilities

    def _evaluate_external_action(self, intent: ActionIntent, policy: Dict) -> tuple[PolicyResult, List[str], Set[str]]:
        """Evaluate external actions (web search, messaging)"""
        reasons = []

        if intent.action_type == ActionType.SEARCH_WEB:
            capabilities = {'search_web'}
        else:  # SEND_MESSAGE
            capabilities = {'send_message'}

        if policy.get('requires_approval', False):
            return PolicyResult.ESCALATE, reasons, capabilities

        return PolicyResult.ALLOW, reasons, capabilities


class PolicyEngine:
    """
    Policy Engine - Makes security decisions

    Evaluates ActionIntents and produces PolicyDecisions with CapabilityTokens
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize policy engine

        Args:
            secret_key: Secret for signing capability tokens
        """
        self.policy = SecurityPolicy()
        self.secret_key = secret_key or os.getenv('CAPABILITY_SECRET', 'default-secret-change-in-production')
        self.audit_log: List[AuditLogEntry] = []

        logger.info("PolicyEngine initialized")

    async def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        """
        Evaluate an action intent and produce policy decision

        Args:
            intent: ActionIntent to evaluate

        Returns:
            PolicyDecision with capability token if allowed
        """
        # Validate intent
        valid, error = intent.validate()
        if not valid:
            return self._create_denial(intent, [f"Invalid intent: {error}"])

        # Evaluate against policy
        result, reasons, capabilities = self.policy.evaluate_action(intent)

        # Create decision
        decision = PolicyDecision(
            intent_id=intent.id,
            result=result,
            allowed_capabilities=capabilities,
            denied_reasons=reasons,
            risk_assessment=intent.risk_level,
            evaluated_by="policy_agent"
        )

        # Generate capability token if allowed
        if result in [PolicyResult.ALLOW, PolicyResult.SANITIZE]:
            token = self._generate_capability_token(intent, capabilities)
            decision.capability_token = token.id

            # Store token for validation
            self._store_token(token)

        # Escalation handling
        if result == PolicyResult.ESCALATE:
            decision.escalation_required = True
            decision.escalation_reason = "; ".join(reasons) if reasons else "Requires human approval"

        # Audit log
        self._audit_decision(intent, decision)

        logger.info(f"Policy decision: {result.value} for intent {intent.id}")
        return decision

    def _create_denial(self, intent: ActionIntent, reasons: List[str]) -> PolicyDecision:
        """Create a denial decision"""
        decision = PolicyDecision(
            intent_id=intent.id,
            result=PolicyResult.DENY,
            denied_reasons=reasons,
            risk_assessment=RiskLevel.CRITICAL,
            evaluated_by="policy_agent"
        )
        self._audit_decision(intent, decision)
        return decision

    def _generate_capability_token(self, intent: ActionIntent, capabilities: Set[str]) -> CapabilityToken:
        """Generate a capability token"""
        # Determine scope
        if intent.action_type in [ActionType.READ_FILE, ActionType.WRITE_FILE]:
            scope = CapabilityScope.SINGLE_USE
        elif intent.action_type in [ActionType.READ_MEMORY, ActionType.WRITE_MEMORY]:
            scope = CapabilityScope.SESSION
        else:
            scope = CapabilityScope.SINGLE_USE

        # Create token
        token = CapabilityToken(
            capabilities=capabilities,
            scope=scope,
            issued_to=intent.requesting_agent,
            intent_id=intent.id,
            max_uses=1 if scope == CapabilityScope.SINGLE_USE else 100
        )

        # Set expiration
        if scope == CapabilityScope.SINGLE_USE:
            token.valid_until = (datetime.now() + timedelta(minutes=5)).isoformat()
        elif scope == CapabilityScope.SESSION:
            token.valid_until = (datetime.now() + timedelta(hours=1)).isoformat()

        # Generate signature
        token.signature = token.generate_signature(self.secret_key)

        return token

    def _store_token(self, token: CapabilityToken):
        """Store capability token (in-memory for now)"""
        # TODO: Persist to database in production
        if not hasattr(self, '_tokens'):
            self._tokens = {}
        self._tokens[token.id] = token

    def get_token(self, token_id: str) -> Optional[CapabilityToken]:
        """Retrieve capability token"""
        if not hasattr(self, '_tokens'):
            return None
        return self._tokens.get(token_id)

    def _audit_decision(self, intent: ActionIntent, decision: PolicyDecision):
        """Audit the policy decision"""
        entry = AuditLogEntry(
            event_type="policy_decision",
            agent_id=intent.requesting_agent,
            session_id=intent.session_id,
            action_intent_id=intent.id,
            policy_decision_id=decision.id,
            event_data={
                'action_type': intent.action_type.value,
                'target': intent.target,
                'result': decision.result.value,
                'capabilities': list(decision.allowed_capabilities),
            },
            result=decision.result.value,
            risk_level=decision.risk_assessment,
            flagged=decision.result == PolicyResult.DENY,
            flag_reason="; ".join(decision.denied_reasons) if decision.denied_reasons else None
        )
        self.audit_log.append(entry)

    def get_audit_log(self, limit: int = 100) -> List[AuditLogEntry]:
        """Get recent audit log entries"""
        return self.audit_log[-limit:]


# Global instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get global policy engine instance"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
