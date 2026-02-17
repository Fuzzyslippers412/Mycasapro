"""
Contractor Agent
Handles contractor job workflow from proposal to completion
"""
from datetime import date
from typing import Dict, Any, Optional, List

from ..storage.repository import Repository
from ..core.schemas import ContractorJobCreate, Priority


class ContractorAgent:
    """
    Contractor Agent - manages contractor job lifecycle
    
    Workflow:
    1. User request -> Create job (proposed)
    2. Agent schedules with contractor -> (pending -> scheduled)
    3. Finance approves cost -> (cost_status: approved)
    4. Job starts -> (in_progress)
    5. Job completes -> (completed)
    """
    
    def __init__(self, repo: Repository):
        self.repo = repo
        self.agent_id = "contractor"
        
        # Known contractors (could be in database)
        self.contractors = {
            "juan": {
                "name": "Juan",
                "phone": "+12534312046",
                "roles": ["general", "deck", "carpentry"],
                "contact_via": "whatsapp"
            },
            "rakia": {
                "name": "Rakia Baldé",
                "phone": "+33782826145",
                "roles": ["cleaning", "house_assistant"],
                "contact_via": "whatsapp"
            }
        }
    
    def create_job(
        self,
        description: str,
        scope: Optional[str] = None,
        contractor_name: Optional[str] = None,
        contractor_role: Optional[str] = None,
        proposed_start: Optional[date] = None,
        proposed_end: Optional[date] = None,
        estimated_cost: Optional[float] = None,
        urgency: Priority = Priority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Create a new contractor job (proposed status).
        
        Step 1 of the workflow.
        """
        job_create = ContractorJobCreate(
            description=description,
            scope=scope,
            contractor_name=contractor_name,
            contractor_role=contractor_role,
            proposed_start=proposed_start,
            proposed_end=proposed_end,
            estimated_cost=estimated_cost,
            urgency=urgency
        )
        
        job = self.repo.create_contractor_job(job_create)
        
        # Determine next steps
        next_steps = []
        if not contractor_name:
            next_steps.append("Assign a contractor")
        if not proposed_start:
            next_steps.append("Set proposed dates")
        next_steps.append("Contact contractor to schedule")
        if estimated_cost:
            next_steps.append("Submit cost for finance approval")
        
        return {
            "job_id": job.id,
            "status": job.status,
            "description": description,
            "next_steps": next_steps,
            "correlation_id": job.correlation_id
        }
    
    def schedule_with_contractor(
        self,
        job_id: int,
        contractor_key: Optional[str] = None,
        confirmed_start: Optional[date] = None,
        confirmed_end: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Schedule job with contractor.
        
        Step 2: Contact contractor (via Rakia or directly) and confirm dates.
        """
        jobs = self.repo.get_contractor_jobs()
        job = next((j for j in jobs if j.id == job_id), None)
        
        if not job:
            return {"success": False, "error": "Job not found"}
        
        # Get contractor info
        contractor = None
        if contractor_key:
            contractor = self.contractors.get(contractor_key.lower())
        
        # Update job with scheduling info
        updates = {"status": "scheduled" if confirmed_start else "pending"}
        
        if contractor:
            updates["contractor_name"] = contractor["name"]
            updates["contact_method"] = f"{contractor['contact_via']}: {contractor['phone']}"
        
        if confirmed_start:
            updates["confirmed_start"] = confirmed_start
        if confirmed_end:
            updates["confirmed_end"] = confirmed_end
        
        self.repo.update_contractor_job(job_id, **updates)
        
        # Create scheduling event
        self.repo.create_event(
            event_type="job_scheduled",
            action=f"Scheduled job with {contractor['name'] if contractor else 'contractor'}",
            agent=self.agent_id,
            entity_type="contractor_job",
            entity_id=job_id,
            details={
                "contractor": contractor["name"] if contractor else None,
                "confirmed_start": confirmed_start.isoformat() if confirmed_start else None,
                "confirmed_end": confirmed_end.isoformat() if confirmed_end else None
            }
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": updates["status"],
            "contractor": contractor["name"] if contractor else None,
            "contact": contractor["phone"] if contractor else None,
            "next_steps": ["Submit cost for finance approval"] if job.estimated_cost else ["Get cost estimate", "Submit for approval"]
        }
    
    def submit_for_approval(self, job_id: int, estimated_cost: float) -> Dict[str, Any]:
        """
        Submit job cost to Finance Manager for approval.
        
        Step 3: Finance manager approves based on budgets.
        """
        from .finance import FinanceManager
        
        finance = FinanceManager(self.repo)
        
        # Update job with cost
        self.repo.update_contractor_job(
            job_id,
            estimated_cost=estimated_cost,
            cost_status="pending_approval"
        )
        
        # Request approval
        result = finance.approve_contractor_cost(job_id, estimated_cost)
        
        return result
    
    def start_job(self, job_id: int) -> Dict[str, Any]:
        """
        Mark job as in progress.
        
        Step 4: Job has started.
        """
        job = self.repo.update_contractor_job(
            job_id,
            status="in_progress",
            actual_start=date.today()
        )
        
        if not job:
            return {"success": False, "error": "Job not found"}
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "in_progress",
            "started_at": date.today().isoformat()
        }
    
    def complete_job(
        self,
        job_id: int,
        actual_cost: Optional[float] = None,
        evidence: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark job as complete.
        
        Step 5: Job is done.
        """
        job = self.repo.update_contractor_job(
            job_id,
            status="completed",
            actual_end=date.today(),
            actual_cost=actual_cost,
            evidence=evidence,
            notes=notes
        )
        
        if not job:
            return {"success": False, "error": "Job not found"}
        
        # If actual cost differs from approved, log it
        if actual_cost and job.approved_cost and abs(actual_cost - job.approved_cost) > 0.01:
            self.repo.create_event(
                event_type="cost_variance",
                action=f"Job completed with cost variance: approved ${job.approved_cost:.2f}, actual ${actual_cost:.2f}",
                agent=self.agent_id,
                entity_type="contractor_job",
                entity_id=job_id,
                details={
                    "approved_cost": job.approved_cost,
                    "actual_cost": actual_cost,
                    "variance": actual_cost - job.approved_cost
                }
            )
        
        # Update spend budget with actual cost
        if actual_cost:
            self.repo.update_budget_spend("monthly", actual_cost - (job.approved_cost or 0))
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "completed",
            "actual_cost": actual_cost,
            "completed_at": date.today().isoformat()
        }
    
    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get current status of a job"""
        jobs = self.repo.get_contractor_jobs()
        job = next((j for j in jobs if j.id == job_id), None)
        
        if not job:
            return None
        
        return {
            "job_id": job.id,
            "description": job.description,
            "status": job.status,
            "contractor_name": job.contractor_name,
            "estimated_cost": job.estimated_cost,
            "approved_cost": job.approved_cost,
            "actual_cost": job.actual_cost,
            "cost_status": job.cost_status,
            "proposed_start": job.proposed_start.isoformat() if job.proposed_start else None,
            "confirmed_start": job.confirmed_start.isoformat() if job.confirmed_start else None,
            "actual_start": job.actual_start.isoformat() if job.actual_start else None,
            "actual_end": job.actual_end.isoformat() if job.actual_end else None
        }
    
    def list_active_jobs(self) -> List[Dict[str, Any]]:
        """List all non-completed jobs"""
        jobs = self.repo.get_contractor_jobs()
        
        return [
            self.get_job_status(j.id)
            for j in jobs
            if j.status not in ["completed", "cancelled"]
        ]
