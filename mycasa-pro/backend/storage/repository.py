"""
MyCasa Pro Data Repository
Centralized data access layer
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import (
    UserSettingsDB, ManagerSettingsDB, BudgetPolicyDB, IncomeSourceDB,
    TransactionDB, TaskDB, ContractorJobDB, EventDB, CostRecordDB,
    InboxMessageDB, ApprovalDB
)
from ..core.schemas import (
    TaskCreate, TaskUpdate, TaskStatus, Transaction, TransactionIngest, ContractorJobCreate,
    CostRecord, CostSummary, IncomeSource
)
from ..core.utils import generate_correlation_id, log_action


class Repository:
    """Centralized data access repository"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============ SETTINGS ============
    
    def get_user_settings(self) -> Optional[UserSettingsDB]:
        return self.db.query(UserSettingsDB).first()
    
    def update_user_settings(self, **kwargs) -> UserSettingsDB:
        settings = self.get_user_settings()
        if not settings:
            settings = UserSettingsDB(user_id="lamido")
            self.db.add(settings)
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.updated_at = datetime.utcnow()
        self.db.commit()
        return settings
    
    def get_manager_settings(self, manager_id: str) -> Optional[ManagerSettingsDB]:
        return self.db.query(ManagerSettingsDB).filter(
            ManagerSettingsDB.manager_id == manager_id
        ).first()
    
    def update_manager_settings(self, manager_id: str, **kwargs) -> ManagerSettingsDB:
        settings = self.get_manager_settings(manager_id)
        if not settings:
            settings = ManagerSettingsDB(manager_id=manager_id)
            self.db.add(settings)
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.updated_at = datetime.utcnow()
        self.db.commit()
        return settings
    
    # ============ BUDGETS ============
    
    def get_budget(self, budget_type: str) -> Optional[BudgetPolicyDB]:
        return self.db.query(BudgetPolicyDB).filter(
            BudgetPolicyDB.budget_type == budget_type,
            BudgetPolicyDB.is_active == True
        ).first()
    
    def get_all_budgets(self) -> List[BudgetPolicyDB]:
        return self.db.query(BudgetPolicyDB).filter(
            BudgetPolicyDB.is_active == True
        ).all()
    
    def update_budget_spend(self, budget_type: str, amount: float) -> BudgetPolicyDB:
        budget = self.get_budget(budget_type)
        if budget:
            budget.current_spend += amount
            budget.updated_at = datetime.utcnow()
            self.db.commit()
        return budget
    
    def reset_budget_period(self, budget_type: str) -> BudgetPolicyDB:
        budget = self.get_budget(budget_type)
        if budget:
            budget.current_spend = 0
            budget.period_start = date.today()
            budget.updated_at = datetime.utcnow()
            self.db.commit()
        return budget
    
    def check_budget_status(self, budget_type: str, proposed_amount: float = 0) -> Dict[str, Any]:
        """Check budget status and return warnings/blocks"""
        budget = self.get_budget(budget_type)
        if not budget:
            return {"status": "no_budget", "can_proceed": True}
        
        current = budget.current_spend
        proposed_total = current + proposed_amount
        limit = budget.limit_amount
        pct = proposed_total / limit if limit > 0 else 0
        
        result = {
            "budget_type": budget_type,
            "current_spend": current,
            "proposed_amount": proposed_amount,
            "proposed_total": proposed_total,
            "limit": limit,
            "pct_used": round(pct * 100, 1),
            "remaining": limit - current,
            "can_proceed": True,
            "warnings": []
        }
        
        if pct >= 1.0:
            result["warnings"].append(f"EXCEEDED: {budget_type} budget at {result['pct_used']}%")
            if budget.enforce_hard_cap:
                result["can_proceed"] = False
                result["block_reason"] = "Budget exceeded - requires override"
        elif pct >= 0.85:
            result["warnings"].append(f"CRITICAL: {budget_type} budget at {result['pct_used']}%")
        elif pct >= 0.70:
            result["warnings"].append(f"WARNING: {budget_type} budget at {result['pct_used']}%")
        
        return result
    
    # ============ INCOME SOURCES ============
    
    def get_primary_income_source(self) -> Optional[IncomeSourceDB]:
        return self.db.query(IncomeSourceDB).filter(
            IncomeSourceDB.is_primary == True,
            IncomeSourceDB.is_active == True
        ).first()
    
    def create_income_source(self, source: IncomeSource) -> IncomeSourceDB:
        db_source = IncomeSourceDB(**source.model_dump(exclude={"id"}))
        self.db.add(db_source)
        self.db.commit()
        return db_source
    
    # ============ TRANSACTIONS ============
    
    def create_transaction(self, txn: Transaction) -> TransactionDB:
        correlation_id = txn.correlation_id or generate_correlation_id()
        db_txn = TransactionDB(
            correlation_id=correlation_id,
            **txn.model_dump(exclude={"id", "correlation_id", "created_at"})
        )
        self.db.add(db_txn)
        self.db.commit()
        
        log_action("transaction_created", {
            "id": db_txn.id,
            "amount": db_txn.amount,
            "merchant": db_txn.merchant
        }, correlation_id)
        
        return db_txn
    
    def ingest_transactions(self, ingest: TransactionIngest) -> Dict[str, Any]:
        """Bulk ingest transactions with deduplication"""
        created = 0
        skipped = 0
        
        for txn in ingest.transactions:
            # Simple dedup by amount + date + merchant
            if ingest.deduplicate:
                existing = self.db.query(TransactionDB).filter(
                    TransactionDB.amount == txn.amount,
                    TransactionDB.date == txn.date,
                    TransactionDB.merchant == txn.merchant
                ).first()
                if existing:
                    skipped += 1
                    continue
            
            self.create_transaction(txn)
            created += 1
        
        return {"created": created, "skipped": skipped, "total": len(ingest.transactions)}
    
    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[TransactionDB]:
        query = self.db.query(TransactionDB)
        
        if start_date:
            query = query.filter(TransactionDB.date >= start_date)
        if end_date:
            query = query.filter(TransactionDB.date <= end_date)
        if category:
            query = query.filter(TransactionDB.consumption_category == category)
        
        return query.order_by(TransactionDB.date.desc()).limit(limit).all()
    
    def get_spend_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get spending summary for the last N days"""
        start_date = date.today() - timedelta(days=days)
        
        # Total spend (excluding internal transfers)
        total = self.db.query(func.sum(TransactionDB.amount)).filter(
            TransactionDB.date >= start_date,
            TransactionDB.is_internal_transfer == False
        ).scalar() or 0
        
        # By category
        by_category = {}
        category_rows = self.db.query(
            TransactionDB.consumption_category,
            func.sum(TransactionDB.amount)
        ).filter(
            TransactionDB.date >= start_date,
            TransactionDB.is_internal_transfer == False
        ).group_by(TransactionDB.consumption_category).all()
        
        for cat, amount in category_rows:
            by_category[cat or "uncategorized"] = amount
        
        # By payment rail
        by_rail = {}
        rail_rows = self.db.query(
            TransactionDB.payment_rail,
            func.sum(TransactionDB.amount)
        ).filter(
            TransactionDB.date >= start_date,
            TransactionDB.is_internal_transfer == False
        ).group_by(TransactionDB.payment_rail).all()
        
        for rail, amount in rail_rows:
            by_rail[rail or "unknown"] = amount
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "total_spend": total,
            "avg_daily": round(total / days, 2) if days > 0 else 0,
            "by_category": by_category,
            "by_payment_rail": by_rail,
            "transaction_count": self.db.query(TransactionDB).filter(
                TransactionDB.date >= start_date
            ).count()
        }
    
    # ============ TASKS ============
    
    def create_task(self, task: TaskCreate) -> TaskDB:
        correlation_id = generate_correlation_id()
        db_task = TaskDB(
            correlation_id=correlation_id,
            **task.model_dump()
        )
        self.db.add(db_task)
        self.db.commit()
        
        self.create_event(
            event_type="task_created",
            action=f"Created task: {task.title}",
            entity_type="task",
            entity_id=db_task.id,
            correlation_id=correlation_id
        )
        
        return db_task
    
    def update_task(self, task_id: int, update: TaskUpdate) -> Optional[TaskDB]:
        task = self.db.query(TaskDB).filter(TaskDB.id == task_id).first()
        if not task:
            return None
        
        for key, value in update.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(task, key, value.value if hasattr(value, 'value') else value)
        
        task.updated_at = datetime.utcnow()
        self.db.commit()
        
        self.create_event(
            event_type="task_updated",
            action=f"Updated task: {task.title}",
            entity_type="task",
            entity_id=task.id,
            correlation_id=task.correlation_id
        )
        
        return task
    
    def get_tasks(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskDB]:
        query = self.db.query(TaskDB)
        
        if status:
            query = query.filter(TaskDB.status == status)
        if category:
            query = query.filter(TaskDB.category == category)
        
        return query.order_by(TaskDB.created_at.desc()).limit(limit).all()
    
    def complete_task(self, task_id: int, evidence: Optional[str] = None, actual_cost: Optional[float] = None) -> Optional[TaskDB]:
        update = TaskUpdate(
            status=TaskStatus.COMPLETED,
            completed_date=date.today(),
            evidence=evidence,
            actual_cost=actual_cost
        )
        return self.update_task(task_id, update)
    
    # ============ CONTRACTOR JOBS ============
    
    def create_contractor_job(self, job: ContractorJobCreate) -> ContractorJobDB:
        correlation_id = generate_correlation_id()
        db_job = ContractorJobDB(
            correlation_id=correlation_id,
            status="proposed",
            **job.model_dump()
        )
        self.db.add(db_job)
        self.db.commit()
        
        self.create_event(
            event_type="job_proposed",
            action=f"Contractor job proposed: {job.description}",
            entity_type="contractor_job",
            entity_id=db_job.id,
            correlation_id=correlation_id
        )
        
        return db_job
    
    def update_contractor_job(self, job_id: int, **kwargs) -> Optional[ContractorJobDB]:
        job = self.db.query(ContractorJobDB).filter(ContractorJobDB.id == job_id).first()
        if not job:
            return None
        
        old_status = job.status
        
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        job.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Log status transitions
        if "status" in kwargs and kwargs["status"] != old_status:
            self.create_event(
                event_type=f"job_{kwargs['status']}",
                action=f"Job status changed: {old_status} -> {kwargs['status']}",
                entity_type="contractor_job",
                entity_id=job.id,
                correlation_id=job.correlation_id
            )
        
        return job
    
    def get_contractor_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ContractorJobDB]:
        query = self.db.query(ContractorJobDB)
        
        if status:
            query = query.filter(ContractorJobDB.status == status)
        
        return query.order_by(ContractorJobDB.created_at.desc()).limit(limit).all()
    
    # ============ EVENTS ============
    
    def create_event(
        self,
        event_type: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        agent: Optional[str] = None,
        details: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ) -> EventDB:
        event = EventDB(
            correlation_id=correlation_id or generate_correlation_id(),
            event_type=event_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            agent=agent,
            details=details or {},
            timestamp=datetime.utcnow()
        )
        self.db.add(event)
        self.db.commit()
        return event
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[EventDB]:
        query = self.db.query(EventDB)
        
        if event_type:
            query = query.filter(EventDB.event_type == event_type)
        
        return query.order_by(EventDB.timestamp.desc()).limit(limit).all()
    
    def get_recent_events(self, limit: int = 50) -> List[EventDB]:
        return self.get_events(limit=limit)
    
    # ============ COST TRACKING ============
    
    def record_cost(self, cost: CostRecord) -> CostRecordDB:
        db_cost = CostRecordDB(
            correlation_id=cost.correlation_id or generate_correlation_id(),
            **cost.model_dump(exclude={"id", "correlation_id"})
        )
        self.db.add(db_cost)
        self.db.commit()
        
        # Update system budget
        if cost.estimated_cost > 0:
            self.update_budget_spend("system", cost.estimated_cost)
        
        return db_cost
    
    def get_cost_summary(self, period: str = "today") -> CostSummary:
        """Get cost summary for a period"""
        if period == "today":
            start = datetime.combine(date.today(), datetime.min.time())
        elif period == "month":
            start = datetime.combine(date.today().replace(day=1), datetime.min.time())
        else:
            start = datetime.min
        
        records = self.db.query(CostRecordDB).filter(
            CostRecordDB.timestamp >= start
        ).all()
        
        total_cost = sum(r.estimated_cost or 0 for r in records)
        total_in = sum(r.tokens_in or 0 for r in records)
        total_out = sum(r.tokens_out or 0 for r in records)
        
        by_model = {}
        by_category = {}
        
        for r in records:
            model = r.model_name or "unknown"
            by_model[model] = by_model.get(model, 0) + (r.estimated_cost or 0)
            
            cat = r.category or "unknown"
            by_category[cat] = by_category.get(cat, 0) + (r.estimated_cost or 0)
        
        budget = self.get_budget("system")
        budget_limit = budget.limit_amount if budget else 1000.0
        
        return CostSummary(
            period=period,
            total_cost=round(total_cost, 4),
            total_tokens_in=total_in,
            total_tokens_out=total_out,
            by_model=by_model,
            by_category=by_category,
            budget_limit=budget_limit,
            budget_used_pct=round((total_cost / budget_limit) * 100, 1) if budget_limit > 0 else 0
        )
    
    # ============ INBOX ============
    
    def get_inbox_messages(
        self,
        source: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[InboxMessageDB]:
        query = self.db.query(InboxMessageDB)
        
        if source:
            query = query.filter(InboxMessageDB.source == source)
        if unread_only:
            query = query.filter(InboxMessageDB.is_read == False)
        
        return query.order_by(InboxMessageDB.timestamp.desc()).limit(limit).all()
    
    def get_unread_counts(self) -> Dict[str, int]:
        gmail = self.db.query(InboxMessageDB).filter(
            InboxMessageDB.source == "gmail",
            InboxMessageDB.is_read == False
        ).count()
        
        whatsapp = self.db.query(InboxMessageDB).filter(
            InboxMessageDB.source == "whatsapp",
            InboxMessageDB.is_read == False
        ).count()
        
        return {
            "gmail": gmail,
            "whatsapp": whatsapp,
            "total": gmail + whatsapp
        }
    
    def mark_message_read(self, message_id: int) -> Optional[InboxMessageDB]:
        msg = self.db.query(InboxMessageDB).filter(InboxMessageDB.id == message_id).first()
        if msg:
            msg.is_read = True
            msg.updated_at = datetime.utcnow()
            self.db.commit()
        return msg
    
    # ============ APPROVALS ============
    
    def create_approval_request(
        self,
        approval_type: str,
        entity_type: str,
        entity_id: int,
        requested_by: str,
        requested_amount: float
    ) -> ApprovalDB:
        # Get budget status for context
        budget_type = "monthly" if approval_type == "cost" else "monthly"
        budget = self.get_budget(budget_type)
        
        approval = ApprovalDB(
            correlation_id=generate_correlation_id(),
            approval_type=approval_type,
            entity_type=entity_type,
            entity_id=entity_id,
            requested_by=requested_by,
            requested_amount=requested_amount,
            status="pending",
            budget_at_decision=budget.current_spend if budget else 0,
            remaining_at_decision=budget.limit_amount - budget.current_spend if budget else 0
        )
        self.db.add(approval)
        self.db.commit()
        return approval
    
    def decide_approval(
        self,
        approval_id: int,
        status: str,
        decision_by: str,
        reason: str
    ) -> Optional[ApprovalDB]:
        approval = self.db.query(ApprovalDB).filter(ApprovalDB.id == approval_id).first()
        if not approval:
            return None
        
        approval.status = status
        approval.decision_by = decision_by
        approval.decision_reason = reason
        approval.decided_at = datetime.utcnow()
        self.db.commit()
        
        self.create_event(
            event_type=f"cost_{status}",
            action=f"Approval {status}: {reason}",
            entity_type=approval.entity_type,
            entity_id=approval.entity_id,
            agent=decision_by,
            correlation_id=approval.correlation_id
        )
        
        return approval
