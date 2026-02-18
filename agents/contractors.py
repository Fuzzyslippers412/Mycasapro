"""
MyCasa Pro - Contractors Agent
Vendor management, job scheduling, quote collection, execution tracking

Authority Model:
- MAY: create jobs, request quotes, collect details, send to Finance, update status
- MUST: route comms through Manager, get Finance approval, report changes, keep records
- MUST NOT: contact directly, approve payment, fabricate info, close without evidence
"""
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent
from database import get_db
from database.models import Contractor
from core.events import emit, emit_task_started, emit_task_completed, EventType


class JobStatus(Enum):
    """Contractor job lifecycle states"""
    PROPOSED = "proposed"        # Initial request recorded
    PENDING = "pending"          # Awaiting info or scheduling
    SCHEDULED = "scheduled"      # Confirmed date with contractor
    IN_PROGRESS = "in_progress"  # Work underway
    COMPLETED = "completed"      # Done with evidence
    BLOCKED = "blocked"          # Awaiting resolution
    CANCELLED = "cancelled"


class CostStatus(Enum):
    """Finance approval states"""
    UNREVIEWED = "unreviewed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContractorsAgent(BaseAgent):
    """
    Contractor coordination agent.
    
    Manages vendor relationships, job scheduling, cost approval flow,
    and execution tracking. All external communication routes through
    the Manager (Galidima).
    
    Flow:
    record → request info → normalize → finance review → schedule → track → verify → close
    """
    
    def __init__(self):
        super().__init__("contractors")
    
    def get_status(self) -> Dict[str, Any]:
        """Get contractors agent status summary"""
        with get_db() as db:
            # Count jobs by status
            from database.models import ContractorJob
            
            proposed = db.query(ContractorJob).filter(ContractorJob.status == JobStatus.PROPOSED.value).count()
            pending = db.query(ContractorJob).filter(ContractorJob.status == JobStatus.PENDING.value).count()
            scheduled = db.query(ContractorJob).filter(ContractorJob.status == JobStatus.SCHEDULED.value).count()
            in_progress = db.query(ContractorJob).filter(ContractorJob.status == JobStatus.IN_PROGRESS.value).count()
            completed = db.query(ContractorJob).filter(ContractorJob.status == JobStatus.COMPLETED.value).count()
            blocked = db.query(ContractorJob).filter(ContractorJob.status == JobStatus.BLOCKED.value).count()
            
            # Count contractors
            contractor_count = db.query(Contractor).count()
        
        active_jobs = proposed + pending + scheduled + in_progress
        
        return {
            "agent": "contractors",
            "status": "active",
            "metrics": {
                "proposed_jobs": proposed,
                "pending_jobs": pending,
                "scheduled_jobs": scheduled,
                "in_progress_jobs": in_progress,
                "completed_jobs": completed,
                "blocked_jobs": blocked,
                "active_jobs": active_jobs,
                "contractor_count": contractor_count,
                "issues": blocked  # Blocked jobs need attention
            },
            "last_check": datetime.now().isoformat()
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # JOB MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_job(
        self,
        description: str,
        scope: str = None,
        originating_request: str = None,  # "user", "maintenance", "project"
        request_id: int = None,  # Link to maintenance task or project
        contractor_role: str = None,  # "plumber", "electrician", etc.
        urgency: str = "medium",
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Create a new contractor job in PROPOSED status.
        
        This is step 1 of the flow - recording the request.
        Next step: request contractor info via Manager.
        """
        from database.models import ContractorJob
        
        emit_task_started(self.name, "create_job")
        
        with get_db() as db:
            job = ContractorJob(
                description=description,
                scope=scope,
                originating_request=originating_request or "user",
                request_id=request_id,
                contractor_role=contractor_role,
                urgency=urgency,
                status=JobStatus.PROPOSED.value,
                cost_status=CostStatus.UNREVIEWED.value,
                notes=notes,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(job)
            db.flush()
            job_id = job.id
            db.commit()
        
        self.log_action("job_created", json.dumps({
            "job_id": job_id,
            "description": description,
            "role": contractor_role
        }))
        
        emit_task_completed(self.name, "create_job", f"job-{job_id}")
        
        # Emit event for Manager
        emit(
            EventType.INFO,
            title="Contractor job created",
            message=f"Job #{job_id}: {description}. Need contractor details.",
            agent_id=self.name,
            metadata={"job_id": job_id, "needs": "contractor_info"}
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": JobStatus.PROPOSED.value,
            "next_action": "Request contractor info via Manager",
            "message": f"Job #{job_id} created. Ask Manager to get contractor details from Rakia."
        }
    
    def update_job_details(
        self,
        job_id: int,
        contractor_id: int = None,
        contractor_name: str = None,
        contractor_role: str = None,
        contact_method: str = None,
        proposed_start: date = None,
        proposed_end: date = None,
        estimated_cost: float = None,
        scope: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Update job with contractor details.
        
        After receiving info from Manager (via Rakia), record the details.
        If cost is provided, job moves to PENDING and triggers Finance review.
        """
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            # Update fields
            if contractor_id:
                job.contractor_id = contractor_id
            if contractor_name:
                job.contractor_name = contractor_name
            if contractor_role:
                job.contractor_role = contractor_role
            if contact_method:
                job.contact_method = contact_method
            if proposed_start:
                job.proposed_start = proposed_start
            if proposed_end:
                job.proposed_end = proposed_end
            if estimated_cost is not None:
                job.estimated_cost = estimated_cost
                job.cost_status = CostStatus.PENDING_APPROVAL.value
            if scope:
                job.scope = scope
            if notes:
                job.notes = (job.notes or "") + f"\n[{datetime.now().isoformat()[:10]}] {notes}"
            
            job.updated_at = datetime.utcnow()
            
            # If we have contractor and cost, move to PENDING
            if job.contractor_name and job.estimated_cost:
                job.status = JobStatus.PENDING.value
            
            db.commit()
            
            result = {
                "success": True,
                "job_id": job_id,
                "status": job.status,
                "cost_status": job.cost_status
            }
        
        self.log_action("job_updated", json.dumps({"job_id": job_id}))
        
        # If cost added, trigger Finance review
        if estimated_cost is not None:
            result["next_action"] = "Submit to Finance Manager for approval"
            result["message"] = f"Cost ${estimated_cost:.2f} recorded. Ready for Finance review."
        
        return result
    
    def submit_to_finance(self, job_id: int) -> Dict[str, Any]:
        """
        Submit job cost to Finance Manager for approval.
        
        Required before confirming any paid work.
        """
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            if not job.estimated_cost:
                return {"success": False, "error": "No cost estimate to submit"}
            
            # Build finance request (capture values before session closes)
            finance_request = {
                "job_id": job.id,
                "description": job.description,
                "scope": job.scope,
                "contractor": job.contractor_name,
                "role": job.contractor_role,
                "cost": job.estimated_cost,
                "cost_type": "one_time",  # Could be made configurable
                "urgency": job.urgency,
                "proposed_start": job.proposed_start.isoformat() if job.proposed_start else None,
                "proposed_end": job.proposed_end.isoformat() if job.proposed_end else None,
                "impact_if_delayed": self._assess_delay_impact(job)
            }
            
            # Capture for event emission
            job_description = job.description
            estimated_cost = job.estimated_cost
            
            job.cost_status = CostStatus.PENDING_APPROVAL.value
            job.updated_at = datetime.utcnow()
            db.commit()
        
        self.log_action("finance_submission", json.dumps({
            "job_id": job_id,
            "cost": finance_request["cost"]
        }))
        
        # Emit event for Finance Manager
        emit(
            EventType.INFO,
            title="Contractor cost approval needed",
            message=f"Job #{job_id}: {job_description} - ${estimated_cost:.2f}",
            agent_id=self.name,
            metadata={"type": "cost_approval_request", "request": finance_request}
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "finance_request": finance_request,
            "status": "pending_approval",
            "message": "Cost submitted to Finance Manager. Awaiting approval."
        }
    
    def record_finance_decision(
        self,
        job_id: int,
        approved: bool,
        reason: str = None,
        approved_amount: float = None
    ) -> Dict[str, Any]:
        """
        Record Finance Manager's decision on job cost.
        
        If approved: job ready for scheduling
        If rejected: job blocked with reason
        """
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            if approved:
                job.cost_status = CostStatus.APPROVED.value
                job.approved_cost = approved_amount or job.estimated_cost
                
                # Log approval
                approval_note = f"[FINANCE APPROVED] ${job.approved_cost:.2f}"
                if reason:
                    approval_note += f" - {reason}"
                job.notes = (job.notes or "") + f"\n{approval_note}"
                
                next_action = "Confirm scheduling with contractor via Manager"
                message = f"Finance approved ${job.approved_cost:.2f}. Ready to confirm with contractor."
            else:
                job.cost_status = CostStatus.REJECTED.value
                job.status = JobStatus.BLOCKED.value
                job.blocked_reason = reason or "Cost not approved by Finance"
                
                # Log rejection
                rejection_note = f"[FINANCE REJECTED] {reason or 'No reason provided'}"
                job.notes = (job.notes or "") + f"\n{rejection_note}"
                
                next_action = "Review options: negotiate cost, find alternative, or cancel"
                message = f"Finance rejected. Reason: {reason or 'Not specified'}. Job blocked."
            
            job.updated_at = datetime.utcnow()
            db.commit()
            
            status = job.status
            cost_status = job.cost_status
        
        self.log_action("finance_decision", json.dumps({
            "job_id": job_id,
            "approved": approved,
            "reason": reason
        }))
        
        return {
            "success": True,
            "job_id": job_id,
            "approved": approved,
            "status": status,
            "cost_status": cost_status,
            "next_action": next_action,
            "message": message
        }
    
    def confirm_scheduling(
        self,
        job_id: int,
        confirmed_start: date,
        confirmed_end: date = None,
        confirmation_evidence: str = None
    ) -> Dict[str, Any]:
        """
        Record confirmed scheduling with contractor.
        
        Requires Finance approval first. Moves job to SCHEDULED.
        """
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            # Verify Finance approval
            if job.cost_status != CostStatus.APPROVED.value and job.estimated_cost:
                return {
                    "success": False,
                    "error": "Cannot schedule - Finance approval required",
                    "cost_status": job.cost_status
                }
            
            job.confirmed_start = confirmed_start
            job.confirmed_end = confirmed_end
            job.status = JobStatus.SCHEDULED.value
            
            if confirmation_evidence:
                job.evidence = json.dumps({
                    "scheduling_confirmation": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "details": confirmation_evidence
                    }
                })
            
            job.updated_at = datetime.utcnow()
            db.commit()
        
        self.log_action("job_scheduled", json.dumps({
            "job_id": job_id,
            "start": confirmed_start.isoformat()
        }))
        
        emit(
            EventType.INFO,
            title="Contractor job scheduled",
            message=f"Job #{job_id} confirmed for {confirmed_start}",
            agent_id=self.name,
            metadata={"job_id": job_id, "status": "scheduled"}
        )
        
        # Create calendar event
        calendar_result = self._create_calendar_event(job_id, job.description, confirmed_start, contractor_name)
        
        return {
            "success": True,
            "job_id": job_id,
            "status": JobStatus.SCHEDULED.value,
            "confirmed_start": confirmed_start.isoformat(),
            "message": f"Job scheduled for {confirmed_start}",
            "calendar_event": calendar_result
        }

    def schedule_job(
        self,
        job_id: int,
        confirmed_start: date,
        confirmed_end: date = None,
        confirmation_evidence: str = None,
    ) -> Dict[str, Any]:
        """Alias for confirm_scheduling (skills API expects schedule_job)."""
        return self.confirm_scheduling(
            job_id=job_id,
            confirmed_start=confirmed_start,
            confirmed_end=confirmed_end,
            confirmation_evidence=confirmation_evidence,
        )
    
    def _create_calendar_event(
        self, 
        job_id: int, 
        description: str, 
        event_date: date,
        contractor_name: str = None
    ) -> Dict[str, Any]:
        """Create a Google Calendar event for a scheduled contractor job"""
        import subprocess
        
        title = f"🔧 Contractor: {description[:50]}"
        if contractor_name:
            title = f"🔧 {contractor_name}: {description[:40]}"
        
        # Format date for gog CLI
        start_time = f"{event_date.isoformat()}T09:00:00"
        end_time = f"{event_date.isoformat()}T17:00:00"
        
        try:
            result = subprocess.run(
                [
                    "gog", "calendar", "create",
                    "--title", title,
                    "--start", start_time,
                    "--end", end_time,
                    "--description", f"MyCasa Pro Job #{job_id}\n\n{description}"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"[{self.name}] Calendar event created for job #{job_id}")
                return {"success": True, "message": "Calendar event created"}
            else:
                self.logger.warning(f"[{self.name}] Calendar creation failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Calendar command timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "gog CLI not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_job(self, job_id: int, notes: str = None) -> Dict[str, Any]:
        """Mark job as in progress when work begins"""
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            job.status = JobStatus.IN_PROGRESS.value
            job.actual_start = date.today()
            if notes:
                job.notes = (job.notes or "") + f"\n[STARTED] {notes}"
            job.updated_at = datetime.utcnow()
            db.commit()
        
        self.log_action("job_started", json.dumps({"job_id": job_id}))
        
        emit(
            EventType.INFO,
            title="Contractor job started",
            message=f"Job #{job_id} work in progress",
            agent_id=self.name,
            metadata={"job_id": job_id, "status": "in_progress"}
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": JobStatus.IN_PROGRESS.value
        }
    
    def complete_job(
        self,
        job_id: int,
        actual_cost: float = None,
        completion_evidence: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Mark job as completed with evidence.
        
        Evidence is REQUIRED - no silent completions.
        """
        from database.models import ContractorJob
        
        if not completion_evidence:
            return {
                "success": False,
                "error": "Completion evidence required. Provide confirmation, photo, or invoice reference."
            }
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            job.status = JobStatus.COMPLETED.value
            job.actual_end = date.today()
            if actual_cost is not None:
                job.actual_cost = actual_cost
            
            # Record evidence
            existing_evidence = json.loads(job.evidence) if job.evidence else {}
            existing_evidence["completion"] = {
                "timestamp": datetime.utcnow().isoformat(),
                "details": completion_evidence,
                "actual_cost": actual_cost
            }
            job.evidence = json.dumps(existing_evidence)
            
            if notes:
                job.notes = (job.notes or "") + f"\n[COMPLETED] {notes}"
            
            job.updated_at = datetime.utcnow()
            db.commit()
            
            # Check for cost variance (capture approved_cost before session closes)
            cost_variance = None
            approved_cost_val = job.approved_cost
            if actual_cost and approved_cost_val:
                cost_variance = actual_cost - approved_cost_val
        
        self.log_action("job_completed", json.dumps({
            "job_id": job_id,
            "actual_cost": actual_cost
        }))
        
        emit(
            EventType.TASK_COMPLETED,
            title="Contractor job completed",
            message=f"Job #{job_id} finished",
            agent_id=self.name,
            task_id=f"job-{job_id}",
            task_type="contractor_job",
            metadata={"job_id": job_id, "actual_cost": actual_cost}
        )
        
        result = {
            "success": True,
            "job_id": job_id,
            "status": JobStatus.COMPLETED.value,
            "actual_cost": actual_cost,
            "message": "Job completed and verified"
        }
        
        if cost_variance and abs(cost_variance) > 0.01:
            result["cost_variance"] = cost_variance
            result["variance_note"] = f"Actual cost ${actual_cost:.2f} vs approved ${approved_cost_val:.2f}"
        
        return result
    
    def block_job(self, job_id: int, reason: str) -> Dict[str, Any]:
        """Block a job with reason, notify Manager"""
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return {"success": False, "error": "Job not found"}
            
            job.status = JobStatus.BLOCKED.value
            job.blocked_reason = reason
            job.notes = (job.notes or "") + f"\n[BLOCKED] {reason}"
            job.updated_at = datetime.utcnow()
            db.commit()
        
        self.log_action("job_blocked", json.dumps({"job_id": job_id, "reason": reason}))
        
        emit(
            EventType.WARNING,
            title="Contractor job blocked",
            message=f"Job #{job_id}: {reason}",
            agent_id=self.name,
            metadata={"job_id": job_id, "blocked_reason": reason}
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": JobStatus.BLOCKED.value,
            "blocked_reason": reason,
            "next_action": "Notify Manager to resolve: follow-up, alternative vendor, or defer"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get full job record"""
        from database.models import ContractorJob
        
        with get_db() as db:
            job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
            if not job:
                return None
            
            return self._job_to_dict(job)
    
    def get_jobs(
        self,
        status: str = None,
        cost_status: str = None,
        contractor_id: int = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get jobs with optional filters"""
        from database.models import ContractorJob
        
        with get_db() as db:
            query = db.query(ContractorJob)
            
            if status:
                query = query.filter(ContractorJob.status == status)
            if cost_status:
                query = query.filter(ContractorJob.cost_status == cost_status)
            if contractor_id:
                query = query.filter(ContractorJob.contractor_id == contractor_id)
            
            jobs = query.order_by(ContractorJob.updated_at.desc()).limit(limit).all()
            
            return [self._job_to_dict(j) for j in jobs]
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all non-completed, non-cancelled jobs"""
        from database.models import ContractorJob
        
        active_statuses = [
            JobStatus.PROPOSED.value,
            JobStatus.PENDING.value,
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value,
            JobStatus.BLOCKED.value
        ]
        
        with get_db() as db:
            jobs = db.query(ContractorJob).filter(
                ContractorJob.status.in_(active_statuses)
            ).order_by(ContractorJob.updated_at.desc()).all()
            
            return [self._job_to_dict(j) for j in jobs]
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get jobs needing action (for agent interface)"""
        tasks = []
        
        # Jobs needing info
        for job in self.get_jobs(status=JobStatus.PROPOSED.value):
            tasks.append({
                "type": "job_needs_info",
                "id": job["id"],
                "title": f"Get contractor details: {job['description'][:50]}",
                "priority": job.get("urgency", "medium"),
                "job": job
            })
        
        # Jobs awaiting Finance
        for job in self.get_jobs(cost_status=CostStatus.PENDING_APPROVAL.value):
            tasks.append({
                "type": "awaiting_finance",
                "id": job["id"],
                "title": f"Finance review: {job['description'][:50]}",
                "priority": "high",
                "job": job
            })
        
        # Blocked jobs
        for job in self.get_jobs(status=JobStatus.BLOCKED.value):
            tasks.append({
                "type": "blocked_job",
                "id": job["id"],
                "title": f"Blocked: {job['description'][:50]}",
                "priority": "high",
                "reason": job.get("blocked_reason"),
                "job": job
            })
        
        return tasks

    def get_jobs_needing_action(self) -> List[Dict[str, Any]]:
        """Alias for get_pending_tasks (skills API expects get_jobs_needing_action)."""
        return self.get_pending_tasks()
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a pending task (for agent interface)"""
        # Most tasks require human/Manager interaction
        return {
            "success": False,
            "error": "Contractor tasks require Manager coordination"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONTRACTOR DIRECTORY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_contractors(self, service_type: str = None) -> List[Dict[str, Any]]:
        """Get contractor directory"""
        with get_db() as db:
            query = db.query(Contractor)
            if service_type:
                query = query.filter(Contractor.service_type == service_type)
            
            contractors = query.order_by(Contractor.name).all()
            
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "company": c.company,
                    "phone": c.phone,
                    "email": c.email,
                    "service_type": c.service_type,
                    "hourly_rate": c.hourly_rate,
                    "rating": c.rating,
                    "last_service_date": c.last_service_date.isoformat() if c.last_service_date else None
                }
                for c in contractors
            ]
    
    def add_contractor(
        self,
        name: str,
        service_type: str,
        phone: str = None,
        email: str = None,
        company: str = None,
        hourly_rate: float = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """Add a new contractor to directory"""
        with get_db() as db:
            contractor = Contractor(
                name=name,
                service_type=service_type,
                phone=phone,
                email=email,
                company=company,
                hourly_rate=hourly_rate,
                notes=notes
            )
            db.add(contractor)
            db.flush()
            contractor_id = contractor.id
            db.commit()
        
        self.log_action("contractor_added", json.dumps({
            "id": contractor_id,
            "name": name,
            "type": service_type
        }))
        
        return {"success": True, "contractor_id": contractor_id}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHAT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary for Manager reporting.
        
        Answers: "Who's doing what, when, how much, and is it approved?"
        """
        from database.models import ContractorJob
        
        with get_db() as db:
            # Count by status
            status_counts = {}
            for status in JobStatus:
                count = db.query(ContractorJob).filter(
                    ContractorJob.status == status.value
                ).count()
                status_counts[status.value] = count
            
            # Get active jobs details
            active_jobs = self.get_active_jobs()
            
            # Calculate costs
            approved_total = db.query(ContractorJob).filter(
                ContractorJob.cost_status == CostStatus.APPROVED.value,
                ContractorJob.status != JobStatus.COMPLETED.value
            ).all()
            pending_approved_cost = sum(j.approved_cost or 0 for j in approved_total)
            
            pending_review = db.query(ContractorJob).filter(
                ContractorJob.cost_status == CostStatus.PENDING_APPROVAL.value
            ).all()
            pending_review_cost = sum(j.estimated_cost or 0 for j in pending_review)
        
        return {
            "summary": {
                "proposed": status_counts.get("proposed", 0),
                "pending": status_counts.get("pending", 0),
                "scheduled": status_counts.get("scheduled", 0),
                "in_progress": status_counts.get("in_progress", 0),
                "completed": status_counts.get("completed", 0),
                "blocked": status_counts.get("blocked", 0)
            },
            "costs": {
                "approved_uncommitted": pending_approved_cost,
                "pending_review": pending_review_cost
            },
            "active_jobs": active_jobs,
            "blocked_jobs": [j for j in active_jobs if j.get("status") == "blocked"],
            "needs_action": len(self.get_pending_tasks())
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _job_to_dict(self, job) -> Dict[str, Any]:
        """Convert job model to dictionary"""
        return {
            "id": job.id,
            "description": job.description,
            "scope": job.scope,
            "originating_request": job.originating_request,
            "request_id": job.request_id,
            "contractor_id": job.contractor_id,
            "contractor_name": job.contractor_name,
            "contractor_role": job.contractor_role,
            "contact_method": job.contact_method,
            "urgency": job.urgency,
            "status": job.status,
            "cost_status": job.cost_status,
            "estimated_cost": job.estimated_cost,
            "approved_cost": job.approved_cost,
            "actual_cost": job.actual_cost,
            "proposed_start": job.proposed_start.isoformat() if job.proposed_start else None,
            "proposed_end": job.proposed_end.isoformat() if job.proposed_end else None,
            "confirmed_start": job.confirmed_start.isoformat() if job.confirmed_start else None,
            "confirmed_end": job.confirmed_end.isoformat() if job.confirmed_end else None,
            "actual_start": job.actual_start.isoformat() if job.actual_start else None,
            "actual_end": job.actual_end.isoformat() if job.actual_end else None,
            "blocked_reason": job.blocked_reason,
            "evidence": json.loads(job.evidence) if job.evidence else None,
            "notes": job.notes,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None
        }
    
    def _assess_delay_impact(self, job) -> str:
        """Assess impact if job is delayed (for Finance review)"""
        urgency = job.urgency
        
        if urgency == "critical":
            return "High impact - immediate safety or functionality concern"
        elif urgency == "high":
            return "Significant impact - affects daily operations"
        elif urgency == "medium":
            return "Moderate impact - can wait short term"
        else:
            return "Low impact - can be deferred"
