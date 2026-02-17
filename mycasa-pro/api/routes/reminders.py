"""
MyCasa Pro - Reminders API Routes
=================================

Bill and task reminder management.
"""

from fastapi import APIRouter
from typing import Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents.reminders import get_reminder_agent

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.post("/check")
async def check_all_reminders() -> Dict[str, Any]:
    """
    Check for and send all due reminders.
    Sends WhatsApp for urgent items, creates notifications for all.
    """
    agent = get_reminder_agent()
    return agent.check_all_reminders()


@router.post("/check/bills")
async def check_bill_reminders() -> Dict[str, Any]:
    """Check and send bill reminders only"""
    agent = get_reminder_agent()
    return agent.check_bill_reminders()


@router.post("/check/tasks")
async def check_task_reminders() -> Dict[str, Any]:
    """Check and send task reminders only"""
    agent = get_reminder_agent()
    return agent.check_task_reminders()


@router.post("/daily-summary")
async def send_daily_summary() -> Dict[str, Any]:
    """
    Send daily financial summary via WhatsApp.
    Includes upcoming bills, overdue items, and task count.
    """
    agent = get_reminder_agent()
    return agent.send_daily_summary()


@router.get("/settings")
async def get_reminder_settings() -> Dict[str, Any]:
    """Get current reminder settings"""
    agent = get_reminder_agent()
    return {
        "bill_remind_days": agent.BILL_REMIND_DAYS,
        "task_remind_days": agent.TASK_REMIND_DAYS,
        "owner_phone": agent.owner_phone,
        "last_check": agent._last_check.isoformat() if agent._last_check else None,
    }
