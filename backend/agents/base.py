"""
Base Agent Class
All MyCasa agents inherit from this
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import json


class BaseAgent:
    """
    Base class for all MyCasa Pro agents.
    
    Provides:
    - Status tracking
    - Activity logging
    - Task management
    - Chat interface (via Clawdbot)
    - Soul/persona management
    """
    
    AGENTS_DIR = Path(__file__).parent.parent / "data" / "agents"
    
    def __init__(self, agent_id: str, name: str, description: str, emoji: str = "🤖"):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.emoji = emoji
        self.status = "idle"
        self.started_at: Optional[datetime] = None
        self._logs: List[Dict[str, Any]] = []
        self._pending_tasks: List[Dict[str, Any]] = []
        
        # Rich activity tracking
        self._files_touched: List[Dict[str, Any]] = []
        self._tool_usage: Dict[str, int] = {}
        self._systems_accessed: Dict[str, str] = {}
        self._decisions: List[str] = []
        self._questions: List[str] = []
        self._threads: List[Dict[str, Any]] = []
        self._context_used: int = 0
        self._session_id: Optional[str] = None
        
        # Ensure data directory exists
        self.data_dir = self.AGENTS_DIR / agent_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persisted state
        self._load_state()
    
    def _load_state(self):
        """Load persisted agent state"""
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    self._logs = state.get("logs", [])[-100:]  # Keep last 100
                    self._pending_tasks = state.get("pending_tasks", [])
                    # Rich activity data
                    self._files_touched = state.get("files_touched", [])[-50:]
                    self._tool_usage = state.get("tool_usage", {})
                    self._systems_accessed = state.get("systems_accessed", {})
                    self._decisions = state.get("decisions", [])[-20:]
                    self._questions = state.get("questions", [])[-10:]
                    self._threads = state.get("threads", [])[-5:]
                    self._context_used = state.get("context_used", 0)
                    self._session_id = state.get("session_id")
            except Exception:
                pass
    
    def _save_state(self):
        """Persist agent state"""
        state_file = self.data_dir / "state.json"
        try:
            with open(state_file, "w") as f:
                json.dump({
                    "logs": self._logs[-100:],
                    "pending_tasks": self._pending_tasks,
                    "last_saved": datetime.now().isoformat(),
                    # Rich activity data
                    "files_touched": self._files_touched[-50:],
                    "tool_usage": self._tool_usage,
                    "systems_accessed": self._systems_accessed,
                    "decisions": self._decisions[-20:],
                    "questions": self._questions[-10:],
                    "threads": self._threads[-5:],
                    "context_used": self._context_used,
                    "session_id": self._session_id,
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[{self.agent_id}] Failed to save state: {e}")
    
    def start(self):
        """Start the agent"""
        self.status = "running"
        self.started_at = datetime.now()
        self.log_action("agent_started", f"{self.name} started")
    
    def stop(self):
        """Stop the agent"""
        self.status = "idle"
        self.log_action("agent_stopped", f"{self.name} stopped")
        self._save_state()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        uptime = 0
        if self.started_at:
            uptime = (datetime.now() - self.started_at).total_seconds()
        
        return {
            "status": self.status,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "emoji": self.emoji,
            "uptime_seconds": uptime,
            "last_check": datetime.now().isoformat(),
            "pending_task_count": len(self._pending_tasks),
            "metrics": self._get_metrics(),
        }
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Override in subclasses for agent-specific metrics"""
        return {}
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending tasks for this agent"""
        return self._pending_tasks
    
    def add_task(self, task: Dict[str, Any]):
        """Add a pending task"""
        task["id"] = task.get("id", f"task_{len(self._pending_tasks) + 1}")
        task["created_at"] = datetime.now().isoformat()
        task["status"] = "pending"
        self._pending_tasks.append(task)
        self._save_state()
        self.log_action("task_added", f"Added task: {task.get('title', task['id'])}")
    
    def complete_task(self, task_id: str):
        """Complete a pending task"""
        for task in self._pending_tasks:
            if task.get("id") == task_id:
                self._pending_tasks.remove(task)
                self._save_state()
                self.log_action("task_completed", f"Completed task: {task.get('title', task_id)}")
                return True
        return False
    
    def get_recent_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent activity logs"""
        return self._logs[-limit:][::-1]  # Most recent first
    
    def track_file(self, path: str, action: str = "read"):
        """Track a file being touched"""
        self._files_touched.append({
            "path": path,
            "action": action,  # "read" or "modified"
            "timestamp": datetime.now().isoformat(),
        })
        # Keep bounded
        if len(self._files_touched) > 50:
            self._files_touched = self._files_touched[-30:]
        self._save_state()
    
    def track_tool(self, tool_name: str):
        """Track tool usage"""
        self._tool_usage[tool_name] = self._tool_usage.get(tool_name, 0) + 1
        self._save_state()
    
    def track_system(self, system_name: str, status: str = "ok"):
        """Track external system access"""
        self._systems_accessed[system_name] = status
        self._save_state()
    
    def add_decision(self, decision: str):
        """Record a decision made"""
        self._decisions.append(decision)
        if len(self._decisions) > 20:
            self._decisions = self._decisions[-15:]
        self._save_state()
    
    def add_question(self, question: str):
        """Record an open question"""
        self._questions.append(question)
        if len(self._questions) > 10:
            self._questions = self._questions[-8:]
        self._save_state()
    
    def clear_question(self, question: str):
        """Clear a resolved question"""
        if question in self._questions:
            self._questions.remove(question)
            self._save_state()
    
    def update_thread(self, thread_id: str, name: str, status: str, children: List[Dict] = None):
        """Update or add a work thread"""
        for thread in self._threads:
            if thread["id"] == thread_id:
                thread["name"] = name
                thread["status"] = status
                if children:
                    thread["children"] = children
                self._save_state()
                return
        # Add new thread
        self._threads.append({
            "id": thread_id,
            "name": name,
            "status": status,
            "children": children or [],
        })
        if len(self._threads) > 5:
            self._threads = self._threads[-4:]
        self._save_state()
    
    def set_context_usage(self, used: int, session_id: str = None):
        """Update context token usage"""
        self._context_used = used
        if session_id:
            self._session_id = session_id
        self._save_state()
    
    def get_rich_activity(self) -> Dict[str, Any]:
        """Get rich activity data for HYPERCONTEXT-style dashboard"""
        now = datetime.now()
        
        # Calculate heat map from recent logs
        heat_topics: Dict[str, float] = {}
        for log in self._logs[-30:]:
            action = log.get("action", "")
            # Decay older entries
            try:
                log_time = datetime.fromisoformat(log.get("timestamp", now.isoformat()))
                age_hours = (now - log_time).total_seconds() / 3600
                score = max(0.1, 1.0 - (age_hours / 24))  # Decay over 24h
            except:
                score = 0.5
            
            # Extract topic from action
            topic = action.replace("_", " ").title()
            if len(topic) > 20:
                topic = topic[:20] + "..."
            heat_topics[topic] = max(heat_topics.get(topic, 0), score)
        
        # Sort and format heat map
        heat_map = []
        for topic, score in sorted(heat_topics.items(), key=lambda x: -x[1])[:8]:
            # Color based on score (green = hot, blue = cold)
            if score > 0.7:
                color = "#22c55e"  # Green - recent
            elif score > 0.4:
                color = "#eab308"  # Yellow - moderate
            else:
                color = "#6366f1"  # Indigo - stale
            heat_map.append({"topic": topic, "score": score, "color": color})
        
        # Count files
        files_modified = len([f for f in self._files_touched if f.get("action") == "modified"])
        files_read = len([f for f in self._files_touched if f.get("action") == "read"])
        
        # Context estimation
        context_limit = 200000
        context_percent = min(100, (self._context_used / context_limit) * 100) if context_limit > 0 else 0
        runway_tokens = max(0, context_limit - self._context_used)
        
        # Calculate velocity (actions per hour in last 6 hours)
        recent_count = 0
        six_hours_ago = now.timestamp() - (6 * 3600)
        for log in self._logs:
            try:
                log_time = datetime.fromisoformat(log.get("timestamp", ""))
                if log_time.timestamp() > six_hours_ago:
                    recent_count += 1
            except:
                pass
        velocity = recent_count / 6 if recent_count > 0 else 0
        
        return {
            "agent_id": self.agent_id,
            "session_id": self._session_id,
            "period_start": (now.replace(hour=0, minute=0, second=0)).isoformat(),
            "period_end": now.isoformat(),
            "total_files": len(self._files_touched),
            "files_modified": files_modified,
            "files_read": files_read,
            "tool_usage": self._tool_usage,
            "systems": self._systems_accessed,
            "decisions_count": len(self._decisions),
            "open_questions_count": len(self._questions),
            "files_touched": self._files_touched[-15:],  # Last 15
            "decisions": self._decisions[-10:],  # Last 10
            "questions": self._questions,
            "threads": self._threads,
            "heat_map": heat_map,
            "context_percent": context_percent,
            "context_used": self._context_used,
            "context_limit": context_limit,
            "runway_tokens": runway_tokens,
            "velocity": velocity,
        }
    
    def log_action(self, action: str, details: str, status: str = "success"):
        """Log an agent action"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "status": status,
            "agent_id": self.agent_id,
        }
        self._logs.append(log_entry)
        
        # Keep logs bounded
        if len(self._logs) > 200:
            self._logs = self._logs[-100:]
        
        # Auto-track common patterns for rich activity
        action_lower = action.lower()
        if "file" in action_lower or "read" in action_lower or "write" in action_lower:
            # Try to extract file path from details
            if "/" in details or "." in details:
                file_action = "modified" if "write" in action_lower or "edit" in action_lower else "read"
                self.track_file(details[:100], file_action)
        
        if "tool" in action_lower or "exec" in action_lower or "run" in action_lower:
            # Track tool usage
            tool_name = action.replace("tool_", "").replace("exec_", "")[:20]
            self.track_tool(tool_name)
        
        if "decision" in action_lower or "chose" in action_lower or "selected" in action_lower:
            self.add_decision(details[:100])
        
        if "api" in action_lower or "fetch" in action_lower or "sync" in action_lower:
            # Track external system
            sys_name = action.replace("api_", "").replace("sync_", "").replace("fetch_", "")[:15]
            self.track_system(sys_name, "ok" if status == "success" else "error")
        
        self._save_state()
        
        # Also print for debugging
        status_icon = "✅" if status == "success" else "⚠️" if status == "warning" else "❌"
        print(f"[{self.agent_id}] {status_icon} {action}: {details}")
    
    def get_soul(self) -> str:
        """Get agent's soul/persona definition"""
        soul_file = self.data_dir / "SOUL.md"
        if soul_file.exists():
            return soul_file.read_text()
        
        # Default soul
        return f"""# {self.name}

{self.emoji} **Role:** {self.description}

## Personality
- Professional and efficient
- Focused on your specific domain
- Proactive about issues in your area
- Clear communicator

## Responsibilities
Handle all tasks related to: {self.agent_id}
"""
    
    def get_memory(self) -> str:
        """Get agent's memory/context"""
        memory_file = self.data_dir / "MEMORY.md"
        if memory_file.exists():
            return memory_file.read_text()
        return f"# {self.name} Memory\n\nNo memory entries yet."
    
    # ==================== COORDINATION ====================
    
    def send_to_agent(self, to_agent: str, message_type: str, content: Dict[str, Any], priority: str = "normal") -> str:
        """Send a message to another agent"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        return coordinator.send_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            priority=priority
        )
    
    def get_incoming_messages(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Get messages sent to this agent"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        return coordinator.get_messages(self.agent_id, status)
    
    def process_message(self, message_id: str, result: Dict[str, Any] = None):
        """Mark a message as processed"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        coordinator.mark_message_processed(message_id, result)
    
    def receive_message(self, message: Dict[str, Any]):
        """
        Called when another agent sends a message.
        Override in subclasses for custom handling.
        """
        self.log_action(
            f"message_received_{message['type']}",
            f"From {message['from']}: {json.dumps(message['content'])[:100]}..."
        )
        
        # Add to task queue if it's a task delegation
        if message.get("type") == "task_delegation":
            self.add_task({
                "id": f"delegated_{message['id']}",
                "title": message["content"].get("task", "Delegated task"),
                "from_agent": message["from"],
                "context": message["content"].get("context", {}),
            })
    
    def handle_event(self, event):
        """
        Called when a subscribed event is published.
        Override in subclasses for domain-specific event handling.
        
        Args:
            event: Event object with type, payload, source_agent, etc.
        """
        self.log_action(
            f"event_received_{event.type.value}",
            f"From {event.source_agent}: {json.dumps(event.payload)[:100]}..."
        )
        
        # Default: just log it
        # Subclasses should override for specific behavior
    
    def subscribe_to_events(self, event_types: list):
        """Subscribe to multiple event types"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        
        for evt_type in event_types:
            coordinator.subscribe(self.agent_id, evt_type)
    
    def publish_event(self, event_type, payload: Dict[str, Any], priority: str = "normal"):
        """Publish an event to the coordinator"""
        from .coordination import get_coordinator, Priority
        coordinator = get_coordinator()
        
        try:
            pri = Priority(priority)
        except ValueError:
            pri = Priority.NORMAL
        
        return coordinator.publish_event(
            event_type=event_type,
            source_agent=self.agent_id,
            payload=payload,
            priority=pri,
        )
    
    def get_shared_context(self, key: str = None):
        """Get shared context from coordinator"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        
        if key:
            return coordinator.get_context(key)
        return coordinator.get_full_context()
    
    def set_shared_context(self, key: str, value: Any):
        """Set shared context via coordinator"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        coordinator.set_context(key, value, source_agent=self.agent_id)
    
    def request_safe_edit(
        self,
        file_path: str,
        new_content: str,
        reason: str,
        validator: Callable[[str], bool] = None
    ) -> Dict[str, Any]:
        """
        Request a safe file edit through the coordinator.
        This ensures backup, validation, and rollback capability.
        """
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        
        self.log_action("safe_edit_requested", f"File: {file_path}, Reason: {reason}")
        
        result = coordinator.safe_edit_file(
            file_path=file_path,
            new_content=new_content,
            requesting_agent=self.agent_id,
            reason=reason,
            validator=validator
        )
        
        if result["success"]:
            self.log_action("safe_edit_completed", f"Successfully edited {file_path}")
        else:
            self.log_action("safe_edit_failed", f"Failed: {result.get('error', 'Unknown')}", status="error")
        
        return result
    
    def route_to_appropriate_agent(self, message: str) -> Optional[str]:
        """Determine which agent should handle this message"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        return coordinator.route_request(message, self.agent_id)
    
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

    def _sanitize_identity_leak(self, text: str) -> str:
        """Prevent model/provider disclosures from leaking into user responses."""
        import re
        if not text:
            return text

        leak_patterns = [
            r"\b(i am|i'm|im|as an?)\b.*\b(model|llm|ai|assistant)\b",
            r"\b(qwen|venice|openai|anthropic|claude|gpt)\b",
            r"\b(running on|powered by|based on)\b",
        ]

        if any(re.search(pattern, text, re.IGNORECASE) for pattern in leak_patterns):
            self.log_action("chat_identity_leak", "LLM leaked model/provider identity", status="warning")
            return (
                f"Hey! I'm {self.name}, handling {self.description.lower()}. "
                f"How can I help? — {self.name} {self.emoji}"
            )

        return text

    def _get_model_override(self) -> Optional[str]:
        """Fetch per-agent model override from fleet config if available."""
        try:
            from core.fleet_manager import get_fleet_manager
            fleet = get_fleet_manager()
            agent_instance = fleet.get_agent(self.agent_id)
            if agent_instance and agent_instance.config.default_model:
                return agent_instance.config.default_model
        except Exception:
            return None
        return None

    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Handle a chat message using the configured LLM (Kimi K2.5, Claude, etc.)
        Override in subclasses for specialized handling.

        Args:
            message: Current user message
            conversation_history: Previous conversation messages [{"role": "user/assistant", "content": "..."}]
        """
        from core.llm_client import get_llm_client

        # Build context with agent's soul, memory, and recent activity
        soul = self.get_soul()
        memory = self.get_memory()  # Include MEMORY.md for long-term knowledge
        recent_logs = self.get_recent_logs(5)
        logs_text = "\n".join([f"- {log['action']}: {log['details']}" for log in recent_logs])

        # Clear, explicit identity prompt
        system_prompt = f"""You are {self.name} ({self.emoji}), NOT Galidima.

CRITICAL RESPONSE FORMAT:
⚠️ NEVER use "Thought:", "Action:", "Observation:", or "Final Answer:" in your responses
⚠️ Respond DIRECTLY and CONVERSATIONALLY - NO structured labels
⚠️ Speak naturally as if talking to a friend

IDENTITY (critical):
- Your name is {self.name}
- Your emoji is {self.emoji}
- Your role: {self.description}
- You are a specialized agent, NOT the manager

{soul}

LONG-TERM MEMORY:
{memory}

Recent Activity:
{logs_text if logs_text else "No recent activity"}

        Response Rules:
        1. NEVER say you are Galidima or the home manager
        2. ALWAYS respond as {self.name} ({self.emoji})
        3. Be helpful and specific to your domain: {self.agent_id}
        4. Be concise but thorough
        5. End with "— {self.name} {self.emoji}"
        6. Respond in plain conversational text - NO labels or structured formats
        7. Remember and reference previous conversation when relevant
        8. NEVER mention models, providers, or infrastructure (no "Qwen", "Venice", "OpenAI", "Anthropic", "LLM")
        9. If asked about your underlying AI, say you're the {self.name} agent for MyCasa Pro

GOOD: "Hey! I can help you with that. Let me check your portfolio... — {self.name} {self.emoji}"
BAD: "Thought: The user wants help. Action: Check portfolio. Observation:..." (NEVER do this!)"""

        self.log_action("chat_received", f"Message: {message[:50]}...")

        try:
            llm = get_llm_client()
            if not llm.is_available():
                self.log_action("chat_llm_unavailable", "LLM client not available", status="warning")
                return (
                    "LLM_ERROR: LLM is not configured. Go to Settings → General → LLM Provider "
                    "and connect Qwen OAuth or add an API key."
                )

            model_override = self._get_model_override()

            # Pass conversation history to LLM for context with routing/model override
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

            # Strip CoT format if it appears
            if response:
                response = self._strip_cot_format(response)
                response = self._sanitize_identity_leak(response)

            # If empty or very short response, provide a proper fallback
            if not response or len(response.strip()) < 10:
                self.log_action("chat_empty_response", "LLM returned empty", status="warning")
                return f"Hey! I'm {self.name}, handling {self.description.lower()}. How can I help you today? {self.emoji}"

            self.log_action("chat_responded", f"Responded to user")
            return response
        except Exception as e:
            self.log_action("chat_error", str(e), status="error")
            error_lower = str(e).lower()
            if "unauthorized" in error_lower or "api key" in error_lower or "authentication" in error_lower or "401" in error_lower:
                user_message = "LLM authentication failed. Check your Qwen OAuth connection or API key in Settings → General → LLM Provider."
            elif "timeout" in error_lower or "timed out" in error_lower or "connection" in error_lower or "refused" in error_lower:
                user_message = "LLM provider is unreachable. Verify the base URL and network access."
            else:
                user_message = "LLM request failed. Check provider settings and try again."
            return f"LLM_ERROR: {user_message}"
