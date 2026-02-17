"""
Household Heartbeat Checker for MyCasa Pro
==========================================

Proactive household monitoring. Runs 2-4x/day, rotates through checks.
Mirrors Galidima's heartbeat behavior.

USAGE:
    checker = HouseholdHeartbeatChecker(tenant_id)
    result = await checker.run_heartbeat()
    
    if result.status == 'HEARTBEAT_OK':
        # Nothing needs attention
        pass
    else:
        # Notify user of findings
        for finding in result.findings:
            notify_user(finding)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import json
from pathlib import Path

logger = logging.getLogger("mycasa.heartbeat")

# Import tenant identity
from core.tenant_identity import TenantIdentityManager
from database import get_db
from database.models import InboxMessage, MaintenanceTask, Bill, Notification, SpendGuardrailAlert


class UrgencyLevel(str, Enum):
    """How urgent is a finding"""
    LOW = "low"           # Can wait for next check
    MEDIUM = "medium"     # Should mention soon
    HIGH = "high"         # Mention now
    CRITICAL = "critical" # Interrupt quiet hours


class CheckType(str, Enum):
    """Types of heartbeat checks"""
    EMAIL = "email"
    CALENDAR = "calendar"
    WEATHER = "weather"
    BILLS = "bills"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    PORTFOLIO = "portfolio"


@dataclass
class HeartbeatFinding:
    """A single finding from a heartbeat check"""
    check_type: str
    title: str
    description: str
    urgency: UrgencyLevel
    source: str  # What system found this
    timestamp: datetime = field(default_factory=datetime.utcnow)
    action_required: bool = True
    action_suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['urgency'] = self.urgency.value
        return data


@dataclass
class HeartbeatResult:
    """Result of a heartbeat check cycle"""
    status: str  # 'HEARTBEAT_OK' or 'HAS_FINDINGS'
    findings: List[HeartbeatFinding] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    next_check_due: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['next_check_due'] = self.next_check_due.isoformat() if self.next_check_due else None
        data['findings'] = [f.to_dict() for f in self.findings]
        return data


class HouseholdHeartbeatChecker:
    """
    Proactive household monitoring.
    Runs 2-4x/day, rotates through checks.
    """
    
    # Default check intervals (hours)
    DEFAULT_CHECK_INTERVALS = {
        CheckType.EMAIL: 6,
        CheckType.CALENDAR: 12,
        CheckType.WEATHER: 8,
        CheckType.BILLS: 24,
        CheckType.MAINTENANCE: 24,
        CheckType.SECURITY: 6,
        CheckType.PORTFOLIO: 1,
    }
    
    # Quiet hours (24h format)
    DEFAULT_QUIET_HOURS = {
        'start': 23,  # 11 PM
        'end': 8,     # 8 AM
    }
    
    def __init__(self, tenant_id: str):
        """
        Initialize heartbeat checker.
        
        Args:
            tenant_id: Tenant identifier
        """
        self.tenant_id = tenant_id
        self.identity_manager = TenantIdentityManager(tenant_id)
        self.tenant_dir = self.identity_manager.tenant_dir
        self.state_path = self.tenant_dir / "memory" / "heartbeat-state.json"
        
        # Load configuration
        self.check_intervals = self.DEFAULT_CHECK_INTERVALS.copy()
        self.quiet_hours = self.DEFAULT_QUIET_HOURS.copy()
        self._load_config()
    
    def _load_config(self) -> None:
        """Load custom config from tenant identity files (best-effort)."""
        try:
            identity = self.identity_manager.load_identity_package()
            heartbeat_text = identity.get("heartbeat") or ""
            if "quiet_hours_start" in heartbeat_text:
                pass
        except Exception:
            # Defaults are fine if tenant config is missing
            return
    
    def _load_state(self) -> Dict[str, Any]:
        """Load heartbeat state from file"""
        if not self.state_path.exists():
            return {
                'lastChecks': {},
                'lastConsolidation': None,
            }
        
        try:
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"[Heartbeat] Failed to load state: {e}")
            return {
                'lastChecks': {},
                'lastConsolidation': None,
            }
    
    def _save_state(self, state: Dict[str, Any]) -> None:
        """Save heartbeat state to file"""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"[Heartbeat] Failed to save state: {e}")
    
    def _get_due_checks(self) -> List[CheckType]:
        """
        Determine which checks are due based on last run times.
        
        Returns:
            List of check types that are due
        """
        state = self._load_state()
        last_checks = state.get('lastChecks', {})
        
        now = datetime.utcnow()
        due_checks = []
        
        for check_type, interval_hours in self.check_intervals.items():
            last_check_str = last_checks.get(check_type.value)
            
            if last_check_str:
                last_check = datetime.fromisoformat(last_check_str)
                elapsed = (now - last_check).total_seconds() / 3600  # hours
                
                if elapsed >= interval_hours:
                    due_checks.append(check_type)
            else:
                # Never checked before - do it now
                due_checks.append(check_type)
        
        return due_checks
    
    def _update_check_timestamp(self, check_type: CheckType) -> None:
        """Update last check timestamp for a check type"""
        state = self._load_state()
        state['lastChecks'][check_type.value] = datetime.utcnow().isoformat()
        self._save_state(state)
    
    def _is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours"""
        now = datetime.now()
        current_hour = now.hour
        
        quiet_start = self.quiet_hours['start']
        quiet_end = self.quiet_hours['end']
        
        # Handle overnight quiet hours (e.g., 23:00 - 08:00)
        if quiet_start > quiet_end:
            return current_hour >= quiet_start or current_hour < quiet_end
        else:
            return quiet_start <= current_hour < quiet_end
    
    async def run_heartbeat(self) -> HeartbeatResult:
        """
        Run a single heartbeat check cycle.
        
        Returns:
            HeartbeatResult with findings
        """
        logger.info(f"[Heartbeat] Running heartbeat for tenant {self.tenant_id}")
        
        findings = []
        checks_run = []
        
        # Get checks that are due
        checks_due = self._get_due_checks()
        
        if not checks_due:
            logger.debug(f"[Heartbeat] No checks due")
            return HeartbeatResult(
                status='HEARTBEAT_OK',
                findings=[],
                checks_run=[],
                next_check_due=self._calculate_next_check_time()
            )
        
        # Run each due check
        for check_type in checks_due:
            try:
                result = await self._run_check(check_type)
                checks_run.append(check_type.value)
                
                if result:
                    findings.append(result)
                
                # Update timestamp
                self._update_check_timestamp(check_type)
                
            except Exception as e:
                logger.error(f"[Heartbeat] Check {check_type.value} failed: {e}")
                # Create error finding
                findings.append(HeartbeatFinding(
                    check_type=check_type.value,
                    title=f"Check failed: {check_type.value}",
                    description=str(e),
                    urgency=UrgencyLevel.MEDIUM,
                    source="heartbeat_checker"
                ))
        
        # Filter findings based on quiet hours
        if self._is_quiet_hours():
            # Only keep critical findings during quiet hours
            findings = [f for f in findings if f.urgency == UrgencyLevel.CRITICAL]
            logger.debug(f"[Heartbeat] Quiet hours - filtered to {len(findings)} critical findings")
        
        # Build result
        status = 'HAS_FINDINGS' if findings else 'HEARTBEAT_OK'
        
        result = HeartbeatResult(
            status=status,
            findings=findings,
            checks_run=checks_run,
            next_check_due=self._calculate_next_check_time()
        )

        # Persist findings as notifications
        if findings:
            with get_db() as db:
                for finding in findings:
                    note = Notification(
                        title=finding.title,
                        message=finding.description,
                        category=finding.check_type,
                        priority=finding.urgency.value,
                    )
                    db.add(note)
                db.commit()
        
        logger.info(f"[Heartbeat] Complete: {status} with {len(findings)} findings")
        
        return result
    
    async def _run_check(self, check_type: CheckType) -> Optional[HeartbeatFinding]:
        """
        Run a single check type.
        
        Args:
            check_type: Type of check to run
            
        Returns:
            HeartbeatFinding if something needs attention, None otherwise
        """
        check_methods = {
            CheckType.EMAIL: self._check_email,
            CheckType.CALENDAR: self._check_calendar,
            CheckType.WEATHER: self._check_weather,
            CheckType.BILLS: self._check_bills,
            CheckType.MAINTENANCE: self._check_maintenance,
            CheckType.SECURITY: self._check_security,
            CheckType.PORTFOLIO: self._check_portfolio,
        }
        
        method = check_methods.get(check_type)
        if not method:
            logger.warning(f"[Heartbeat] Unknown check type: {check_type}")
            return None
        
        return await method()
    
    async def _check_email(self) -> Optional[HeartbeatFinding]:
        """Check email inbox for urgent messages"""
        now = datetime.utcnow()
        cutoff = now - timedelta(days=7)
        with get_db() as db:
            unread = (
                db.query(InboxMessage)
                .filter(
                    InboxMessage.source == "gmail",
                    InboxMessage.is_read == False,  # noqa: E712
                    InboxMessage.timestamp >= cutoff,
                )
                .order_by(InboxMessage.timestamp.desc())
                .all()
            )
        if not unread:
            return None
        urgent = [m for m in unread if (m.urgency or "medium") in {"high"}]
        title = f"{len(unread)} unread email{'s' if len(unread) != 1 else ''}"
        if urgent:
            title = f"{len(urgent)} urgent email{'s' if len(urgent) != 1 else ''}"
        latest = unread[0]
        desc = latest.preview or latest.subject or "Unread email requires attention."
        return HeartbeatFinding(
            check_type=CheckType.EMAIL.value,
            title=title,
            description=desc,
            urgency=UrgencyLevel.HIGH if urgent else UrgencyLevel.MEDIUM,
            source="inbox",
            metadata={"unread": len(unread), "urgent": len(urgent)},
        )
    
    async def _check_calendar(self) -> Optional[HeartbeatFinding]:
        """Check calendar for upcoming events"""
        now = datetime.utcnow()
        upcoming = now + timedelta(hours=24)
        with get_db() as db:
            events = (
                db.query(InboxMessage)
                .filter(
                    InboxMessage.domain == "calendar",
                    InboxMessage.timestamp >= now,
                    InboxMessage.timestamp <= upcoming,
                )
                .order_by(InboxMessage.timestamp.asc())
                .all()
            )
        if not events:
            return None
        next_event = events[0]
        title = f"{len(events)} upcoming calendar event{'s' if len(events) != 1 else ''}"
        desc = next_event.subject or next_event.preview or "Upcoming calendar event"
        return HeartbeatFinding(
            check_type=CheckType.CALENDAR.value,
            title=title,
            description=desc,
            urgency=UrgencyLevel.MEDIUM,
            source="calendar",
            metadata={"events": len(events)},
        )
    
    async def _check_weather(self) -> Optional[HeartbeatFinding]:
        """Check weather for alerts"""
        with get_db() as db:
            alerts = (
                db.query(Notification)
                .filter(
                    Notification.category == "weather",
                    Notification.is_read == False,  # noqa: E712
                )
                .order_by(Notification.created_at.desc())
                .all()
            )
        if not alerts:
            return None
        latest = alerts[0]
        return HeartbeatFinding(
            check_type=CheckType.WEATHER.value,
            title=latest.title or "Weather alert",
            description=latest.message or "Weather alert requires attention.",
            urgency=UrgencyLevel.HIGH,
            source="notifications",
            metadata={"alerts": len(alerts)},
        )
    
    async def _check_bills(self) -> Optional[HeartbeatFinding]:
        """Check for bills due soon"""
        today = datetime.utcnow().date()
        horizon = today + timedelta(days=7)
        with get_db() as db:
            due = (
                db.query(Bill)
                .filter(
                    Bill.is_paid == False,  # noqa: E712
                    Bill.due_date != None,  # noqa: E711
                    Bill.due_date <= horizon,
                )
                .order_by(Bill.due_date.asc())
                .all()
            )
        if not due:
            return None
        overdue = [b for b in due if b.due_date and b.due_date < today]
        next_bill = due[0]
        title = f"{len(due)} bill{'s' if len(due) != 1 else ''} due soon"
        if overdue:
            title = f"{len(overdue)} overdue bill{'s' if len(overdue) != 1 else ''}"
        desc = f"{next_bill.name} due {next_bill.due_date}" if next_bill.due_date else next_bill.name
        return HeartbeatFinding(
            check_type=CheckType.BILLS.value,
            title=title,
            description=desc,
            urgency=UrgencyLevel.HIGH if overdue else UrgencyLevel.MEDIUM,
            source="finance",
            metadata={"due": len(due), "overdue": len(overdue)},
        )
    
    async def _check_maintenance(self) -> Optional[HeartbeatFinding]:
        """Check for overdue maintenance tasks"""
        today = datetime.utcnow().date()
        horizon = today + timedelta(days=7)
        with get_db() as db:
            tasks = (
                db.query(MaintenanceTask)
                .filter(
                    MaintenanceTask.status.notin_(["completed", "cancelled"]),
                    MaintenanceTask.due_date != None,  # noqa: E711
                    MaintenanceTask.due_date <= horizon,
                )
                .order_by(MaintenanceTask.due_date.asc())
                .all()
            )
        if not tasks:
            return None
        overdue = [t for t in tasks if t.due_date and t.due_date < today]
        next_task = tasks[0]
        title = f"{len(tasks)} maintenance task{'s' if len(tasks) != 1 else ''} due soon"
        if overdue:
            title = f"{len(overdue)} overdue maintenance task{'s' if len(overdue) != 1 else ''}"
        desc = next_task.title
        return HeartbeatFinding(
            check_type=CheckType.MAINTENANCE.value,
            title=title,
            description=desc,
            urgency=UrgencyLevel.HIGH if overdue else UrgencyLevel.MEDIUM,
            source="maintenance",
            metadata={"due": len(tasks), "overdue": len(overdue)},
        )
    
    async def _check_security(self) -> Optional[HeartbeatFinding]:
        """Check security system for alerts"""
        with get_db() as db:
            alerts = (
                db.query(Notification)
                .filter(
                    Notification.category == "security",
                    Notification.is_read == False,  # noqa: E712
                )
                .order_by(Notification.created_at.desc())
                .all()
            )
        if not alerts:
            return None
        latest = alerts[0]
        return HeartbeatFinding(
            check_type=CheckType.SECURITY.value,
            title=latest.title or "Security alert",
            description=latest.message or "Security alert requires attention.",
            urgency=UrgencyLevel.CRITICAL,
            source="notifications",
            metadata={"alerts": len(alerts)},
        )
    
    async def _check_portfolio(self) -> Optional[HeartbeatFinding]:
        """Check portfolio for significant moves"""
        with get_db() as db:
            alerts = (
                db.query(SpendGuardrailAlert)
                .filter(SpendGuardrailAlert.acknowledged == False)  # noqa: E712
                .order_by(SpendGuardrailAlert.created_at.desc())
                .all()
            )
        if not alerts:
            return None
        latest = alerts[0]
        title = latest.message or "Spending alert"
        return HeartbeatFinding(
            check_type=CheckType.PORTFOLIO.value,
            title=title,
            description=latest.message or "Spending guardrail triggered.",
            urgency=UrgencyLevel.HIGH,
            source="finance",
            metadata={"alerts": len(alerts)},
        )
    
    def _calculate_next_check_time(self) -> datetime:
        """Calculate when the next check is due"""
        state = self._load_state()
        last_checks = state.get('lastChecks', {})
        
        next_check = None
        
        for check_type, interval_hours in self.check_intervals.items():
            last_check_str = last_checks.get(check_type.value)
            
            if last_check_str:
                last_check = datetime.fromisoformat(last_check_str)
                due_time = last_check + timedelta(hours=interval_hours)
                
                if next_check is None or due_time < next_check:
                    next_check = due_time
        
        return next_check or (datetime.utcnow() + timedelta(hours=1))
    
    async def run_memory_consolidation(self) -> Dict[str, Any]:
        """
        Run memory consolidation (review daily notes, update MEMORY.md).
        This should be run periodically (every few days).
        
        Returns:
            Dict with consolidation results
        """
        logger.info(f"[Heartbeat] Running memory consolidation for tenant {self.tenant_id}")
        
        # Deterministic consolidation: append recent note summaries into MEMORY.md
        identity = self.identity_manager.load_identity_package()
        daily_notes = identity.get("daily_notes", {})
        memory_path = self.tenant_dir / "MEMORY.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not memory_path.exists():
            memory_path.write_text("# MEMORY.md — Household Memory\n\n", encoding="utf-8")

        summary_lines = []
        for day, content in sorted(daily_notes.items(), reverse=True):
            snippet = content.strip().splitlines()
            snippet = "\n".join(snippet[:6]) if snippet else ""
            summary_lines.append(f"### {day}\n{snippet}\n")
        if summary_lines:
            with memory_path.open("a", encoding="utf-8") as f:
                f.write(f"\n## Consolidation {datetime.utcnow().isoformat()}\n")
                f.write("\n".join(summary_lines))
        
        state = self._load_state()
        state['lastConsolidation'] = datetime.utcnow().isoformat()
        self._save_state(state)
        
        return {
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat(),
        }
