"""
Maintenance Agent - Ousmane
Handles home maintenance tasks and schedules
"""
from typing import Dict, Any, List, Optional, Union
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import re
from dateutil import parser as date_parser
from .base import BaseAgent


class MaintenanceAgent(BaseAgent):
    """
    Maintenance Agent (Ousmane) - handles home maintenance
    
    Responsibilities:
    - Track maintenance tasks
    - Schedule repairs and upkeep
    - Monitor home systems
    - Coordinate with contractors
    """
    
    def __init__(self):
        super().__init__(
            agent_id="maintenance",
            name="Ousmane",
            description="Maintenance Manager - Home tasks and schedules",
            emoji="🔧"
        )
        self.start()
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get maintenance-specific metrics"""
        try:
            tasks = self.get_tasks_from_db()
            pending = [t for t in tasks if t.get("status") == "pending"]
            overdue = [t for t in tasks if t.get("is_overdue")]
            return {
                "total_tasks": len(tasks),
                "pending_tasks": len(pending),
                "overdue_tasks": len(overdue),
            }
        except Exception:
            return {}

    def _get_timezone(self) -> str:
        try:
            from core.settings_typed import get_settings_store
            settings = get_settings_store().get()
            return getattr(settings.system, "timezone", "America/Los_Angeles") or "America/Los_Angeles"
        except Exception:
            return "America/Los_Angeles"

    def _today(self) -> date:
        try:
            tz = ZoneInfo(self._get_timezone())
            return datetime.now(tz).date()
        except Exception:
            return date.today()
    
    def get_tasks_from_db(self) -> List[Dict[str, Any]]:
        """Get maintenance tasks from database"""
        from database import get_db
        from database.models import MaintenanceTask

        today = date.today()
        with get_db() as db:
            tasks = (
                db.query(MaintenanceTask)
                .order_by(MaintenanceTask.due_date.is_(None), MaintenanceTask.due_date)
                .all()
            )
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
                    "priority": t.priority,
                    "category": t.category,
                    "description": t.description,
                    "is_overdue": bool(t.due_date and t.status == "pending" and t.due_date < today),
                }
                for t in tasks
            ]

    def add_task(
        self,
        title_or_task: Union[Dict[str, Any], str],
        category: str = "general",
        priority: str = "medium",
        scheduled_date: Optional[Union[date, str]] = None,
        description: str = "",
        due_date: Optional[Union[date, str]] = None,
    ) -> Dict[str, Any]:
        """Create a maintenance task in the database (supports dict payloads)."""
        from database import get_db
        from database.models import MaintenanceTask

        def coerce_date(value: Optional[Union[date, str]]) -> Optional[date]:
            if not value:
                return None
            if isinstance(value, date):
                return value
            try:
                return date.fromisoformat(str(value))
            except Exception:
                try:
                    return date_parser.parse(str(value), fuzzy=True).date()
                except Exception:
                    return None

        if isinstance(title_or_task, dict):
            payload = title_or_task
            title = payload.get("title") or "Maintenance task"
            category = payload.get("category", category)
            priority = payload.get("priority", priority)
            description = payload.get("description", description)
            scheduled_date = payload.get("scheduled_date", scheduled_date)
            due_date = payload.get("due_date", due_date)
        else:
            title = title_or_task or "Maintenance task"

        scheduled = coerce_date(scheduled_date)
        due = coerce_date(due_date) or scheduled
        if not title:
            title = "Maintenance task"

        with get_db() as db:
            task = MaintenanceTask(
                title=title.strip(),
                description=description or None,
                category=category or "general",
                priority=priority or "medium",
                status="pending",
                scheduled_date=scheduled,
                due_date=due,
            )
            db.add(task)
            db.flush()
            task_id = task.id

        self.log_action("task_created", f"{title} (id={task_id})")
        return {
            "success": True,
            "task_id": task_id,
            "title": title,
            "due_date": due.isoformat() if due else None,
            "scheduled_date": scheduled.isoformat() if scheduled else None,
        }

    def complete_task(self, task_id: int, evidence: Optional[str] = None) -> Dict[str, Any]:
        """Mark a maintenance task as complete."""
        from database import get_db
        from database.models import MaintenanceTask

        with get_db() as db:
            task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
            if not task:
                return {"success": False, "error": "Task not found"}
            task.status = "completed"
            task.completed_date = date.today()
            if evidence:
                task.notes = (task.notes or "") + f"\n{evidence}"
            db.add(task)
        self.log_action("task_completed", f"{task_id}")
        return {"success": True, "task_id": task_id}

    def _extract_due_date(self, message: str) -> Optional[date]:
        text = message.lower()
        today = self._today()

        if "today" in text:
            return today
        if "tomorrow" in text:
            return today + timedelta(days=1)

        weekday_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        match = re.search(r"\b(this|next|by|on)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text)
        if match:
            modifier = (match.group(1) or "by").strip()
            target = weekday_map[match.group(2)]
            current = today.weekday()
            delta = (target - current) % 7
            if modifier == "next":
                if delta == 0:
                    delta = 7
            else:
                # "this/by/on" = next occurrence, including today if it matches
                delta = delta
            return today + timedelta(days=delta)

        # ISO date
        match = re.search(r"\b(\d{4}-\d{1,2}-\d{1,2})\b", text)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except Exception:
                pass

        # US date
        match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", text)
        if match:
            try:
                return date_parser.parse(match.group(1), fuzzy=True).date()
            except Exception:
                pass

        return None

    def _extract_task_title(self, message: str) -> str:
        text = message.strip()
        patterns = [
            r"(?i)remind me to (.+)",
            r"(?i)reminder to (.+)",
            r"(?i)add (?:a )?task(?: reminder)? to (.+)",
            r"(?i)create (?:a )?task(?: reminder)? to (.+)",
            r"(?i)schedule (.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                title = re.split(r"\b(?:by|on|this|next)\b", title, 1, flags=re.IGNORECASE)[0].strip()
                if title:
                    return title
        return text

    def create_task_from_message(self, message: str) -> Optional[Dict[str, Any]]:
        msg_lower = message.lower()
        if not any(k in msg_lower for k in ["remind", "reminder", "add a task", "add task", "schedule", "task reminder"]):
            return None
        title = self._extract_task_title(message)
        due_date = self._extract_due_date(message)
        try:
            return self.add_task(
                title=title,
                category="maintenance",
                priority="medium",
                scheduled_date=due_date,
                due_date=due_date,
                description="Created from chat request",
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    
    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Handle maintenance-related chat"""
        msg_lower = message.lower()

        task_result = self.create_task_from_message(message)
        if task_result:
            if not task_result.get("success", True):
                return f"Sorry — I couldn’t create that task. {task_result.get('error', 'Please try again.')} — Ousmane 🔧"
            due = task_result.get("due_date")
            if due:
                return f"Got it. I added the task \"{task_result['title']}\" due {due}. — Ousmane 🔧"
            return f"Got it. I added the task \"{task_result['title']}\". — Ousmane 🔧"
        
        if "tasks" in msg_lower or "todo" in msg_lower:
            tasks = self.get_tasks_from_db()
            pending = [t for t in tasks if t.get("status") == "pending"]
            if pending:
                lines = ["🔧 **Pending Maintenance Tasks:**"]
                for t in pending[:10]:
                    icon = "🔴" if t.get("is_overdue") else "🟡"
                    lines.append(f"  {icon} {t['title']} (due: {t.get('due_date', 'no date')})")
                self.log_action("tasks_viewed", f"Showed {len(pending)} pending tasks")
                return "\n".join(lines) + f"\n\n— Ousmane 🔧"
            else:
                return "No pending maintenance tasks! The house is in good shape. 🔧"
        
        return await super().chat(message)
