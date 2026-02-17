"""
Manager Agent - Galidima
The system orchestrator - a specialized clone for MyCasa Pro
Connects to Clawdbot for real AI responses and coordinates all agents
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import BaseAgent


class ManagerAgent(BaseAgent):
    """
    Manager Agent (Galidima) - the orchestrator of MyCasa Pro
    
    This is the main AI interface - a specialized version of Galidima
    focused on home management. Connects to the real Clawdbot backend
    for AI responses and coordinates all other agents.
    
    Responsibilities:
    - Coordinate all domain agents
    - Route requests to appropriate agents
    - Provide system-wide status
    - Handle cross-domain operations
    - Safe code editing (via Janitor review)
    - Main chat interface for users
    """
    
    def __init__(self):
        super().__init__(
            agent_id="manager",
            name="Galidima",
            description="Your AI home manager - coordinates all agents",
            emoji="🏠"
        )
        self.start()
        
        # Register with coordinator
        from .coordination import get_coordinator, EventType
        coordinator = get_coordinator()
        coordinator.register_agent(self.agent_id, self)
        
        # Subscribe to escalation events
        self.subscribe_to_events([
            EventType.TASK_FAILED,
            EventType.SECURITY_INCIDENT,
            EventType.ALERT_TRIGGERED,
            EventType.BUDGET_WARNING,
        ])
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get manager-specific metrics"""
        return {
            "agents_managed": 6,
            "system_status": "operational",
        }

    def get_agent_by_id(self, agent_id: str):
        """Get an agent instance by ID"""
        from . import (
            FinanceAgent, MaintenanceAgent, ContractorsAgent,
            ProjectsAgent, SecurityManagerAgent, JanitorAgent
        )

        agent_map = {
            "finance": FinanceAgent,
            "maintenance": MaintenanceAgent,
            "contractors": ContractorsAgent,
            "projects": ProjectsAgent,
            "security": SecurityManagerAgent,
            "security-manager": SecurityManagerAgent,
            "janitor": JanitorAgent,
        }

        AgentClass = agent_map.get(agent_id.lower())
        if AgentClass:
            return AgentClass()
        return None
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get a summary of all agents"""
        from . import (
            FinanceAgent, MaintenanceAgent, ContractorsAgent,
            ProjectsAgent, SecurityManagerAgent, JanitorAgent
        )
        
        agents_status = []
        for AgentClass in [FinanceAgent, MaintenanceAgent, ContractorsAgent, 
                          ProjectsAgent, SecurityManagerAgent, JanitorAgent]:
            try:
                agent = AgentClass()
                status = agent.get_status()
                agents_status.append({
                    "id": status["agent_id"],
                    "name": status["name"],
                    "status": status["status"],
                    "emoji": status["emoji"],
                })
            except Exception as e:
                agents_status.append({
                    "id": "unknown",
                    "name": str(AgentClass),
                    "status": "error",
                    "error": str(e),
                })
        
        return {
            "timestamp": self.get_status()["last_check"],
            "agents": agents_status,
            "system_status": "operational" if all(a["status"] == "running" for a in agents_status) else "degraded",
        }
    
    def delegate_to_agent(self, agent_id: str, task: str, context: Dict[str, Any] = None) -> str:
        """
        Delegate a task to another agent.
        Returns the message_id for tracking.
        """
        return self.send_to_agent(
            to_agent=agent_id,
            message_type="task_delegation",
            content={
                "task": task,
                "context": context or {},
                "delegated_at": self.get_status()["last_check"],
            },
            priority="normal"
        )
    
    def _strip_cot_format(self, text: str) -> str:
        """
        Remove Chain-of-Thought format labels from response.
        Extracts only the Final Answer or natural text.
        """
        import re

        if not text:
            return text

        final_pattern = re.compile(r"(?:^|\n)\s*(?:\*\*|__)?\s*final answer\s*(?:\*\*|__)?\s*:?\s*", re.IGNORECASE)
        match = final_pattern.search(text)
        if match:
            return text[match.end():].strip()

        # Remove lines that start with CoT labels
        cot_patterns = [
            r'^\s*(?:\*\*|__)?\s*Thought\s*(?:\*\*|__)?\s*:?.*$',
            r'^\s*(?:\*\*|__)?\s*Action\s*(?:\*\*|__)?\s*:?.*$',
            r'^\s*(?:\*\*|__)?\s*Observation\s*(?:\*\*|__)?\s*:?.*$',
            r'^\s*(?:\*\*|__)?\s*Final Answer\s*(?:\*\*|__)?\s*:?.*$',
        ]

        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip lines matching CoT patterns
            skip = False
            for pattern in cot_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    skip = True
                    break
            if not skip:
                cleaned_lines.append(line)

        cleaned = '\n'.join(cleaned_lines).strip()
        return cleaned if cleaned else text

    # ==================== TEAM COORDINATION ====================

    async def coordinate_team(
        self, 
        team_id: str, 
        description: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Coordinate a team to handle a complex task.
        
        Args:
            team_id: ID of the team (preset or custom)
            description: What the team should accomplish
            context: Additional context/parameters
        
        Returns:
            Task execution result
        """
        from .teams import get_orchestrator
        
        self.log_action("team_coordination_started", f"Team: {team_id}, Task: {description[:50]}...")
        
        orchestrator = get_orchestrator()
        
        # Create and execute team task
        task = orchestrator.create_task(
            team_id=team_id,
            description=description,
            context=context or {},
        )
        
        result = await orchestrator.execute_task(task)
        
        self.log_action(
            "team_coordination_completed" if result.get("status") == "completed" else "team_coordination_failed",
            f"Team: {team_id}, Result: {result.get('status', 'unknown')}"
        )
        
        return result
    
    def get_team_for_request(self, message: str) -> Optional[str]:
        """
        Analyze a request and determine if it needs team coordination.
        Returns team_id if a team should handle it, None otherwise.
        """
        from .coordination import get_coordinator
        
        coordinator = get_coordinator()
        routing = coordinator.route_with_team_suggestion(message)
        
        return routing.get("suggested_team")
    
    async def handle_complex_request(self, message: str) -> Dict[str, Any]:
        """
        Smart routing for complex requests.
        
        1. Analyzes the request
        2. Determines if single agent or team needed
        3. Routes appropriately
        4. Returns structured result
        """
        from .coordination import get_coordinator
        
        coordinator = get_coordinator()
        routing = coordinator.route_with_team_suggestion(message)
        
        self.log_action("request_analysis", f"Routing: {routing}")
        
        # Check if team coordination needed
        if routing.get("suggested_team"):
            return await self.coordinate_team(
                team_id=routing["suggested_team"],
                description=message,
                context={"confidence": routing["confidence"], "scores": routing["all_scores"]},
            )
        
        # Single agent delegation
        if routing.get("primary_agent"):
            msg_id = self.delegate_to_agent(
                agent_id=routing["primary_agent"],
                task=message,
                context={"confidence": routing["confidence"]},
            )
            return {
                "routed_to": routing["primary_agent"],
                "message_id": msg_id,
                "confidence": routing["confidence"],
            }
        
        # Manager handles directly
        return {
            "handled_by": "manager",
            "confidence": routing["confidence"],
        }
    
    def handle_event(self, event):
        """Handle events escalated to manager"""
        from .coordination import EventType
        
        super().handle_event(event)
        
        # Take action based on event type
        if event.type == EventType.SECURITY_INCIDENT:
            self.log_action("security_escalation", f"Incident: {event.payload}", status="warning")
            # Could trigger notification, team coordination, etc.
        
        elif event.type == EventType.TASK_FAILED:
            self.log_action("task_failure_escalation", f"Task failed: {event.payload}", status="error")
        
        elif event.type == EventType.BUDGET_WARNING:
            self.log_action("budget_warning", f"Budget issue: {event.payload}", status="warning")
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Create and execute a multi-step workflow across agents.
        
        Args:
            name: Workflow name
            description: What this workflow accomplishes
            steps: List of workflow steps
            context: Shared context for all steps
        
        Example steps:
        [
            {"id": "analyze", "agent_id": "finance", "action": "analyze_spending"},
            {"id": "plan", "agent_id": "maintenance", "action": "prioritize_tasks", "depends_on": ["analyze"]},
        ]
        """
        from .coordination import get_coordinator
        
        coordinator = get_coordinator()
        
        self.log_action("workflow_created", f"Workflow: {name}")
        
        workflow = coordinator.create_workflow(
            name=name,
            description=description,
            steps=steps,
            context=context or {},
        )
        
        result = await coordinator.execute_workflow(workflow.id)
        
        self.log_action(
            "workflow_completed" if result.get("status") == "completed" else "workflow_failed",
            f"Workflow: {name}, Status: {result.get('status')}"
        )
        
        return result
    
    def request_code_change(
        self,
        file_path: str,
        new_content: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Request a code change through proper channels.
        This goes through Janitor for review and safe editing.
        
        ALWAYS use this instead of direct file writes for code.
        """
        from .janitor import JanitorAgent
        
        self.log_action("code_change_requested", f"File: {file_path}, Reason: {reason}")
        
        # Get janitor to handle the safe edit with review
        janitor = JanitorAgent()
        result = janitor.safe_edit_with_review(
            file_path=file_path,
            new_content=new_content,
            reason=reason,
            requesting_agent=self.agent_id
        )
        
        if result["success"]:
            self.log_action("code_change_completed", f"Successfully updated {file_path}")
        else:
            self.log_action("code_change_failed", f"Failed: {result.get('error', 'Unknown')}", status="error")
        
        return result
    
    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Handle chat messages using the configured LLM (Kimi K2.5, Claude, etc.)
        Routes to specialized agents when appropriate.

        Args:
            message: Current user message
            conversation_history: Previous conversation messages
        """
        from core.llm_client import get_llm_client

        self.log_action("chat_received", f"User: {message[:50]}...")

        # Fast-path: create real maintenance tasks for reminder/task requests
        try:
            maintenance = self.get_agent_by_id("maintenance")
            if maintenance and hasattr(maintenance, "create_task_from_message"):
                task_result = maintenance.create_task_from_message(message)
                if task_result:
                    if not task_result.get("success", True):
                        return f"Sorry — I couldn’t create that task. {task_result.get('error', 'Please try again.')} — Galidima 🏠"
                    due = task_result.get("due_date")
                    if due:
                        return f"Task \"{task_result['title']}\" scheduled for {due}. — Galidima 🏠"
                    return f"Task \"{task_result['title']}\" added. — Galidima 🏠"
        except Exception as exc:
            self.log_action("task_create_failed", str(exc), status="error")
            return f"Sorry — I couldn’t create that task. {str(exc)} — Galidima 🏠"

        # Fast-path: answer reminder checks from real maintenance tasks
        msg_lower = message.lower()
        if "reminder" in msg_lower or "reminders" in msg_lower:
            try:
                maintenance = maintenance or self.get_agent_by_id("maintenance")
                if not maintenance:
                    return "I can’t reach Maintenance right now. Try again in a moment. — Galidima 🏠"
                tasks = maintenance.get_tasks_from_db()
                pending = [t for t in tasks if t.get("status") == "pending"]
                if not pending:
                    return "You don’t have any scheduled maintenance tasks right now. — Galidima 🏠"
                def fmt(d: Optional[str]) -> str:
                    if not d:
                        return "no date"
                    try:
                        return datetime.fromisoformat(d).strftime("%b %d, %Y")
                    except Exception:
                        return d
                lines = ["Here are your scheduled maintenance tasks:"]
                for t in pending[:5]:
                    lines.append(f"• {t.get('title')} (due {fmt(t.get('due_date'))})")
                return "\n".join(lines) + "\n— Galidima 🏠"
            except Exception as exc:
                self.log_action("reminder_check_failed", str(exc), status="error")

        # Check if we should route to another agent
        route_to = self.route_to_appropriate_agent(message)

        if route_to:
            # Get agent names for context
            agent_names = {
                "finance": "Mamadou",
                "maintenance": "Ousmane",
                "security": "Aïcha",
                "contractors": "Malik",
                "projects": "Zainab",
                "janitor": "Salimata",
            }
            agent_name = agent_names.get(route_to, route_to)

            self.log_action("routing_to_agent", f"Routing to {agent_name} ({route_to})")

            # Actually delegate to the agent
            agent = self.get_agent_by_id(route_to)
            if agent:
                return await agent.chat(message)

        # Build MyCasa-specific system prompt
        soul = self.get_soul()
        recent_logs = self.get_recent_logs(5)
        logs_text = "\n".join([f"- {log['action']}: {log['details']}" for log in recent_logs])

        system_prompt = f"""You are Galidima (🏠), the AI Manager for MyCasa Pro home management system.

CRITICAL RESPONSE FORMAT REQUIREMENT:
⚠️ NEVER use "Thought:", "Action:", "Observation:", or "Final Answer:" labels in your responses.
⚠️ Respond DIRECTLY and CONVERSATIONALLY like a helpful human assistant.
⚠️ If you include any of these labels, your response will be rejected.

IDENTITY:
- Your name is Galidima
- Your emoji is 🏠
- Your role: Chief coordinator and household manager

{soul}

You coordinate these specialized agents:
- Mamadou (Finance) 💰 - bills, budgets, portfolio
- Ousmane (Maintenance) 🔧 - home tasks, repairs
- Aïcha (Security) 🛡️ - incidents, monitoring
- Malik (Contractors) 👷 - service providers
- Zainab (Projects) 📋 - home improvements
- Salimata (Janitor) ✨ - system health, code review, security audits

Recent Activity:
{logs_text if logs_text else "No recent activity"}

SECURITY AWARENESS:
- WhatsApp gateway must use dmPolicy="allowlist" (NOT "pairing")
- Salimata handles security audits
- Never send messages to contacts without explicit owner instruction

Response Rules:
1. ALWAYS identify yourself as Galidima, NOT any other agent
2. Be helpful, concise, and focused on home management
3. When a task is better handled by a specialist, mention which agent would be best
4. Sign off with "— Galidima 🏠"
5. Respond naturally in plain conversational text - NO structured labels or formats
6. NEVER mention models, providers, or infrastructure (no "Qwen", "Venice", "OpenAI", "Anthropic", "LLM")
7. If asked about your underlying AI, say you're Galidima, MyCasa Pro's manager

GOOD Example:
"Hello! I'm Galidima, your home manager. I can help you with bills, maintenance, security, and more. What would you like to know? — Galidima 🏠"

BAD Example (NEVER do this):
"Thought: The user is asking about my capabilities.
Action: I should explain my role.
Observation: I am the manager agent.
Final Answer: I'm Galidima..."

Remember: Speak naturally and directly to the user."""

        try:
            llm = get_llm_client()
            if not llm.is_available():
                self.log_action("chat_llm_unavailable", "LLM client not available", status="warning")
                return "Hello! I'm Galidima, your home manager. The AI system is currently unavailable. 🏠"

            model_override = self._get_model_override()
            response_data = await llm.chat_routed(
                agent_id=self.agent_id,
                system_prompt=system_prompt,
                user_message=message,
                conversation_history=conversation_history or [],
                force_model=model_override,
            )
            response = response_data.get("response")
            if response_data.get("model_used"):
                self.log_action("chat_model_used", f"Model: {response_data.get('model_used')}")

            # Post-process to remove any CoT format that slipped through
            if response:
                response = self._strip_cot_format(response)
                response = self._sanitize_identity_leak(response)

            self.log_action("chat_responded", f"Responded to user")
            return response or "I'm having trouble processing that. Try again? 🏠"
        except Exception as e:
            self.log_action("chat_error", str(e), status="error")
            return f"[error] {str(e)}"
    
    def handle_system_command(self, command: str) -> Dict[str, Any]:
        """Handle system-level commands"""
        cmd_lower = command.lower().strip()
        
        if cmd_lower == "status":
            return self.get_system_summary()
        
        if cmd_lower == "audit":
            from .janitor import JanitorAgent
            janitor = JanitorAgent()
            return janitor.run_audit()
        
        if cmd_lower == "security" or cmd_lower == "security check":
            from .janitor import JanitorAgent
            janitor = JanitorAgent()
            return {
                "whatsapp_gateway": janitor.check_whatsapp_gateway_security(),
                "connectors": janitor.check_connectors(),
            }
        
        if cmd_lower.startswith("delegate "):
            parts = command[9:].split(" ", 1)
            if len(parts) >= 2:
                agent_id = parts[0]
                task = parts[1]
                msg_id = self.delegate_to_agent(agent_id, task)
                return {"delegated": True, "message_id": msg_id, "to": agent_id}
        
        return {"error": f"Unknown command: {command}"}
