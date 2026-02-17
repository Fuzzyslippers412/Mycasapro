"""
Projects Agent for MyCasa Pro
Manages renovations, improvements, and multi-phase home projects.
"""
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent
from database import get_db
from database.models import Project, ProjectMilestone


class ProjectsAgent(BaseAgent):
    """
    Project coordinator for MyCasa Pro.
    
    Responsibilities:
    - Manage multi-phase home projects
    - Track milestones and timelines
    - Monitor project budgets
    - Identify blockers and risks
    """
    
    def __init__(self):
        super().__init__("projects")
    
    def get_status(self) -> Dict[str, Any]:
        """Get projects agent status"""
        with get_db() as db:
            total_projects = db.query(Project).count()
            active_projects = db.query(Project).filter(
                Project.status == "in_progress"
            ).count()
            planning_projects = db.query(Project).filter(
                Project.status == "planning"
            ).count()
            
            # Check for overdue milestones
            overdue_milestones = db.query(ProjectMilestone).filter(
                ProjectMilestone.completed == False,
                ProjectMilestone.due_date < date.today()
            ).count()
            
            # Budget status
            projects = db.query(Project).filter(
                Project.status.in_(["in_progress", "planning"])
            ).all()
            
            total_budget = sum(p.budget or 0 for p in projects)
            total_spent = sum(p.spent or 0 for p in projects)
        
        return {
            "agent": "projects",
            "status": "active",
            "metrics": {
                "total_projects": total_projects,
                "active_projects": active_projects,
                "planning_projects": planning_projects,
                "overdue_milestones": overdue_milestones,
                "total_budget": total_budget,
                "total_spent": total_spent,
                "issues": overdue_milestones
            }
        }
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending project tasks (overdue milestones, budget alerts)"""
        tasks = []
        
        with get_db() as db:
            # Overdue milestones
            overdue = db.query(ProjectMilestone).join(Project).filter(
                ProjectMilestone.completed == False,
                ProjectMilestone.due_date < date.today(),
                Project.status == "in_progress"
            ).all()
            
            for m in overdue:
                tasks.append({
                    "id": m.id,
                    "type": "overdue_milestone",
                    "title": f"Overdue: {m.title}",
                    "project_id": m.project_id,
                    "due_date": m.due_date.isoformat(),
                    "days_overdue": (date.today() - m.due_date).days,
                    "priority": "high"
                })
            
            # Projects over budget
            over_budget = db.query(Project).filter(
                Project.status == "in_progress",
                Project.spent > Project.budget
            ).all()
            
            for p in over_budget:
                tasks.append({
                    "id": p.id,
                    "type": "over_budget",
                    "title": f"Over budget: {p.name}",
                    "budget": p.budget,
                    "spent": p.spent,
                    "overage": p.spent - p.budget,
                    "priority": "high"
                })
        
        return tasks
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a project task"""
        self.log_action("execute_task", f"Task {task_id} execution requested")
        return {"success": True, "message": "Task acknowledged"}
    
    # ============ PROJECT MANAGEMENT ============
    
    def get_projects(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all projects, optionally filtered by status"""
        with get_db() as db:
            query = db.query(Project)
            if status:
                query = query.filter(Project.status == status)
            
            projects = query.order_by(Project.created_at.desc()).all()
            
            result = []
            for p in projects:
                milestones = db.query(ProjectMilestone).filter(
                    ProjectMilestone.project_id == p.id
                ).all()
                
                completed_milestones = len([m for m in milestones if m.completed])
                total_milestones = len(milestones)
                progress = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
                
                result.append({
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "status": p.status,
                    "start_date": p.start_date.isoformat() if p.start_date else None,
                    "target_end_date": p.target_end_date.isoformat() if p.target_end_date else None,
                    "budget": p.budget,
                    "spent": p.spent,
                    "budget_remaining": (p.budget or 0) - (p.spent or 0),
                    "budget_pct": ((p.spent or 0) / p.budget * 100) if p.budget else 0,
                    "progress": progress,
                    "milestones_completed": completed_milestones,
                    "milestones_total": total_milestones,
                    "notes": p.notes
                })
            
            return result
    
    def get_active_projects(self) -> List[Dict[str, Any]]:
        """Get only active (in_progress) projects"""
        return self.get_projects(status="in_progress")
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get a single project with full details"""
        with get_db() as db:
            p = db.query(Project).filter(Project.id == project_id).first()
            if not p:
                return None
            
            milestones = db.query(ProjectMilestone).filter(
                ProjectMilestone.project_id == project_id
            ).order_by(ProjectMilestone.due_date.asc()).all()
            
            completed_milestones = len([m for m in milestones if m.completed])
            progress = (completed_milestones / len(milestones) * 100) if milestones else 0
            
            return {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "status": p.status,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "target_end_date": p.target_end_date.isoformat() if p.target_end_date else None,
                "actual_end_date": p.actual_end_date.isoformat() if p.actual_end_date else None,
                "budget": p.budget,
                "spent": p.spent,
                "budget_remaining": (p.budget or 0) - (p.spent or 0),
                "progress": progress,
                "notes": p.notes,
                "milestones": [
                    {
                        "id": m.id,
                        "title": m.title,
                        "description": m.description,
                        "due_date": m.due_date.isoformat() if m.due_date else None,
                        "completed": m.completed,
                        "completed_date": m.completed_date.isoformat() if m.completed_date else None
                    }
                    for m in milestones
                ]
            }
    
    def create_project(
        self,
        name: str,
        description: str = None,
        category: str = "improvement",
        budget: float = None,
        target_end_date: date = None,
        milestones: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new project"""
        with get_db() as db:
            project = Project(
                name=name,
                description=description,
                category=category,
                status="planning",
                budget=budget,
                target_end_date=target_end_date,
                spent=0
            )
            db.add(project)
            db.flush()
            project_id = project.id
            
            # Add milestones if provided
            if milestones:
                for m in milestones:
                    milestone = ProjectMilestone(
                        project_id=project_id,
                        title=m["title"],
                        description=m.get("description"),
                        due_date=m.get("due_date"),
                        completed=False
                    )
                    db.add(milestone)
        
        self.log_action("create_project", f"Created project: {name}")
        self.append_memory("Active Projects", f"Created: {name} (budget: ${budget or 'TBD'})")
        
        return {"success": True, "project_id": project_id}
    
    def update_project(self, project_id: int, **updates) -> Dict[str, Any]:
        """Update project details"""
        with get_db() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "Project not found"}
            
            for key, value in updates.items():
                if hasattr(project, key) and value is not None:
                    setattr(project, key, value)
        
        self.log_action("update_project", f"Updated project {project_id}")
        return {"success": True}
    
    def update_project_status(self, project_id: int, status: str) -> Dict[str, Any]:
        """Change project status"""
        valid_statuses = ["planning", "in_progress", "on_hold", "completed"]
        if status not in valid_statuses:
            return {"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}
        
        with get_db() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "Project not found"}
            
            old_status = project.status
            project.status = status
            
            if status == "in_progress" and not project.start_date:
                project.start_date = date.today()
            elif status == "completed":
                project.actual_end_date = date.today()
        
        self.log_action("update_status", f"Project {project_id}: {old_status} → {status}")
        return {"success": True}
    
    def add_spending(self, project_id: int, amount: float, description: str = None) -> Dict[str, Any]:
        """Record spending on a project"""
        with get_db() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "Project not found"}
            
            project.spent = (project.spent or 0) + amount
            
            # Check budget
            budget_pct = (project.spent / project.budget * 100) if project.budget else 0
            over_budget = project.spent > (project.budget or float('inf'))
        
        self.log_action("add_spending", f"Project {project_id}: +${amount:.2f}")
        
        # Alert if over budget or approaching
        if over_budget:
            self.report_event("project_over_budget", {
                "project_id": project_id,
                "budget": project.budget,
                "spent": project.spent
            }, severity="high")
        elif budget_pct >= 90:
            self.report_event("project_budget_warning", {
                "project_id": project_id,
                "budget": project.budget,
                "spent": project.spent,
                "pct": budget_pct
            }, severity="medium")
        
        return {"success": True, "new_total": project.spent, "budget_pct": budget_pct}
    
    # ============ MILESTONE MANAGEMENT ============
    
    def add_milestone(
        self,
        project_id: int,
        title: str,
        description: str = None,
        due_date: date = None
    ) -> Dict[str, Any]:
        """Add a milestone to a project"""
        with get_db() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"success": False, "error": "Project not found"}
            
            milestone = ProjectMilestone(
                project_id=project_id,
                title=title,
                description=description,
                due_date=due_date,
                completed=False
            )
            db.add(milestone)
            db.flush()
            milestone_id = milestone.id
        
        self.log_action("add_milestone", f"Added milestone to project {project_id}: {title}")
        return {"success": True, "milestone_id": milestone_id}
    
    def complete_milestone(self, milestone_id: int) -> Dict[str, Any]:
        """Mark a milestone as complete"""
        with get_db() as db:
            milestone = db.query(ProjectMilestone).filter(
                ProjectMilestone.id == milestone_id
            ).first()
            if not milestone:
                return {"success": False, "error": "Milestone not found"}
            
            milestone.completed = True
            milestone.completed_date = date.today()
            
            project_id = milestone.project_id
            title = milestone.title
        
        self.log_action("complete_milestone", f"Completed: {title}")
        return {"success": True}
    
    def get_upcoming_milestones(self, days: int = 14) -> List[Dict[str, Any]]:
        """Get milestones due in the next N days"""
        cutoff = date.today() + timedelta(days=days)
        
        with get_db() as db:
            milestones = db.query(ProjectMilestone).join(Project).filter(
                ProjectMilestone.completed == False,
                ProjectMilestone.due_date <= cutoff,
                Project.status == "in_progress"
            ).order_by(ProjectMilestone.due_date.asc()).all()
            
            return [
                {
                    "id": m.id,
                    "title": m.title,
                    "project_id": m.project_id,
                    "due_date": m.due_date.isoformat() if m.due_date else None,
                    "days_until_due": (m.due_date - date.today()).days if m.due_date else None
                }
                for m in milestones
            ]
    
    # ============ CHAT ============
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for project-related alerts"""
        alerts = []
        
        with get_db() as db:
            # Overdue milestones
            overdue = db.query(ProjectMilestone).join(Project).filter(
                ProjectMilestone.completed == False,
                ProjectMilestone.due_date < date.today(),
                Project.status == "in_progress"
            ).count()
            
            if overdue > 0:
                alerts.append({
                    "type": "overdue_milestones",
                    "severity": "high",
                    "title": f"{overdue} project milestone(s) overdue",
                    "message": "Review project timelines"
                })
            
            # Projects over budget
            over_budget = db.query(Project).filter(
                Project.status == "in_progress",
                Project.spent > Project.budget
            ).count()
            
            if over_budget > 0:
                alerts.append({
                    "type": "over_budget",
                    "severity": "high",
                    "title": f"{over_budget} project(s) over budget",
                    "message": "Review project spending"
                })
            
            # Projects nearing budget (>80%)
            nearing_budget = db.query(Project).filter(
                Project.status == "in_progress",
                Project.budget > 0,
                Project.spent > Project.budget * 0.8,
                Project.spent <= Project.budget
            ).count()
            
            if nearing_budget > 0:
                alerts.append({
                    "type": "budget_warning",
                    "severity": "medium",
                    "title": f"{nearing_budget} project(s) at >80% budget",
                    "message": "Monitor spending carefully"
                })
        
        return alerts
    
    # ============ REPORTING ============
    
    def get_project_summary(self) -> Dict[str, Any]:
        """Get a summary of all projects"""
        projects = self.get_projects()
        
        by_status = {
            "planning": [],
            "in_progress": [],
            "on_hold": [],
            "completed": []
        }
        
        for p in projects:
            by_status.get(p["status"], []).append(p)
        
        total_budget = sum(p["budget"] or 0 for p in projects if p["status"] != "completed")
        total_spent = sum(p["spent"] or 0 for p in projects if p["status"] != "completed")
        
        return {
            "by_status": by_status,
            "counts": {status: len(items) for status, items in by_status.items()},
            "total_budget": total_budget,
            "total_spent": total_spent,
            "budget_remaining": total_budget - total_spent
        }
