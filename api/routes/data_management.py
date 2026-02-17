"""
MyCasa Pro API - Data Management Routes
Clean slate operations for resetting/clearing data.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

router = APIRouter(prefix="/data", tags=["Data Management"])


class ClearResult(BaseModel):
    success: bool
    cleared_count: int
    message: str


class DataCounts(BaseModel):
    inbox_messages: int
    unread_messages: int
    pending_tasks: int
    completed_tasks: int
    unpaid_bills: int
    paid_bills: int
    activity_events: int
    portfolio_holdings: int
    projects: int
    contractors: int


@router.get("/counts", response_model=DataCounts)
async def get_data_counts():
    """Return counts for clean slate controls."""
    from database import get_db
    from database.models import (
        InboxMessage,
        MaintenanceTask,
        Bill,
        PortfolioHolding,
        Project,
        Contractor,
    )
    from sqlalchemy import text

    with get_db() as db:
        inbox_messages = db.query(InboxMessage).count()
        unread_messages = db.query(InboxMessage).filter(InboxMessage.is_read.is_(False)).count()
        pending_tasks = db.query(MaintenanceTask).filter(
            MaintenanceTask.status.in_(["pending", "in_progress"])
        ).count()
        completed_tasks = db.query(MaintenanceTask).filter(
            MaintenanceTask.status == "completed"
        ).count()
        unpaid_bills = db.query(Bill).filter(Bill.is_paid.is_(False)).count()
        paid_bills = db.query(Bill).filter(Bill.is_paid.is_(True)).count()
        portfolio_holdings = db.query(PortfolioHolding).count()
        projects = db.query(Project).count()
        contractors = db.query(Contractor).count()

        activity_events = 0
        try:
            result = db.execute(text("SELECT COUNT(*) FROM event_log"))
            activity_events = int(result.scalar() or 0)
        except Exception:
            activity_events = 0

    return DataCounts(
        inbox_messages=inbox_messages,
        unread_messages=unread_messages,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        unpaid_bills=unpaid_bills,
        paid_bills=paid_bills,
        activity_events=activity_events,
        portfolio_holdings=portfolio_holdings,
        projects=projects,
        contractors=contractors,
    )


# ============ INBOX OPERATIONS ============

@router.post("/inbox/mark-all-read", response_model=ClearResult)
async def mark_all_inbox_read():
    """Mark all inbox messages as read"""
    from database import get_db
    from database.models import InboxMessage

    with get_db() as db:
        count = db.query(InboxMessage).filter(InboxMessage.is_read.is_(False)).update(
            {"is_read": True},
            synchronize_session=False
        )
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Marked {count} messages as read"
    )


@router.post("/inbox/clear", response_model=ClearResult)
async def clear_inbox():
    """Delete all inbox messages"""
    from database import get_db
    from database.models import InboxMessage

    with get_db() as db:
        count = db.query(InboxMessage).delete()
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Deleted {count} inbox messages"
    )


# ============ TASKS OPERATIONS ============

@router.post("/tasks/mark-all-complete", response_model=ClearResult)
async def mark_all_tasks_complete():
    """Mark all pending tasks as completed"""
    from database import get_db
    from database.models import MaintenanceTask

    with get_db() as db:
        count = db.query(MaintenanceTask).filter(
            MaintenanceTask.status.in_(["pending", "in_progress"])
        ).update(
            {"status": "completed", "completed_date": date.today()},
            synchronize_session=False
        )
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Marked {count} tasks as complete"
    )


@router.post("/tasks/clear", response_model=ClearResult)
async def clear_tasks():
    """Delete all maintenance tasks"""
    from database import get_db
    from database.models import MaintenanceTask

    with get_db() as db:
        count = db.query(MaintenanceTask).delete()
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Deleted {count} tasks"
    )


# ============ BILLS OPERATIONS ============

@router.post("/bills/mark-all-paid", response_model=ClearResult)
async def mark_all_bills_paid():
    """Mark all unpaid bills as paid"""
    from database import get_db
    from database.models import Bill

    with get_db() as db:
        count = db.query(Bill).filter(Bill.is_paid.is_(False)).update(
            {"is_paid": True, "paid_date": date.today()},
            synchronize_session=False
        )
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Marked {count} bills as paid"
    )


@router.post("/bills/clear", response_model=ClearResult)
async def clear_bills():
    """Delete all bills"""
    from database import get_db
    from database.models import Bill

    with get_db() as db:
        count = db.query(Bill).delete()
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Deleted {count} bills"
    )


# ============ ACTIVITY/EVENTS OPERATIONS ============

@router.post("/activity/clear", response_model=ClearResult)
async def clear_activity():
    """Clear all activity/event logs"""
    from database import get_db
    from sqlalchemy import text

    with get_db() as db:
        try:
            result = db.execute(text("DELETE FROM event_log"))
            count = result.rowcount
            db.commit()
        except Exception:
            count = 0

    return ClearResult(
        success=True,
        cleared_count=count,
        message=f"Deleted {count} activity events"
    )


# ============ PORTFOLIO OPERATIONS ============

@router.post("/portfolio/clear", response_model=ClearResult)
async def clear_portfolio():
    """Clear all portfolio holdings and cash"""
    from database import get_db
    from database.models import PortfolioHolding, CashHolding

    with get_db() as db:
        holdings_count = db.query(PortfolioHolding).delete()
        cash_count = db.query(CashHolding).delete()
        db.commit()

    return ClearResult(
        success=True,
        cleared_count=holdings_count + cash_count,
        message=f"Cleared {holdings_count} holdings and {cash_count} cash entries"
    )


# ============ CLEAN SLATE - ALL AT ONCE ============

class CleanSlateResult(BaseModel):
    success: bool
    results: dict
    message: str


@router.post("/clean-slate", response_model=CleanSlateResult)
async def clean_slate(
    clear_inbox: bool = True,
    clear_tasks: bool = True,
    clear_bills: bool = True,
    clear_activity: bool = True,
    clear_portfolio: bool = False,  # Default false - portfolio is usually important
    clear_projects: bool = False,
    clear_contractors: bool = False,
):
    """
    Clean slate - reset multiple data categories at once.
    By default clears inbox, tasks, bills, and activity.
    Portfolio and contractors are preserved unless explicitly requested.
    """
    from database import get_db
    from database.models import (
        InboxMessage, MaintenanceTask, Bill,
        PortfolioHolding, CashHolding, Project, ProjectMilestone,
        Contractor, ContractorJob
    )
    from sqlalchemy import text

    results = {}

    with get_db() as db:
        if clear_inbox:
            count = db.query(InboxMessage).delete()
            results["inbox"] = count

        if clear_tasks:
            count = db.query(MaintenanceTask).delete()
            results["tasks"] = count

        if clear_bills:
            count = db.query(Bill).delete()
            results["bills"] = count

        if clear_activity:
            try:
                result = db.execute(text("DELETE FROM event_log"))
                results["activity"] = result.rowcount
            except Exception:
                results["activity"] = 0

        if clear_portfolio:
            holdings = db.query(PortfolioHolding).delete()
            cash = db.query(CashHolding).delete()
            results["portfolio"] = holdings + cash

        if clear_projects:
            milestones = db.query(ProjectMilestone).delete()
            projects = db.query(Project).delete()
            results["projects"] = projects + milestones

        if clear_contractors:
            jobs = db.query(ContractorJob).delete()
            contractors = db.query(Contractor).delete()
            results["contractors"] = contractors + jobs

        db.commit()

    total = sum(results.values())
    return CleanSlateResult(
        success=True,
        results=results,
        message=f"Clean slate complete. Cleared {total} total records."
    )


# ============ DATA COUNTS (for UI) ============

class DataCounts(BaseModel):
    inbox_messages: int
    unread_messages: int
    pending_tasks: int
    completed_tasks: int
    unpaid_bills: int
    paid_bills: int
    activity_events: int
    portfolio_holdings: int
    projects: int
    contractors: int


@router.get("/counts", response_model=DataCounts)
async def get_data_counts():
    """Get counts of all data for the UI"""
    from database import get_db
    from database.models import (
        InboxMessage, MaintenanceTask, Bill,
        PortfolioHolding, Project, Contractor
    )
    from sqlalchemy import text

    with get_db() as db:
        inbox_total = db.query(InboxMessage).count()
        unread = db.query(InboxMessage).filter(InboxMessage.is_read.is_(False)).count()

        pending_tasks = db.query(MaintenanceTask).filter(
            MaintenanceTask.status.in_(["pending", "in_progress"])
        ).count()
        completed_tasks = db.query(MaintenanceTask).filter(
            MaintenanceTask.status == "completed"
        ).count()

        unpaid_bills = db.query(Bill).filter(Bill.is_paid.is_(False)).count()
        paid_bills = db.query(Bill).filter(Bill.is_paid.is_(True)).count()

        # Use raw SQL for event_log to avoid schema mismatch issues
        try:
            result = db.execute(text("SELECT COUNT(*) FROM event_log"))
            activity = result.scalar() or 0
        except Exception:
            activity = 0

        holdings = db.query(PortfolioHolding).count()
        projects = db.query(Project).count()
        contractors = db.query(Contractor).count()

    return DataCounts(
        inbox_messages=inbox_total,
        unread_messages=unread,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        unpaid_bills=unpaid_bills,
        paid_bills=paid_bills,
        activity_events=activity,
        portfolio_holdings=holdings,
        projects=projects,
        contractors=contractors
    )
