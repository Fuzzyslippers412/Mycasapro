"""
MyCasa Pro - Bill & Task Reminders
==================================

Sends reminders via WhatsApp through wacli.
"""

import subprocess
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from database import get_db
from database.models import Bill, MaintenanceTask, Notification


class ReminderAgent:
    """
    Handles sending reminders for bills and tasks.
    Uses local wacli for WhatsApp delivery.
    """
    
    # Default reminder settings
    BILL_REMIND_DAYS = [7, 3, 1, 0]  # Days before due date to remind
    TASK_REMIND_DAYS = [3, 1, 0]
    
    def __init__(self, owner_phone: str = "+12677180107"):
        self.owner_phone = owner_phone
        self._last_check: Optional[datetime] = None
    
    def _send_whatsapp(self, message: str) -> bool:
        """Send WhatsApp message via wacli"""
        try:
            result = subprocess.run(
                [
                    "wacli", "send", "text",
                    "--to", self.owner_phone,
                    "--message", message,
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"[Reminders] WhatsApp sent: {message[:50]}...")
                return True
            else:
                print(f"[Reminders] WhatsApp failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("[Reminders] WhatsApp timeout")
            return False
        except FileNotFoundError:
            print("[Reminders] wacli not found")
            return False
        except Exception as e:
            print(f"[Reminders] WhatsApp error: {e}")
            return False
    
    def _create_notification(self, title: str, message: str, category: str, priority: str = "medium"):
        """Create an in-app notification"""
        try:
            with get_db() as db:
                notification = Notification(
                    title=title,
                    message=message,
                    category=category,
                    priority=priority
                )
                db.add(notification)
            return True
        except Exception as e:
            print(f"[Reminders] Failed to create notification: {e}")
            return False
    
    def check_bill_reminders(self) -> Dict[str, Any]:
        """
        Check for bills that need reminders.
        Returns summary of reminders sent.
        """
        today = date.today()
        reminders_sent = []
        
        with get_db() as db:
            # Get unpaid bills
            unpaid_bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date != None
            ).all()
            
            for bill in unpaid_bills:
                days_until = (bill.due_date - today).days
                
                # Check if we should remind
                if days_until in self.BILL_REMIND_DAYS:
                    # Format message
                    if days_until == 0:
                        urgency = "🚨 DUE TODAY"
                        priority = "urgent"
                    elif days_until == 1:
                        urgency = "⚠️ Due tomorrow"
                        priority = "high"
                    elif days_until <= 3:
                        urgency = f"📅 Due in {days_until} days"
                        priority = "medium"
                    else:
                        urgency = f"📋 Due in {days_until} days"
                        priority = "low"
                    
                    amount_str = f"${bill.amount:,.2f}" if bill.amount else "Amount TBD"
                    auto_pay_note = " (auto-pay enabled)" if bill.auto_pay else ""
                    
                    message = f"{urgency}: {bill.name}\n💰 {amount_str}{auto_pay_note}\n📆 Due: {bill.due_date.strftime('%b %d, %Y')}"
                    
                    # Send WhatsApp if urgent or high priority
                    if priority in ["urgent", "high"]:
                        self._send_whatsapp(message)
                    
                    # Always create in-app notification
                    self._create_notification(
                        title=f"Bill Reminder: {bill.name}",
                        message=message,
                        category="finance",
                        priority=priority
                    )
                    
                    reminders_sent.append({
                        "bill_id": bill.id,
                        "name": bill.name,
                        "days_until": days_until,
                        "amount": bill.amount,
                        "priority": priority,
                        "whatsapp_sent": priority in ["urgent", "high"]
                    })
        
        self._last_check = datetime.now()
        
        return {
            "success": True,
            "checked_at": self._last_check.isoformat(),
            "reminders_sent": len(reminders_sent),
            "details": reminders_sent
        }
    
    def check_task_reminders(self) -> Dict[str, Any]:
        """Check for maintenance tasks that need reminders"""
        today = date.today()
        reminders_sent = []
        
        with get_db() as db:
            # Get pending tasks with due dates
            pending_tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status.in_(["pending", "in_progress"]),
                MaintenanceTask.due_date != None
            ).all()
            
            for task in pending_tasks:
                days_until = (task.due_date - today).days
                
                if days_until in self.TASK_REMIND_DAYS:
                    if days_until == 0:
                        urgency = "🚨 DUE TODAY"
                        priority = "high"
                    elif days_until == 1:
                        urgency = "⚠️ Due tomorrow"
                        priority = "medium"
                    else:
                        urgency = f"📋 Due in {days_until} days"
                        priority = "low"
                    
                    message = f"{urgency}: {task.title}\n📂 {task.category or 'General'}\n🔹 Priority: {task.priority}"
                    
                    # WhatsApp for urgent tasks
                    if priority == "high" and task.priority in ["high", "urgent"]:
                        self._send_whatsapp(message)
                    
                    self._create_notification(
                        title=f"Task Reminder: {task.title}",
                        message=message,
                        category="maintenance",
                        priority=priority
                    )
                    
                    reminders_sent.append({
                        "task_id": task.id,
                        "title": task.title,
                        "days_until": days_until,
                        "priority": priority
                    })
        
        return {
            "success": True,
            "checked_at": datetime.now().isoformat(),
            "reminders_sent": len(reminders_sent),
            "details": reminders_sent
        }
    
    def check_all_reminders(self) -> Dict[str, Any]:
        """Check both bill and task reminders"""
        bill_result = self.check_bill_reminders()
        task_result = self.check_task_reminders()
        
        total_sent = bill_result["reminders_sent"] + task_result["reminders_sent"]
        
        return {
            "success": True,
            "checked_at": datetime.now().isoformat(),
            "total_reminders": total_sent,
            "bills": bill_result,
            "tasks": task_result
        }
    
    def send_daily_summary(self) -> Dict[str, Any]:
        """
        Send a daily financial summary via WhatsApp.
        Best run in the morning (e.g., 8am).
        """
        today = date.today()
        week_ahead = today + timedelta(days=7)
        
        with get_db() as db:
            # Bills due this week
            upcoming_bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date >= today,
                Bill.due_date <= week_ahead
            ).order_by(Bill.due_date).all()
            
            # Overdue bills
            overdue_bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date < today
            ).all()
            
            # Pending tasks
            pending_tasks = db.query(MaintenanceTask).filter(
                MaintenanceTask.status == "pending"
            ).count()
        
        # Build summary message
        lines = [f"🏠 *MyCasa Daily Summary*\n📅 {today.strftime('%A, %B %d')}"]
        
        if overdue_bills:
            total_overdue = sum(b.amount or 0 for b in overdue_bills)
            lines.append(f"\n🚨 *OVERDUE BILLS: {len(overdue_bills)}*")
            lines.append(f"Total: ${total_overdue:,.2f}")
            for b in overdue_bills[:3]:
                lines.append(f"  • {b.name}: ${b.amount:,.2f}")
        
        if upcoming_bills:
            total_upcoming = sum(b.amount or 0 for b in upcoming_bills)
            lines.append(f"\n📋 *This Week: {len(upcoming_bills)} bills*")
            lines.append(f"Total: ${total_upcoming:,.2f}")
            for b in upcoming_bills[:5]:
                days = (b.due_date - today).days
                day_str = "Today" if days == 0 else f"in {days}d"
                lines.append(f"  • {b.name} ({day_str}): ${b.amount:,.2f}")
        
        if pending_tasks > 0:
            lines.append(f"\n🔧 *Pending Tasks: {pending_tasks}*")
        
        if not overdue_bills and not upcoming_bills:
            lines.append("\n✅ All clear! No bills due this week.")
        
        message = "\n".join(lines)
        
        sent = self._send_whatsapp(message)
        
        return {
            "success": sent,
            "message": message,
            "stats": {
                "overdue_bills": len(overdue_bills),
                "upcoming_bills": len(upcoming_bills),
                "pending_tasks": pending_tasks
            }
        }


# Singleton instance
_reminder_agent: Optional[ReminderAgent] = None


def get_reminder_agent() -> ReminderAgent:
    global _reminder_agent
    if _reminder_agent is None:
        _reminder_agent = ReminderAgent()
    return _reminder_agent
