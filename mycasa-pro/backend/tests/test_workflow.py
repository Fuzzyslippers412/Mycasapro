"""
MyCasa Pro End-to-End Workflow Tests
Tests the complete contractor workflow and all major features
"""
import pytest
import os
import tempfile
from datetime import date, timedelta

# Set up test database before imports
TEST_DB = tempfile.mktemp(suffix=".db")
os.environ["MYCASA_DB_PATH"] = TEST_DB

from ..storage.database import init_db, get_db
from ..storage.repository import Repository
from ..core.schemas import (
    TaskCreate, TaskUpdate, TaskStatus, Priority,
    Transaction, TransactionIngest, IncomeSource,
    CostRecord
)
from ..agents.finance import FinanceManager
from ..agents.contractor import ContractorAgent
from ..agents.backup import BackupAgent


@pytest.fixture(scope="module")
def db():
    """Set up test database"""
    init_db()
    with get_db() as session:
        yield session


@pytest.fixture
def repo(db):
    """Get repository instance"""
    return Repository(db)


class TestIntake:
    """Test system intake/setup"""
    
    def test_create_income_source(self, repo):
        """Test creating primary income source"""
        source = IncomeSource(
            name="J.P. Morgan Brokerage",
            account_type="brokerage",
            institution="J.P. Morgan",
            is_primary=True,
            expected_monthly_min=5000,
            expected_monthly_max=15000
        )
        
        result = repo.create_income_source(source)
        assert result.id is not None
        assert result.is_primary == True
        
        # Verify primary income configured
        primary = repo.get_primary_income_source()
        assert primary is not None
        assert primary.institution == "J.P. Morgan"
    
    def test_budgets_initialized(self, repo):
        """Test that default budgets exist"""
        budgets = repo.get_all_budgets()
        assert len(budgets) >= 3
        
        budget_types = [b.budget_type for b in budgets]
        assert "monthly" in budget_types
        assert "daily" in budget_types
        assert "system" in budget_types
    
    def test_budget_limits(self, repo):
        """Test budget limit values"""
        monthly = repo.get_budget("monthly")
        daily = repo.get_budget("daily")
        system = repo.get_budget("system")
        
        assert monthly.limit_amount == 10000.0
        assert daily.limit_amount == 150.0
        assert system.limit_amount == 1000.0


class TestTransactions:
    """Test transaction ingestion and tracking"""
    
    def test_ingest_jpm_transactions(self, repo):
        """Test ingesting JPM brokerage transactions"""
        transactions = [
            Transaction(
                amount=5000.0,
                merchant="JPM Brokerage",
                description="Monthly withdrawal",
                date=date.today(),
                funding_source="JPM Brokerage",
                payment_rail="ACH",
                consumption_category="income_transfer",
                is_internal_transfer=True
            )
        ]
        
        result = repo.ingest_transactions(TransactionIngest(
            transactions=transactions,
            source="import"
        ))
        
        assert result["created"] == 1
        assert result["skipped"] == 0
    
    def test_ingest_apple_cash_transactions(self, repo):
        """Test ingesting Apple Cash transactions"""
        transactions = [
            Transaction(
                amount=45.50,
                merchant="Whole Foods",
                date=date.today(),
                funding_source="Chase Checking",
                payment_rail="Apple Cash",
                consumption_category="groceries",
                is_discretionary=True
            ),
            Transaction(
                amount=89.00,
                merchant="Amazon",
                date=date.today(),
                funding_source="Chase Freedom",
                payment_rail="card",
                consumption_category="shopping",
                is_discretionary=True
            )
        ]
        
        result = repo.ingest_transactions(TransactionIngest(
            transactions=transactions,
            source="import"
        ))
        
        assert result["created"] == 2
    
    def test_deduplication(self, repo):
        """Test transaction deduplication"""
        txn = Transaction(
            amount=45.50,
            merchant="Whole Foods",
            date=date.today(),
            funding_source="Chase Checking",
            payment_rail="Apple Cash",
            consumption_category="groceries"
        )
        
        # First ingest
        result1 = repo.ingest_transactions(TransactionIngest(
            transactions=[txn],
            source="import",
            deduplicate=True
        ))
        
        # Second ingest (should be skipped)
        result2 = repo.ingest_transactions(TransactionIngest(
            transactions=[txn],
            source="import",
            deduplicate=True
        ))
        
        assert result2["skipped"] == 1
    
    def test_spend_summary(self, repo):
        """Test spending summary"""
        summary = repo.get_spend_summary(days=30)
        
        assert "total_spend" in summary
        assert "by_category" in summary
        assert "by_payment_rail" in summary


class TestContractorWorkflow:
    """Test complete contractor job workflow"""
    
    def test_step1_create_job(self, repo):
        """Step 1: Create contractor job (proposed)"""
        agent = ContractorAgent(repo)
        
        result = agent.create_job(
            description="Deck repair and staining",
            scope="Replace damaged boards, sand, and apply stain",
            contractor_role="carpentry",
            proposed_start=date.today() + timedelta(days=7),
            proposed_end=date.today() + timedelta(days=9),
            estimated_cost=800.0,
            urgency=Priority.MEDIUM
        )
        
        assert result["job_id"] is not None
        assert result["status"] == "proposed"
        assert "Contact contractor to schedule" in result["next_steps"]
        
        # Store for next tests
        TestContractorWorkflow.job_id = result["job_id"]
    
    def test_step2_schedule_with_rakia(self, repo):
        """Step 2: Schedule job via Rakia"""
        agent = ContractorAgent(repo)
        job_id = TestContractorWorkflow.job_id
        
        # Manager contacts Rakia to schedule with Juan
        result = agent.schedule_with_contractor(
            job_id=job_id,
            contractor_key="juan",
            confirmed_start=date.today() + timedelta(days=7),
            confirmed_end=date.today() + timedelta(days=9)
        )
        
        assert result["success"] == True
        assert result["status"] == "scheduled"
        assert result["contractor"] == "Juan"
        assert "+12534312046" in result["contact"]
    
    def test_step3_finance_approval(self, repo):
        """Step 3: Finance manager approves cost"""
        agent = ContractorAgent(repo)
        job_id = TestContractorWorkflow.job_id
        
        result = agent.submit_for_approval(job_id, estimated_cost=800.0)
        
        assert result["approved"] == True
        assert result["approved_cost"] == 800.0
    
    def test_step4_job_starts(self, repo):
        """Step 4: Job starts"""
        agent = ContractorAgent(repo)
        job_id = TestContractorWorkflow.job_id
        
        result = agent.start_job(job_id)
        
        assert result["success"] == True
        assert result["status"] == "in_progress"
    
    def test_step5_job_completes(self, repo):
        """Step 5: Job completes"""
        agent = ContractorAgent(repo)
        job_id = TestContractorWorkflow.job_id
        
        result = agent.complete_job(
            job_id=job_id,
            actual_cost=750.0,  # Came in under budget
            evidence="Photos of completed deck",
            notes="Job completed ahead of schedule"
        )
        
        assert result["success"] == True
        assert result["status"] == "completed"
        assert result["actual_cost"] == 750.0
    
    def test_final_status(self, repo):
        """Verify final job status"""
        agent = ContractorAgent(repo)
        job_id = TestContractorWorkflow.job_id
        
        status = agent.get_job_status(job_id)
        
        assert status["status"] == "completed"
        assert status["approved_cost"] == 800.0
        assert status["actual_cost"] == 750.0
        assert status["cost_status"] == "approved"


class TestBudgetEnforcement:
    """Test budget enforcement and warnings"""
    
    def test_budget_check_within_limit(self, repo):
        """Test budget check for amount within limits"""
        finance = FinanceManager(repo)
        
        result = finance.check_spend_approval(100.0, "general", "test")
        
        assert result["approved"] == True
    
    def test_budget_warning_at_70(self, repo):
        """Test warning at 70% budget"""
        # Set monthly budget to low value for testing
        budget = repo.get_budget("monthly")
        budget.current_spend = 7000.0  # 70% of 10000
        repo.db.commit()
        
        finance = FinanceManager(repo)
        result = finance.check_spend_approval(100.0)
        
        assert any("WARNING" in w for w in result["warnings"])
    
    def test_budget_block_at_100(self, repo):
        """Test block at 100% budget"""
        budget = repo.get_budget("monthly")
        budget.current_spend = 10000.0  # 100%
        repo.db.commit()
        
        finance = FinanceManager(repo)
        result = finance.check_spend_approval(100.0)
        
        assert result["approved"] == False
        assert any("EXCEEDED" in w for w in result["warnings"])


class TestTasks:
    """Test task management"""
    
    def test_create_task(self, repo):
        """Test creating a task"""
        task = TaskCreate(
            title="Check smoke detectors",
            description="Monthly smoke detector test",
            category="maintenance",
            priority=Priority.MEDIUM,
            scheduled_date=date.today() + timedelta(days=7)
        )
        
        result = repo.create_task(task)
        
        assert result.id is not None
        assert result.status == "pending"
        
        TestTasks.task_id = result.id
    
    def test_update_task(self, repo):
        """Test updating a task"""
        update = TaskUpdate(status=TaskStatus.IN_PROGRESS)
        
        result = repo.update_task(TestTasks.task_id, update)
        
        assert result.status == "in_progress"
    
    def test_complete_task(self, repo):
        """Test completing a task"""
        result = repo.complete_task(
            TestTasks.task_id,
            evidence="All detectors tested and working"
        )
        
        assert result.status == "completed"
        assert result.completed_date == date.today()


class TestCostTracking:
    """Test system cost tracking"""
    
    def test_record_cost(self, repo):
        """Test recording AI cost"""
        cost = CostRecord(
            model_name="claude-opus-4",
            tokens_in=1000,
            tokens_out=500,
            estimated_cost=0.0525,  # $0.015/1K in + $0.075/1K out
            category="ai_api",
            service_name="Anthropic",
            tool_calls=["web_search", "browser"]
        )
        
        result = repo.record_cost(cost)
        
        assert result.id is not None
        assert result.estimated_cost == 0.0525
    
    def test_cost_summary(self, repo):
        """Test cost summary"""
        summary = repo.get_cost_summary("month")
        
        assert summary.total_cost > 0
        assert summary.budget_limit == 1000.0
        assert "claude-opus-4" in summary.by_model


class TestBackup:
    """Test backup and restore"""
    
    def test_export_backup(self, repo):
        """Test exporting backup"""
        agent = BackupAgent(repo)
        
        result = agent.export_backup(notes="Test backup")
        
        assert result["success"] == True
        assert "filename" in result
        assert "checksum" in result
        
        TestBackup.backup_path = result["path"]
    
    def test_verify_backup(self, repo):
        """Test verifying backup integrity"""
        agent = BackupAgent(repo)
        
        result = agent.verify_backup(TestBackup.backup_path)
        
        assert result["success"] == True
        assert result["dry_run"] == True


class TestEvents:
    """Test event logging"""
    
    def test_events_created(self, repo):
        """Test that events were created during workflow"""
        events = repo.get_recent_events(limit=50)
        
        assert len(events) > 0
        
        event_types = [e.event_type for e in events]
        assert "task_created" in event_types
        assert "job_proposed" in event_types


class TestFailureModes:
    """Test failure handling"""
    
    def test_missing_task(self, repo):
        """Test updating non-existent task"""
        result = repo.update_task(99999, TaskUpdate(status=TaskStatus.COMPLETED))
        assert result is None
    
    def test_invalid_budget_check(self, repo):
        """Test budget check with no budget"""
        result = repo.check_budget_status("nonexistent", 100)
        assert result["status"] == "no_budget"


# Run with: pytest backend/tests/test_workflow.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
