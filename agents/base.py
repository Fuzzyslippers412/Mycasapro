"""
Base Agent Class for MyCasa Pro
Enhanced with persistent memory, second-brain capabilities, and real-time activity tracking.

Per SECONDBRAIN_INTEGRATION.md spec, agents MUST use SecondBrain for memory operations:
- Finance Agent: spending history, policy notes, portfolio entities
- Maintenance Agent: task notes, vendor entities, maintenance history
- Contractors Agent: contractor entities, work history, payment records
- Manager Agent: cross-domain decision chains, all entity types
- Janitor Agent: telemetry notes, incident notes, audit logs

Per AGENT_ACTIVITY_VISION.md, all agents MUST record their activities for real-time dashboard:
- Files touched (read/modified/created/deleted)
- Tools used (with counts and context)
- Systems accessed (with status)
- Decisions made and open questions
- Context usage metrics
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import os
import json
from pathlib import Path
import sys
import asyncio
import atexit
from functools import wraps

from config.settings import DEFAULT_TENANT_ID

# Fix for asyncio.run() in async contexts - allows nested event loops
import nest_asyncio
nest_asyncio.apply()

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_db
from database.models import AgentLog, Notification

# Import activity tracking
try:
    from api.routes.agent_activity import record_agent_activity
    ACTIVITY_TRACKING_AVAILABLE = True
except ImportError:
    ACTIVITY_TRACKING_AVAILABLE = False
    print("[WARNING] Activity tracking not available")

logging.basicConfig(level=logging.INFO)

AGENTS_MEMORY_DIR = Path(__file__).parent / "memory"


def track_activity(func):
    """Decorator to automatically track agent activities"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, '_track_method_call'):
            # Record method execution
            self._track_method_call(func.__name__, args, kwargs)
        return func(self, *args, **kwargs)
    return wrapper


class BaseAgent(ABC):
    """
    Base class for all MyCasa Pro agents.
    
    Each agent has:
    - SOUL.md: Defines persona, objectives, constraints
    - MEMORY.md: Long-term curated memory
    - context/: Working context files
    """
    
    def __init__(self, name: str, tenant_id: str = DEFAULT_TENANT_ID):
        self.name = name
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(f"mycasa.{name}")
        self.memory_dir = AGENTS_MEMORY_DIR / name
        self._secondbrain = None  # Lazy-loaded
        self._ensure_memory_structure()
        
        # Initialize activity tracking
        self._init_activity_tracking()
        
        # Register cleanup function
        atexit.register(self._cleanup_activity_session)
    
    # ============ SECONDBRAIN INTEGRATION ============
    # Per SECONDBRAIN_INTEGRATION.md - all agent memory operations MUST go through SecondBrain
    
    def _get_secondbrain(self):
        """Lazy-load SecondBrain to avoid circular imports"""
        if self._secondbrain is None:
            try:
                from core.secondbrain import SecondBrain
                from core.secondbrain.models import AgentType
                
                # Convert agent name to AgentType enum if valid
                agent_type = None
                try:
                    agent_type = AgentType(self.name)
                except ValueError:
                    # Agent name not in enum, use default
                    pass
                
                self._secondbrain = SecondBrain(tenant_id=self.tenant_id, agent=agent_type)
            except ImportError:
                self.logger.warning(f"[{self.name}] SecondBrain not available, using fallback")
                return None
        return self._secondbrain

    def _run_async(self, coro):
        """Run async coroutine safely from sync context"""
        try:
            loop = asyncio.get_running_loop()
            # nest_asyncio allows re-entrancy for run_until_complete
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    def write_to_secondbrain(
        self,
        note_type: str,
        title: str,
        body: str,
        folder: Optional[str] = None,
        entities: Optional[List[str]] = None,
        refs: Optional[List[str]] = None,
        confidence: str = "high"
    ) -> Optional[str]:
        """
        Write a note to SecondBrain vault.
        
        Per SECONDBRAIN_INTEGRATION.md spec:
        - Agents NEVER write files directly
        - All writes go through SecondBrain skill
        - Append-only - no silent edits
        
        Args:
            note_type: decision, event, entity, policy, task, message, telemetry
            title: Note title
            body: Note content (markdown)
            folder: Target folder (decisions, memory, entities, etc.)
            entities: Related entity IDs
            refs: Related note IDs
            confidence: high, medium, low
        
        Returns:
            Note ID if successful, None on failure
        """
        sb = self._get_secondbrain()
        if sb is None:
            # Fallback to local memory
            self.append_memory(note_type.title(), f"**{title}**\n{body}")
            return None
        
        try:
            # nest_asyncio allows asyncio.run() even in async contexts
            note_id = self._run_async(
                sb.write_note(
                    type=note_type,
                    title=title,
                    body=body,
                    folder=folder,
                    entities=entities,
                    refs=refs,
                    confidence=confidence
                )
            )
            self.logger.info(f"[{self.name}] Wrote to SecondBrain: {note_id}")
            return note_id
        except Exception as e:
            self.logger.error(f"[{self.name}] SecondBrain write failed: {e}")
            # Fallback to local memory
            self.append_memory(note_type.title(), f"**{title}**\n{body}")
            return None
    
    def search_secondbrain(
        self,
        query: str,
        scope: Optional[List[str]] = None,
        note_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search SecondBrain for relevant notes.
        
        Args:
            query: Search query
            scope: Folders to search (e.g., ["decisions", "memory"])
            note_type: Filter by note type
            limit: Max results
        
        Returns:
            List of matching notes with content
        """
        sb = self._get_secondbrain()
        if sb is None:
            return []
        
        try:
            return self._run_async(
                sb.search(query=query, scope=scope, note_type=note_type, limit=limit)
            )
        except Exception as e:
            self.logger.error(f"[{self.name}] SecondBrain search failed: {e}")
            return []
    
    def record_decision_to_sb(
        self,
        decision: str,
        rationale: str,
        outcome: Optional[str] = None,
        refs: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Record a decision to SecondBrain (not just local MEMORY.md).
        Per spec, decisions MUST go to SecondBrain.
        """
        body = f"## Decision\n{decision}\n\n## Rationale\n{rationale}"
        if outcome:
            body += f"\n\n## Outcome\n{outcome}"
        
        note_id = self.write_to_secondbrain(
            note_type="decision",
            title=decision[:50],  # Truncate for title
            body=body,
            folder="decisions",
            refs=refs
        )
        
        # Also record locally for quick access
        self.record_decision(decision, rationale, outcome)
        
        return note_id
    
    def record_event_to_sb(
        self,
        event: str,
        details: str,
        entities: Optional[List[str]] = None
    ) -> Optional[str]:
        """Record an event to SecondBrain."""
        return self.write_to_secondbrain(
            note_type="event",
            title=event,
            body=details,
            folder="memory",
            entities=entities
        )
    
    def record_telemetry_to_sb(
        self,
        metric_type: str,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """Record telemetry/system data to SecondBrain (for Janitor agent)."""
        body = f"## {metric_type}\n\n```json\n{json.dumps(data, indent=2, default=str)}\n```"
        return self.write_to_secondbrain(
            note_type="telemetry",
            title=f"{metric_type} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            body=body,
            folder="logs"
        )
    
    def _ensure_memory_structure(self):
        """Ensure agent memory directory structure exists"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "context").mkdir(exist_ok=True)
        
        # Create SOUL.md if missing
        soul_path = self.memory_dir / "SOUL.md"
        if not soul_path.exists():
            soul_path.write_text(f"# SOUL.md — {self.name.title()} Agent\n\n<!-- Define persona here -->\n")
            # Track file operation
            self._track_file_operation(soul_path, "created")
        else:
            # Track read operation
            self._track_file_operation(soul_path, "read")
        
        # Create MEMORY.md if missing
        memory_path = self.memory_dir / "MEMORY.md"
        if not memory_path.exists():
            memory_path.write_text(f"# MEMORY.md — {self.name.title()} Agent Long-Term Memory\n\n")
            # Track file operation
            self._track_file_operation(memory_path, "created")
        else:
            # Track read operation
            self._track_file_operation(memory_path, "read")
    
    # ============ MEMORY OPERATIONS ============
    
    def get_soul(self) -> str:
        """Read this agent's SOUL.md (persona definition)"""
        soul_path = self.memory_dir / "SOUL.md"
        if soul_path.exists():
            return soul_path.read_text()
        return ""
    
    def get_memory(self) -> str:
        """Read this agent's long-term memory"""
        memory_path = self.memory_dir / "MEMORY.md"
        if memory_path.exists():
            return memory_path.read_text()
        return ""
    
    def append_memory(self, section: str, content: str, timestamp: bool = True):
        """
        Append content to a section in MEMORY.md.
        Creates section if it't exist.
        """
        memory_path = self.memory_dir / "MEMORY.md"
        memory = memory_path.read_text() if memory_path.exists() else f"# MEMORY.md — {self.name.title()} Agent\n\n"
        
        ts = f"\n_[{datetime.now().isoformat()}]_ " if timestamp else "\n"
        
        # Find section or append at end
        section_header = f"## {section}"
        if section_header in memory:
            # Insert after section header
            idx = memory.find(section_header) + len(section_header)
            # Find next section or end
            next_section = memory.find("\n## ", idx)
            if next_section == -1:
                memory = memory.rstrip() + ts + content + "\n"
            else:
                memory = memory[:next_section] + ts + content + "\n" + memory[next_section:]
        else:
            # Create new section at end
            memory = memory.rstrip() + f"\n\n{section_header}\n{ts}{content}\n"
        
        memory_path.write_text(memory)
        
        # Track file operation
        self._track_file_operation(memory_path, "modified")
        
        self.logger.debug(f"[{self.name}] Memory updated: {section}")
    
    def get_context(self, context_name: str) -> Optional[Dict[str, Any]]:
        """Read a context file from context/"""
        context_path = self.memory_dir / "context" / f"{context_name}.json"
        if context_path.exists():
            # Track file operation
            self._track_file_operation(context_path, "read")
            return json.loads(context_path.read_text())
        return None
    
    def save_context(self, context_name: str, data: Dict[str, Any]):
        """Save a context file to context/"""
        context_path = self.memory_dir / "context" / f"{context_name}.json"
        context_path.write_text(json.dumps(data, indent=2, default=str))
        
        # Track file operation
        self._track_file_operation(context_path, "modified")
        
        self.logger.debug(f"[{self.name}] Context saved: {context_name}")
    
    def record_decision(self, decision: str, rationale: str, outcome: str = None):
        """Record a decision with rationale for learning"""
        entry = f"**Decision:** {decision}\n  - Rationale: {rationale}"
        if outcome:
            entry += f"\n  - Outcome: {outcome}"
        self.append_memory("Historical Decisions", entry)
    
    def record_learning(self, learning: str, source: str = None):
        """Record something learned for future reference"""
        entry = learning
        if source:
            entry += f" _(source: {source})_"
        self.append_memory("Learnings", entry)
    
    # ============ ABSTRACT METHODS ============
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
    
    @abstractmethod
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending tasks for this agent"""
    
    @abstractmethod
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a specific task"""
    
    # ============ CHAT METHOD ============

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Process a chat message and return a response using LLM.

        Enhanced implementation with:
        1. Fleet management for request tracking
        2. Context manager for optimized context building
        3. Request scorer for automatic model routing
        4. Cost and performance tracking

        Subclasses can override for custom behavior.
        """
        import time
        start_time = time.perf_counter()

        # Get fleet manager for request tracking
        from core.fleet_manager import get_fleet_manager
        fleet = get_fleet_manager()

        # Signal request start (fast - in-memory operation)
        can_proceed = await fleet.request_start(self.name)
        if not can_proceed:
            self.logger.warning(f"[{self.name}] Request rejected - agent unavailable or over budget")
            return f"I'm currently unavailable. Please try again later."

        try:
            # Load agent identity (fast - file reads)
            soul = self.get_soul()
            memory = self.get_memory()

            # Get agent system prompt
            from core.agent_prompts import get_agent_prompt, IDENTITY_GUARD
            agent_prompt = get_agent_prompt(self.name)
            system_prompt = agent_prompt
            if soul:
                system_prompt = f"{agent_prompt}\n\n## Identity\n{soul}"
            developer_prompt = IDENTITY_GUARD.strip()

            # Recall relevant context from SecondBrain - with timeout
            # Skip for very short messages to reduce latency
            memories = []
            if len(message) > 20:  # Only fetch context for substantial messages
                sb = self._get_secondbrain()
                if sb:
                    try:
                        # Add 1 second timeout for SecondBrain recall
                        recall = await asyncio.wait_for(
                            sb.recall(message, limit=2),  # Reduced from 3 to 2
                            timeout=1.0
                        )
                        memories = recall.get('general', [])
                    except asyncio.TimeoutError:
                        self.logger.debug(f"[{self.name}] SecondBrain recall timed out, proceeding without context")
                    except Exception as e:
                        self.logger.debug(f"[{self.name}] SecondBrain recall failed: {e}")

            # Skip log_action during chat to reduce DB overhead
            # (We'll log at the end with metrics instead)
            prep_time = (time.perf_counter() - start_time) * 1000
            self.logger.debug(f"[{self.name}] Prep time: {prep_time:.0f}ms")

            # Build request with enforceable context budgets
            history_messages = context.get("history") if context else None
            if not history_messages and conversation_history:
                history_messages = conversation_history
            tool_results = context.get("tool_results") if context else None
            request_id = context.get("request_id") if context else None

            retrieval_items = []
            for item in memories or []:
                snippet = item.get("snippet") or item.get("content") or ""
                if snippet:
                    retrieval_items.append({"id": item.get("id"), "content": snippet})

            from database import get_db
            from core.request_builder import RequestBuilder, BuildInput

            with get_db() as db:
                builder = RequestBuilder(db)
                run_result = await builder.run(
                    agent_name=self.name,
                    build_input=BuildInput(
                        system_prompt=system_prompt,
                        developer_prompt=developer_prompt,
                        memory=memory,
                        history=history_messages or [],
                        retrieval=retrieval_items,
                        tool_results=tool_results or [],
                        user_message=message,
                    ),
                    request_id=request_id,
                    temperature=1.0,
                )

            if run_result["status"] == "blocked":
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                await fleet.request_end(
                    self.name,
                    success=False,
                    response_time_ms=elapsed_ms,
                    error=run_result.get("error") or "Request blocked",
                )
                return (
                    f"⚠️ Request blocked: {run_result.get('error')}. "
                    "Adjust the agent context budgets or shorten the request."
                )

            if run_result["status"] == "error":
                error_message = run_result.get("error") or "LLM error"
                error_lower = error_message.lower()
                base_url = (
                    os.getenv("LLM_BASE_URL")
                    or os.getenv("OPENAI_BASE_URL")
                    or os.getenv("OPENAI_API_BASE")
                    or os.getenv("LMSTUDIO_BASE_URL")
                    or os.getenv("LOCAL_LLM_BASE_URL")
                    or os.getenv("OLLAMA_HOST")
                    or os.getenv("OLLAMA_BASE_URL")
                )
                if "llm not available" in error_lower:
                    user_message = (
                        "LLM is not configured. Go to Settings → General → LLM Provider "
                        "and connect Qwen OAuth or add an API key."
                    )
                elif "unauthorized" in error_lower or "api key" in error_lower or "authentication" in error_lower or "401" in error_lower:
                    user_message = (
                        "LLM authentication failed. Check your Qwen OAuth connection or API key "
                        "in Settings → General → LLM Provider."
                    )
                elif "timeout" in error_lower or "timed out" in error_lower or "connection" in error_lower or "refused" in error_lower:
                    location = base_url or "the configured LLM endpoint"
                    user_message = (
                        f"LLM provider is unreachable at {location}. "
                        "Verify the base URL and network access in Settings → General → LLM Provider."
                    )
                else:
                    user_message = "I apologize, I'm having trouble responding right now."
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                await fleet.request_end(
                    self.name,
                    success=False,
                    response_time_ms=elapsed_ms,
                    error=error_message,
                )
                return f"LLM_ERROR: {user_message}"

            response = run_result["response"] or ""
            routing = run_result.get("routing") or {}
            model_used = run_result.get("model_used") or "unknown"
            llm_time = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"[{self.name}] LLM response time: {llm_time:.0f}ms")

            # Sanitize any identity leaks
            try:
                from core.llm import AGENT_PERSONAS, _sanitize_identity_leak
                persona = AGENT_PERSONAS.get(self.name, {"name": self.name, "role": "agent"})
                response = _sanitize_identity_leak(response, persona)
            except Exception:
                pass

            # Strip chain-of-thought formatting if it slips through
            response = self._strip_cot_format(response)

            # Calculate cost (approximate)
            tier_costs = {
                "simple": 0.0003,
                "medium": 0.003,
                "complex": 0.006,
                "reasoning": 0.015,
            }
            estimated_cost = tier_costs.get(routing.get("tier"), 0.003)

            # Log routing decision
            self.logger.info(
                f"[{self.name}] Routed to {routing['tier']} tier "
                f"(score: {routing['score']:.2f}, model: {model_used})"
            )

            # Signal request end with metrics (do this first, it's fast)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            usage = run_result.get("usage") or {}
            tokens_input = run_result["build"].input_tokens_estimated if run_result.get("build") else 0
            tokens_output = (
                usage.get("output_tokens")
                or usage.get("completion_tokens")
                or len(response.split()) * 2
            )

            await fleet.request_end(
                self.name,
                success=True,
                response_time_ms=elapsed_ms,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=estimated_cost,
                tier=routing.get("tier", "medium"),
            )

            # Log total time
            self.logger.info(f"[{self.name}] Total chat time: {elapsed_ms:.0f}ms")

            # Track activity (simple, non-blocking)
            if ACTIVITY_TRACKING_AVAILABLE:
                try:
                    record_agent_activity(
                        agent_id=self.name,
                        tools={"llm_call": 1},
                        decisions=[f"Routed to {routing['tier']} tier ({model_used})"],
                        context_used=tokens_input,
                    )
                except Exception:
                    pass

            return response

        except Exception as e:
            self.logger.error(f"[{self.name}] LLM error: {e}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            await fleet.request_end(
                self.name,
                success=False,
                response_time_ms=elapsed_ms,
                error=str(e),
            )
            return f"I apologize, I'm having trouble responding right now. Error: {str(e)}"

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

        cot_patterns = [
            r'^\s*(?:\*\*|__)?\s*Thought\s*(?:\*\*|__)?\s*:?.*$',
            r'^\s*(?:\*\*|__)?\s*Action\s*(?:\*\*|__)?\s*:?.*$',
            r'^\s*(?:\*\*|__)?\s*Observation\s*(?:\*\*|__)?\s*:?.*$',
            r'^\s*(?:\*\*|__)?\s*Final Answer\s*(?:\*\*|__)?\s*:?.*$',
        ]

        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            skip = False
            for pattern in cot_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    skip = True
                    break
            if not skip:
                cleaned_lines.append(line)

        cleaned = '\n'.join(cleaned_lines).strip()
        return cleaned if cleaned else text
    
    # ============ LOGGING & NOTIFICATIONS ============
    
    def log_action(self, action: str, details: str = None, status: str = "success"):
        """Log an agent action to the database"""
        with get_db() as db:
            log = AgentLog(
                agent=self.name,
                action=action,
                details=details,
                status=status
            )
            db.add(log)
        self.logger.info(f"[{self.name}] {action}: {status}")
    
    def create_notification(
        self,
        title: str,
        message: str,
        category: str = None,
        priority: str = "medium",
        action_url: str = None,
        action_label: str = None
    ):
        """Create a system notification"""
        with get_db() as db:
            notification = Notification(
                title=title,
                message=message,
                category=category or self.name,
                priority=priority,
                action_url=action_url,
                action_label=action_label
            )
            db.add(notification)
        self.logger.info(f"[{self.name}] Notification: {title}")
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs for this agent"""
        with get_db() as db:
            logs = db.query(AgentLog).filter(
                AgentLog.agent == self.name
            ).order_by(AgentLog.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "action": log.action,
                    "details": log.details,
                    "status": log.status,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
    
    # ============ INTER-AGENT COMMUNICATION ============
    
    def send_to_manager(self, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to the manager agent.
        Returns acknowledgment or response.
        """
        # Save to outbox for manager to process
        outbox = self.get_context("outbox") or {"messages": []}
        outbox["messages"].append({
            "timestamp": datetime.now().isoformat(),
            "from": self.name,
            "type": message_type,
            "payload": payload,
            "processed": False
        })
        self.save_context("outbox", outbox)
        
        return {"status": "queued", "message_type": message_type}
    
    def report_event(self, event_type: str, data: Dict[str, Any], severity: str = "info"):
        """Report an event to the manager for cross-domain awareness"""
        return self.send_to_manager("event", {
            "event_type": event_type,
            "severity": severity,
            "data": data
        })
    
    def request_approval(self, action: str, details: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Request approval from user via manager"""
        return self.send_to_manager("approval_request", {
            "action": action,
            "details": details,
            "reason": reason,
            "requested_at": datetime.now().isoformat()
        })
    
    def propose_insight(self, insight: str, confidence: str, supporting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Propose an insight for manager to evaluate and potentially surface"""
        return self.send_to_manager("insight", {
            "insight": insight,
            "confidence": confidence,
            "supporting_data": supporting_data
        })
    
    # ============ COORDINATION LAYER (Soccer Team Architecture) ============
    
    def _get_coordinator(self):
        """Lazy import coordinator to avoid circular imports"""
        from core.coordinator import get_coordinator
        return get_coordinator()
    
    def register_with_coordinator(self, handoff_handler=None, approval_handler=None):
        """
        Register this agent with the coordination layer.
        Call this during agent initialization if the agent needs to
        handle incoming handoffs or approval requests.
        """
        from core.coordinator import register_agent
        register_agent(
            self.name,
            handoff_handler=handoff_handler or self._default_handoff_handler,
            approval_handler=approval_handler or self._default_approval_handler
        )
        self.logger.info(f"[{self.name}] Registered with coordinator")
    
    def _default_handoff_handler(self, handoff) -> Dict[str, Any]:
        """Default handler for incoming task handoffs"""
        self.logger.info(f"[{self.name}] Received handoff: {handoff.task_type}")
        # Subclasses should override this
        return {"accepted": True, "message": "Task accepted by default handler"}
    
    def _default_approval_handler(self, request) -> Dict[str, Any]:
        """Default handler for approval requests (if this agent is an approver)"""
        self.logger.info(f"[{self.name}] Received approval request: {request.approval_type}")
        # By default, deny - subclasses should implement proper logic
        return {"approved": False, "reason": "No approval handler configured"}
    
    def handoff_to(self, target_agent: str, task_type: str, 
                   task_data: Dict[str, Any], 
                   priority: str = "medium",
                   wait_for_response: bool = True) -> Dict[str, Any]:
        """
        Hand off a task to another agent.
        
        Args:
            target_agent: Agent to hand off to (e.g., "contractors", "finance")
            task_type: Type of task (e.g., "repair_request", "cost_check")
            task_data: Task details
            priority: low, medium, high, urgent
            wait_for_response: Whether to block waiting for acceptance
        
        Returns:
            Handoff result with status
        """
        from core.coordinator import handoff_task
        
        result = handoff_task(
            from_agent=self.name,
            to_agent=target_agent,
            task_type=task_type,
            task_data=task_data,
            priority=priority,
            wait_for_response=wait_for_response
        )
        
        self.log_action(
            f"handoff_to_{target_agent}",
            f"Task: {task_type}, Status: {result.status}",
            status="success" if result.status == "accepted" else "pending"
        )
        
        return result.to_dict()
    
    def request_cost_approval(self, amount_usd: float, 
                              description: str,
                              details: Dict[str, Any] = None,
                              wait_for_response: bool = True) -> Dict[str, Any]:
        """
        Request cost approval from Finance agent.
        
        Args:
            amount_usd: Cost amount
            description: Human-readable description
            details: Additional details
            wait_for_response: Whether to wait for approval
        
        Returns:
            Approval result with status (approved/denied/timeout)
        """
        from core.coordinator import request_approval
        
        result = request_approval(
            requester_agent=self.name,
            approval_type="cost",
            amount_usd=amount_usd,
            description=description,
            details=details or {},
            wait_for_response=wait_for_response
        )
        
        self.log_action(
            "cost_approval_request",
            f"${amount_usd:.2f} - {description}, Status: {result.status}",
            status="success" if result.status == "approved" else result.status
        )
        
        return result.to_dict()
    
    def request_action_approval(self, action: str,
                                description: str,
                                details: Dict[str, Any] = None,
                                wait_for_response: bool = True) -> Dict[str, Any]:
        """
        Request approval for an action from Manager.
        
        Args:
            action: Action type being requested
            description: Human-readable description
            details: Additional details
            wait_for_response: Whether to wait for approval
        
        Returns:
            Approval result
        """
        from core.coordinator import request_approval
        
        result = request_approval(
            requester_agent=self.name,
            approval_type="action",
            description=description,
            details={"action": action, **(details or {})},
            wait_for_response=wait_for_response
        )
        
        return result.to_dict()
    
    def escalate_to_manager(self, issue: str, 
                           priority: str = "high",
                           details: Dict[str, Any] = None) -> None:
        """
        Escalate an issue to the Manager agent.
        
        Args:
            issue: Description of the issue
            priority: low, medium, high, urgent
            details: Additional context
        """
        from core.coordinator import escalate_to_manager as coord_escalate
        coord_escalate(self.name, issue, priority=priority, details=details)
        
        self.log_action(
            "escalate_to_manager",
            f"[{priority.upper()}] {issue}",
            status="escalated"
        )
    
    def escalate_to_user(self, message: str,
                        requires_response: bool = False,
                        options: List[str] = None) -> None:
        """
        Escalate directly to user (via Manager).
        Use for urgent matters requiring human attention.
        
        Args:
            message: Message for the user
            requires_response: Whether user needs to respond
            options: Response options if applicable
        """
        from core.coordinator import escalate_to_user as coord_escalate
        coord_escalate(
            self.name, 
            message, 
            requires_response=requires_response, 
            options=options
        )
        
        self.log_action(
            "escalate_to_user",
            message,
            status="escalated"
        )
    
    def send_heartbeat(self, current_task: str = None,
                      queue_depth: int = 0,
                      metrics: Dict[str, Any] = None) -> None:
        """
        Send heartbeat to coordinator.
        Call this periodically to indicate agent is alive.
        
        Args:
            current_task: Currently executing task if any
            queue_depth: Number of pending tasks
            metrics: Additional metrics to report
        """
        from core.coordinator import heartbeat
        from core.events import AgentState
        
        state = AgentState.RUNNING if current_task else AgentState.IDLE
        heartbeat(
            self.name,
            state=state,
            current_task=current_task,
            queue_depth=queue_depth,
            metrics=metrics
        )
    
    def broadcast_status(self, status: Dict[str, Any]) -> None:
        """
        Broadcast status update to interested agents.
        
        Args:
            status: Status data to broadcast
        """
        coordinator = self._get_coordinator()
        coordinator.broadcast_status(self.name, status)
    
    def can_communicate_with(self, target_agent: str) -> bool:
        """Check if this agent can initiate communication with target"""
        coordinator = self._get_coordinator()
        return coordinator.can_communicate(self.name, target_agent)
    
    def get_pending_handoffs_to_me(self) -> List[Dict[str, Any]]:
        """Get pending task handoffs waiting for this agent"""
        coordinator = self._get_coordinator()
        handoffs = coordinator.get_pending_handoffs(self.name)
        return [h.to_dict() for h in handoffs]
    
    def get_pending_approvals_for_me(self) -> List[Dict[str, Any]]:
        """Get pending approval requests for this agent (if approver)"""
        coordinator = self._get_coordinator()
        approvals = coordinator.get_pending_approvals(self.name)
        return [a.to_dict() for a in approvals]

    # ============ ACTIVITY TRACKING METHODS ============
    # Per AGENT_ACTIVITY_VISION.md - all agents must record activities for real-time dashboard
    
    def _init_activity_tracking(self):
        """Initialize activity tracking for this agent session"""
        self._session_id = f"{self.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self._activity_stats = {
            'files_touched': [],
            'tools_used': {},
            'systems_accessed': [],
            'decisions_made': [],
            'open_questions': [],
            'context_used': 0,
            'start_time': datetime.now()
        }
        
        # Record initial session start
        if ACTIVITY_TRACKING_AVAILABLE:
            try:
                record_agent_activity(
                    agent_id=self.name,
                    files=[],
                    tools={'startup': 1},
                    systems=[{'system': 'core', 'status': 'ok'}],
                    decisions=[f"Started {self.name} agent session"],
                    context_used=0
                )
                self.logger.info(f"[{self.name}] Activity tracking initialized")
            except Exception as e:
                self.logger.warning(f"[{self.name}] Could not initialize activity tracking: {e}")

    def _safe_activity(self, fn, *args, **kwargs):
        """Safely execute activity tracking (avoid attribute errors)"""
        try:
            if not hasattr(self, '_activity_stats'):
                self._init_activity_tracking()
            return fn(*args, **kwargs)
        except Exception as e:
            self.logger.warning(f"[{self.name}] Activity tracking failed: {e}")

    def _track_file_operation(self, filepath: str, operation: str):
        """Track file operations (read, write, modify, etc.)"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        def _do():
            file_info = {
                "path": str(filepath),
                "action": operation
            }
            self._activity_stats['files_touched'].append(file_info)
            
            record_agent_activity(
                agent_id=self.name,
                files=[file_info],
                tools={operation: 1},
                context_used=self._activity_stats['context_used']
            )
            self.logger.debug(f"[{self.name}] Tracked file operation: {operation} {filepath}")
        
        self._safe_activity(_do)

    def _track_tool_use(self, tool_name: str, count: int = 1, details: Optional[Dict] = None):
        """Track tool usage with counts"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        def _do():
            self._activity_stats['tools_used'][tool_name] = self._activity_stats['tools_used'].get(tool_name, 0) + count
            
            tool_data = {tool_name: count}
            systems_accessed = []
            if details and 'system' in details:
                systems_accessed = [{'system': details['system'], 'status': details.get('status', 'ok')}]
            
            record_agent_activity(
                agent_id=self.name,
                tools=tool_data,
                systems=systems_accessed,
                context_used=self._activity_stats['context_used']
            )
            self.logger.debug(f"[{self.name}] Tracked tool use: {tool_name} x{count}")
        
        self._safe_activity(_do)

    def _track_decision(self, decision: str, rationale: str = "", outcome: Optional[str] = None):
        """Track decisions made by the agent"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        def _do():
            decision_text = decision
            if rationale:
                decision_text = f"{decision} (Rationale: {rationale})"
            if outcome:
                decision_text = f"{decision_text} (Outcome: {outcome})"
                
            self._activity_stats['decisions_made'].append(decision_text)
            
            record_agent_activity(
                agent_id=self.name,
                decisions=[decision_text],
                context_used=self._activity_stats['context_used']
            )
            self.logger.debug(f"[{self.name}] Tracked decision: {decision[:50]}...")
        
        self._safe_activity(_do)

    def _track_system_access(self, system_name: str, status: str = "ok", details: Optional[Dict] = None):
        """Track external system access"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        def _do():
            system_info = {
                "system": system_name,
                "status": status
            }
            if details:
                system_info.update(details)
                
            self._activity_stats['systems_accessed'].append(system_info)
            
            record_agent_activity(
                agent_id=self.name,
                systems=[system_info],
                context_used=self._activity_stats['context_used']
            )
            self.logger.debug(f"[{self.name}] Tracked system access: {system_name} ({status})")
        
        self._safe_activity(_do)

    def _track_question(self, question: str, status: str = "open"):
        """Track questions or issues raised by the agent"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        def _do():
            question_text = f"[{status.upper()}] {question}"
            self._activity_stats['open_questions'].append(question_text)
            
            record_agent_activity(
                agent_id=self.name,
                questions=[question_text],
                context_used=self._activity_stats['context_used']
            )
            self.logger.debug(f"[{self.name}] Tracked question: {question[:50]}...")
        
        self._safe_activity(_do)

    def _track_method_call(self, method_name: str, args: tuple, kwargs: dict):
        """Track method calls for activity monitoring"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
        
        self._safe_activity(lambda: self._track_tool_use(method_name, 1, {'type': 'internal_method'}))

    def update_context_usage(self, tokens_used: int):
        """Update context/token usage for this agent"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        def _do():
            self._activity_stats['context_used'] = tokens_used
            
            record_agent_activity(
                agent_id=self.name,
                context_used=tokens_used
            )
            self.logger.debug(f"[{self.name}] Updated context usage: {tokens_used} tokens")
        
        self._safe_activity(_do)

    def get_activity_summary(self) -> Dict[str, Any]:
        """Get current activity summary for this agent"""
        elapsed = (datetime.now() - self._activity_stats['start_time']).total_seconds() / 60  # minutes
        velocity = self._activity_stats['context_used'] / elapsed if elapsed > 0 else 0
        
        return {
            'agent_id': self.name,
            'session_id': self._session_id,
            'elapsed_minutes': elapsed,
            'velocity_tokens_per_min': velocity,
            'stats': self._activity_stats.copy()
        }

    def _cleanup_activity_session(self):
        """Cleanup function called on agent shutdown"""
        if not ACTIVITY_TRACKING_AVAILABLE:
            return
            
        try:
            record_agent_activity(
                agent_id=self.name,
                tools={'shutdown': 1},
                decisions=[f"Shutting down {self.name} agent session"],
                context_used=self._activity_stats['context_used']
            )
            self.logger.info(f"[{self.name}] Activity session cleaned up")
        except Exception as e:
            self.logger.warning(f"[{self.name}] Could not cleanup activity session: {e}")
