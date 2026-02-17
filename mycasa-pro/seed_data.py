"""
Seed initial data for MyCasa Pro
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, get_db
from database.models import (
    Contractor, MaintenanceTask, Bill, Budget, ScheduledJob
)

def seed_contractors():
    """Add initial contractors"""
    contractors = [
        {
            "name": "Rakia Balde",
            "phone": "+33782826145",
            "service_type": "cleaning",
            "notes": "House assistant, regular cleaning schedule"
        },
        {
            "name": "Juan",
            "phone": "+12534312046",
            "service_type": "general",
            "notes": "General contractor, speaks Spanish"
        }
    ]
    
    with get_db() as db:
        for c in contractors:
            existing = db.query(Contractor).filter(Contractor.name == c["name"]).first()
            if not existing:
                db.add(Contractor(**c))
        print(f"✅ Seeded {len(contractors)} contractors")


def seed_tasks():
    """Add sample maintenance tasks"""
    tasks = [
        {
            "title": "House cleaning",
            "description": "Regular house cleaning",
            "category": "cleaning",
            "priority": "medium",
            "scheduled_date": date.today() + timedelta(days=3),
            "recurrence": "biweekly"
        },
        {
            "title": "Check smoke detectors",
            "description": "Test all smoke detectors and replace batteries if needed",
            "category": "security",
            "priority": "high",
            "scheduled_date": date.today() + timedelta(days=7)
        },
        {
            "title": "HVAC filter replacement",
            "description": "Replace HVAC filters throughout the house",
            "category": "hvac",
            "priority": "medium",
            "scheduled_date": date.today() + timedelta(days=14),
            "recurrence": "quarterly"
        }
    ]
    
    with get_db() as db:
        for t in tasks:
            existing = db.query(MaintenanceTask).filter(MaintenanceTask.title == t["title"]).first()
            if not existing:
                db.add(MaintenanceTask(**t))
        print(f"✅ Seeded {len(tasks)} maintenance tasks")


def seed_bills():
    """Add sample bills"""
    bills = [
        {
            "name": "PSE Electric",
            "amount": 250.00,
            "due_date": date.today() + timedelta(days=10),
            "category": "utilities",
            "payee": "Puget Sound Energy",
            "is_recurring": True,
            "recurrence": "monthly",
            "auto_pay": True
        },
        {
            "name": "Internet - Xfinity",
            "amount": 89.99,
            "due_date": date.today() + timedelta(days=15),
            "category": "internet",
            "payee": "Comcast",
            "is_recurring": True,
            "recurrence": "monthly",
            "auto_pay": True
        },
        {
            "name": "Water/Sewer",
            "amount": 120.00,
            "due_date": date.today() + timedelta(days=20),
            "category": "utilities",
            "is_recurring": True,
            "recurrence": "monthly"
        },
        {
            "name": "Home Insurance",
            "amount": 450.00,
            "due_date": date.today() + timedelta(days=25),
            "category": "insurance",
            "is_recurring": True,
            "recurrence": "monthly",
            "auto_pay": True
        }
    ]
    
    with get_db() as db:
        for b in bills:
            existing = db.query(Bill).filter(Bill.name == b["name"]).first()
            if not existing:
                db.add(Bill(**b))
        print(f"✅ Seeded {len(bills)} bills")


def seed_budgets():
    """Add sample budgets"""
    budgets = [
        {"category": "utilities", "monthly_limit": 500.00},
        {"category": "internet", "monthly_limit": 100.00},
        {"category": "insurance", "monthly_limit": 600.00},
        {"category": "maintenance", "monthly_limit": 300.00},
        {"category": "subscriptions", "monthly_limit": 200.00}
    ]
    
    with get_db() as db:
        for b in budgets:
            existing = db.query(Budget).filter(Budget.category == b["category"]).first()
            if not existing:
                db.add(Budget(**b))
        print(f"✅ Seeded {len(budgets)} budgets")


def seed_scheduled_jobs():
    """Add scheduled job references"""
    jobs = [
        {
            "name": "Daily Portfolio Check",
            "agent": "finance",
            "job_type": "portfolio_update",
            "cron_expression": "0 7 * * *",
            "is_active": True
        },
        {
            "name": "Weekly Bill Reminder",
            "agent": "finance", 
            "job_type": "bill_reminder",
            "cron_expression": "0 9 * * 1",
            "is_active": True
        },
        {
            "name": "Daily System Check",
            "agent": "supervisor",
            "job_type": "daily_check",
            "cron_expression": "0 8 * * *",
            "is_active": True
        }
    ]
    
    with get_db() as db:
        for j in jobs:
            existing = db.query(ScheduledJob).filter(ScheduledJob.name == j["name"]).first()
            if not existing:
                db.add(ScheduledJob(**j))
        print(f"✅ Seeded {len(jobs)} scheduled jobs")


def main():
    print("🌱 Seeding MyCasa Pro database...")
    print("")
    
    init_db()
    
    seed_contractors()
    seed_tasks()
    seed_bills()
    seed_budgets()
    seed_scheduled_jobs()
    
    print("")
    print("🎉 Database seeded successfully!")


if __name__ == "__main__":
    main()
