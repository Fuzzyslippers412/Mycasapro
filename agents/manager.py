"""
Manager Agent for MyCasa Pro
The supervisory control agent that orchestrates all sub-agents.

ROLE: Single user-facing coordinator. All other agents report here.
Maintains global context, enforces policy, provides accurate system-level view.

PRIMARY PROMISE: User can always ask "What's going on?" and receive
a complete, truthful, auditable system report.
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import subprocess
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent
from database import get_db
from database.models import Notification, AgentLog, ScheduledJob
from agents.persona_registry import get_persona_registry
from agents.teams import TeamRouter, TeamType
from agents.heartbeat_checker import HouseholdHeartbeatChecker, CheckType
from core.tenant_identity import TenantIdentityManager


class ManagerAgent(BaseAgent):
    """
    MyCasa Pro — Manager (Supervisor + Status Reporter)
    
    The single coordination authority. Sub-agents must not directly
    request user decisions unless Manager explicitly delegates.
    
    AUTHORITY:
    - Present unified plans and reports to user
    - Approve/deny escalation from other agents
    - Resolve conflicts between agents
    - Start/stop/enable/disable agent autonomy (subject to user policy)
    
    OPERATING LOOP:
    observe → evaluate → decide → delegate → verify → summarize → persist
    """
    
    # Agent registry - lazy loaded
    _AGENT_REGISTRY = {
        "maintenance": "agents.maintenance.MaintenanceAgent",
        "finance": "agents.finance.FinanceAgent",
        "contractors": "agents.contractors.ContractorsAgent",
        "projects": "agents.projects.ProjectsAgent",
        "janitor": "agents.janitor.JanitorAgent",
        "security-manager": "agents.security_manager.SecurityManagerAgent",
        "mail-skill": "agents.mail_skill.MailSkillAgent",
        "backup-recovery": "agents.backup_recovery.BackupRecoveryAgent",
    }
    
    def __init__(self):
        super().__init__("manager")
        self._sub_agents: Dict[str, Any] = {}
        self._agent_health: Dict[str, Dict] = {}
        self._galidima_available = None  # Lazy check
        self._init_timestamp = datetime.now()
        self._team_router = TeamRouter(manager_agent=self)
    
    # ============ LAZY LOADING ============
    
    def _get_agent(self, name: str):
        """
        Lazy-load a sub-agent on first access.
        PROHIBITION: No eager aggregation - load only when needed.
        """
        if name not in self._sub_agents:
            if name not in self._AGENT_REGISTRY:
                return None
            
            # Dynamic import
            module_path, class_name = self._AGENT_REGISTRY[name].rsplit(".", 1)
            start = time.time()
            
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                self._sub_agents[name] = agent_class()
                
                # Record health
                self._agent_health[name] = {
                    "loaded_at": datetime.now().isoformat(),
                    "load_time_ms": round((time.time() - start) * 1000, 2),
                    "state": "online",
                    "last_heartbeat": datetime.now().isoformat(),
                    "error_count": 0,
                    "last_error": None
                }
            except Exception as e:
                self._agent_health[name] = {
                    "state": "error",
                    "last_error": str(e),
                    "error_count": 1
                }
                return None
        
        return self._sub_agents.get(name)

    async def _delegate_to_specialist(self, agent_type, task: str, context: Dict[str, Any]):
        """Delegate a task to a specialist agent"""
        # Map AgentType to manager properties
        agent_map = {
            "finance": self.finance,
            "maintenance": self.maintenance,
            "contractors": self.contractors,
            "projects": self.projects,
            "janitor": self.janitor,
            "security": self.security_manager,
            "mail": self.mail_skill,
            "backup": self.backup_recovery,
        }
        agent_key = agent_type.value if hasattr(agent_type, "value") else str(agent_type)
        agent = agent_map.get(agent_key)
        if not agent:
            return {"content": f"Agent {agent_key} not available", "confidence": 0.0}

        # If a task_id is provided, route to execute_task(task_id)
        try:
            task_id = context.get("task_id") if isinstance(context, dict) else None
            if task_id is not None and hasattr(agent, "execute_task"):
                result = agent.execute_task(task_id)
                return {"content": str(result), "confidence": 0.75}
        except Exception:
            pass

        # If agent provides a status or overview, use it for synthesis
        for method_name in ["get_status", "get_finance_overview", "get_pending_tasks"]:
            if hasattr(agent, method_name):
                try:
                    result = getattr(agent, method_name)()
                    return {"content": str(result), "confidence": 0.7}
                except Exception:
                    pass

        # Fallback to chat if implemented
        if hasattr(agent, "chat"):
            response = await agent.chat(task, context)
            return {"content": response, "confidence": 0.8}

        return {"content": f"Agent {agent_key} has no handler", "confidence": 0.0}

    async def coordinate_team(self, team_type: TeamType, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a team task via TeamRouter"""
        result = await self._team_router.delegate_to_team(team_type, task, context)
        # Log decision for audit trail
        self.log_action(
            "team_task",
            f"Team {team_type.value} executed task: {task[:80]}",
            status="success" if result else "error"
        )
        return result.to_dict() if hasattr(result, "to_dict") else {"result": str(result)}

    async def route_and_execute(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route a task to a team if applicable, else handle directly"""
        context = context or {}
        team = self._team_router.suggest_team(task)
        if team:
            return await self.coordinate_team(team, task, context)
        # Default: try finance/maintenance based on keywords
        return {"response": f"No team matched. Task: {task}", "handled_by": "manager"}

    async def run_heartbeat(self) -> Dict[str, Any]:
        """Run the household heartbeat checks and return findings."""
        checker = HouseholdHeartbeatChecker(self.tenant_id)
        result = await checker.run_heartbeat()
        return result.to_dict()
    
    @property
    def maintenance(self):
        return self._get_agent("maintenance")
    
    @property
    def finance(self):
        return self._get_agent("finance")
    
    @property
    def contractors(self):
        return self._get_agent("contractors")
    
    @property
    def projects(self):
        return self._get_agent("projects")
    
    @property
    def janitor(self):
        return self._get_agent("janitor")
    
    @property
    def security_manager(self):
        return self._get_agent("security-manager")
    
    @property
    def mail_skill(self):
        return self._get_agent("mail-skill")
    
    @property
    def backup_recovery(self):
        return self._get_agent("backup-recovery")
    
    def _check_galidima(self) -> bool:
        """Check if Galidima (Clawdbot) is available - lazy"""
        if self._galidima_available is None:
            try:
                result = subprocess.run(
                    ["clawdbot", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                self._galidima_available = result.returncode == 0
            except Exception:
                self._galidima_available = False
        return self._galidima_available

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Manager chat entrypoint.
        Fast-path task/reminder requests to Maintenance (real DB), then fallback to LLM.
        """
        msg_lower = message.lower()

        # Task/reminder creation
        if any(k in msg_lower for k in ["remind", "reminder", "add a task", "add task", "schedule", "task reminder"]):
            maintenance = self.maintenance
            if maintenance and hasattr(maintenance, "create_task_from_message"):
                try:
                    result = maintenance.create_task_from_message(message)
                    if result:
                        if not result.get("success", True):
                            return f"Sorry — I couldn’t create that task. {result.get('error', 'Please try again.')} — Galidima 🏠"
                        due = result.get("due_date")
                        if due:
                            return f"Task \"{result['title']}\" scheduled for {due}. — Galidima 🏠"
                        return f"Task \"{result['title']}\" added. — Galidima 🏠"
                except Exception as exc:
                    self.log_action("task_create_failed", str(exc), status="error")
                    return f"Sorry — I couldn’t create that task. {str(exc)} — Galidima 🏠"

        # Reminder checks
        if "reminder" in msg_lower or "reminders" in msg_lower:
            maintenance = self.maintenance
            if not maintenance:
                return "I can’t reach Maintenance right now. Try again in a moment. — Galidima 🏠"
            try:
                tasks = maintenance.get_pending_tasks()
                if not tasks:
                    return "You don’t have any scheduled maintenance tasks right now. — Galidima 🏠"
                def fmt(d: Optional[str]) -> str:
                    if not d:
                        return "no date"
                    try:
                        return datetime.fromisoformat(d).strftime("%b %d, %Y")
                    except Exception:
                        return d
                lines = ["Here are your scheduled maintenance tasks:"]
                for t in tasks[:5]:
                    lines.append(f"• {t.get('title')} (due {fmt(t.get('due_date'))})")
                return "\n".join(lines) + "\n— Galidima 🏠"
            except Exception as exc:
                self.log_action("reminder_check_failed", str(exc), status="error")

        # Fallback to LLM
        return await super().chat(message, context, conversation_history=conversation_history)
    
    # ============ SYSTEM REPORTING MODES ============
    
    def quick_status(self) -> Dict[str, Any]:
        """
        QUICK STATUS (default mode)
        
        Compact dashboard summary:
        - agents: online/offline + what each is doing in 1 line
        - tasks: running/queued/scheduled counts + next 3 upcoming
        - alerts: top risks and required approvals
        - recent changes: last 5 meaningful events
        
        FACTS / RECOMMENDATIONS / UNKNOWNS clearly separated.
        """
        result = {
            "mode": "quick",
            "timestamp": datetime.now().isoformat(),
            "facts": {},
            "recommendations": [],
            "unknowns": []
        }
        
        # FACTS: Agent status (only loaded agents)
        agents_summary = {}
        for name in self._AGENT_REGISTRY.keys():
            if name in self._sub_agents:
                health = self._agent_health.get(name, {})
                agents_summary[name] = {
                    "state": health.get("state", "unknown"),
                    "doing": self._get_agent_current_task(name)
                }
            else:
                agents_summary[name] = {"state": "not_loaded", "doing": None}
        
        result["facts"]["agents"] = agents_summary
        # NOTE: Galidima check is expensive (subprocess call), skip in quick status
        # User can request full_report() for Galidima status
        result["facts"]["galidima_connected"] = self._galidima_available  # Use cached value or None
        
        # FACTS: Task counts (from DB, no agent load required)
        with get_db() as db:
            from database.models import MaintenanceTask
            pending_tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status.in_(["pending", "in_progress"])
            ).count()
            
            # Next 3 upcoming tasks
            upcoming = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.scheduled_date != None
            ).order_by(MaintenanceTask.scheduled_date.asc()).limit(3).all()
            
            result["facts"]["tasks"] = {
                "pending": pending_tasks,
                "upcoming": [
                    {"title": t.title, "date": t.scheduled_date.isoformat() if t.scheduled_date else None}
                    for t in upcoming
                ]
            }
            
            # FACTS: Alerts (unread high-priority notifications)
            alerts = db.query(Notification).filter(
                Notification.is_read == False,
                Notification.priority.in_(["high", "critical"])
            ).order_by(Notification.created_at.desc()).limit(5).all()
            
            result["facts"]["alerts"] = [
                {"title": a.title, "priority": a.priority, "category": a.category}
                for a in alerts
            ]
            
            # FACTS: Recent activity
            recent = db.query(AgentLog).order_by(
                AgentLog.created_at.desc()
            ).limit(5).all()
            
            result["facts"]["recent_changes"] = [
                {
                    "agent": r.agent,
                    "action": r.action,
                    "status": r.status,
                    "time": r.created_at.isoformat()
                }
                for r in recent
            ]

            # FACTS: Identity status
            try:
                identity_manager = TenantIdentityManager(self.tenant_id)
                identity_manager.ensure_identity_structure()
                result["facts"]["identity"] = identity_manager.get_identity_status()
            except Exception as exc:
                result["facts"]["identity"] = {"ready": False, "error": str(exc)}

            # FACTS: Household heartbeat status
            try:
                checker = HouseholdHeartbeatChecker(self.tenant_id)
                state = checker._load_state()
                last_checks = state.get("lastChecks", {})
                last_run = max(last_checks.values()) if last_checks else None
                next_due = checker._calculate_next_check_time().isoformat()
                categories = [c.value for c in CheckType]
                open_findings = (
                    db.query(Notification)
                    .filter(Notification.category.in_(categories))
                    .filter(Notification.is_read == False)  # noqa: E712
                    .count()
                )
                result["facts"]["heartbeat"] = {
                    "last_run": last_run,
                    "next_due": next_due,
                    "open_findings": open_findings,
                    "last_consolidation": state.get("lastConsolidation"),
                }
            except Exception as exc:
                result["facts"]["heartbeat"] = {"error": str(exc)}
        
        # RECOMMENDATIONS
        if pending_tasks > 5:
            result["recommendations"].append("High task backlog - consider reviewing priorities")
        if len(alerts) > 0:
            result["recommendations"].append(f"{len(alerts)} alert(s) require attention")
        
        # UNKNOWNS
        for name, health in self._agent_health.items():
            if health.get("state") == "error":
                result["unknowns"].append(f"Agent '{name}' failed to load: {health.get('last_error')}")
        
        return result
    
    def full_report(self) -> Dict[str, Any]:
        """
        FULL SYSTEM REPORT (on request or on incident)
        
        Structured, complete report with:
        - Agent table: name, state, last heartbeat, current task, error count
        - Task table: id, owner, status, start time, ETA/timeout, dependencies
        - Scheduler: upcoming jobs, disabled jobs, missed runs
        - Memory/Storage: last writes, growth anomalies
        - Incidents: P0–P3 with status + remediation owner
        - Recommendations: next actions ranked by impact
        
        NO FABRICATED DATA. Unknown = UNKNOWN.
        """
        result = {
            "mode": "full",
            "timestamp": datetime.now().isoformat(),
            "manager_uptime_seconds": (datetime.now() - self._init_timestamp).total_seconds(),
            "sections": {}
        }
        
        # SECTION: Agent Table
        agent_table = []
        for name in self._AGENT_REGISTRY.keys():
            health = self._agent_health.get(name, {"state": "not_loaded"})
            
            row = {
                "name": name,
                "state": health.get("state", "not_loaded"),
                "last_heartbeat": health.get("last_heartbeat", "never"),
                "current_task": self._get_agent_current_task(name) if name in self._sub_agents else None,
                "error_count": health.get("error_count", 0),
                "load_time_ms": health.get("load_time_ms", None)
            }
            agent_table.append(row)
        
        result["sections"]["agents"] = agent_table
        
        # SECTION: Task Table
        with get_db() as db:
            from database.models import MaintenanceTask, Bill
            
            tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status.in_(["pending", "in_progress"])
            ).order_by(MaintenanceTask.scheduled_date.asc()).all()
            
            result["sections"]["tasks"] = [
                {
                    "id": t.id,
                    "title": t.title,
                    "owner": "maintenance",
                    "status": t.status,
                    "priority": t.priority,
                    "scheduled": t.scheduled_date.isoformat() if t.scheduled_date else "UNKNOWN",
                    "category": t.category
                }
                for t in tasks
            ]
            
            # SECTION: Bills (Finance tasks)
            unpaid_bills = db.query(Bill).filter(Bill.is_paid == False).all()
            result["sections"]["bills"] = [
                {
                    "id": b.id,
                    "name": b.name,
                    "amount": b.amount,
                    "due_date": b.due_date.isoformat() if b.due_date else "UNKNOWN",
                    "auto_pay": b.auto_pay
                }
                for b in unpaid_bills
            ]
            
            # SECTION: Scheduler
            jobs = db.query(ScheduledJob).all()
            result["sections"]["scheduler"] = {
                "active_jobs": [
                    {
                        "name": j.name,
                        "agent": j.agent,
                        "next_run": j.next_run.isoformat() if j.next_run else "UNKNOWN",
                        "is_active": j.is_active
                    }
                    for j in jobs if j.is_active
                ],
                "disabled_jobs": [j.name for j in jobs if not j.is_active],
                "missed_runs": []  # TODO: implement missed run detection
            }
            
            # SECTION: Recent Logs
            logs = db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(20).all()
            result["sections"]["audit_log"] = [
                {
                    "agent": l.agent,
                    "action": l.action,
                    "details": l.details,
                    "status": l.status,
                    "time": l.created_at.isoformat()
                }
                for l in logs
            ]
        
        # SECTION: Incidents (from Janitor if loaded)
        if "janitor" in self._sub_agents:
            incidents = self.janitor.get_context("incidents") or {"active": [], "resolved": []}
            result["sections"]["incidents"] = {
                "active": incidents.get("active", []),
                "resolved_count": len(incidents.get("resolved", []))
            }
        else:
            result["sections"]["incidents"] = {"status": "UNKNOWN - Janitor not loaded"}
        
        # SECTION: Recommendations (ranked by impact)
        recommendations = []
        
        if len(result["sections"].get("tasks", [])) > 10:
            recommendations.append({
                "priority": "high",
                "action": "Review task backlog - 10+ pending tasks"
            })
        
        overdue_bills = [b for b in result["sections"].get("bills", []) 
                        if b.get("due_date") and b["due_date"] != "UNKNOWN" 
                        and date.fromisoformat(b["due_date"]) < date.today()]
        if overdue_bills:
            recommendations.append({
                "priority": "critical",
                "action": f"Pay {len(overdue_bills)} overdue bill(s)"
            })
        
        result["recommendations"] = recommendations
        
        return result
    
    def audit_trace(self, action_id: str = None, query: str = None) -> Dict[str, Any]:
        """
        AUDIT TRACE (when user asks "why")
        
        Provide traceability:
        - what triggered the action
        - which agent acted
        - what data was used
        - what tool calls occurred
        - evidence of completion
        - rollback/undo options if applicable
        
        NO FABRICATED EVIDENCE. Unknown = UNKNOWN + propose verification.
        """
        result = {
            "mode": "audit",
            "timestamp": datetime.now().isoformat(),
            "query": query or action_id,
            "trace": [],
            "unknowns": [],
            "verification_options": []
        }
        
        with get_db() as db:
            if action_id:
                # Find specific action
                logs = db.query(AgentLog).filter(
                    AgentLog.id == int(action_id) if action_id.isdigit() else AgentLog.action.contains(action_id)
                ).all()
            elif query:
                # Search logs
                logs = db.query(AgentLog).filter(
                    AgentLog.action.contains(query) | AgentLog.details.contains(query)
                ).order_by(AgentLog.created_at.desc()).limit(10).all()
            else:
                # Last 10 actions
                logs = db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(10).all()
            
            for log in logs:
                trace_entry = {
                    "id": log.id,
                    "agent": log.agent,
                    "action": log.action,
                    "details": log.details,
                    "status": log.status,
                    "timestamp": log.created_at.isoformat(),
                    "trigger": "UNKNOWN",  # TODO: implement trigger tracking
                    "evidence": log.details if log.status == "success" else None,
                    "rollback": None  # TODO: implement rollback options
                }
                result["trace"].append(trace_entry)
                
                if not log.details:
                    result["unknowns"].append(f"Action {log.id} has no evidence recorded")
            
            if not logs:
                result["unknowns"].append(f"No matching actions found for: {query or action_id}")
                result["verification_options"].append("Check agent memory files for additional context")
        
        return result
    
    def _get_agent_current_task(self, agent_name: str) -> Optional[str]:
        """Get what an agent is currently doing (1-line summary)"""
        # For now, return None - agents don't track "current task" yet
        return None
    
    # ============ LEGACY COMPATIBILITY ============
    
    def get_status(self) -> Dict[str, Any]:
        """
        Legacy status method - returns quick_status format.
        DOES NOT eagerly load all agents.
        """
        quick = self.quick_status()
        
        # Reshape for backwards compatibility
        return {
            "agent": "manager",
            "status": "active",
            "health": "healthy" if not quick["unknowns"] else "degraded",
            "galidima_connected": quick["facts"].get("galidima_connected", False),
            "loaded_agents": list(self._sub_agents.keys()),
            "total_agents": len(self._AGENT_REGISTRY),
            "pending_tasks": quick["facts"]["tasks"]["pending"],
            "alerts": len(quick["facts"]["alerts"]),
            "last_check": quick["timestamp"]
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Dashboard summary - loads agents ONLY as needed.
        Returns structured data for UI rendering.
        
        PROHIBITION: No eager aggregation of all agent data.
        Load incrementally based on what UI section requests.
        """
        # Start with quick status (no agent loading)
        quick = self.quick_status()
        
        result = {
            "status": self.get_status(),
            "upcoming_tasks": [],
            "upcoming_bills": [],
            "overdue_tasks": [],
            "recent_activity": quick["facts"]["recent_changes"],
            "notifications": [],
            "alerts": quick["facts"]["alerts"],
            "quick_stats": {
                "tasks_today": 0,
                "bills_this_week": 0,
                "active_projects": 0,
                "portfolio_value": None  # UNKNOWN until finance agent called
            }
        }
        
        # Load ONLY what's needed from DB (no agent instantiation)
        with get_db() as db:
            from database.models import MaintenanceTask, Bill
            
            # Upcoming tasks
            upcoming = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending"
            ).order_by(MaintenanceTask.scheduled_date.asc()).limit(5).all()
            
            result["upcoming_tasks"] = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
                    "category": t.category
                }
                for t in upcoming
            ]
            
            # Tasks today
            today_tasks = [t for t in upcoming if t.scheduled_date == date.today()]
            result["quick_stats"]["tasks_today"] = len(today_tasks)
            
            # Overdue tasks
            overdue = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.scheduled_date < date.today()
            ).all()
            result["overdue_tasks"] = [
                {"id": t.id, "title": t.title, "scheduled_date": t.scheduled_date.isoformat()}
                for t in overdue
            ]
            
            # Upcoming bills
            week_ahead = date.today() + timedelta(days=30)
            bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date <= week_ahead
            ).order_by(Bill.due_date.asc()).limit(5).all()
            
            result["upcoming_bills"] = [
                {
                    "id": b.id,
                    "name": b.name,
                    "amount": b.amount,
                    "due_date": b.due_date.isoformat() if b.due_date else None,
                    "days_until_due": (b.due_date - date.today()).days if b.due_date else None,
                    "is_paid": b.is_paid,
                    "auto_pay": b.auto_pay
                }
                for b in bills
            ]
            
            # Bills this week
            week_bills = [b for b in bills if b.due_date and (b.due_date - date.today()).days <= 7]
            result["quick_stats"]["bills_this_week"] = len(week_bills)
            
            # Notifications
            notifications = db.query(Notification).filter(
                Notification.is_read == False
            ).order_by(Notification.created_at.desc()).limit(5).all()
            
            result["notifications"] = [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority,
                    "category": n.category,
                    "created_at": n.created_at.isoformat()
                }
                for n in notifications
            ]
        
        # NOTE: portfolio_value left as None - UI should call finance agent directly if needed
        # This prevents eager loading of yfinance API calls
        
        return result
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks - from DB only, no agent aggregation"""
        with get_db() as db:
            from database.models import MaintenanceTask, Bill
            
            tasks = []
            
            # Maintenance tasks
            mtasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status.in_(["pending", "in_progress"])
            ).order_by(MaintenanceTask.scheduled_date.asc()).all()
            
            for t in mtasks:
                tasks.append({
                    "type": "maintenance",
                    "id": t.id,
                    "title": t.title,
                    "priority": t.priority,
                    "status": t.status,
                    "due_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
                    "category": t.category
                })
            
            # Unpaid bills as tasks
            bills = db.query(Bill).filter(Bill.is_paid == False).all()
            for b in bills:
                days_until = (b.due_date - date.today()).days if b.due_date else None
                priority = "urgent" if days_until and days_until < 0 else \
                          "high" if days_until and days_until <= 3 else \
                          "medium" if days_until and days_until <= 7 else "low"
                
                tasks.append({
                    "type": "bill",
                    "id": b.id,
                    "title": f"Pay {b.name}",
                    "priority": priority,
                    "status": "pending",
                    "due_date": b.due_date.isoformat() if b.due_date else None,
                    "amount": b.amount
                })
            
            # Sort by priority
            priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
            tasks.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
            
            return tasks
    
    def execute_task(self, task_id: int, agent: str = None) -> Dict[str, Any]:
        """Execute a task, routing to appropriate agent"""
        if agent and agent in self._AGENT_REGISTRY:
            target = self._get_agent(agent)
            if target:
                return target.execute_task(task_id)
        return {"success": False, "error": "Unknown agent or task"}
    
    # ============ ALERTS & NOTIFICATIONS ============
    
    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts - from DB and loaded agents only"""
        alerts = []
        
        # DB-based alerts
        with get_db() as db:
            from database.models import MaintenanceTask, Bill
            
            # Overdue tasks
            overdue = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.scheduled_date < date.today()
            ).count()
            
            if overdue > 0:
                alerts.append({
                    "type": "overdue_tasks",
                    "severity": "high",
                    "title": f"{overdue} overdue task(s)",
                    "source_agent": "maintenance"
                })
            
            # Overdue bills
            overdue_bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date < date.today()
            ).count()
            
            if overdue_bills > 0:
                alerts.append({
                    "type": "overdue_bills",
                    "severity": "critical",
                    "title": f"{overdue_bills} overdue bill(s)",
                    "source_agent": "finance"
                })
        
        # Janitor alerts (if loaded)
        if "janitor" in self._sub_agents:
            janitor_alerts = self.janitor.check_alerts()
            alerts.extend(janitor_alerts)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: severity_order.get(x.get("severity", "medium"), 2))
        
        return alerts
    
    def get_notifications(self, unread_only: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
        """Get system notifications"""
        with get_db() as db:
            query = db.query(Notification)
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "category": n.category,
                    "priority": n.priority,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat()
                }
                for n in notifications
            ]
    
    # ============ AUTONOMY POLICY ============
    
    def can_auto_execute(self, action: Dict[str, Any]) -> tuple[bool, str]:
        """
        AUTO-EXECUTE ONLY IF ALL TRUE:
        - reversible
        - cost < approved threshold
        - no new vendor introduced
        - no major disruption
        - aligns with user patterns
        - evidence-based (no guesses)
        """
        thresholds = self._load_thresholds()
        
        if not action.get("reversible", True):
            return False, "Action is not reversible"
        
        cost = action.get("cost", 0)
        if cost >= thresholds.get("auto_approve_cost", 100):
            return False, f"Cost ${cost} exceeds threshold"
        
        if action.get("new_vendor"):
            return False, "Introduces new vendor"
        
        if action.get("disrupts_schedule"):
            return False, "Impacts daily schedule"
        
        if action.get("evidence") is None:
            return False, "No evidence provided - cannot auto-execute guesses"
        
        return True, "All auto-execute conditions met"
    
    def requires_user_confirmation(self, action: Dict[str, Any]) -> tuple[bool, str]:
        """
        USER CONFIRMATION REQUIRED IF ANY TRUE:
        - irreversible
        - cost ≥ threshold
        - involves credentials, payments, contracts
        - introduces new vendor
        - impacts utilities/access/schedule
        - alters system autonomy or permissions
        """
        thresholds = self._load_thresholds()
        
        if not action.get("reversible", True):
            return True, "Irreversible action"
        
        cost = action.get("cost", 0)
        if cost >= thresholds.get("auto_approve_cost", 100):
            return True, f"Cost ${cost} requires approval"
        
        if action.get("involves_credentials") or action.get("involves_payment") or action.get("involves_contract"):
            return True, "Involves sensitive operations"
        
        if action.get("new_vendor"):
            return True, "New vendor introduction"
        
        if action.get("impacts_utilities") or action.get("impacts_access") or action.get("disrupts_schedule"):
            return True, "Impacts utilities, access, or schedule"
        
        if action.get("alters_permissions"):
            return True, "Alters system permissions"
        
        return False, "No confirmation required"
    
    def _load_thresholds(self) -> Dict[str, Any]:
        """Load autonomy thresholds from context"""
        config = self.get_context('household_config') or {}
        return config.get('thresholds', {
            'auto_approve_cost': 100,
            'high_alert_cost': 500,
        })
    
    # ============ SCHEDULED OPERATIONS ============
    
    def run_daily_check(self) -> Dict[str, Any]:
        """Run daily system check - returns full report"""
        self.log_action("daily_check", "Running daily system check")
        
        report = self.full_report()
        
        # Create alerts for critical items
        for rec in report.get("recommendations", []):
            if rec.get("priority") == "critical":
                self.create_notification(
                    title=rec["action"],
                    message="Daily check identified critical item",
                    priority="high",
                    category="system"
                )
        
        self.log_action("daily_check_complete", f"Report generated with {len(report.get('recommendations', []))} recommendations")
        
        return report
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        with get_db() as db:
            jobs = db.query(ScheduledJob).order_by(ScheduledJob.next_run.asc()).all()
            
            return [
                {
                    "id": job.id,
                    "name": job.name,
                    "agent": job.agent,
                    "job_type": job.job_type,
                    "is_active": job.is_active,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "next_run": job.next_run.isoformat() if job.next_run else None
                }
                for job in jobs
            ]
    
    # ============ PERSONA MANAGEMENT ============
    # Final authority to add/remove personas rests with the user via Manager.
    # No persona is permanent. All personas are optional, composable, reversible.
    
    def list_personas(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """List all personas with their states"""
        registry = get_persona_registry()
        return registry.list_personas(include_disabled=include_disabled)
    
    def get_persona(self, persona_id: str) -> Dict[str, Any]:
        """Get full persona definition"""
        registry = get_persona_registry()
        persona = registry.get_persona(persona_id)
        if persona:
            from dataclasses import asdict
            return asdict(persona)
        return {"error": "Persona not found"}
    
    def get_active_personas(self) -> List[str]:
        """Get list of active persona IDs"""
        registry = get_persona_registry()
        return registry.get_active_personas()
    
    def why_persona_active(self, persona_id: str) -> Dict[str, Any]:
        """Explain why a persona is active"""
        registry = get_persona_registry()
        return registry.why_active(persona_id)
    
    def add_persona(
        self,
        persona_id: str,
        name: str,
        soul_md: str,
        description: str = "",
        auto_enable: bool = False,
        reason: str = "User request"
    ) -> Dict[str, Any]:
        """
        Add a new persona at runtime.
        
        AUTHORITY: Manager (Galidima) - final authority
        Does NOT require restart.
        """
        registry = get_persona_registry()
        result = registry.add_persona(
            persona_id=persona_id,
            name=name,
            soul_md=soul_md,
            description=description,
            created_by="manager",
            auto_enable=auto_enable
        )
        
        if result["success"]:
            self.log_action("persona_added", f"Added persona: {name} ({persona_id})")
            self.append_memory("Persona Changes", f"Added: {name} - {reason}")
        
        return result
    
    def enable_persona(self, persona_id: str, reason: str = "User request") -> Dict[str, Any]:
        """Enable a disabled or pending persona"""
        registry = get_persona_registry()
        result = registry.enable_persona(persona_id, enabled_by="manager")
        
        if result["success"]:
            self.log_action("persona_enabled", f"Enabled persona: {persona_id}")
            self.append_memory("Persona Changes", f"Enabled: {persona_id} - {reason}")
        
        return result
    
    def disable_persona(self, persona_id: str, reason: str) -> Dict[str, Any]:
        """
        Disable a persona without removing it.
        
        AUTHORITY: Manager (Galidima) - final authority
        Does NOT require restart. Persona can be re-enabled later.
        """
        registry = get_persona_registry()
        result = registry.disable_persona(persona_id, reason=reason, disabled_by="manager")
        
        if result["success"]:
            self.log_action("persona_disabled", f"Disabled persona: {persona_id} - {reason}")
            self.append_memory("Persona Changes", f"Disabled: {persona_id} - {reason}")
        
        return result
    
    def remove_persona(self, persona_id: str, reason: str, archive: bool = True) -> Dict[str, Any]:
        """
        Remove a persona.
        
        AUTHORITY: Manager (Galidima) - final authority
        If archive=True, persona files are moved to archive (reversible).
        """
        registry = get_persona_registry()
        result = registry.remove_persona(
            persona_id=persona_id,
            reason=reason,
            removed_by="manager",
            archive=archive
        )
        
        if result["success"]:
            self.log_action("persona_removed", f"Removed persona: {persona_id} - {reason}")
            self.append_memory("Persona Changes", f"Removed: {persona_id} - {reason}")
        
        return result
    
    def update_persona(
        self,
        persona_id: str,
        soul_md: str = None,
        description: str = None,
        reason: str = "Update"
    ) -> Dict[str, Any]:
        """
        Update a persona definition, creating a new version.
        
        Previous version is preserved for rollback.
        """
        registry = get_persona_registry()
        result = registry.update_persona(
            persona_id=persona_id,
            soul_md=soul_md,
            description=description,
            updated_by="manager",
            reason=reason
        )
        
        if result["success"]:
            self.log_action("persona_updated", f"Updated persona: {persona_id} to v{result['new_version']}")
            self.append_memory("Persona Changes", f"Updated: {persona_id} - {reason}")
        
        return result
    
    def rollback_persona(self, persona_id: str, to_version: int, reason: str) -> Dict[str, Any]:
        """Rollback a persona to a previous version"""
        registry = get_persona_registry()
        result = registry.rollback_persona(
            persona_id=persona_id,
            to_version=to_version,
            rolled_back_by="manager",
            reason=reason
        )
        
        if result["success"]:
            self.log_action("persona_rollback", f"Rolled back {persona_id} to v{to_version}")
            self.append_memory("Persona Changes", f"Rollback: {persona_id} to v{to_version} - {reason}")
        
        return result
    
    def get_persona_recommendations(self) -> List[Dict[str, Any]]:
        """Get Janitor's recommendations for persona management"""
        registry = get_persona_registry()
        return registry.get_audit_recommendations()
    
    # ============ MESSAGING CAPABILITIES ============
    # Enable Manager to send messages via WhatsApp connector
    
    def _get_whatsapp_connector(self):
        """Lazy-load WhatsApp connector"""
        if not hasattr(self, '_whatsapp'):
            try:
                from connectors.whatsapp import WhatsAppConnector
                self._whatsapp = WhatsAppConnector()
            except ImportError:
                self._whatsapp = None
        return self._whatsapp
    
    def lookup_contact(self, query: str) -> Optional[Dict[str, str]]:
        """
        Look up a contact by name or phone number.
        
        Args:
            query: Name (partial match) or phone number
        
        Returns:
            Contact dict with name, phone, relation, jid
        """
        wa = self._get_whatsapp_connector()
        if wa:
            return wa.lookup_contact(query)
        return None
    
    def get_contacts(self) -> List[Dict[str, str]]:
        """Get all known contacts"""
        wa = self._get_whatsapp_connector()
        if wa:
            return wa.get_all_contacts()
        return []
    
    def send_whatsapp(
        self,
        to: str,
        message: str,
        record_in_secondbrain: bool = True
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message.
        
        Args:
            to: Contact name or phone number
            message: Message text
            record_in_secondbrain: Whether to log this in SecondBrain
        
        Returns:
            Result dict with success status
        
        Example:
            manager.send_whatsapp("Anastasia", "Hello! How are you?")
            manager.send_whatsapp("+351915443876", "Hi there!")
        """
        import asyncio
        
        wa = self._get_whatsapp_connector()
        if not wa:
            return {"success": False, "error": "WhatsApp connector not available"}
        
        # Resolve contact name
        original_to = to
        contact = wa.lookup_contact(to)
        if contact:
            resolved_to = contact.get("phone")
            contact_name = contact.get("name")
            self.logger.info(f"Resolved '{to}' to {resolved_to} ({contact_name})")
        else:
            resolved_to = to
            contact_name = to
        
        try:
            # Send via connector
            result = self._run_async(wa.send(
                tenant_id=self.tenant_id,
                payload={
                    "to": resolved_to,
                    "message": message
                }
            ))
            
            # Log the action
            self.log_action(
                "whatsapp_sent",
                f"Sent to {contact_name}: {message[:50]}...",
                status="success"
            )
            
            # Record in SecondBrain if requested
            if record_in_secondbrain:
                self.record_event_to_sb(
                    event=f"WhatsApp sent to {contact_name}",
                    details=f"To: {contact_name}\nMessage: {message}",
                    entities=[f"ent_contact_{contact_name.lower().replace(' ', '_')}"] if contact else []
                )
            
            return {
                "success": True,
                "to": contact_name,
                "phone": resolved_to,
                "message_preview": message[:100] + "..." if len(message) > 100 else message
            }
            
        except Exception as e:
            self.logger.error(f"WhatsApp send failed: {e}")
            self.log_action("whatsapp_failed", f"Failed to send to {contact_name}: {e}", status="error")
            return {"success": False, "error": str(e)}
    
    def handle_messaging_request(
        self,
        request: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle a natural language messaging request.
        
        Examples:
            "Send a WhatsApp to Anastasia saying hello"
            "Message Juan about the roof repair"
            "Text Erika that I'll be late"
        
        Args:
            request: Natural language request
            context: Additional context (e.g., previous conversation)
        
        Returns:
            Result dict with success status and details
        """
        # Parse the request (simple heuristics for now)
        request_lower = request.lower()
        
        # Extract recipient - check full name and first name
        recipient = None
        for contact in self.get_contacts():
            full_name = contact.get("name", "").lower()
            first_name = full_name.split()[0] if full_name else ""
            
            # Check if full name or first name is in the request
            if full_name in request_lower or (first_name and first_name in request_lower):
                recipient = contact
                break
        
        if not recipient:
            return {
                "success": False,
                "error": "Could not identify recipient",
                "available_contacts": [c.get("name") for c in self.get_contacts()]
            }
        
        # Extract message (basic extraction)
        message = None
        
        # Common patterns
        patterns = [
            "saying ", "say ", "message ", "that ", "about "
        ]
        for pattern in patterns:
            if pattern in request_lower:
                idx = request.lower().find(pattern) + len(pattern)
                message = request[idx:].strip()
                break
        
        if not message:
            return {
                "success": False,
                "error": "Could not extract message content",
                "suggestion": f"Try: 'Send WhatsApp to {recipient['name']} saying [your message]'"
            }
        
        # Send the message
        return self.send_whatsapp(recipient["name"], message)


    # ============ CHAT METHOD ============
    
    def _classify_intent(self, message: str) -> str:
        """Simple intent classification based on keywords."""
        finance_keywords = ["money", "budget", "spend", "cost", "portfolio", "bill", "payment", "finance", "mamadou"]
        maintenance_keywords = ["fix", "repair", "maintenance", "task", "schedule", "clean", "ousmane"]
        security_keywords = ["security", "safe", "alarm", "incident", "camera", "aïcha", "aicha"]
        contractor_keywords = ["contractor", "plumber", "electrician", "service", "provider", "malik"]
        project_keywords = ["project", "renovation", "improvement", "remodel", "zainab"]
        status_keywords = ["status", "overview", "how", "what's going on", "summary"]
        
        if any(kw in message for kw in finance_keywords):
            return "finance"
        elif any(kw in message for kw in maintenance_keywords):
            return "maintenance"
        elif any(kw in message for kw in security_keywords):
            return "security"
        elif any(kw in message for kw in contractor_keywords):
            return "contractors"
        elif any(kw in message for kw in project_keywords):
            return "projects"
        elif any(kw in message for kw in status_keywords):
            return "status"
        
        return "general"


# Backwards compatibility alias
SupervisorAgent = ManagerAgent
