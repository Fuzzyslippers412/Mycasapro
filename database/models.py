"""
MyCasa Pro Database Models
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, UniqueConstraint, Index, JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid

from config.settings import DEFAULT_TENANT_ID

Base = declarative_base()

# JSON type compatible with SQLite/Postgres
JSONType = JSON().with_variant(JSONB, "postgresql")


class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecurrenceType(enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# ============ HOME MAINTENANCE ============

class Contractor(Base):
    __tablename__ = "contractors"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    company = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    service_type = Column(String(50))  # cleaning, yard, plumbing, electrical, etc.
    hourly_rate = Column(Float)
    rating = Column(Integer)  # 1-5
    notes = Column(Text)
    last_service_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tasks = relationship("MaintenanceTask", back_populates="contractor")


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # cleaning, yard, repair, renovation, etc.
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="pending")
    conversation_id = Column(String(36), index=True)
    assigned_to = Column(String(64))
    
    scheduled_date = Column(Date)
    completed_date = Column(Date)
    due_date = Column(Date)
    
    recurrence = Column(String(20), default="none")
    next_occurrence = Column(Date)
    
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    
    contractor_id = Column(Integer, ForeignKey("contractors.id"))
    contractor = relationship("Contractor", back_populates="tasks")
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # renovation, improvement, repair
    status = Column(String(20), default="planning")  # planning, in_progress, on_hold, completed
    
    start_date = Column(Date)
    target_end_date = Column(Date)
    actual_end_date = Column(Date)
    
    budget = Column(Float)
    spent = Column(Float, default=0)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    milestones = relationship("ProjectMilestone", back_populates="project")


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="milestones")
    
    title = Column(String(200), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    completed = Column(Boolean, default=False)
    completed_date = Column(Date)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ContractorJob(Base):
    """
    Contractor job tracking with full lifecycle management.
    Flow: proposed → pending → scheduled → in_progress → completed
    """
    __tablename__ = "contractor_jobs"
    
    id = Column(Integer, primary_key=True)
    
    # Request origin
    description = Column(String(500), nullable=False)
    scope = Column(Text)
    originating_request = Column(String(50))  # user, maintenance, project
    request_id = Column(Integer)  # Link to maintenance task or project
    
    # Contractor details
    contractor_id = Column(Integer, ForeignKey("contractors.id"))
    contractor_name = Column(String(100))
    contractor_role = Column(String(50))  # plumber, electrician, etc.
    contact_method = Column(String(100))  # phone, whatsapp, email
    
    # Scheduling
    proposed_start = Column(Date)
    proposed_end = Column(Date)
    confirmed_start = Column(Date)
    confirmed_end = Column(Date)
    actual_start = Column(Date)
    actual_end = Column(Date)
    
    # Cost tracking
    estimated_cost = Column(Float)
    approved_cost = Column(Float)
    actual_cost = Column(Float)
    cost_status = Column(String(30), default="unreviewed")  # unreviewed, pending_approval, approved, rejected
    
    # Status
    status = Column(String(30), default="proposed")  # proposed, pending, scheduled, in_progress, completed, blocked, cancelled
    urgency = Column(String(20), default="medium")
    blocked_reason = Column(Text)
    
    # Evidence & audit trail
    evidence = Column(Text)  # JSON: scheduling confirmations, completion proof
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HomeReading(Base):
    """Track home metrics like water quality, energy usage, etc."""
    __tablename__ = "home_readings"
    
    id = Column(Integer, primary_key=True)
    reading_type = Column(String(50))  # water_quality, energy, temperature, etc.
    value = Column(Float)
    unit = Column(String(20))
    location = Column(String(50))
    notes = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)


# ============ FINANCE ============

class Bill(Base):
    __tablename__ = "bills"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))  # utilities, insurance, subscription, mortgage, etc.
    payee = Column(String(100))
    
    amount = Column(Float)
    due_date = Column(Date)
    
    is_recurring = Column(Boolean, default=False)
    recurrence = Column(String(20))
    
    auto_pay = Column(Boolean, default=False)
    payment_method = Column(String(50))
    
    is_paid = Column(Boolean, default=False)
    paid_date = Column(Date)
    paid_amount = Column(Float)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    description = Column(String(200), nullable=False)
    category = Column(String(50))
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20))  # income, expense, transfer
    
    date = Column(Date, default=date.today)
    account = Column(String(50))
    
    bill_id = Column(Integer, ForeignKey("bills.id"))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    
    month = Column(Integer)  # 1-12, null for all months
    year = Column(Integer)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpendEntry(Base):
    """
    Three-layer spend tracking model:
    - Funding Source: where money comes from
    - Payment Rail: how money moves
    - Consumption Category: what money is for
    """
    __tablename__ = "spend_entries"
    
    id = Column(Integer, primary_key=True)
    
    # Core fields
    amount = Column(Float, nullable=False)
    merchant = Column(String(200))
    description = Column(Text)
    date = Column(Date, default=date.today, nullable=False)
    
    # Three-layer model
    funding_source = Column(String(50))  # Chase Checking, Chase Freedom, Cash, etc.
    payment_rail = Column(String(50))    # Direct, Apple Cash, Zelle, ACH, Venmo, etc.
    consumption_category = Column(String(50))  # Dining, Groceries, Housing, etc.
    
    # Classification
    is_internal_transfer = Column(Boolean, default=False)  # Exclude from consumption totals
    is_discretionary = Column(Boolean)  # Fixed vs discretionary
    is_recurring = Column(Boolean, default=False)
    
    # Confidence tracking
    confidence_level = Column(String(20), default="low")  # high, medium, low
    source = Column(String(20), default="manual")  # manual, screenshot, inferred, import
    category_confirmed = Column(Boolean, default=False)  # User confirmed the category
    
    # Metadata
    receipt_path = Column(String(500))  # Path to receipt image if captured
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpendingBaseline(Base):
    """Track baseline week status and behavioral insights"""
    __tablename__ = "spending_baseline"
    
    id = Column(Integer, primary_key=True)
    
    # Baseline tracking
    baseline_start_date = Column(Date)
    baseline_end_date = Column(Date)
    baseline_complete = Column(Boolean, default=False)
    
    # Aggregated insights (updated after baseline)
    total_baseline_spend = Column(Float)
    avg_daily_spend = Column(Float)
    discretionary_pct = Column(Float)
    
    # Rail insights (JSON-like text for simplicity)
    rail_velocity = Column(Text)  # JSON: {"apple_cash": 150.0, "zelle": 200.0, ...}
    rail_discretionary_pct = Column(Text)  # JSON: {"apple_cash": 0.85, ...}
    funding_source_correlations = Column(Text)  # JSON
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ FINANCE MANAGER SETTINGS ============

class FinanceManagerSettings(Base):
    """
    Finance Manager configuration and intake data.
    Must be completed before finance logic runs.
    """
    __tablename__ = "finance_manager_settings"
    
    id = Column(Integer, primary_key=True)
    
    # Intake status
    intake_complete = Column(Boolean, default=False)
    intake_completed_at = Column(DateTime)
    
    # System Cost Budget (MyCasa Pro operational costs)
    system_cost_budget = Column(Float, default=1000.0)  # $1000/month max
    system_cost_warn_70 = Column(Boolean, default=True)
    system_cost_warn_85 = Column(Boolean, default=True)
    system_cost_warn_95 = Column(Boolean, default=True)
    
    # Spend Guardrails
    monthly_spend_limit = Column(Float, default=10000.0)  # $10k/month
    daily_soft_cap = Column(Float, default=150.0)        # $150/day
    spend_alerts_enabled = Column(Boolean, default=True)
    
    # Preferred payment rails (JSON array)
    preferred_payment_rails = Column(Text)  # JSON: ["apple_cash", "card", "ach"]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IncomeSource(Base):
    """
    Income sources for the household.
    Primary source is required during intake.
    """
    __tablename__ = "income_sources"
    
    id = Column(Integer, primary_key=True)
    
    # Source identification
    name = Column(String(100), nullable=False)  # "J.P. Morgan Brokerage"
    account_type = Column(String(50))           # brokerage, checking, savings
    institution = Column(String(100))           # "J.P. Morgan"
    
    # Classification
    is_primary = Column(Boolean, default=False)
    income_type = Column(String(50))            # investment, salary, mixed, other
    
    # Expected inflow
    expected_monthly_min = Column(Float)        # Range minimum
    expected_monthly_max = Column(Float)        # Range maximum
    
    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemCostEntry(Base):
    """
    Track MyCasa Pro's own operational costs.
    Categories: ai_api, hosting, storage, integrations
    """
    __tablename__ = "system_cost_entries"
    
    id = Column(Integer, primary_key=True)
    
    # Cost details
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)  # ai_api, hosting, storage, integrations
    description = Column(String(200))
    service_name = Column(String(100))             # "Claude API", "OpenAI", "AWS", etc.
    
    # Period
    date = Column(Date, default=date.today, nullable=False)
    period_start = Column(Date)                    # For monthly costs
    period_end = Column(Date)
    
    # Classification
    is_recurring = Column(Boolean, default=False)
    recurrence = Column(String(20))                # monthly, yearly
    
    # Tracking
    invoice_ref = Column(String(100))
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class SpendGuardrailAlert(Base):
    """
    Log of spend guardrail alerts (warnings, threshold crossings).
    """
    __tablename__ = "spend_guardrail_alerts"
    
    id = Column(Integer, primary_key=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # daily_limit, monthly_limit, system_cost
    threshold_pct = Column(Float)                     # 70, 85, 95, 100
    actual_amount = Column(Float)
    limit_amount = Column(Float)
    
    # Message
    message = Column(Text)
    
    # Status
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(50))
    
    # Period context
    period_type = Column(String(20))  # day, month
    period_date = Column(Date)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


# ============ INBOX / MESSAGES ============

class InboxMessage(Base):
    """
    Unified inbox for Gmail + WhatsApp messages.
    Ingested by Mail Skill Agent, routed by Manager.
    """
    __tablename__ = "inbox_messages"
    
    id = Column(Integer, primary_key=True)
    
    # Source identification
    external_id = Column(String(200), unique=True)  # gmail:thread_id or whatsapp:jid
    source = Column(String(20), nullable=False)  # gmail, whatsapp
    thread_id = Column(String(200))
    
    # Sender info
    sender_name = Column(String(200))
    sender_id = Column(String(200))  # email or phone/jid
    
    # Content
    subject = Column(String(500))
    preview = Column(Text)
    
    # Timing
    timestamp = Column(DateTime, nullable=False)
    
    # Classification (by Mail Skill Agent)
    domain = Column(String(50))  # maintenance, finance, contractors, projects, unknown
    urgency = Column(String(20), default="medium")  # low, medium, high
    confidence = Column(String(20), default="inferred")  # inferred, confirmed
    
    # State
    is_read = Column(Boolean, default=False)
    required_action = Column(String(50))  # reply, approve, ignore, none
    
    # Linking
    linked_task_id = Column(Integer, ForeignKey("maintenance_tasks.id"))
    assigned_agent = Column(String(50))  # maintenance, finance, etc.
    
    # Raw data for debugging
    raw_data = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ AGENT SYSTEM ============

class AgentLog(Base):
    """Track agent actions and decisions"""
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True)
    agent = Column(String(50), nullable=False)  # supervisor, maintenance, finance
    action = Column(String(100), nullable=False)
    details = Column(Text)
    status = Column(String(20))  # success, failed, pending
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduledJob(Base):
    """Track scheduled agent jobs"""
    __tablename__ = "scheduled_jobs"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    agent = Column(String(50), nullable=False)
    job_type = Column(String(50))  # check_bills, portfolio_update, etc.
    
    cron_expression = Column(String(50))
    is_active = Column(Boolean, default=True)
    
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    """System notifications"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    message = Column(Text)
    category = Column(String(50))  # maintenance, finance, system
    priority = Column(String(20), default="medium")
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    action_url = Column(String(200))
    action_label = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioHolding(Base):
    """Portfolio holdings for the Finance Agent"""
    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        UniqueConstraint('portfolio_name', 'ticker', name='uq_portfolio_ticker'),
    )
    
    id = Column(Integer, primary_key=True)
    portfolio_name = Column(String(100), nullable=False, default="Lamido Main", index=True)
    ticker = Column(String(20), nullable=False, index=True)
    shares = Column(Float, nullable=False)
    asset_type = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CashHolding(Base):
    """Cash holdings for the Finance Agent"""
    __tablename__ = "cash_holdings"
    __table_args__ = (
        UniqueConstraint('account_name', name='uq_cash_account'),
    )
    
    id = Column(Integer, primary_key=True)
    account_name = Column(String(100), nullable=False, default="JPM", index=True)
    amount = Column(Float, nullable=False, default=0)
    currency = Column(String(10), default="USD")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ TELEMETRY & OBSERVABILITY ============

class TelemetryEvent(Base):
    """Telemetry events for cost tracking and observability"""
    __tablename__ = "telemetry_events"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String(36), nullable=False, unique=True)
    event_type = Column(String(50), nullable=False)
    category = Column(String(30), nullable=False)  # ai_api, connector_sync, agent_task
    source = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    operation = Column(String(100))
    tenant_id = Column(String(36), default='default')
    
    # AI/LLM specific
    model = Column(String(50))
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    cost_estimate = Column(Float)
    
    # Performance
    duration_ms = Column(Integer)
    
    # Status
    status = Column(String(20), default='success')
    error = Column(Text)
    
    # Tracing
    correlation_id = Column(String(36))
    endpoint_name = Column(String(100))
    
    # Metadata
    extra_data = Column(Text)  # JSON
    
    created_at = Column(DateTime, default=datetime.utcnow)


class EventLog(Base):
    """Event log for event bus persistence and at-least-once delivery"""
    __tablename__ = "event_log"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String(36), nullable=False, unique=True)
    event_type = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tenant_id = Column(String(36), default='default')
    correlation_id = Column(String(36))
    causation_id = Column(String(36))
    
    # Payload
    payload = Column(Text)  # JSON
    
    # Delivery tracking
    status = Column(String(20), default='pending')
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)


# ============ USER MANAGEMENT ============

class Org(Base):
    __tablename__ = "orgs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False)
    slug = Column(String(80), unique=True, index=True, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    users = relationship("User", back_populates="org")
    memberships = relationship("OrgMembership", back_populates="org", cascade="all, delete-orphan")


class OrgMembership(Base):
    __tablename__ = "org_memberships"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_memberships_org_user"),
    )

    id = Column(Integer, primary_key=True)
    org_id = Column(String(36), ForeignKey("orgs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="active")  # invited, active, suspended
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    org = relationship("Org", back_populates="memberships")
    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255))
    scope = Column(String(20), default="global")  # global or org
    is_system = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "org_id", name="uq_user_roles_user_role_org"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(String(36), ForeignKey("orgs.id"), nullable=True, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")


class UserCredential(Base):
    __tablename__ = "user_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_credentials_user_id"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    last_changed_at = Column(DateTime, default=datetime.utcnow)
    requires_reset = Column(Boolean, default=False)

    user = relationship("User", back_populates="credentials")


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_identities_provider_user"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    provider_user_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="auth_identities")


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    identifier = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(64))
    user_agent = Column(String(255))
    success = Column(Boolean, default=False)
    failure_reason = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(80))
    target_id = Column(String(80))
    org_id = Column(String(36), ForeignKey("orgs.id"), nullable=True, index=True)
    ip_address = Column(String(64))
    user_agent = Column(String(255))
    metadata_json = Column("metadata", JSONType)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    org_id = Column(String(36), ForeignKey("orgs.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String, unique=True, nullable=False, index=True)
    prefix = Column(String(12), index=True)
    scopes_json = Column(JSONType)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    revoked_at = Column(DateTime)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True)
    key = Column(String(120), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False)
    rules_json = Column(JSONType)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(36), default=DEFAULT_TENANT_ID, index=True)
    org_id = Column(String(36), ForeignKey("orgs.id"), nullable=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    username_normalized = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_normalized = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String(120))
    avatar_path = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    status = Column(String(20), default="active")
    lockout_until = Column(DateTime)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SessionToken(Base):
    __tablename__ = "session_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String(20), default="refresh", index=True)
    session_id = Column(String(36), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime)
    ip_address = Column(String(64))
    user_agent = Column(String(255))
    rotation_parent_id = Column(Integer, ForeignKey("session_tokens.id"))
    
    user = relationship("User", back_populates="session_tokens")


class OAuthDeviceSession(Base):
    __tablename__ = "oauth_device_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    device_code = Column(String, nullable=False)
    user_code = Column(String(64), nullable=False)
    verification_uri = Column(String, nullable=False)
    verification_uri_complete = Column(String)
    code_verifier = Column(String, nullable=False)
    code_challenge = Column(String, nullable=False)
    code_challenge_method = Column(String(10), default="S256")
    scope = Column(String, nullable=False)
    interval_seconds = Column(Integer, default=5)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending", index=True)
    error = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="oauth_device_sessions")

User.session_tokens = relationship("SessionToken", back_populates="user", lazy="dynamic")
User.chat_conversations = relationship("ChatConversation", back_populates="user", lazy="dynamic")
User.oauth_device_sessions = relationship(
    "OAuthDeviceSession", back_populates="user", cascade="all, delete-orphan"
)
User.memberships = relationship(
    "OrgMembership",
    back_populates="user",
    cascade="all, delete-orphan",
    foreign_keys="OrgMembership.user_id",
)
User.roles = relationship(
    "UserRole",
    back_populates="user",
    cascade="all, delete-orphan",
    foreign_keys="UserRole.user_id",
)
User.credentials = relationship("UserCredential", back_populates="user", uselist=False, cascade="all, delete-orphan")
User.auth_identities = relationship("AuthIdentity", back_populates="user", cascade="all, delete-orphan")
User.org = relationship("Org", back_populates="users", foreign_keys=[User.org_id])


def _normalize_user_fields(mapper, connection, target):
    if target.username:
        target.username = target.username.strip()
        target.username_normalized = target.username.lower()
    if target.email:
        target.email = target.email.strip()
        target.email_normalized = target.email.lower()


event.listen(User, "before_insert", _normalize_user_fields)
event.listen(User, "before_update", _normalize_user_fields)


# ============ AGENT CONTEXT BUDGETS & RUN LOGGING ============

class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, index=True, nullable=False)
    model = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    context_window_tokens = Column(Integer, nullable=False)
    reserved_output_tokens = Column(Integer, nullable=False, default=2048)
    budgets_json = Column(JSONType, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runs = relationship("LLMRun", back_populates="agent_profile", cascade="all, delete-orphan")
    snapshots = relationship("AgentContextSnapshot", back_populates="agent_profile", cascade="all, delete-orphan")


class LLMRun(Base):
    __tablename__ = "llm_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agent_profiles.id"), nullable=False, index=True)
    request_id = Column(String(64), index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    model = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    input_tokens_measured = Column(Integer)
    output_tokens_measured = Column(Integer)
    input_tokens_estimated = Column(Integer, nullable=False)
    output_tokens_estimated = Column(Integer, nullable=False)
    component_tokens_json = Column(JSONType, nullable=False)
    included_summary_json = Column(JSONType, nullable=False)
    trimming_applied_json = Column(JSONType, nullable=False)
    status = Column(String(20), nullable=False)
    error_json = Column(JSONType)

    agent_profile = relationship("AgentProfile", back_populates="runs")


class AgentContextSnapshot(Base):
    __tablename__ = "agent_context_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(36), ForeignKey("agent_profiles.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    snapshot_json = Column(JSONType)

    agent_profile = relationship("AgentProfile", back_populates="snapshots")


# ============ CHAT PERSISTENCE ============

class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("ChatConversation", back_populates="messages")

 
# ============ JANITOR AUDIT WIZARD ============

class JanitorWizardRun(Base):
    __tablename__ = "janitor_wizard_runs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    health_score = Column(Integer, default=0)
    status = Column(String(20), default="unknown")
    checks_passed = Column(Integer, default=0)
    checks_total = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)
    findings_json = Column(JSONType, default=list)
    sections_json = Column(JSONType, default=list)
    recommendations_json = Column(JSONType, default=list)

 
