"""
MyCasa Pro - Agent Scheduler
============================

Schedule agents to run at specific times, like cron but for AI agents.
Inspired by LobeHub's scheduled runs feature.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class ScheduleFrequency(str, Enum):
    """How often a scheduled job runs"""
    ONCE = "once"           # Run once at specified time
    HOURLY = "hourly"       # Every hour
    DAILY = "daily"         # Once a day
    WEEKLY = "weekly"       # Once a week
    MONTHLY = "monthly"     # Once a month


class JobStatus(str, Enum):
    """Status of a scheduled job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ScheduledJob:
    """A scheduled agent run"""
    id: str
    name: str
    description: str
    agent: str  # Agent type to run
    task: str   # Task/prompt to give the agent
    frequency: ScheduleFrequency
    next_run: datetime
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    last_result: Optional[str] = None
    last_status: Optional[JobStatus] = None
    run_count: int = 0
    failure_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Schedule config
    hour: int = 9          # Hour of day (for daily/weekly/monthly)
    minute: int = 0        # Minute of hour
    day_of_week: int = 0   # 0=Monday (for weekly)
    day_of_month: int = 1  # Day of month (for monthly)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["next_run"] = self.next_run.isoformat() if self.next_run else None
        data["created_at"] = self.created_at.isoformat()
        data["last_run"] = self.last_run.isoformat() if self.last_run else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledJob":
        if data.get("next_run"):
            data["next_run"] = datetime.fromisoformat(data["next_run"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_run"):
            data["last_run"] = datetime.fromisoformat(data["last_run"])
        if data.get("frequency"):
            data["frequency"] = ScheduleFrequency(data["frequency"])
        if data.get("last_status"):
            data["last_status"] = JobStatus(data["last_status"])
        return cls(**data)
    
    def calculate_next_run(self) -> datetime:
        """Calculate the next run time based on frequency"""
        now = datetime.utcnow()
        
        if self.frequency == ScheduleFrequency.ONCE:
            # One-time jobs keep their original next_run
            return self.next_run
        
        elif self.frequency == ScheduleFrequency.HOURLY:
            # Next hour at specified minute
            next_run = now.replace(minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run
        
        elif self.frequency == ScheduleFrequency.DAILY:
            # Tomorrow at specified time
            next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        elif self.frequency == ScheduleFrequency.WEEKLY:
            # Next week on specified day
            days_ahead = self.day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
            return next_run
        
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Next month on specified day
            next_run = now.replace(day=self.day_of_month, hour=self.hour, minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                # Move to next month
                if now.month == 12:
                    next_run = next_run.replace(year=now.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=now.month + 1)
            return next_run
        
        return now + timedelta(hours=1)  # Default fallback


@dataclass
class JobRun:
    """Record of a single job execution"""
    id: str
    job_id: str
    job_name: str
    agent: str
    task: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return data


class AgentScheduler:
    """
    Manages scheduled agent runs.
    
    Features:
    - Create/update/delete scheduled jobs
    - Run jobs on schedule
    - Track job history
    - Persist jobs to disk
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        agent_runner: Optional[Callable] = None,
    ):
        self.storage_path = storage_path or Path.home() / ".mycasa" / "scheduler"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.jobs_file = self.storage_path / "jobs.json"
        self.history_file = self.storage_path / "history.json"
        
        self.jobs: Dict[str, ScheduledJob] = {}
        self.history: List[JobRun] = []
        self.agent_runner = agent_runner
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        self._load_jobs()
        self._load_history()
    
    def _load_jobs(self):
        """Load jobs from disk"""
        if self.jobs_file.exists():
            try:
                data = json.loads(self.jobs_file.read_text())
                for job_data in data:
                    job = ScheduledJob.from_dict(job_data)
                    self.jobs[job.id] = job
                logger.info(f"Loaded {len(self.jobs)} scheduled jobs")
            except Exception as e:
                logger.error(f"Failed to load jobs: {e}")
    
    def _save_jobs(self):
        """Save jobs to disk"""
        try:
            data = [job.to_dict() for job in self.jobs.values()]
            self.jobs_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
    
    def _load_history(self):
        """Load run history from disk"""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                # Keep only last 1000 runs
                self.history = data[-1000:]
            except Exception as e:
                logger.error(f"Failed to load history: {e}")
    
    def _save_history(self):
        """Save run history to disk"""
        try:
            self.history_file.write_text(json.dumps(self.history[-1000:], indent=2))
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def create_job(
        self,
        name: str,
        agent: str,
        task: str,
        frequency: ScheduleFrequency,
        description: str = "",
        hour: int = 9,
        minute: int = 0,
        day_of_week: int = 0,
        day_of_month: int = 1,
        config: Optional[Dict[str, Any]] = None,
    ) -> ScheduledJob:
        """Create a new scheduled job"""
        job = ScheduledJob(
            id=f"job_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            agent=agent,
            task=task,
            frequency=frequency,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            config=config or {},
            next_run=datetime.utcnow(),  # Will be calculated
        )
        
        # Calculate first run time
        job.next_run = job.calculate_next_run()
        
        self.jobs[job.id] = job
        self._save_jobs()
        
        logger.info(f"Created job {job.id}: {job.name} ({job.frequency.value})")
        return job
    
    def update_job(self, job_id: str, **updates) -> Optional[ScheduledJob]:
        """Update an existing job"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        # Recalculate next run if schedule changed
        if any(k in updates for k in ["frequency", "hour", "minute", "day_of_week", "day_of_month"]):
            job.next_run = job.calculate_next_run()
        
        self._save_jobs()
        return job
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID"""
        return self.jobs.get(job_id)
    
    def list_jobs(self, include_disabled: bool = False) -> List[ScheduledJob]:
        """List all jobs"""
        jobs = list(self.jobs.values())
        if not include_disabled:
            jobs = [j for j in jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.next_run)
    
    def get_due_jobs(self) -> List[ScheduledJob]:
        """Get jobs that are due to run"""
        now = datetime.utcnow()
        return [
            job for job in self.jobs.values()
            if job.enabled and job.next_run <= now
        ]
    
    def get_history(self, job_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get run history"""
        history = self.history
        if job_id:
            history = [h for h in history if h.get("job_id") == job_id]
        return history[-limit:]
    
    async def run_job(self, job: ScheduledJob) -> JobRun:
        """Execute a scheduled job"""
        run = JobRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            job_id=job.id,
            job_name=job.name,
            agent=job.agent,
            task=job.task,
            started_at=datetime.utcnow(),
            status=JobStatus.RUNNING,
        )
        
        logger.info(f"Running job {job.id}: {job.name}")
        
        try:
            # Run the agent
            if self.agent_runner:
                result = await self.agent_runner(job.agent, job.task, job.config)
                run.result = str(result)
                run.status = JobStatus.COMPLETED
            else:
                # No runner configured - just log
                run.result = f"[DRY RUN] Would run agent '{job.agent}' with task: {job.task}"
                run.status = JobStatus.COMPLETED
            
            job.last_status = JobStatus.COMPLETED
            job.run_count += 1
            
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            run.status = JobStatus.FAILED
            run.error = str(e)
            job.last_status = JobStatus.FAILED
            job.failure_count += 1
        
        run.completed_at = datetime.utcnow()
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
        
        # Update job
        job.last_run = run.completed_at
        job.last_result = run.result or run.error
        
        # For one-time jobs, disable after running
        if job.frequency == ScheduleFrequency.ONCE:
            job.enabled = False
        else:
            # Calculate next run
            job.next_run = job.calculate_next_run()
        
        # Save
        self._save_jobs()
        self.history.append(run.to_dict())
        self._save_history()
        
        return run
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Agent scheduler started")
        
        while self._running:
            try:
                due_jobs = self.get_due_jobs()
                
                for job in due_jobs:
                    await self.run_job(job)
                
                # Sleep for 30 seconds before checking again
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Agent scheduler stopped")
    
    def start(self):
        """Start the scheduler"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
    
    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        now = datetime.utcnow()
        enabled_jobs = [j for j in self.jobs.values() if j.enabled]
        
        return {
            "running": self._running,
            "total_jobs": len(self.jobs),
            "enabled_jobs": len(enabled_jobs),
            "due_jobs": len(self.get_due_jobs()),
            "next_job": min(
                (j.next_run for j in enabled_jobs),
                default=None
            ).isoformat() if enabled_jobs else None,
            "total_runs": len(self.history),
            "recent_failures": sum(
                1 for h in self.history[-20:]
                if h.get("status") == JobStatus.FAILED.value
            ),
        }


# Singleton instance
_scheduler: Optional[AgentScheduler] = None


def get_scheduler() -> AgentScheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AgentScheduler()
    return _scheduler


# Pre-built job templates
JOB_TEMPLATES = {
    "household_heartbeat": {
        "name": "Household Heartbeat",
        "description": "Run proactive household checks (inbox, calendar, bills, maintenance, security)",
        "agent": "heartbeat",
        "task": "Run household heartbeat checks and record findings.",
        "frequency": ScheduleFrequency.HOURLY,
        "minute": 5,
    },
    "memory_consolidation": {
        "name": "Memory Consolidation",
        "description": "Summarize recent daily notes into MEMORY.md",
        "agent": "heartbeat",
        "task": "Consolidate recent daily notes into long-term memory.",
        "frequency": ScheduleFrequency.DAILY,
        "hour": 2,
        "minute": 15,
        "config": {"action": "memory_consolidation"},
    },
    "daily_finance_review": {
        "name": "Daily Finance Review",
        "description": "Review recent transactions and budget status",
        "agent": "finance",
        "task": "Review yesterday's transactions, check budget categories, and flag any unusual spending.",
        "frequency": ScheduleFrequency.DAILY,
        "hour": 8,
        "minute": 0,
    },
    "weekly_maintenance_check": {
        "name": "Weekly Maintenance Check",
        "description": "Check for upcoming maintenance tasks",
        "agent": "maintenance",
        "task": "Review scheduled maintenance tasks for the week, check for any overdue items, and summarize what needs attention.",
        "frequency": ScheduleFrequency.WEEKLY,
        "hour": 9,
        "minute": 0,
        "day_of_week": 0,  # Monday
    },
    "daily_security_audit": {
        "name": "Daily Security Audit",
        "description": "Review security events and alerts",
        "agent": "security",
        "task": "Audit yesterday's security events, check for any anomalies, and verify all systems are healthy.",
        "frequency": ScheduleFrequency.DAILY,
        "hour": 7,
        "minute": 30,
    },
    "monthly_portfolio_review": {
        "name": "Monthly Portfolio Review",
        "description": "Deep dive into investment performance",
        "agent": "finance",
        "task": "Analyze portfolio performance for the past month, compare against benchmarks, review asset allocation, and suggest any rebalancing opportunities.",
        "frequency": ScheduleFrequency.MONTHLY,
        "hour": 10,
        "minute": 0,
        "day_of_month": 1,
    },
    "weekly_contractor_followup": {
        "name": "Weekly Contractor Follow-up",
        "description": "Check on pending contractor work",
        "agent": "contractors",
        "task": "Review any pending contractor tasks, check for projects awaiting quotes, and flag any overdue follow-ups needed.",
        "frequency": ScheduleFrequency.WEEKLY,
        "hour": 10,
        "minute": 0,
        "day_of_week": 4,  # Friday
    },
    "daily_bill_reminders": {
        "name": "Daily Bill Reminders",
        "description": "Check for bills due soon and send WhatsApp alerts",
        "agent": "reminders",
        "task": "Check for upcoming and overdue bills. Send WhatsApp alerts for urgent items.",
        "frequency": ScheduleFrequency.DAILY,
        "hour": 8,
        "minute": 30,
        "config": {"endpoint": "/api/reminders/check/bills"}
    },
    "morning_summary": {
        "name": "Morning Financial Summary",
        "description": "Send daily summary via WhatsApp",
        "agent": "reminders",
        "task": "Send morning summary with upcoming bills and task overview.",
        "frequency": ScheduleFrequency.DAILY,
        "hour": 7,
        "minute": 0,
        "config": {"endpoint": "/api/reminders/daily-summary"}
    },
    "task_reminders": {
        "name": "Task Reminders",
        "description": "Check for maintenance tasks due soon",
        "agent": "reminders",
        "task": "Check for upcoming maintenance tasks and send reminders.",
        "frequency": ScheduleFrequency.DAILY,
        "hour": 9,
        "minute": 0,
        "config": {"endpoint": "/api/reminders/check/tasks"}
    },
}
