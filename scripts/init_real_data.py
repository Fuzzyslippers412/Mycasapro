#!/usr/bin/env python3
"""
MyCasa Pro - Initialize Real Data
Only seeds REAL data from household config. No fake/demo data.
Agents generate additional data as needed.
Portfolio data should be added by user via Finance agent.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, get_db
from database.models import (
    Contractor, FinanceManagerSettings, 
    IncomeSource, Notification
)

# Real household contractors
REAL_CONTRACTORS = [
    {
        "name": "Juan",
        "phone": "+12534312046",
        "service_type": "General",
        "notes": "General contractor, speaks Spanish"
    },
    {
        "name": "Rakia Baldé", 
        "phone": "+33782826145",
        "service_type": "House Manager",
        "notes": "House assistant"
    }
]

REAL_INCOME_SOURCES = [
    {
        "name": "J.P. Morgan Brokerage",
        "account_type": "brokerage",
        "institution": "J.P. Morgan",
        "is_primary": True,
        "income_type": "investment",
        "notes": "Primary income source - dividends and capital gains"
    }
]


def sync_contractors():
    """Sync contractors with real data"""
    with get_db() as db:
        for c in REAL_CONTRACTORS:
            existing = db.query(Contractor).filter(
                Contractor.phone == c["phone"]
            ).first()
            
            if existing:
                # Update
                existing.name = c["name"]
                existing.service_type = c["service_type"]
                existing.notes = c.get("notes")
            else:
                # Create
                db.add(Contractor(**c))
        
        print(f"✅ Contractors synced: {len(REAL_CONTRACTORS)} contractors")


def init_finance_settings():
    """Initialize finance manager settings if not done"""
    with get_db() as db:
        settings = db.query(FinanceManagerSettings).first()
        if not settings:
            settings = FinanceManagerSettings(
                intake_complete=False,  # User must complete intake
                system_cost_budget=1000.0,
                monthly_spend_limit=10000.0,
                daily_soft_cap=150.0,
                spend_alerts_enabled=True
            )
            db.add(settings)
            print("✅ Finance settings initialized (intake pending)")
        else:
            print(f"✅ Finance settings exist (intake: {'complete' if settings.intake_complete else 'pending'})")


def init_income_sources():
    """Initialize real income sources"""
    with get_db() as db:
        for src in REAL_INCOME_SOURCES:
            existing = db.query(IncomeSource).filter(
                IncomeSource.name == src["name"]
            ).first()
            
            if not existing:
                db.add(IncomeSource(**src))
        
        print(f"✅ Income sources synced: {len(REAL_INCOME_SOURCES)} sources")


def create_system_notification(title: str, message: str, priority: str = "medium"):
    """Create a persistent system notification"""
    with get_db() as db:
        notification = Notification(
            title=title,
            message=message,
            category="system",
            priority=priority
        )
        db.add(notification)
    print(f"📬 Notification created: {title}")


def verify_notification_persistence():
    """Verify notifications are persisting to database"""
    with get_db() as db:
        count = db.query(Notification).count()
        print(f"✅ Notifications in database: {count}")
        
        if count > 0:
            latest = db.query(Notification).order_by(
                Notification.created_at.desc()
            ).first()
            print(f"   Latest: {latest.title} ({latest.priority})")


def main():
    print("🏠 MyCasa Pro - Initializing Real Data")
    print("=" * 50)
    print()
    
    # Initialize database
    init_db()
    
    # Sync real data (NO portfolio - user adds via Finance agent)
    sync_contractors()
    init_finance_settings()
    init_income_sources()
    
    print()
    print("=" * 50)
    print("✅ Real data sync complete!")
    print()
    print("📝 Notes:")
    print("   - Portfolio: Add via Finance agent conversation")
    print("   - Bills: Add via UI or agent conversation")
    print("   - Tasks: Add via UI or agent conversation")
    print("   - Projects: Add via UI or agent conversation")
    print()
    print("   Agents will generate notifications as events occur.")
    print()
    
    # Verify notifications
    verify_notification_persistence()


if __name__ == "__main__":
    main()
