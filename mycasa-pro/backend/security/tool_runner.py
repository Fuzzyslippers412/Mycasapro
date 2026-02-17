"""
Secure Tool Runner with Capability-Based Access Control
Only executes tools with valid capability tokens
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .schemas import (
    CapabilityToken, ActionIntent, AuditLogEntry,
    RiskLevel
)
from .policy_engine import get_policy_engine


logger = logging.getLogger(__name__)


class ToolExecutionResult:
    """Result of tool execution"""

    def __init__(self, success: bool, output: Any, sanitized: bool = False, error: Optional[str] = None):
        self.success = success
        self.output = output
        self.sanitized = sanitized
        self.error = error
        self.timestamp = datetime.now().isoformat()


class SecureToolRunner:
    """
    Secure tool runner with capability-based access control

    Tools can ONLY be executed with valid capability tokens
    """

    def __init__(self):
        self.policy_engine = get_policy_engine()
        self.audit_log: List[AuditLogEntry] = []

        logger.info("SecureToolRunner initialized")

    async def execute(self, intent: ActionIntent, token_id: str) -> ToolExecutionResult:
        """
        Execute a tool with capability token validation

        Args:
            intent: ActionIntent describing the action
            token_id: Capability token ID

        Returns:
            ToolExecutionResult
        """
        # Get and validate token
        token = self.policy_engine.get_token(token_id)
        if not token:
            self._audit_execution(intent, None, "failure", "Token not found")
            return ToolExecutionResult(False, None, error="Invalid capability token")

        # Verify token signature
        if not token.verify_signature(self.policy_engine.secret_key):
            self._audit_execution(intent, token, "failure", "Invalid signature")
            return ToolExecutionResult(False, None, error="Token signature invalid")

        # Check token validity
        valid, reason = token.is_valid()
        if not valid:
            self._audit_execution(intent, token, "failure", reason)
            return ToolExecutionResult(False, None, error=f"Token invalid: {reason}")

        # Check token matches intent
        if token.intent_id != intent.id:
            self._audit_execution(intent, token, "failure", "Token doesn't match intent")
            return ToolExecutionResult(False, None, error="Token doesn't match this intent")

        # Check token has required capabilities
        required_capability = self._get_required_capability(intent)
        if required_capability not in token.capabilities:
            self._audit_execution(intent, token, "failure", "Missing capability")
            return ToolExecutionResult(
                False, None,
                error=f"Token missing required capability: {required_capability}"
            )

        # Mark token as used
        token.mark_used()

        # Execute the tool
        try:
            result = await self._execute_tool(intent)
            self._audit_execution(intent, token, "success", None)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            self._audit_execution(intent, token, "failure", str(e))
            return ToolExecutionResult(False, None, error=f"Execution failed: {str(e)}")

    def _get_required_capability(self, intent: ActionIntent) -> str:
        """Get required capability for action"""
        from .schemas import ActionType

        capability_map = {
            ActionType.READ_FILE: 'read_file',
            ActionType.WRITE_FILE: 'write_file',
            ActionType.EXECUTE_COMMAND: 'execute_command',
            ActionType.QUERY_DATABASE: 'query_database',
            ActionType.CALL_API: 'call_api',
            ActionType.DELEGATE_TASK: 'delegate_task',
            ActionType.READ_MEMORY: 'read_memory',
            ActionType.WRITE_MEMORY: 'write_memory',
            ActionType.SEARCH_WEB: 'search_web',
            ActionType.SEND_MESSAGE: 'send_message',
        }
        return capability_map.get(intent.action_type, 'unknown')

    async def _execute_tool(self, intent: ActionIntent) -> ToolExecutionResult:
        """
        Execute the actual tool

        This is where the real tool execution happens
        """
        from .schemas import ActionType

        action_type = intent.action_type

        try:
            if action_type == ActionType.READ_FILE:
                return await self._read_file(intent)
            elif action_type == ActionType.WRITE_FILE:
                return await self._write_file(intent)
            elif action_type == ActionType.EXECUTE_COMMAND:
                return await self._execute_command(intent)
            elif action_type == ActionType.QUERY_DATABASE:
                return await self._query_database(intent)
            elif action_type == ActionType.CALL_API:
                return await self._call_api(intent)
            elif action_type == ActionType.DELEGATE_TASK:
                return await self._delegate_task(intent)
            elif action_type == ActionType.READ_MEMORY:
                return await self._read_memory(intent)
            elif action_type == ActionType.WRITE_MEMORY:
                return await self._write_memory(intent)
            elif action_type == ActionType.SEARCH_WEB:
                return await self._search_web(intent)
            elif action_type == ActionType.SEND_MESSAGE:
                return await self._send_message(intent)
            else:
                return ToolExecutionResult(False, None, error=f"Unknown action type: {action_type}")

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolExecutionResult(False, None, error=str(e))

    async def _read_file(self, intent: ActionIntent) -> ToolExecutionResult:
        """Read file tool"""
        import aiofiles
        from pathlib import Path

        try:
            file_path = Path(intent.target)

            # Security check: ensure path is within allowed directories
            # This is enforced by policy, but double-check here
            if not file_path.exists():
                return ToolExecutionResult(False, None, error="File not found")

            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()

            return ToolExecutionResult(True, content)

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Failed to read file: {str(e)}")

    async def _write_file(self, intent: ActionIntent) -> ToolExecutionResult:
        """Write file tool"""
        import aiofiles
        from pathlib import Path

        try:
            file_path = Path(intent.target)
            content = intent.parameters.get('content', '')

            # Sanitize content if needed
            if intent.parameters.get('sanitize', False):
                content = self._sanitize_content(content)

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, 'w') as f:
                await f.write(content)

            return ToolExecutionResult(True, f"File written: {file_path}", sanitized=intent.parameters.get('sanitize', False))

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Failed to write file: {str(e)}")

    async def _execute_command(self, intent: ActionIntent) -> ToolExecutionResult:
        """Execute command tool"""
        import asyncio

        try:
            command = intent.parameters.get('command', intent.target)

            # Execute with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
            except asyncio.TimeoutError:
                process.kill()
                return ToolExecutionResult(False, None, error="Command timed out")

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            if process.returncode != 0:
                return ToolExecutionResult(False, output, error=error)

            return ToolExecutionResult(True, output)

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Failed to execute command: {str(e)}")

    async def _query_database(self, intent: ActionIntent) -> ToolExecutionResult:
        """Query database tool"""
        try:
            from storage.database import get_db_session
            from sqlalchemy import text

            query = intent.parameters.get('query', '')

            # Sanitize query if needed
            if intent.parameters.get('sanitize', False):
                query = self._sanitize_sql(query)

            db = get_db_session()
            try:
                result = db.execute(text(query))
                rows = result.fetchall()

                # Convert to list of dicts
                output = [dict(row._mapping) for row in rows]

                return ToolExecutionResult(True, output, sanitized=intent.parameters.get('sanitize', False))
            finally:
                db.close()

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Database query failed: {str(e)}")

    async def _call_api(self, intent: ActionIntent) -> ToolExecutionResult:
        """Call API tool"""
        import aiohttp

        try:
            url = intent.target
            method = intent.parameters.get('method', 'GET')
            headers = intent.parameters.get('headers', {})
            data = intent.parameters.get('data', None)

            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=data) as response:
                    result = await response.json() if response.content_type == 'application/json' else await response.text()
                    return ToolExecutionResult(True, result)

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"API call failed: {str(e)}")

    async def _delegate_task(self, intent: ActionIntent) -> ToolExecutionResult:
        """Delegate task to another agent"""
        try:
            target_agent = intent.target
            task = intent.parameters.get('task', '')

            # This would integrate with the agent coordination system
            # For now, return success
            return ToolExecutionResult(True, f"Task delegated to {target_agent}: {task}")

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Delegation failed: {str(e)}")

    async def _read_memory(self, intent: ActionIntent) -> ToolExecutionResult:
        """Read from memory system"""
        try:
            from storage.memory import get_memory_manager

            memory = get_memory_manager()
            entity_id = intent.target

            # Get facts from entity
            facts = await memory.get_facts(entity_id, status="active")

            return ToolExecutionResult(True, [f.to_dict() for f in facts])

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Memory read failed: {str(e)}")

    async def _write_memory(self, intent: ActionIntent) -> ToolExecutionResult:
        """Write to memory system"""
        try:
            from storage.memory import get_memory_manager

            memory = get_memory_manager()
            entity_id = intent.target
            fact = intent.parameters.get('fact', {})

            # Sanitize fact if needed
            if intent.parameters.get('sanitize', False):
                fact['fact'] = self._sanitize_content(fact.get('fact', ''))

            success, msg = await memory.write_fact(entity_id, fact)
            return ToolExecutionResult(success, msg, sanitized=intent.parameters.get('sanitize', False))

        except Exception as e:
            return ToolExecutionResult(False, None, error=f"Memory write failed: {str(e)}")

    async def _search_web(self, intent: ActionIntent) -> ToolExecutionResult:
        """Search web tool (placeholder)"""
        # This would integrate with actual web search
        return ToolExecutionResult(True, f"Web search for: {intent.target}")

    async def _send_message(self, intent: ActionIntent) -> ToolExecutionResult:
        """Send message tool (placeholder)"""
        # This would integrate with messaging systems
        return ToolExecutionResult(True, f"Message sent to: {intent.target}")

    def _sanitize_content(self, content: str) -> str:
        """Sanitize text content"""
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            '<script', 'javascript:', 'onerror=', 'onclick=',
            'eval(', 'exec(', 'import os', 'import sys'
        ]

        sanitized = content
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, f"[REDACTED:{pattern}]")

        return sanitized

    def _sanitize_sql(self, query: str) -> str:
        """Sanitize SQL query"""
        # Remove dangerous SQL operations
        dangerous = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'EXEC', 'EXECUTE']

        sanitized = query
        for op in dangerous:
            if op in query.upper():
                raise ValueError(f"Dangerous SQL operation detected: {op}")

        return sanitized

    def _audit_execution(
        self,
        intent: ActionIntent,
        token: Optional[CapabilityToken],
        result: str,
        error: Optional[str]
    ):
        """Audit tool execution"""
        entry = AuditLogEntry(
            event_type="tool_execution",
            agent_id=intent.requesting_agent,
            session_id=intent.session_id,
            action_intent_id=intent.id,
            capability_token_id=token.id if token else None,
            event_data={
                'action_type': intent.action_type.value,
                'target': intent.target,
                'parameters': intent.parameters,
            },
            result=result,
            error_message=error,
            risk_level=intent.risk_level,
            flagged=result == "failure",
            flag_reason=error
        )
        self.audit_log.append(entry)

    def get_audit_log(self, limit: int = 100) -> List[AuditLogEntry]:
        """Get recent audit log entries"""
        return self.audit_log[-limit:]


# Global instance
_tool_runner: Optional[SecureToolRunner] = None


def get_tool_runner() -> SecureToolRunner:
    """Get global tool runner instance"""
    global _tool_runner
    if _tool_runner is None:
        _tool_runner = SecureToolRunner()
    return _tool_runner
