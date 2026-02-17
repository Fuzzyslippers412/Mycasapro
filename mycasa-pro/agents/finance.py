"""
Finance Agent for MyCasa Pro
Responsible for household financial tracking, analysis, and routine financial operations.

Finance Manager Requirements:
- Track system costs (cap $1k/month)
- Require income source intake (primary: JPM brokerage)
- Enforce visibility-based spend limits ($10k/month, $150/day)
- Normalize spend vs transfers
- Block finance logic until intake is complete
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent
from database import get_db
from database.models import (
    Bill, Transaction, Budget, 
    FinanceManagerSettings, IncomeSource, SystemCostEntry, SpendGuardrailAlert
)
from config.settings import PORTFOLIO, ALERTS

# Try to import yfinance for portfolio data
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

# Try to import Polymarket BTC 15m skill
try:
    from backend.skills.polymarket_btc_15m.skill_interface import analyze_btc_15m_direction, quick_call
    POLYMARKET_SKILL_AVAILABLE = True
except ImportError:
    POLYMARKET_SKILL_AVAILABLE = False


class FinanceAgent(BaseAgent):
    """Agent responsible for household financial operations"""
    
    def __init__(self):
        super().__init__("finance")
        self.portfolio_config = PORTFOLIO
        self.alert_thresholds = ALERTS
        self._portfolio_cache = None
        self._cache_timestamp = None
        self._settings_cache = None
    
    # ============ INTAKE & SETTINGS ============
    
    def is_intake_complete(self) -> bool:
        """Check if finance manager intake has been completed"""
        settings = self.get_settings()
        return settings.get("intake_complete", False)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get finance manager settings"""
        with get_db() as db:
            settings = db.query(FinanceManagerSettings).first()
            if not settings:
                return {
                    "intake_complete": False,
                    "system_cost_budget": 1000.0,
                    "monthly_spend_limit": 10000.0,
                    "daily_soft_cap": 150.0,
                    "spend_alerts_enabled": True,
                    "preferred_payment_rails": []
                }
            
            return {
                "id": settings.id,
                "intake_complete": settings.intake_complete,
                "intake_completed_at": settings.intake_completed_at.isoformat() if settings.intake_completed_at else None,
                "system_cost_budget": settings.system_cost_budget,
                "system_cost_warn_70": settings.system_cost_warn_70,
                "system_cost_warn_85": settings.system_cost_warn_85,
                "system_cost_warn_95": settings.system_cost_warn_95,
                "monthly_spend_limit": settings.monthly_spend_limit,
                "daily_soft_cap": settings.daily_soft_cap,
                "spend_alerts_enabled": settings.spend_alerts_enabled,
                "preferred_payment_rails": json.loads(settings.preferred_payment_rails) if settings.preferred_payment_rails else []
            }
    
    def update_settings(self, **kwargs) -> Dict[str, Any]:
        """Update finance manager settings"""
        with get_db() as db:
            settings = db.query(FinanceManagerSettings).first()
            if not settings:
                settings = FinanceManagerSettings()
                db.add(settings)
            
            for key, value in kwargs.items():
                if key == "preferred_payment_rails" and isinstance(value, list):
                    value = json.dumps(value)
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            db.commit()
            self.log_action("settings_updated", json.dumps(kwargs))
            
            return {"success": True, "settings": self.get_settings()}
    
    def complete_intake(
        self,
        primary_income_source: Dict[str, Any],
        secondary_income_sources: List[Dict[str, Any]] = None,
        system_cost_budget: float = 1000.0,
        monthly_spend_limit: float = 10000.0,
        daily_soft_cap: float = 150.0,
        preferred_payment_rails: List[str] = None
    ) -> Dict[str, Any]:
        """
        Complete the finance manager intake flow.
        Required before any finance logic runs.
        """
        with get_db() as db:
            # Create/update settings
            settings = db.query(FinanceManagerSettings).first()
            if not settings:
                settings = FinanceManagerSettings()
                db.add(settings)
            
            settings.intake_complete = True
            settings.intake_completed_at = datetime.utcnow()
            settings.system_cost_budget = system_cost_budget
            settings.monthly_spend_limit = monthly_spend_limit
            settings.daily_soft_cap = daily_soft_cap
            settings.preferred_payment_rails = json.dumps(preferred_payment_rails or ["card", "ach"])
            
            # Add primary income source
            primary = IncomeSource(
                name=primary_income_source.get("name"),
                account_type=primary_income_source.get("account_type", "brokerage"),
                institution=primary_income_source.get("institution"),
                is_primary=True,
                income_type=primary_income_source.get("income_type", "investment"),
                expected_monthly_min=primary_income_source.get("expected_monthly_min"),
                expected_monthly_max=primary_income_source.get("expected_monthly_max"),
                notes=primary_income_source.get("notes")
            )
            db.add(primary)
            
            # Add secondary sources
            if secondary_income_sources:
                for src in secondary_income_sources:
                    secondary = IncomeSource(
                        name=src.get("name"),
                        account_type=src.get("account_type"),
                        institution=src.get("institution"),
                        is_primary=False,
                        income_type=src.get("income_type"),
                        expected_monthly_min=src.get("expected_monthly_min"),
                        expected_monthly_max=src.get("expected_monthly_max"),
                        notes=src.get("notes")
                    )
                    db.add(secondary)
            
            db.commit()
            
            self.log_action("intake_completed", json.dumps({
                "primary_source": primary_income_source.get("name"),
                "secondary_count": len(secondary_income_sources or []),
                "system_cost_budget": system_cost_budget,
                "monthly_spend_limit": monthly_spend_limit,
                "daily_soft_cap": daily_soft_cap
            }))
            
            return {
                "success": True,
                "message": "Finance Manager intake complete. All finance features are now active.",
                "settings": self.get_settings()
            }
    
    def get_income_sources(self) -> List[Dict[str, Any]]:
        """Get all income sources"""
        with get_db() as db:
            sources = db.query(IncomeSource).filter(IncomeSource.is_active == True).all()
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "account_type": s.account_type,
                    "institution": s.institution,
                    "is_primary": s.is_primary,
                    "income_type": s.income_type,
                    "expected_monthly_min": s.expected_monthly_min,
                    "expected_monthly_max": s.expected_monthly_max,
                    "notes": s.notes
                }
                for s in sources
            ]
    
    def add_income_source(self, **kwargs) -> Dict[str, Any]:
        """Add a new income source"""
        with get_db() as db:
            source = IncomeSource(**kwargs)
            db.add(source)
            db.commit()
            
            self.log_action("income_source_added", json.dumps({"name": kwargs.get("name")}))
            return {"success": True, "id": source.id}
    
    # ============ SYSTEM COST TRACKING ============
    
    def add_system_cost(
        self,
        amount: float,
        category: str,
        description: str = None,
        service_name: str = None,
        cost_date: date = None,
        is_recurring: bool = False,
        recurrence: str = None
    ) -> Dict[str, Any]:
        """
        Record a MyCasa Pro operational cost.
        Categories: ai_api, hosting, storage, integrations
        """
        with get_db() as db:
            entry = SystemCostEntry(
                amount=amount,
                category=category,
                description=description,
                service_name=service_name,
                date=cost_date or date.today(),
                is_recurring=is_recurring,
                recurrence=recurrence
            )
            db.add(entry)
            db.commit()
            
            # Check thresholds
            self._check_system_cost_thresholds()
            
            self.log_action("system_cost_added", json.dumps({
                "amount": amount,
                "category": category,
                "service": service_name
            }))
            
            return {"success": True, "id": entry.id}
    
    def get_system_costs(self, month: int = None, year: int = None) -> Dict[str, Any]:
        """Get system costs for a given month (defaults to current)"""
        if month is None:
            month = date.today().month
        if year is None:
            year = date.today().year
        
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        with get_db() as db:
            entries = db.query(SystemCostEntry).filter(
                SystemCostEntry.date >= month_start,
                SystemCostEntry.date <= month_end
            ).all()
            
            total = sum(e.amount for e in entries)
            by_category = {}
            by_service = {}
            
            for e in entries:
                by_category[e.category] = by_category.get(e.category, 0) + e.amount
                if e.service_name:
                    by_service[e.service_name] = by_service.get(e.service_name, 0) + e.amount
            
            settings = self.get_settings()
            budget = settings.get("system_cost_budget", 1000.0)
            pct_used = (total / budget * 100) if budget > 0 else 0
            
            return {
                "month": month,
                "year": year,
                "total": round(total, 2),
                "budget": budget,
                "remaining": round(budget - total, 2),
                "pct_used": round(pct_used, 1),
                "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
                "by_service": {k: round(v, 2) for k, v in sorted(by_service.items(), key=lambda x: -x[1])},
                "entry_count": len(entries),
                "status": "ok" if pct_used < 70 else "warning" if pct_used < 95 else "critical"
            }
    
    def forecast_system_costs(self) -> Dict[str, Any]:
        """
        Forecast monthly system cost burn based on current spending.
        Returns projected end-of-month total and recommendations.
        """
        today = date.today()
        month_start = today.replace(day=1)
        days_elapsed = (today - month_start).days + 1
        days_in_month = 30  # Approximate
        
        current = self.get_system_costs()
        total_so_far = current.get("total", 0)
        
        # Project based on daily run rate
        daily_rate = total_so_far / days_elapsed if days_elapsed > 0 else 0
        projected_total = daily_rate * days_in_month
        
        budget = current.get("budget", 1000.0)
        projected_pct = (projected_total / budget * 100) if budget > 0 else 0
        
        recommendations = []
        if projected_pct > 100:
            recommendations.append("🚨 Projected overrun! Consider reducing API calls or switching to cheaper models.")
        elif projected_pct > 85:
            recommendations.append("⚠️ On track to exceed 85% of budget. Monitor closely.")
        
        # Check which categories are driving costs
        by_category = current.get("by_category", {})
        if by_category.get("ai_api", 0) > budget * 0.5:
            recommendations.append("AI/API costs are >50% of budget. Consider caching or batching requests.")
        
        return {
            "current_total": round(total_so_far, 2),
            "days_elapsed": days_elapsed,
            "daily_rate": round(daily_rate, 2),
            "projected_total": round(projected_total, 2),
            "budget": budget,
            "projected_pct": round(projected_pct, 1),
            "status": "ok" if projected_pct < 70 else "warning" if projected_pct < 95 else "critical",
            "recommendations": recommendations
        }
    
    def _check_system_cost_thresholds(self):
        """Check if system costs have crossed warning thresholds"""
        settings = self.get_settings()
        costs = self.get_system_costs()
        
        pct_used = costs.get("pct_used", 0)
        budget = costs.get("budget", 1000)
        total = costs.get("total", 0)
        
        thresholds_to_check = []
        if settings.get("system_cost_warn_70") and pct_used >= 70:
            thresholds_to_check.append(70)
        if settings.get("system_cost_warn_85") and pct_used >= 85:
            thresholds_to_check.append(85)
        if settings.get("system_cost_warn_95") and pct_used >= 95:
            thresholds_to_check.append(95)
        
        if not thresholds_to_check:
            return
        
        # Check for existing unacknowledged alert at same threshold
        with get_db() as db:
            for threshold in thresholds_to_check:
                existing = db.query(SpendGuardrailAlert).filter(
                    SpendGuardrailAlert.alert_type == "system_cost",
                    SpendGuardrailAlert.threshold_pct == threshold,
                    SpendGuardrailAlert.period_date == date.today().replace(day=1),
                    SpendGuardrailAlert.acknowledged == False
                ).first()
                
                if not existing:
                    alert = SpendGuardrailAlert(
                        alert_type="system_cost",
                        threshold_pct=threshold,
                        actual_amount=total,
                        limit_amount=budget,
                        message=f"System costs at {pct_used:.0f}% of ${budget:.0f} monthly budget",
                        period_type="month",
                        period_date=date.today().replace(day=1)
                    )
                    db.add(alert)
            db.commit()
    
    # ============ SPEND GUARDRAILS ============
    
    def check_spend_guardrails(self) -> Dict[str, Any]:
        """
        Check current spend against guardrails.
        Returns warnings and status - does NOT block spending.
        """
        if not self.is_intake_complete():
            return {"error": "Intake not complete", "blocked": True}
        
        settings = self.get_settings()
        monthly_limit = settings.get("monthly_spend_limit", 10000)
        daily_cap = settings.get("daily_soft_cap", 150)
        
        # Get today's spend
        today_spend = self._get_spend_for_date(date.today())
        
        # Get this month's spend
        month_start = date.today().replace(day=1)
        month_spend = self._get_spend_for_period(month_start, date.today())
        
        # Calculate percentages
        daily_pct = (today_spend / daily_cap * 100) if daily_cap > 0 else 0
        monthly_pct = (month_spend / monthly_limit * 100) if monthly_limit > 0 else 0
        
        warnings = []
        
        if daily_pct >= 100:
            warnings.append({
                "type": "daily_limit",
                "severity": "high",
                "message": f"Daily spend (${today_spend:.0f}) exceeds soft cap (${daily_cap:.0f})"
            })
        elif daily_pct >= 80:
            warnings.append({
                "type": "daily_limit",
                "severity": "medium",
                "message": f"Approaching daily cap: ${today_spend:.0f} / ${daily_cap:.0f}"
            })
        
        if monthly_pct >= 100:
            warnings.append({
                "type": "monthly_limit",
                "severity": "high",
                "message": f"Monthly spend (${month_spend:.0f}) exceeds limit (${monthly_limit:.0f})"
            })
        elif monthly_pct >= 85:
            warnings.append({
                "type": "monthly_limit",
                "severity": "high",
                "message": f"At {monthly_pct:.0f}% of monthly limit"
            })
        elif monthly_pct >= 70:
            warnings.append({
                "type": "monthly_limit",
                "severity": "medium",
                "message": f"At {monthly_pct:.0f}% of monthly limit"
            })
        
        return {
            "today": {
                "spent": round(today_spend, 2),
                "cap": daily_cap,
                "pct": round(daily_pct, 1),
                "remaining": round(max(0, daily_cap - today_spend), 2)
            },
            "month": {
                "spent": round(month_spend, 2),
                "limit": monthly_limit,
                "pct": round(monthly_pct, 1),
                "remaining": round(max(0, monthly_limit - month_spend), 2)
            },
            "warnings": warnings,
            "status": "ok" if not warnings else "warning" if all(w["severity"] == "medium" for w in warnings) else "alert"
        }
    
    def _get_spend_for_date(self, spend_date: date) -> float:
        """Get total spend for a specific date (excluding internal transfers)"""
        from database.models import SpendEntry
        
        with get_db() as db:
            entries = db.query(SpendEntry).filter(
                SpendEntry.date == spend_date,
                SpendEntry.is_internal_transfer == False
            ).all()
            return sum(e.amount for e in entries) if entries else 0
    
    def _get_spend_for_period(self, start_date: date, end_date: date) -> float:
        """Get total spend for a date range (excluding internal transfers)"""
        from database.models import SpendEntry
        
        with get_db() as db:
            entries = db.query(SpendEntry).filter(
                SpendEntry.date >= start_date,
                SpendEntry.date <= end_date,
                SpendEntry.is_internal_transfer == False
            ).all()
            return sum(e.amount for e in entries) if entries else 0
    
    def get_guardrail_alerts(self, unacknowledged_only: bool = True) -> List[Dict[str, Any]]:
        """Get spend guardrail alerts"""
        with get_db() as db:
            query = db.query(SpendGuardrailAlert)
            if unacknowledged_only:
                query = query.filter(SpendGuardrailAlert.acknowledged == False)
            
            alerts = query.order_by(SpendGuardrailAlert.created_at.desc()).limit(50).all()
            
            return [
                {
                    "id": a.id,
                    "type": a.alert_type,
                    "threshold_pct": a.threshold_pct,
                    "actual": a.actual_amount,
                    "limit": a.limit_amount,
                    "message": a.message,
                    "period": a.period_type,
                    "period_date": a.period_date.isoformat() if a.period_date else None,
                    "acknowledged": a.acknowledged,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in alerts
            ]
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "user") -> Dict[str, Any]:
        """Acknowledge a guardrail alert"""
        with get_db() as db:
            alert = db.query(SpendGuardrailAlert).filter(SpendGuardrailAlert.id == alert_id).first()
            if not alert:
                return {"success": False, "error": "Alert not found"}
            
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            db.commit()
            
            return {"success": True}
    
    def get_finance_overview(self) -> Dict[str, Any]:
        """
        Get complete finance overview including intake status, guardrails, and costs.
        """
        intake_complete = self.is_intake_complete()
        
        overview = {
            "intake_complete": intake_complete,
            "settings": self.get_settings()
        }
        
        if not intake_complete:
            overview["message"] = "Finance Manager intake required. Complete setup to enable all features."
            overview["blocked_features"] = ["spend_tracking", "budget_alerts", "portfolio_analysis"]
            return overview
        
        # Full overview for completed intake
        overview["income_sources"] = self.get_income_sources()
        overview["guardrails"] = self.check_spend_guardrails()
        overview["system_costs"] = self.get_system_costs()
        overview["system_forecast"] = self.forecast_system_costs()
        overview["alerts"] = self.get_guardrail_alerts(unacknowledged_only=True)
        
        return overview
    
    # ============ ORIGINAL STATUS METHODS ============
    
    def get_status(self) -> Dict[str, Any]:
        """Get finance agent status"""
        intake_complete = self.is_intake_complete()
        
        with get_db() as db:
            unpaid_bills = db.query(Bill).filter(Bill.is_paid == False).count()
            
            # Bills due in next 7 days
            upcoming_due = date.today() + timedelta(days=7)
            bills_due_soon = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date <= upcoming_due
            ).count()
            
            # Overdue bills
            overdue_bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date < date.today()
            ).count()
            
            # Monthly spending (current month)
            month_start = date.today().replace(day=1)
            monthly_expenses = db.query(Transaction).filter(
                Transaction.transaction_type == "expense",
                Transaction.date >= month_start
            ).all()
            total_monthly_spent = sum(t.amount for t in monthly_expenses) if monthly_expenses else 0
        
        # Get portfolio value if possible
        portfolio_value = self._get_portfolio_value()
        
        # Get system costs and guardrails if intake complete
        system_costs = None
        guardrails = None
        unacked_alerts = 0
        
        if intake_complete:
            system_costs = self.get_system_costs()
            guardrails = self.check_spend_guardrails()
            unacked_alerts = len(self.get_guardrail_alerts(unacknowledged_only=True))
        
        # Calculate issues
        issues = overdue_bills + unacked_alerts
        if system_costs and system_costs.get("status") == "critical":
            issues += 1
        
        return {
            "agent": "finance",
            "status": "active" if intake_complete else "pending_intake",
            "intake_complete": intake_complete,
            "metrics": {
                "unpaid_bills": unpaid_bills,
                "bills_due_soon": bills_due_soon,
                "overdue_bills": overdue_bills,
                "monthly_spending": round(total_monthly_spent, 2),
                "portfolio_value": portfolio_value,
                "system_cost_pct": system_costs.get("pct_used") if system_costs else None,
                "monthly_spend_pct": guardrails.get("month", {}).get("pct") if guardrails else None,
                "unacked_alerts": unacked_alerts,
                "issues": issues
            },
            "system_costs": system_costs,
            "guardrails": guardrails,
            "last_check": datetime.now().isoformat()
        }
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending financial tasks (unpaid bills, etc.)"""
        tasks = []
        
        with get_db() as db:
            # Unpaid bills
            unpaid = db.query(Bill).filter(Bill.is_paid == False).order_by(Bill.due_date.asc()).all()
            for bill in unpaid:
                days_until = (bill.due_date - date.today()).days if bill.due_date else None
                priority = "urgent" if days_until and days_until < 0 else \
                          "high" if days_until and days_until <= 3 else \
                          "medium" if days_until and days_until <= 7 else "low"
                
                tasks.append({
                    "type": "bill_payment",
                    "id": bill.id,
                    "title": f"Pay {bill.name}",
                    "amount": bill.amount,
                    "due_date": bill.due_date.isoformat() if bill.due_date else None,
                    "days_until_due": days_until,
                    "priority": priority,
                    "auto_pay": bill.auto_pay
                })
        
        return tasks
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a financial task (mark bill as paid, etc.)"""
        # For now, this just marks bills as paid
        return self.pay_bill(task_id)
    
    # ============ BILLS ============
    
    def get_bills(self, include_paid: bool = False) -> List[Dict[str, Any]]:
        """Get all bills"""
        with get_db() as db:
            query = db.query(Bill)
            if not include_paid:
                query = query.filter(Bill.is_paid == False)
            bills = query.order_by(Bill.due_date.asc()).all()
            
            return [self._bill_to_dict(b) for b in bills]
    
    def get_upcoming_bills(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get bills due in the next N days"""
        with get_db() as db:
            cutoff = date.today() + timedelta(days=days)
            bills = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date <= cutoff
            ).order_by(Bill.due_date.asc()).all()
            
            return [self._bill_to_dict(b) for b in bills]
    
    def add_bill(
        self,
        name: str,
        amount: float,
        due_date: date,
        category: str = "general",
        payee: str = None,
        is_recurring: bool = False,
        recurrence: str = None,
        auto_pay: bool = False,
        payment_method: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """Add a new bill"""
        with get_db() as db:
            bill = Bill(
                name=name,
                amount=amount,
                due_date=due_date,
                category=category,
                payee=payee,
                is_recurring=is_recurring,
                recurrence=recurrence,
                auto_pay=auto_pay,
                payment_method=payment_method,
                notes=notes
            )
            db.add(bill)
            db.flush()
            
            self.log_action("bill_added", f"Added bill: {name} (${amount})")
            
            return {"success": True, "bill": self._bill_to_dict(bill)}
    
    def pay_bill(self, bill_id: int, paid_amount: float = None) -> Dict[str, Any]:
        """Mark a bill as paid"""
        with get_db() as db:
            bill = db.query(Bill).filter(Bill.id == bill_id).first()
            if not bill:
                return {"success": False, "error": "Bill not found"}
            
            bill.is_paid = True
            bill.paid_date = date.today()
            bill.paid_amount = paid_amount or bill.amount
            
            # Record transaction
            transaction = Transaction(
                description=f"Bill payment: {bill.name}",
                category=bill.category,
                amount=bill.paid_amount,
                transaction_type="expense",
                date=date.today(),
                bill_id=bill.id
            )
            db.add(transaction)
            
            # Create next occurrence if recurring
            if bill.is_recurring and bill.recurrence:
                self._create_next_bill_occurrence(db, bill)
            
            self.log_action("bill_paid", f"Paid bill: {bill.name} (${bill.paid_amount})")
            
            return {"success": True, "bill": self._bill_to_dict(bill)}
    
    def _create_next_bill_occurrence(self, db, bill: Bill):
        """Create the next occurrence of a recurring bill"""
        intervals = {
            "weekly": timedelta(weeks=1),
            "biweekly": timedelta(weeks=2),
            "monthly": timedelta(days=30),
            "quarterly": timedelta(days=90),
            "yearly": timedelta(days=365)
        }
        
        interval = intervals.get(bill.recurrence)
        if not interval or not bill.due_date:
            return
        
        next_due = bill.due_date + interval
        
        new_bill = Bill(
            name=bill.name,
            amount=bill.amount,
            due_date=next_due,
            category=bill.category,
            payee=bill.payee,
            is_recurring=True,
            recurrence=bill.recurrence,
            auto_pay=bill.auto_pay,
            payment_method=bill.payment_method,
            notes=bill.notes
        )
        db.add(new_bill)
    
    # ============ TRANSACTIONS ============
    
    def get_transactions(self, days: int = 30, category: str = None) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        with get_db() as db:
            cutoff = date.today() - timedelta(days=days)
            query = db.query(Transaction).filter(Transaction.date >= cutoff)
            
            if category:
                query = query.filter(Transaction.category == category)
            
            transactions = query.order_by(Transaction.date.desc()).all()
            
            return [
                {
                    "id": t.id,
                    "description": t.description,
                    "category": t.category,
                    "amount": t.amount,
                    "type": t.transaction_type,
                    "date": t.date.isoformat() if t.date else None,
                    "account": t.account,
                    "notes": t.notes
                }
                for t in transactions
            ]
    
    def add_transaction(
        self,
        description: str,
        amount: float,
        transaction_type: str = "expense",
        category: str = None,
        transaction_date: date = None,
        account: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """Add a transaction"""
        with get_db() as db:
            transaction = Transaction(
                description=description,
                amount=amount,
                transaction_type=transaction_type,
                category=category,
                date=transaction_date or date.today(),
                account=account,
                notes=notes
            )
            db.add(transaction)
            db.flush()
            
            self.log_action("transaction_added", f"{transaction_type}: {description} (${amount})")
            
            return {"success": True, "transaction_id": transaction.id}
    
    # ============ BUDGETS ============
    
    def get_budget_status(self) -> List[Dict[str, Any]]:
        """Get current budget status by category"""
        with get_db() as db:
            # Get active budgets
            current_month = date.today().month
            current_year = date.today().year
            
            budgets = db.query(Budget).filter(
                (Budget.month == current_month) | (Budget.month == None),
                (Budget.year == current_year) | (Budget.year == None)
            ).all()
            
            # Get spending by category this month
            month_start = date.today().replace(day=1)
            
            result = []
            for budget in budgets:
                spent = db.query(Transaction).filter(
                    Transaction.category == budget.category,
                    Transaction.transaction_type == "expense",
                    Transaction.date >= month_start
                ).all()
                total_spent = sum(t.amount for t in spent) if spent else 0
                
                result.append({
                    "category": budget.category,
                    "limit": budget.monthly_limit,
                    "spent": round(total_spent, 2),
                    "remaining": round(budget.monthly_limit - total_spent, 2),
                    "percentage": round((total_spent / budget.monthly_limit) * 100, 1) if budget.monthly_limit > 0 else 0
                })
            
            return result
    
    # ============ PORTFOLIO ============
    
    def _get_portfolio_value(self) -> Optional[float]:
        """Get current portfolio value"""
        if not HAS_YFINANCE:
            return None
        
        # Use cache if recent (5 minutes)
        if self._portfolio_cache and self._cache_timestamp:
            age = (datetime.now() - self._cache_timestamp).total_seconds()
            if age < 300:
                return self._portfolio_cache
        
        try:
            total = 0
            for holding in self.portfolio_config["holdings"]:
                ticker = yf.Ticker(holding["ticker"])
                price = ticker.info.get("regularMarketPrice") or ticker.info.get("previousClose", 0)
                total += price * holding["shares"]
            
            self._portfolio_cache = round(total, 2)
            self._cache_timestamp = datetime.now()
            return self._portfolio_cache
        except Exception as e:
            self.logger.error(f"Failed to get portfolio value: {e}")
            return None
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with holdings (database first, config fallback)"""
        # Try database first
        db_holdings = self.get_holdings_from_db()
        cash_total = 0.0
        try:
            from database.models import CashHolding
            with get_db() as db:
                cash_rows = db.query(CashHolding).all()
                cash_total = sum(c.amount or 0 for c in cash_rows)
        except Exception:
            cash_total = 0.0
        
        # Only use database holdings - no fallback to config
        # User must add holdings manually
        if db_holdings:
            source_holdings = db_holdings
            portfolio_name = db_holdings[0].get("portfolio_name", "Lamido Main") if db_holdings else "Lamido Main"
        else:
            # Return empty portfolio if no database holdings
            return {
                "name": "My Portfolio",
                "total_value": 0,
                "holdings": [],
                "cash": round(cash_total, 2),
                "last_updated": datetime.now().isoformat(),
                "source": "empty"
            }
        
        if not HAS_YFINANCE:
            return {
                "error": "yfinance not installed",
                "holdings": source_holdings,
                "cash": round(cash_total, 2),
            }
        
        holdings = []
        total_value = 0
        
        try:
            for holding in source_holdings:
                ticker_symbol = holding.get("ticker")
                shares = holding.get("shares", 0)
                asset_type = holding.get("type") or holding.get("asset_type", "")
                
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info
                
                price = info.get("regularMarketPrice") or info.get("previousClose", 0)
                prev_close = info.get("previousClose", price)
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                
                value = price * shares
                total_value += value
                
                holdings.append({
                    "ticker": ticker_symbol,
                    "shares": shares,
                    "type": asset_type,
                    "price": round(price, 2),
                    "value": round(value, 2),
                    "change_pct": round(change_pct, 2)
                })
            
            day_change = sum(
                (h.get("value", 0) * (h.get("change_pct", 0) / 100))
                for h in holdings
                if isinstance(h.get("value"), (int, float))
            )
            holdings_total = round(total_value, 2)
            day_change_pct = round((day_change / holdings_total) * 100, 2) if holdings_total > 0 else 0

            return {
                "name": portfolio_name,
                "total_value": round(total_value + cash_total, 2),
                "holdings": holdings,
                "cash": round(cash_total, 2),
                "day_change": round(day_change, 2),
                "day_change_pct": day_change_pct,
                "last_updated": datetime.now().isoformat(),
                "source": "database" if db_holdings else "config"
            }
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return {"error": str(e), "holdings": source_holdings, "cash": round(cash_total, 2)}
    
    # ============ SPEND TRACKING ============
    
    def add_spend_entry(
        self,
        amount: float,
        merchant: str = None,
        description: str = None,
        funding_source: str = None,
        payment_rail: str = None,
        consumption_category: str = None,
        spend_date: date = None,
        is_internal_transfer: bool = False,
        confidence_level: str = "low",
        source: str = "manual",
        receipt_path: str = None,
    ) -> Dict[str, Any]:
        """
        Add a spend entry with three-layer classification.
        
        Args:
            amount: Dollar amount
            merchant: Where the money went
            description: What it was for
            funding_source: Bank account, card, cash
            payment_rail: How money moved (direct, apple_cash, zelle, etc.)
            consumption_category: What type of spend (dining, groceries, etc.)
            spend_date: When (defaults to today)
            is_internal_transfer: If True, excluded from consumption totals
            confidence_level: high/medium/low
            source: manual/screenshot/inferred/import
        """
        from database.models import SpendEntry, SpendingBaseline
        
        with get_db() as db:
            entry = SpendEntry(
                amount=amount,
                merchant=merchant,
                description=description,
                funding_source=funding_source,
                payment_rail=payment_rail,
                consumption_category=consumption_category,
                date=spend_date or date.today(),
                is_internal_transfer=is_internal_transfer,
                confidence_level=confidence_level,
                source=source,
                category_confirmed=False,
                receipt_path=receipt_path,
            )
            db.add(entry)
            db.commit()
            
            # Check if this is the first entry - start baseline if so
            baseline = db.query(SpendingBaseline).first()
            if not baseline:
                baseline = SpendingBaseline(
                    baseline_start_date=date.today(),
                    baseline_end_date=date.today() + timedelta(days=7),
                    baseline_complete=False
                )
                db.add(baseline)
                db.commit()
                self.log_action("baseline_started", json.dumps({"start_date": date.today().isoformat()}))
            
            self.log_action("spend_added", json.dumps({
                "amount": amount,
                "category": consumption_category,
                "rail": payment_rail,
                "confidence": confidence_level
            }))
            
            return {
                "success": True,
                "entry_id": entry.id,
                "baseline_active": not baseline.baseline_complete,
                "receipt_path": receipt_path,
                "message": f"Recorded ${amount:.2f} spend" + 
                          (f" at {merchant}" if merchant else "") +
                          (f" via {payment_rail}" if payment_rail else "")
            }
    
    def get_spend_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get spending summary for the last N days"""
        from database.models import SpendEntry, SpendingBaseline
        
        start_date = date.today() - timedelta(days=days)
        
        with get_db() as db:
            # Get baseline status
            baseline = db.query(SpendingBaseline).first()
            baseline_active = baseline and not baseline.baseline_complete if baseline else False
            
            # Get all entries in period (excluding internal transfers)
            entries = db.query(SpendEntry).filter(
                SpendEntry.date >= start_date,
                SpendEntry.is_internal_transfer == False
            ).all()
            
            if not entries:
                return {
                    "period_days": days,
                    "total_spend": 0,
                    "entry_count": 0,
                    "baseline_active": baseline_active,
                    "by_category": {},
                    "by_rail": {},
                    "by_source": {}
                }
            
            total = sum(e.amount for e in entries)
            
            # Group by category
            by_category = {}
            for e in entries:
                cat = e.consumption_category or "Uncategorized"
                by_category[cat] = by_category.get(cat, 0) + e.amount
            
            # Group by payment rail
            by_rail = {}
            for e in entries:
                rail = e.payment_rail or "Unknown"
                by_rail[rail] = by_rail.get(rail, 0) + e.amount
            
            # Group by funding source
            by_source = {}
            for e in entries:
                src = e.funding_source or "Unknown"
                by_source[src] = by_source.get(src, 0) + e.amount
            
            # Discretionary vs fixed
            discretionary = sum(e.amount for e in entries if e.is_discretionary)
            fixed = sum(e.amount for e in entries if e.is_discretionary == False)
            unclassified = total - discretionary - fixed
            
            return {
                "period_days": days,
                "total_spend": round(total, 2),
                "entry_count": len(entries),
                "avg_daily": round(total / days, 2),
                "baseline_active": baseline_active,
                "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
                "by_rail": {k: round(v, 2) for k, v in sorted(by_rail.items(), key=lambda x: -x[1])},
                "by_source": {k: round(v, 2) for k, v in sorted(by_source.items(), key=lambda x: -x[1])},
                "discretionary": round(discretionary, 2),
                "fixed": round(fixed, 2),
                "unclassified": round(unclassified, 2),
                "discretionary_pct": round(discretionary / total * 100, 1) if total > 0 else 0
            }
    
    def get_baseline_status(self) -> Dict[str, Any]:
        """Get spending baseline status"""
        from database.models import SpendingBaseline
        
        with get_db() as db:
            baseline = db.query(SpendingBaseline).first()
            
            if not baseline:
                return {
                    "status": "not_started",
                    "message": "Baseline week not started. Add first spend entry to begin."
                }
            
            if baseline.baseline_complete:
                return {
                    "status": "complete",
                    "start_date": baseline.baseline_start_date.isoformat() if baseline.baseline_start_date else None,
                    "end_date": baseline.baseline_end_date.isoformat() if baseline.baseline_end_date else None,
                    "total_spend": baseline.total_baseline_spend,
                    "avg_daily": baseline.avg_daily_spend,
                    "discretionary_pct": baseline.discretionary_pct
                }
            
            # Baseline in progress
            days_elapsed = (date.today() - baseline.baseline_start_date).days if baseline.baseline_start_date else 0
            days_remaining = 7 - days_elapsed
            
            return {
                "status": "in_progress",
                "start_date": baseline.baseline_start_date.isoformat() if baseline.baseline_start_date else None,
                "end_date": baseline.baseline_end_date.isoformat() if baseline.baseline_end_date else None,
                "days_elapsed": days_elapsed,
                "days_remaining": max(0, days_remaining),
                "message": f"Baseline capture in progress. {days_remaining} days remaining. Keep logging all spending."
            }
    
    def complete_baseline(self) -> Dict[str, Any]:
        """Complete baseline week and calculate insights"""
        from database.models import SpendEntry, SpendingBaseline
        import json
        
        with get_db() as db:
            baseline = db.query(SpendingBaseline).first()
            
            if not baseline:
                return {"error": "No baseline found"}
            
            if baseline.baseline_complete:
                return {"error": "Baseline already complete"}
            
            # Get all entries from baseline period
            entries = db.query(SpendEntry).filter(
                SpendEntry.date >= baseline.baseline_start_date,
                SpendEntry.date <= baseline.baseline_end_date,
                SpendEntry.is_internal_transfer == False
            ).all()
            
            if len(entries) < 5:
                return {
                    "error": "Insufficient data",
                    "message": f"Only {len(entries)} entries. Need at least 5 for meaningful baseline."
                }
            
            # Calculate totals
            total = sum(e.amount for e in entries)
            days = (baseline.baseline_end_date - baseline.baseline_start_date).days + 1
            avg_daily = total / days if days > 0 else 0
            
            # Calculate discretionary %
            discretionary = sum(e.amount for e in entries if e.is_discretionary)
            discretionary_pct = (discretionary / total * 100) if total > 0 else 0
            
            # Rail velocity
            rail_totals = {}
            for e in entries:
                rail = e.payment_rail or "unknown"
                rail_totals[rail] = rail_totals.get(rail, 0) + e.amount
            rail_velocity = {k: round(v / days * 7, 2) for k, v in rail_totals.items()}  # Weekly avg
            
            # Rail discretionary %
            rail_disc = {}
            for rail in rail_totals.keys():
                rail_entries = [e for e in entries if e.payment_rail == rail]
                rail_disc_total = sum(e.amount for e in rail_entries if e.is_discretionary)
                rail_total = sum(e.amount for e in rail_entries)
                rail_disc[rail] = round(rail_disc_total / rail_total, 2) if rail_total > 0 else 0
            
            # Update baseline
            baseline.baseline_complete = True
            baseline.total_baseline_spend = round(total, 2)
            baseline.avg_daily_spend = round(avg_daily, 2)
            baseline.discretionary_pct = round(discretionary_pct, 1)
            baseline.rail_velocity = json.dumps(rail_velocity)
            baseline.rail_discretionary_pct = json.dumps(rail_disc)
            
            db.commit()
            
            self.log_action("baseline_completed", json.dumps({
                "total_spend": total,
                "avg_daily": avg_daily,
                "discretionary_pct": discretionary_pct
            }))
            
            return {
                "success": True,
                "total_spend": round(total, 2),
                "avg_daily": round(avg_daily, 2),
                "discretionary_pct": round(discretionary_pct, 1),
                "rail_velocity": rail_velocity,
                "message": "Baseline complete! Finance Agent can now provide optimization recommendations."
            }
    
    # ============ INVESTMENT RECOMMENDATIONS ============
    
    def get_typed_settings(self) -> Optional[Any]:
        """Get typed finance settings from core/settings_typed.py"""
        try:
            from core.settings_typed import FinanceSettings
            # In a real implementation, this would load from database
            # For now, return default settings
            return FinanceSettings()
        except ImportError:
            return None
    
    def get_system_cost_status(self) -> Dict[str, Any]:
        """
        Get current system AI/API cost status.
        Used to enforce $1000/month cap and add cost awareness to recommendations.
        """
        try:
            costs = self.get_system_costs()
            total = costs.get("total", 0)
            budget = costs.get("budget", 1000.0)
            pct_used = costs.get("pct_used", 0)
            
            return {
                "total_cost": total,
                "budget": budget,
                "pct_used": pct_used,
                "status": costs.get("status", "ok"),
                "remaining": round(budget - total, 2),
                "at_risk": pct_used >= 80,
                "over_budget": pct_used >= 100,
            }
        except Exception as e:
            self.logger.warning(f"Could not get system costs: {e}")
            return {
                "total_cost": 0,
                "budget": 1000.0,
                "pct_used": 0,
                "status": "unknown",
                "remaining": 1000.0,
                "at_risk": False,
                "over_budget": False,
            }
    
    def get_investment_recommendations(self, holdings: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate investment recommendations based on recommendation style.
        
        Uses FinanceSettings.recommendation_style to frame recommendations:
        - QUICK_FLIP: Focus on momentum and quick gains
        - ONE_YEAR_PLAN: Medium-term growth
        - LONG_TERM_HOLD: Buy and hold strategy
        - BALANCED: Mix of strategies
        
        ⚠️ NOT FINANCIAL ADVICE - Educational purposes only
        """
        typed_settings = self.get_typed_settings()
        
        # Check system cost status for cost awareness
        cost_status = self.get_system_cost_status()
        
        if typed_settings is None:
            # Fallback - basic recommendations
            return {
                "style": "balanced",
                "disclaimer": "⚠️ NOT FINANCIAL ADVICE - For educational purposes only",
                "recommendations": ["Unable to load recommendation settings"],
                "error": "Settings module not available"
            }
        
        # Get framing based on style
        from core.settings_typed import RecommendationStyle
        framing = typed_settings.get_recommendation_framing()
        style = typed_settings.recommendation_style
        
        # Get current portfolio if not provided
        if holdings is None:
            portfolio = self.get_portfolio_summary()
            holdings = portfolio.get("holdings", [])
        
        recommendations = []
        actions = []
        
        # Analyze holdings based on recommendation style
        for holding in holdings:
            ticker = holding.get("ticker", "")
            change_pct = holding.get("change_pct", 0)
            value = holding.get("value", 0)
            
            if style == RecommendationStyle.QUICK_FLIP:
                # Momentum-based recommendations
                if change_pct > 5:
                    recommendations.append(f"🔥 {ticker} up {change_pct:.1f}% - consider taking profits")
                    actions.append({"ticker": ticker, "action": "consider_sell", "reason": "momentum_profit"})
                elif change_pct < -5:
                    recommendations.append(f"📉 {ticker} down {change_pct:.1f}% - cut loss or hold?")
                    actions.append({"ticker": ticker, "action": "review", "reason": "loss_cut_candidate"})
            
            elif style == RecommendationStyle.LONG_TERM_HOLD:
                # Long-term focused recommendations
                if change_pct < -10:
                    recommendations.append(f"💰 {ticker} down {change_pct:.1f}% - potential buying opportunity")
                    actions.append({"ticker": ticker, "action": "consider_buy", "reason": "dip_buy"})
                elif change_pct > 0:
                    recommendations.append(f"✅ {ticker} performing well (+{change_pct:.1f}%) - hold long-term")
            
            elif style == RecommendationStyle.ONE_YEAR_PLAN:
                # Medium-term growth focus
                if change_pct > 15:
                    recommendations.append(f"📊 {ticker} +{change_pct:.1f}% - consider partial profit taking")
                elif change_pct < -15:
                    recommendations.append(f"🔄 {ticker} {change_pct:.1f}% - reassess position thesis")
            
            else:  # BALANCED
                if abs(change_pct) > 10:
                    recommendations.append(f"👀 {ticker} moved {change_pct:+.1f}% - review position")
        
        # Add general recommendations based on style
        if not recommendations:
            recommendations.append(f"Portfolio stable - no immediate actions based on {style.value} strategy")
        
        # Add cost awareness warnings if approaching budget
        cost_warnings = []
        if cost_status.get("over_budget"):
            cost_warnings.append("🚨 OVER BUDGET: System costs have exceeded $1000/month cap")
        elif cost_status.get("at_risk"):
            cost_warnings.append(f"⚠️ Cost Warning: {cost_status.get('pct_used', 0):.0f}% of monthly budget used (${cost_status.get('total_cost', 0):.2f})")
        
        return {
            "style": style.value,
            "timeframe": framing.get("timeframe", "varies"),
            "focus": framing.get("focus", ""),
            "exit_strategy": framing.get("exit_strategy", ""),
            "disclaimer": "⚠️ NOT FINANCIAL ADVICE - For educational purposes only",
            "recommendations": recommendations,
            "suggested_actions": actions,
            "include_disclaimer": typed_settings.include_disclaimer,
            "generated_at": datetime.now().isoformat(),
            "cost_status": {
                "monthly_budget": cost_status.get("budget", 1000),
                "used": cost_status.get("total_cost", 0),
                "pct_used": cost_status.get("pct_used", 0),
                "at_risk": cost_status.get("at_risk", False),
            },
            "cost_warnings": cost_warnings if cost_warnings else None,
        }
    
    # ============ PORTFOLIO MANAGEMENT ============
    
    def clear_portfolio(self) -> Dict[str, Any]:
        """Clear all holdings from the portfolio database"""
        from database.models import PortfolioHolding
        
        with get_db() as db:
            count = db.query(PortfolioHolding).count()
            db.query(PortfolioHolding).delete()
            db.commit()
            
            self.log_action("portfolio_cleared", json.dumps({"holdings_removed": count}))
            
            return {
                "success": True,
                "message": f"Portfolio cleared — {count} holdings removed",
                "holdings_removed": count
            }
    
    def add_holding(
        self,
        ticker: str,
        shares: float,
        asset_type: str = None,
        portfolio_name: str = "Lamido Main"
    ) -> Dict[str, Any]:
        """Add a holding to the portfolio"""
        from database.models import PortfolioHolding
        
        with get_db() as db:
            # Check if ticker already exists
            existing = db.query(PortfolioHolding).filter(
                PortfolioHolding.ticker == ticker.upper(),
                PortfolioHolding.portfolio_name == portfolio_name
            ).first()
            
            if existing:
                existing.shares = shares
                existing.asset_type = asset_type
                db.commit()
                self.log_action("holding_updated", json.dumps({"ticker": ticker, "shares": shares}))
                return {"success": True, "action": "updated", "id": existing.id}
            
            holding = PortfolioHolding(
                portfolio_name=portfolio_name,
                ticker=ticker.upper(),
                shares=shares,
                asset_type=asset_type
            )
            db.add(holding)
            db.commit()
            
            self.log_action("holding_added", json.dumps({"ticker": ticker, "shares": shares}))
            return {"success": True, "action": "added", "id": holding.id}
    
    def remove_holding(self, ticker: str, portfolio_name: str = "Lamido Main") -> Dict[str, Any]:
        """Remove a holding from the portfolio"""
        from database.models import PortfolioHolding
        
        with get_db() as db:
            holding = db.query(PortfolioHolding).filter(
                PortfolioHolding.ticker == ticker.upper(),
                PortfolioHolding.portfolio_name == portfolio_name
            ).first()
            
            if not holding:
                return {"success": False, "error": f"Holding {ticker} not found"}
            
            db.delete(holding)
            db.commit()
            
            self.log_action("holding_removed", json.dumps({"ticker": ticker}))
            return {"success": True, "message": f"Removed {ticker}"}
    
    def get_holdings_from_db(self, portfolio_name: str = "Lamido Main") -> List[Dict[str, Any]]:
        """Get holdings from database"""
        from database.models import PortfolioHolding
        
        with get_db() as db:
            holdings = db.query(PortfolioHolding).filter(
                PortfolioHolding.portfolio_name == portfolio_name
            ).all()
            
            return [
                {
                    "id": h.id,
                    "ticker": h.ticker,
                    "shares": h.shares,
                    "type": h.asset_type,
                    "portfolio_name": h.portfolio_name
                }
                for h in holdings
            ]
    
    # ============ EDGE LAB INTEGRATION (Simplified) ============
    
    def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a single stock using EdgeLab-style features.
        Uses yfinance directly for data.
        """
        if not HAS_YFINANCE:
            return {"success": False, "error": "yfinance not installed"}
        
        try:
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period="6mo")
            info = ticker.info
            
            if hist.empty:
                return {"success": False, "error": f"No data for {symbol}"}
            
            # Calculate EdgeLab-style features
            close = hist['Close']
            volume = hist['Volume']
            
            # Returns
            ret_1d = ((close.iloc[-1] / close.iloc[-2]) - 1) * 100 if len(close) >= 2 else 0
            ret_5d = ((close.iloc[-1] / close.iloc[-6]) - 1) * 100 if len(close) >= 6 else 0
            ret_20d = ((close.iloc[-1] / close.iloc[-21]) - 1) * 100 if len(close) >= 21 else 0
            
            # Volatility (20-day)
            vol_20d = close.pct_change().tail(20).std() * (252 ** 0.5) * 100
            
            # Volume analysis
            avg_vol_20d = volume.tail(20).mean()
            rel_vol = volume.iloc[-1] / avg_vol_20d if avg_vol_20d > 0 else 1
            
            # Moving averages
            sma_20 = close.tail(20).mean()
            sma_50 = close.tail(50).mean() if len(close) >= 50 else sma_20
            dist_sma_20 = ((close.iloc[-1] / sma_20) - 1) * 100
            dist_sma_50 = ((close.iloc[-1] / sma_50) - 1) * 100
            
            # Momentum score (simplified)
            momentum_score = (ret_5d * 0.4 + ret_20d * 0.3 + dist_sma_20 * 0.3) / 10
            
            # Risk flags
            risk_flags = []
            if vol_20d > 50:
                risk_flags.append("HIGH_VOLATILITY")
            if abs(ret_1d) > 10:
                risk_flags.append("EXTREME_1D_MOVE")
            if info.get("marketCap", 0) < 500_000_000:
                risk_flags.append("MICROCAP")
            
            return {
                "success": True,
                "symbol": symbol.upper(),
                "price": round(close.iloc[-1], 2),
                "features": {
                    "ret_1d": round(ret_1d, 2),
                    "ret_5d": round(ret_5d, 2),
                    "ret_20d": round(ret_20d, 2),
                    "vol_20d": round(vol_20d, 2),
                    "rel_vol": round(rel_vol, 2),
                    "dist_sma_20": round(dist_sma_20, 2),
                    "dist_sma_50": round(dist_sma_50, 2),
                },
                "momentum_score": round(momentum_score, 2),
                "risk_flags": risk_flags,
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector"),
            }
            
        except Exception as e:
            self.logger.error(f"Stock analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_portfolio_stocks(self) -> Dict[str, Any]:
        """
        Run EdgeLab-style analysis on all portfolio holdings.
        """
        holdings = self.get_holdings_from_db()
        
        if not holdings:
            return {"success": False, "error": "No holdings in portfolio"}
        
        results = []
        for holding in holdings:
            analysis = self.analyze_stock(holding["ticker"])
            if analysis.get("success"):
                analysis["shares"] = holding.get("shares", 0)
                analysis["value"] = round(analysis.get("price", 0) * holding.get("shares", 0), 2)
                results.append(analysis)
        
        # Sort by momentum score
        results.sort(key=lambda x: x.get("momentum_score", 0), reverse=True)
        
        return {
            "success": True,
            "analyzed_count": len(results),
            "holdings": results,
            "top_momentum": results[:3] if len(results) >= 3 else results,
            "high_risk": [r for r in results if r.get("risk_flags")],
        }
    
    def get_stock_recommendations(self, watchlist: List[str] = None) -> Dict[str, Any]:
        """
        Get stock recommendations using EdgeLab-style scoring.
        Analyzes watchlist or defaults to popular tickers.
        """
        default_watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD"]
        symbols = watchlist or default_watchlist
        
        results = []
        for symbol in symbols:
            analysis = self.analyze_stock(symbol)
            if analysis.get("success"):
                results.append(analysis)
        
        # Sort by momentum score
        results.sort(key=lambda x: x.get("momentum_score", 0), reverse=True)
        
        return {
            "success": True,
            "recommendations": results[:5],
            "all_analyzed": results,
        }
    
    # ============ POLYMARKET BTC 15M DIRECTION ============

    async def analyze_polymarket_direction(
        self,
        market_data: Optional[Dict[str, Any]] = None,
        market_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze Polymarket BTC 15m direction

        Args:
            market_data: Pre-scraped market data
            market_url: Polymarket URL (will be scraped if provided and no market_data)

        Returns:
            PolymarketDirectionOutput as dict
        """
        if not POLYMARKET_SKILL_AVAILABLE:
            return {
                "error": "Polymarket BTC 15m skill not installed",
                "message": "The skill module is not available",
            }

        try:
            # If URL provided but no market_data, scrape it
            if market_url and not market_data:
                from backend.skills.polymarket_btc_15m.url_scraper import PolymarketURLScraper
                scraper = PolymarketURLScraper()
                market_data = scraper.scrape_market_url(market_url)
                self.log_action("polymarket_scrape", f"Scraped market data from {market_url}")

            result = await analyze_btc_15m_direction(
                market_data=market_data,
                market_url=market_url,
                bankroll_usd=5000
            )

            self.log_action("polymarket_analysis", f"Analyzed BTC 15m direction: {result.call.value}")

            # Convert to dict for JSON serialization
            return result.to_dict()

        except Exception as e:
            self.log_action("polymarket_analysis_failed", str(e), status="error")
            # Re-raise to let the route handler provide better error messages
            raise

    # ============ HELPERS ============

    def _bill_to_dict(self, bill: Bill) -> Dict[str, Any]:
        """Convert bill to dictionary"""
        days_until = (bill.due_date - date.today()).days if bill.due_date and not bill.is_paid else None
        
        return {
            "id": bill.id,
            "name": bill.name,
            "category": bill.category,
            "payee": bill.payee,
            "amount": bill.amount,
            "due_date": bill.due_date.isoformat() if bill.due_date else None,
            "days_until_due": days_until,
            "is_recurring": bill.is_recurring,
            "recurrence": bill.recurrence,
            "auto_pay": bill.auto_pay,
            "payment_method": bill.payment_method,
            "is_paid": bill.is_paid,
            "paid_date": bill.paid_date.isoformat() if bill.paid_date else None,
            "paid_amount": bill.paid_amount,
            "notes": bill.notes
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for financial alerts"""
        alerts = []
        
        # Check overdue bills
        with get_db() as db:
            overdue = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date < date.today()
            ).all()
            
            for bill in overdue:
                days_overdue = (date.today() - bill.due_date).days
                alerts.append({
                    "type": "overdue_bill",
                    "severity": "high",
                    "title": f"Overdue: {bill.name}",
                    "message": f"${bill.amount} was due {days_overdue} days ago",
                    "action": f"pay_bill:{bill.id}"
                })
            
            # Check bills due soon
            upcoming = date.today() + timedelta(days=self.alert_thresholds["bill_due_days_ahead"])
            due_soon = db.query(Bill).filter(
                Bill.is_paid == False,
                Bill.due_date >= date.today(),
                Bill.due_date <= upcoming,
                Bill.auto_pay == False
            ).all()
            
            for bill in due_soon:
                days_until = (bill.due_date - date.today()).days
                alerts.append({
                    "type": "bill_due_soon",
                    "severity": "medium",
                    "title": f"Due Soon: {bill.name}",
                    "message": f"${bill.amount} due in {days_until} days",
                    "action": f"pay_bill:{bill.id}"
                })
        
        return alerts
