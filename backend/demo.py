#!/usr/bin/env python3
"""
MyCasa Pro Demo Script
Runs complete workflow to demonstrate all features

Usage:
    python -m backend.demo
    
Or via CLI:
    mycasa demo
"""
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.database import init_db, get_db
from backend.storage.repository import Repository
from backend.core.schemas import (
    Transaction, TransactionIngest, IncomeSource, CostRecord,
    Priority
)
from backend.agents.finance import FinanceManager
from backend.agents.contractor import ContractorAgent
from backend.agents.backup import BackupAgent


def print_step(step: str, description: str):
    """Print step header"""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {description}")
    print('='*60)


def print_result(label: str, value):
    """Print result"""
    print(f"  {label}: {value}")


def run_demo():
    """Run complete demo workflow"""
    print("\n" + "="*60)
    print("  MYCASA PRO DEMO")
    print("  Complete Workflow Demonstration")
    print("="*60)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    
    with get_db() as db:
        repo = Repository(db)
        
        # ============ STEP 1: INTAKE ============
        print_step("1", "SYSTEM INTAKE")
        
        # Create primary income source
        income = IncomeSource(
            name="J.P. Morgan Brokerage",
            account_type="brokerage",
            institution="J.P. Morgan",
            is_primary=True,
            expected_monthly_min=5000,
            expected_monthly_max=15000
        )
        repo.create_income_source(income)
        print_result("Primary Income", "J.P. Morgan Brokerage (brokerage)")
        
        # Verify budgets
        budgets = repo.get_all_budgets()
        print_result("Budgets Configured", len(budgets))
        for b in budgets:
            print_result(f"  {b.name}", f"${b.limit_amount:,.2f}")
        
        # Mark intake complete
        repo.update_user_settings(intake_complete=True)
        print_result("Intake Status", "COMPLETE ✓")
        
        # ============ STEP 2: INGEST TRANSACTIONS ============
        print_step("2", "TRANSACTION INGESTION")
        
        # JPM transfers
        jpm_transactions = [
            Transaction(
                amount=8000.0,
                merchant="JPM Brokerage",
                description="Monthly withdrawal",
                date=date.today() - timedelta(days=5),
                funding_source="JPM Brokerage",
                payment_rail="ACH",
                consumption_category="income_transfer",
                is_internal_transfer=True,
                source="import"
            )
        ]
        
        # Apple Cash transactions
        apple_cash_transactions = [
            Transaction(
                amount=45.50,
                merchant="Whole Foods",
                date=date.today() - timedelta(days=3),
                funding_source="Chase Checking",
                payment_rail="Apple Cash",
                consumption_category="groceries"
            ),
            Transaction(
                amount=32.00,
                merchant="Chipotle",
                date=date.today() - timedelta(days=2),
                funding_source="Chase Checking",
                payment_rail="Apple Cash",
                consumption_category="dining"
            ),
            Transaction(
                amount=89.00,
                merchant="Amazon",
                date=date.today() - timedelta(days=1),
                funding_source="Chase Freedom",
                payment_rail="card",
                consumption_category="shopping"
            )
        ]
        
        all_txns = jpm_transactions + apple_cash_transactions
        result = repo.ingest_transactions(TransactionIngest(
            transactions=all_txns,
            source="demo"
        ))
        
        print_result("JPM Transfers", f"${jpm_transactions[0].amount:,.2f}")
        print_result("Apple Cash Transactions", len(apple_cash_transactions))
        print_result("Total Ingested", result["created"])
        
        # Show summary
        summary = repo.get_spend_summary(days=7)
        print_result("7-Day Spend", f"${summary['total_spend']:,.2f}")
        
        # ============ STEP 3: CREATE CONTRACTOR JOB ============
        print_step("3", "CONTRACTOR JOB REQUEST")
        
        contractor_agent = ContractorAgent(repo)
        
        job_result = contractor_agent.create_job(
            description="Deck repair and staining",
            scope="Replace 3 damaged boards, sand entire deck, apply 2 coats of stain",
            contractor_role="carpentry",
            proposed_start=date.today() + timedelta(days=7),
            proposed_end=date.today() + timedelta(days=9),
            estimated_cost=800.0,
            urgency=Priority.MEDIUM
        )
        
        job_id = job_result["job_id"]
        print_result("Job Created", f"#{job_id}")
        print_result("Status", job_result["status"])
        print_result("Estimated Cost", "$800.00")
        print_result("Next Steps", ", ".join(job_result["next_steps"][:2]))
        
        # ============ STEP 4: SCHEDULE WITH RAKIA ============
        print_step("4", "SCHEDULE VIA RAKIA")
        
        schedule_result = contractor_agent.schedule_with_contractor(
            job_id=job_id,
            contractor_key="juan",
            confirmed_start=date.today() + timedelta(days=7),
            confirmed_end=date.today() + timedelta(days=9)
        )
        
        print_result("Scheduled With", schedule_result["contractor"])
        print_result("Contact", schedule_result["contact"])
        print_result("Status", schedule_result["status"])
        print("  (In reality: Manager would contact Rakia to coordinate with Juan)")
        
        # ============ STEP 5: FINANCE APPROVAL ============
        print_step("5", "FINANCE MANAGER APPROVAL")
        
        finance = FinanceManager(repo)
        
        # Check budget first
        check = finance.check_spend_approval(800.0, "contractor", "contractor_agent")
        print_result("Budget Check", "PASSED" if check["approved"] else "FAILED")
        print_result("Monthly Budget", f"{check['monthly_budget']['pct_used']:.1f}% used")
        
        # Submit for approval
        approval_result = contractor_agent.submit_for_approval(job_id, 800.0)
        print_result("Approval", "APPROVED ✓" if approval_result["approved"] else "DENIED ✗")
        print_result("Approved Amount", f"${approval_result.get('approved_cost', 0):,.2f}")
        
        if approval_result.get("warnings"):
            for w in approval_result["warnings"]:
                print_result("Warning", w)
        
        # ============ STEP 6: JOB EXECUTION ============
        print_step("6", "JOB EXECUTION")
        
        # Start job
        start_result = contractor_agent.start_job(job_id)
        print_result("Job Started", start_result["started_at"])
        print_result("Status", start_result["status"])
        
        # Complete job
        complete_result = contractor_agent.complete_job(
            job_id=job_id,
            actual_cost=750.0,  # Came in under budget!
            evidence="Photos: deck_before.jpg, deck_after.jpg, receipt.pdf",
            notes="Completed 1 day early. Juan found less damage than expected."
        )
        
        print_result("Job Completed", complete_result["completed_at"])
        print_result("Actual Cost", f"${complete_result['actual_cost']:,.2f}")
        print_result("Savings", f"${800.0 - 750.0:,.2f} under budget")
        
        # ============ STEP 7: RECORD SYSTEM COSTS ============
        print_step("7", "SYSTEM COST TRACKING")
        
        # Record some AI costs
        costs = [
            CostRecord(
                model_name="claude-opus-4",
                tokens_in=2000,
                tokens_out=1000,
                estimated_cost=0.105,  # $0.015*2 + $0.075*1
                category="ai_api",
                service_name="Anthropic",
                tool_calls=["web_search", "browser"]
            ),
            CostRecord(
                model_name="claude-sonnet-4",
                tokens_in=5000,
                tokens_out=2000,
                estimated_cost=0.045,  # $0.003*5 + $0.015*2
                category="ai_api",
                service_name="Anthropic"
            )
        ]
        
        for cost in costs:
            repo.record_cost(cost)
        
        cost_summary = repo.get_cost_summary("month")
        print_result("Total System Cost", f"${cost_summary.total_cost:.4f}")
        print_result("Budget Used", f"{cost_summary.budget_used_pct:.1f}%")
        print_result("Models Used", ", ".join(cost_summary.by_model.keys()))
        
        # ============ STEP 8: BACKUP ============
        print_step("8", "BACKUP EXPORT")
        
        backup_agent = BackupAgent(repo)
        backup_result = backup_agent.export_backup(notes="Demo backup")
        
        print_result("Backup Created", backup_result["filename"])
        print_result("Size", f"{backup_result['size_bytes']:,} bytes")
        print_result("Checksum", backup_result["checksum"][:16] + "...")
        
        backup_path = backup_result["path"]
        
        # ============ STEP 9: VERIFY BACKUP ============
        print_step("9", "BACKUP VERIFICATION")
        
        verify_result = backup_agent.verify_backup(backup_path)
        print_result("Verification", "PASSED ✓" if verify_result["success"] else "FAILED ✗")
        print_result("Records", verify_result.get("metadata", {}).get("record_counts", {}))
        
        # ============ STEP 10: DASHBOARD STATUS ============
        print_step("10", "DASHBOARD STATUS")
        
        # Tasks
        tasks = repo.get_tasks(limit=10)
        print_result("Total Tasks", len(tasks))
        
        # Events
        events = repo.get_recent_events(limit=10)
        print_result("Recent Events", len(events))
        
        # Budget status
        print("\n  Budget Health:")
        for b in repo.get_all_budgets():
            pct = (b.current_spend / b.limit_amount * 100) if b.limit_amount > 0 else 0
            status = "✓" if pct < 70 else "⚠" if pct < 100 else "✗"
            print(f"    {status} {b.name}: ${b.current_spend:,.2f} / ${b.limit_amount:,.2f} ({pct:.1f}%)")
        
        # ============ SUMMARY ============
        print("\n" + "="*60)
        print("  DEMO COMPLETE")
        print("="*60)
        print("""
  ✓ System intake with JPM brokerage income source
  ✓ Transaction ingestion (JPM + Apple Cash)
  ✓ Contractor job workflow (propose → schedule → approve → complete)
  ✓ Budget enforcement and warnings
  ✓ System cost tracking
  ✓ Backup export and verification
  ✓ Dashboard status
  
  All data persisted to: data/mycasa.db
  Backup saved to: backups/
        """)


if __name__ == "__main__":
    run_demo()
