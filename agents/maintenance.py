"""
Home Maintenance Agent for MyCasa Pro
Responsible for tracking, scheduling, and executing home maintenance tasks.
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import sys
import re
import time
from dateutil import parser as date_parser
try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for older runtimes
    ZoneInfo = None

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent
from database import get_db
from database.models import (
    MaintenanceTask, Contractor, Project, HomeReading
)


class MaintenanceAgent(BaseAgent):
    """Agent responsible for home maintenance operations"""
    
    def __init__(self):
        super().__init__("maintenance")
        self.service_categories = [
            "cleaning", "yard", "plumbing", "electrical", "hvac",
            "appliance", "pest_control", "pool", "security", "general"
        ]
        self._backend_db_ready = False
    
    def _get_timezone(self) -> str:
        try:
            from core.settings_typed import get_settings_store
            settings = get_settings_store().get()
            return getattr(settings.system, "timezone", "America/Los_Angeles") or "America/Los_Angeles"
        except Exception:
            return "America/Los_Angeles"

    def _today(self) -> date:
        if ZoneInfo is None:
            return date.today()
        try:
            tz = ZoneInfo(self._get_timezone())
            return datetime.now(tz).date()
        except Exception:
            return date.today()
    
    def get_status(self) -> Dict[str, Any]:
        """Get maintenance agent status"""
        today = self._today()
        with get_db() as db:
            pending_tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending"
            ).count()
            
            overdue_tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.due_date < today
            ).count()
            
            upcoming_week = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.scheduled_date >= today,
                MaintenanceTask.scheduled_date <= today + timedelta(days=7)
            ).count()
            
            active_projects = db.query(Project).filter(
                Project.status == "in_progress"
            ).count()
            
            total_contractors = db.query(Contractor).count()
        
        return {
            "agent": "maintenance",
            "status": "active",
            "metrics": {
                "pending_tasks": pending_tasks,
                "overdue_tasks": overdue_tasks,
                "upcoming_this_week": upcoming_week,
                "active_projects": active_projects,
                "total_contractors": total_contractors,
                "issues": overdue_tasks  # Count overdue as issues
            },
            "last_check": datetime.now().isoformat()
        }
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending maintenance tasks"""
        with get_db() as db:
            tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status.in_(["pending", "in_progress"])
            ).order_by(MaintenanceTask.due_date.asc()).all()
            
            return [self._task_to_dict(t) for t in tasks]
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get overdue tasks"""
        today = self._today()
        with get_db() as db:
            tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.due_date < today
            ).all()
            return [self._task_to_dict(t) for t in tasks]
    
    def get_upcoming_tasks(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get tasks scheduled in the next N days"""
        today = self._today()
        with get_db() as db:
            tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.scheduled_date >= today,
                MaintenanceTask.scheduled_date <= today + timedelta(days=days)
            ).order_by(MaintenanceTask.scheduled_date.asc()).all()
            
            return [self._task_to_dict(t) for t in tasks]
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Mark a task as in progress or completed"""
        today = self._today()
        with get_db() as db:
            task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
            if not task:
                return {"success": False, "error": "Task not found"}
            
            if task.status == "pending":
                task.status = "in_progress"
            elif task.status == "in_progress":
                task.status = "completed"
                task.completed_date = today
                
                # Handle recurring tasks
                if task.recurrence != "none":
                    self._create_next_occurrence(db, task)
            
            self.log_action(
                f"task_status_change",
                f"Task {task_id} ({task.title}) -> {task.status}"
            )
            
            return {"success": True, "task": self._task_to_dict(task)}
    
    def create_task(
        self,
        title: str,
        description: str = None,
        category: str = "general",
        priority: str = "medium",
        scheduled_date: Union[date, str, None] = None,
        due_date: Union[date, str, None] = None,
        recurrence: str = "none",
        estimated_cost: float = None,
        contractor_id: int = None,
        notes: str = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new maintenance task"""
        scheduled_date = self._coerce_date(scheduled_date)
        due_date = self._coerce_date(due_date) or scheduled_date
        def _create():
            with get_db() as db:
                task = MaintenanceTask(
                    title=title,
                    description=description,
                    category=category,
                    priority=priority,
                    scheduled_date=scheduled_date,
                    due_date=due_date or scheduled_date,
                    recurrence=recurrence,
                    estimated_cost=estimated_cost,
                    contractor_id=contractor_id,
                    notes=notes,
                    conversation_id=conversation_id,
                )
                db.add(task)
                db.flush()
                
                self.log_action("task_created", f"Created task: {title}", db=db)
                
                return {"success": True, "task": self._task_to_dict(task)}

        return self._with_db_retry(_create)

    def get_tasks_from_db(self) -> List[Dict[str, Any]]:
        """Get all maintenance tasks (any status)."""
        with get_db() as db:
            tasks = db.query(MaintenanceTask).order_by(
                MaintenanceTask.status.asc(),
                MaintenanceTask.due_date.is_(None),
                MaintenanceTask.due_date.asc(),
            ).all()
            return [self._task_to_dict(t) for t in tasks]

    def complete_task(self, task_id: int, evidence: Optional[str] = None) -> Dict[str, Any]:
        """Mark a task complete."""
        def _complete():
            with get_db() as db:
                task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
                if not task:
                    return {"success": False, "error": "Task not found"}
                task.status = "completed"
                task.completed_date = self._today()
                if evidence:
                    task.notes = (task.notes or "") + f"\n{evidence}"
                self.log_action("task_completed", f"Completed task: {task_id}", db=db)
                return {"success": True, "task": self._task_to_dict(task)}
        return self._with_db_retry(_complete)

    def _coerce_date(self, value: Union[date, str, None]) -> Optional[date]:
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
            if modifier == "next" and delta == 0:
                delta = 7
            return today + timedelta(days=delta)

        match = re.search(r"\b(\d{4}-\d{1,2}-\d{1,2})\b", text)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except Exception:
                pass

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
            r"(?i)i need to (.+)",
            r"(?i)i have to (.+)",
            r"(?i)please (.+)",
            r"(?i)can you (.+)",
            r"(?i)could you (.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                title = re.split(r"\b(?:by|on|this|next)\b", title, 1, flags=re.IGNORECASE)[0].strip()
                if title:
                    return title
        return text

    def create_task_from_message(self, message: str, conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        msg_lower = message.lower()
        intent_keywords = [
            "remind",
            "reminder",
            "add a task",
            "add task",
            "schedule",
            "task reminder",
            "need to",
            "have to",
            "please",
            "can you",
            "could you",
            "clean",
            "fix",
            "repair",
            "replace",
            "inspect",
        ]
        if not any(k in msg_lower for k in intent_keywords):
            return None
        # Require either an explicit task word or a detectable date/weekday to reduce false positives.
        if "task" not in msg_lower and "remind" not in msg_lower:
            if self._extract_due_date(message) is None:
                return None
        title = self._extract_task_title(message)
        due_date = self._extract_due_date(message)
        task = self.add_task(
            title=title,
            description="Created from chat request",
            category="maintenance",
            priority="medium",
            due_date=due_date,
            conversation_id=conversation_id,
        )
        if not task or not task.get("id"):
            return {"success": False, "error": "Failed to create task"}
        return {
            "success": True,
            "task_id": task.get("id"),
            "title": task.get("title", title),
            "due_date": task.get("due_date"),
            "scheduled_date": task.get("scheduled_date"),
            "conversation_id": conversation_id,
        }
    
    def _create_next_occurrence(self, db, task: MaintenanceTask):
        """Create the next occurrence of a recurring task"""
        intervals = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "biweekly": timedelta(weeks=2),
            "monthly": timedelta(days=30),
            "quarterly": timedelta(days=90),
            "yearly": timedelta(days=365)
        }
        
        interval = intervals.get(task.recurrence)
        if not interval:
            return
        
        next_date = task.scheduled_date + interval if task.scheduled_date else date.today() + interval
        
        new_task = MaintenanceTask(
            title=task.title,
            description=task.description,
            category=task.category,
            priority=task.priority,
            scheduled_date=next_date,
            due_date=next_date,
            recurrence=task.recurrence,
            estimated_cost=task.estimated_cost,
            contractor_id=task.contractor_id,
            notes=task.notes,
            conversation_id=getattr(task, "conversation_id", None),
        )
        db.add(new_task)

    # ============ TASK API (for /api/tasks) ============

    def _status_to_db(self, status: Optional[str]) -> Optional[str]:
        if not status:
            return None
        mapping = {
            "todo": "pending",
            "in_progress": "in_progress",
            "completed": "completed",
            "cancelled": "cancelled",
        }
        return mapping.get(status, status)

    def _status_from_db(self, status: Optional[str]) -> str:
        mapping = {
            "pending": "todo",
            "in_progress": "in_progress",
            "completed": "completed",
            "cancelled": "cancelled",
        }
        return mapping.get(status or "pending", "todo")

    def _taskdb_to_dict(self, task: Any) -> Dict[str, Any]:
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "category": task.category or "general",
            "priority": task.priority or "medium",
            "status": self._status_from_db(task.status),
            "due_date": task.due_date,
            "assigned_to": task.assigned_agent or task.assigned_contractor,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_date,
        }

    def _ensure_backend_db(self) -> None:
        if self._backend_db_ready:
            return
        try:
            from backend.storage.database import init_db
            init_db()
            self._backend_db_ready = True
        except Exception:
            # If init fails, still let operations attempt; errors will surface on use.
            self._backend_db_ready = True

    def _with_db_retry(self, operation, retries: int = 3, base_delay: float = 0.2):
        """Retry small DB writes when SQLite is briefly locked."""
        from sqlalchemy.exc import OperationalError
        for attempt in range(retries):
            try:
                return operation()
            except OperationalError as exc:
                if "database is locked" not in str(exc).lower() or attempt >= retries - 1:
                    raise
                time.sleep(base_delay * (attempt + 1))

    def list_tasks(self, filters: Optional[Dict[str, Any]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with get_db() as db:
            query = db.query(MaintenanceTask)
            if filters:
                if filters.get("category"):
                    query = query.filter(MaintenanceTask.category == filters["category"])
                if filters.get("status"):
                    query = query.filter(MaintenanceTask.status == filters["status"])
                if filters.get("priority"):
                    query = query.filter(MaintenanceTask.priority == filters["priority"])
            tasks = (
                query.order_by(MaintenanceTask.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._task_to_dict(t) for t in tasks]

    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        category: str = "maintenance",
        priority: str = "medium",
        due_date: Optional[date] = None,
        assigned_to: Optional[str] = None,
        estimated_duration_hours: Optional[float] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        due_date = self._coerce_date(due_date)
        def _create():
            with get_db() as db:
                task = MaintenanceTask(
                    title=title,
                    description=description,
                    category=category,
                    priority=priority,
                    status="pending",
                    due_date=due_date,
                    conversation_id=conversation_id,
                )
                if estimated_duration_hours is not None:
                    task.notes = f"estimated_duration_hours={estimated_duration_hours}"
                db.add(task)
                db.flush()
                self.log_action("task_created", f"Created task: {title}")
                return self._task_to_dict(task)
        return self._with_db_retry(_create)

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
            if not task:
                return None
            return self._task_to_dict(task)

    def update_task(self, task_id: int, **updates: Any) -> Dict[str, Any]:
        def _update():
            with get_db() as db:
                task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
                if not task:
                    return {"error": "Task not found"}
                if updates.get("title") is not None:
                    task.title = updates["title"]
                if updates.get("description") is not None:
                    task.description = updates["description"]
                if updates.get("category") is not None:
                    task.category = updates["category"]
                if updates.get("priority") is not None:
                    task.priority = updates["priority"]
                if updates.get("due_date") is not None:
                    task.due_date = self._coerce_date(updates["due_date"])
                if updates.get("status") is not None:
                    task.status = updates["status"]
                if updates.get("estimated_duration_hours") is not None:
                    task.notes = f"estimated_duration_hours={updates['estimated_duration_hours']}"
                self.log_action("task_updated", f"Updated task: {task_id}")
                return self._task_to_dict(task)
        return self._with_db_retry(_update)

    def complete_task(self, task_id: int, completion_notes: Optional[str] = None) -> Dict[str, Any]:
        def _complete():
            with get_db() as db:
                task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
                if not task:
                    return {"error": "Task not found"}
                task.status = "completed"
                task.completed_date = self._today()
                if completion_notes:
                    task.notes = completion_notes
                self.log_action("task_completed", f"Completed task: {task_id}")
                return self._task_to_dict(task)
        return self._with_db_retry(_complete)

    def remove_task(self, task_id: int) -> Dict[str, Any]:
        def _remove():
            with get_db() as db:
                task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
                if not task:
                    return {"error": "Task not found"}
                db.delete(task)
                self.log_action("task_removed", f"Removed task: {task_id}", db=db)
                return {"success": True, "id": task_id}
        return self._with_db_retry(_remove)
    
    # ============ CONTRACTORS ============
    
    def get_contractors(self, service_type: str = None) -> List[Dict[str, Any]]:
        """Get all contractors, optionally filtered by service type"""
        with get_db() as db:
            query = db.query(Contractor)
            if service_type:
                query = query.filter(Contractor.service_type == service_type)
            contractors = query.order_by(Contractor.name).all()
            
            return [self._contractor_to_dict(c) for c in contractors]
    
    def add_contractor(
        self,
        name: str,
        phone: str = None,
        email: str = None,
        company: str = None,
        service_type: str = "general",
        hourly_rate: float = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """Add a new contractor"""
        with get_db() as db:
            contractor = Contractor(
                name=name,
                phone=phone,
                email=email,
                company=company,
                service_type=service_type,
                hourly_rate=hourly_rate,
                notes=notes
            )
            db.add(contractor)
            db.flush()
            
            self.log_action("contractor_added", f"Added contractor: {name}")
            
            return {"success": True, "contractor": self._contractor_to_dict(contractor)}
    
    # ============ PROJECTS ============
    
    def get_projects(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all projects"""
        with get_db() as db:
            query = db.query(Project)
            if status:
                query = query.filter(Project.status == status)
            projects = query.order_by(Project.created_at.desc()).all()
            
            return [self._project_to_dict(p) for p in projects]
    
    def create_project(
        self,
        name: str,
        description: str = None,
        category: str = "renovation",
        budget: float = None,
        start_date: date = None,
        target_end_date: date = None
    ) -> Dict[str, Any]:
        """Create a new project"""
        with get_db() as db:
            project = Project(
                name=name,
                description=description,
                category=category,
                budget=budget,
                start_date=start_date,
                target_end_date=target_end_date
            )
            db.add(project)
            db.flush()
            
            self.log_action("project_created", f"Created project: {name}")
            
            return {"success": True, "project": self._project_to_dict(project)}
    
    # ============ HOME READINGS ============
    
    def log_reading(
        self,
        reading_type: str,
        value: float,
        unit: str,
        location: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """Log a home reading (water quality, energy, etc.)"""
        with get_db() as db:
            reading = HomeReading(
                reading_type=reading_type,
                value=value,
                unit=unit,
                location=location,
                notes=notes
            )
            db.add(reading)
            db.flush()
            
            self.log_action("reading_logged", f"{reading_type}: {value} {unit}")
            
            return {"success": True, "reading_id": reading.id}
    
    def get_readings(self, reading_type: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent home readings"""
        with get_db() as db:
            query = db.query(HomeReading)
            if reading_type:
                query = query.filter(HomeReading.reading_type == reading_type)
            
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(HomeReading.recorded_at >= cutoff)
            
            readings = query.order_by(HomeReading.recorded_at.desc()).all()
            
            return [
                {
                    "id": r.id,
                    "type": r.reading_type,
                    "value": r.value,
                    "unit": r.unit,
                    "location": r.location,
                    "notes": r.notes,
                    "recorded_at": r.recorded_at.isoformat()
                }
                for r in readings
            ]
    
    # ============ HELPERS ============
    
    def _task_to_dict(self, task: MaintenanceTask) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "category": task.category,
            "priority": task.priority,
            "status": task.status,
            "conversation_id": getattr(task, "conversation_id", None),
            "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "completed_date": task.completed_date.isoformat() if task.completed_date else None,
            "recurrence": task.recurrence,
            "estimated_cost": task.estimated_cost,
            "actual_cost": task.actual_cost,
            "contractor_id": task.contractor_id,
            "notes": task.notes,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "completed_at": task.completed_date.isoformat() if task.completed_date else None,
        }
    
    def _contractor_to_dict(self, contractor: Contractor) -> Dict[str, Any]:
        """Convert contractor to dictionary"""
        return {
            "id": contractor.id,
            "name": contractor.name,
            "company": contractor.company,
            "phone": contractor.phone,
            "email": contractor.email,
            "service_type": contractor.service_type,
            "hourly_rate": contractor.hourly_rate,
            "rating": contractor.rating,
            "notes": contractor.notes,
            "last_service_date": contractor.last_service_date.isoformat() if contractor.last_service_date else None
        }
    
    def _project_to_dict(self, project: Project) -> Dict[str, Any]:
        """Convert project to dictionary"""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "category": project.category,
            "status": project.status,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "target_end_date": project.target_end_date.isoformat() if project.target_end_date else None,
            "actual_end_date": project.actual_end_date.isoformat() if project.actual_end_date else None,
            "budget": project.budget,
            "spent": project.spent,
            "notes": project.notes
        }
    
    # ============ CHAT ============
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for maintenance-related alerts"""
        alerts = []
        
        with get_db() as db:
            # Overdue tasks
            overdue = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.due_date < date.today()
            ).all()
            
            for task in overdue:
                days_overdue = (date.today() - task.due_date).days
                severity = "high" if task.priority in ["urgent", "high"] else "medium"
                
                alerts.append({
                    "type": "overdue_task",
                    "severity": severity,
                    "title": f"Overdue: {task.title}",
                    "message": f"Was due {days_overdue} days ago",
                    "action": f"complete_task:{task.id}"
                })
            
            # Tasks due soon (next 3 days) that are high priority
            upcoming = date.today() + timedelta(days=3)
            due_soon = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending",
                MaintenanceTask.due_date >= date.today(),
                MaintenanceTask.due_date <= upcoming,
                MaintenanceTask.priority.in_(["urgent", "high"])
            ).all()
            
            for task in due_soon:
                days_until = (task.due_date - date.today()).days
                alerts.append({
                    "type": "task_due_soon",
                    "severity": "medium",
                    "title": f"Due Soon: {task.title}",
                    "message": f"Due in {days_until} day(s)",
                    "action": f"view_task:{task.id}"
                })
        
        return alerts
