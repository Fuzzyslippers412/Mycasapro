"""
MyCasa Pro SQLAlchemy Database Models
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text, 
    ForeignKey, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ============ SETTINGS ============

class UserSettingsDB(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False, default="lamido")
    timezone = Column(String(50), default="America/Los_Angeles")
    notification_channels = Column(JSON, default=["whatsapp"])
    intake_complete = Column(Boolean, default=False)
    intake_completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ManagerSettingsDB(Base):
    __tablename__ = "manager_settings"
    
    id = Column(Integer, primary_key=True)
    manager_id = Column(String(50), unique=True, nullable=False)
    enabled = Column(Boolean, default=True)
    config = Column(Text, default="{}")  # JSON config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BudgetPolicyDB(Base):
    __tablename__ = "budget_policies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    budget_type = Column(String(20), nullable=False)  # monthly, daily, system
    limit_amount = Column(Float, nullable=False)
    warn_at_70 = Column(Boolean, default=True)
    warn_at_85 = Column(Boolean, default=True)
    warn_at_100 = Column(Boolean, default=True)
    enforce_hard_cap = Column(Boolean, default=True)
    current_spend = Column(Float, default=0)
    period_start = Column(Date, default=date.today)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IncomeSourceDB(Base):
    __tablename__ = "income_sources"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    account_type = Column(String(50))
    institution = Column(String(100))
    is_primary = Column(Boolean, default=False)
    expected_monthly_min = Column(Float)
    expected_monthly_max = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ TRANSACTIONS ============

class TransactionDB(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index('ix_transactions_date', 'date'),
        Index('ix_transactions_category', 'consumption_category'),
    )
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(20), index=True)
    
    amount = Column(Float, nullable=False)
    merchant = Column(String(200))
    description = Column(Text)
    date = Column(Date, nullable=False, default=date.today)
    
    # Three-layer model
    funding_source = Column(String(50))
    payment_rail = Column(String(50))
    consumption_category = Column(String(50))
    
    # Classification
    is_internal_transfer = Column(Boolean, default=False)
    is_discretionary = Column(Boolean)
    is_recurring = Column(Boolean, default=False)
    
    # Metadata
    source = Column(String(20), default="manual")
    confidence = Column(String(20), default="low")
    category_confirmed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ TASKS ============

class TaskDB(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index('ix_tasks_status', 'status'),
        Index('ix_tasks_category', 'category'),
    )
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(20), index=True)
    
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), default="general")
    
    status = Column(String(20), default="pending")
    priority = Column(String(20), default="medium")
    
    assigned_agent = Column(String(50))
    assigned_contractor = Column(String(100))
    
    scheduled_date = Column(Date)
    due_date = Column(Date)
    completed_date = Column(Date)
    
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    cost_approved = Column(Boolean, default=False)
    cost_approval_id = Column(Integer)
    
    evidence = Column(Text)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ CONTRACTOR JOBS ============

class ContractorJobDB(Base):
    __tablename__ = "contractor_jobs"
    __table_args__ = (
        Index('ix_contractor_jobs_status', 'status'),
    )
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(20), index=True)
    
    # Job details
    description = Column(String(500), nullable=False)
    scope = Column(Text)
    originating_request = Column(String(50), default="user")
    request_id = Column(Integer)
    
    # Contractor
    contractor_id = Column(Integer)
    contractor_name = Column(String(100))
    contractor_role = Column(String(50))
    contact_method = Column(String(100))
    
    # Scheduling
    proposed_start = Column(Date)
    proposed_end = Column(Date)
    confirmed_start = Column(Date)
    confirmed_end = Column(Date)
    actual_start = Column(Date)
    actual_end = Column(Date)
    
    # Cost
    estimated_cost = Column(Float)
    approved_cost = Column(Float)
    actual_cost = Column(Float)
    cost_status = Column(String(30), default="unreviewed")
    
    # Status
    status = Column(String(30), default="proposed")
    urgency = Column(String(20), default="medium")
    blocked_reason = Column(Text)
    
    # Audit
    evidence = Column(Text)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ EVENTS ============

class EventDB(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index('ix_events_type', 'event_type'),
    )
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(20), index=True)
    
    event_type = Column(String(50), nullable=False)
    agent = Column(String(50))
    user_id = Column(String(50), default="lamido")
    
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    
    action = Column(String(100), nullable=False)
    details = Column(JSON, default={})
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# ============ COST TRACKING ============

class CostRecordDB(Base):
    __tablename__ = "cost_records"
    __table_args__ = (
        Index('ix_cost_records_timestamp', 'timestamp'),
    )
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(20), index=True)
    run_id = Column(String(50))
    prompt_id = Column(String(50))
    
    model_name = Column(String(50), nullable=False)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    
    estimated_cost = Column(Float, default=0)
    actual_cost = Column(Float)
    
    category = Column(String(50), default="ai_api")
    service_name = Column(String(100))
    
    tool_calls = Column(JSON, default=[])
    
    timestamp = Column(DateTime, default=datetime.utcnow)


# ============ JANITOR AUDITS ============

class JanitorAuditDB(Base):
    __tablename__ = "janitor_audits"
    __table_args__ = (
        Index("ix_janitor_audits_timestamp", "timestamp"),
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    health_score = Column(Integer, default=0)
    status = Column(String(30), default="unknown")
    checks_passed = Column(Integer, default=0)
    checks_total = Column(Integer, default=0)
    findings_count = Column(Integer, default=0)

    findings_json = Column(JSON, default=[])
    sections_json = Column(JSON, default=[])
    recommendations_json = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)


# ============ INBOX ============

class InboxMessageDB(Base):
    __tablename__ = "inbox_messages"
    __table_args__ = (
        Index('ix_inbox_messages_timestamp', 'timestamp'),
        Index('ix_inbox_messages_source', 'source'),
    )
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(200), unique=True, nullable=False)
    source = Column(String(20), nullable=False)
    
    thread_id = Column(String(200))
    sender_name = Column(String(200))
    sender_id = Column(String(200))
    
    subject = Column(String(500))
    body = Column(Text)
    
    timestamp = Column(DateTime, nullable=False)
    
    domain = Column(String(50), default="unknown")
    urgency = Column(String(20), default="medium")
    
    is_read = Column(Boolean, default=False)
    required_action = Column(String(50))
    
    linked_task_id = Column(Integer, ForeignKey("tasks.id"))
    assigned_agent = Column(String(50))
    
    raw_data = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ APPROVALS ============

class ApprovalDB(Base):
    __tablename__ = "approvals"
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String(20), index=True)
    
    approval_type = Column(String(50), nullable=False)  # cost, task, job
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    
    requested_by = Column(String(50))  # agent name
    requested_amount = Column(Float)
    
    status = Column(String(20), default="pending")  # pending, approved, denied, override
    decision_by = Column(String(50))
    decision_reason = Column(Text)
    
    budget_at_decision = Column(Float)
    remaining_at_decision = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)


# ============ BACKUP ============

class BackupRecordDB(Base):
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True)
    backup_id = Column(String(20), unique=True, nullable=False)

    file_path = Column(String(500), nullable=False)
    checksum = Column(String(64))
    size_bytes = Column(Integer)

    tables_included = Column(JSON, default=[])
    record_counts = Column(JSON, default={})

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    restored_at = Column(DateTime)


# ============ CONVERSATION HISTORY ============

class ConversationDB(Base):
    """
    Conversation session for agent chats
    Each conversation represents a continuous chat session with an agent
    """
    __tablename__ = "conversations"
    __table_args__ = (
        Index('ix_conversations_agent_id', 'agent_id'),
        Index('ix_conversations_user_id', 'user_id'),
        Index('ix_conversations_created_at', 'created_at'),
        Index('ix_conversations_status', 'status'),
    )

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(50), unique=True, nullable=False, index=True)

    # Agent and user
    agent_id = Column(String(50), nullable=False)
    user_id = Column(String(50), nullable=False, default="lamido")

    # Conversation metadata
    title = Column(String(500))  # Auto-generated from first message
    context = Column(JSON, default={})  # Additional context/metadata

    # Status
    status = Column(String(20), default="active", nullable=False)  # active, archived, deleted

    # Statistics
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime)


class MessageDB(Base):
    """
    Individual messages within a conversation
    Stores the complete message history with metadata
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index('ix_messages_conversation_id', 'conversation_id'),
        Index('ix_messages_created_at', 'created_at'),
        Index('ix_messages_role', 'role'),
    )

    id = Column(Integer, primary_key=True)
    message_id = Column(String(50), unique=True, nullable=False, index=True)

    # Foreign key to conversation
    conversation_id = Column(String(50), ForeignKey("conversations.conversation_id"), nullable=False)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Message metadata
    tokens = Column(Integer, default=0)
    model_used = Column(String(100))  # Which LLM model was used
    latency_ms = Column(Integer)  # Response time in milliseconds

    # Tool usage tracking
    tool_calls = Column(JSON, default=[])  # List of tool calls made
    tool_results = Column(JSON, default=[])  # Results from tools

    # Error tracking
    error = Column(Text)  # If message generation failed
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Index defined in __table_args__

    # Soft delete (for GDPR compliance)
    deleted_at = Column(DateTime)
