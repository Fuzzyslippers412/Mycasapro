"""
MyCasa Pro Pydantic Schemas
All data models for API request/response and internal use
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
from enum import Enum
from uuid import uuid4


# ============ ENUMS ============

class TaskStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    OVERRIDE = "override"


class ConnectorStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    STUB = "stub"


# ============ BASE SCHEMAS ============

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    status: Literal["success", "error"] = "success"
    correlation_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None


class HealthStatus(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str = "1.0.0"
    uptime_seconds: float = 0
    db_status: str = "connected"
    queue_status: str = "idle"
    active_tasks: int = 0
    connectors: Dict[str, str] = {}


# ============ USER & SETTINGS ============

class UserSettings(BaseModel):
    """Global user settings"""
    user_id: str = "lamido"
    timezone: str = "America/Los_Angeles"
    notification_channels: List[str] = ["whatsapp"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ManagerSettings(BaseModel):
    """Per-manager settings"""
    manager_id: str  # finance, contractor, mail, janitor, backup
    enabled: bool = True
    config: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BudgetPolicy(BaseModel):
    """Budget policy configuration"""
    id: Optional[int] = None
    name: str
    budget_type: Literal["monthly", "daily", "system"]
    limit_amount: float
    warn_at_70: bool = True
    warn_at_85: bool = True
    warn_at_100: bool = True
    enforce_hard_cap: bool = True
    current_spend: float = 0
    period_start: date = Field(default_factory=date.today)
    is_active: bool = True


class IncomeSource(BaseModel):
    """Income source definition"""
    id: Optional[int] = None
    name: str
    account_type: str  # brokerage, checking, savings
    institution: str
    is_primary: bool = False
    expected_monthly_min: Optional[float] = None
    expected_monthly_max: Optional[float] = None
    is_active: bool = True


# ============ TRANSACTIONS ============

class Transaction(BaseModel):
    """Financial transaction"""
    id: Optional[int] = None
    correlation_id: str = ""
    amount: float
    merchant: Optional[str] = None
    description: Optional[str] = None
    txn_date: date = Field(default_factory=date.today)
    
    # Three-layer model
    funding_source: Optional[str] = None  # Chase Checking, JPM Brokerage, etc.
    payment_rail: Optional[str] = None    # Direct, Apple Cash, Zelle, ACH
    consumption_category: Optional[str] = None  # Dining, Groceries, Housing
    
    # Classification
    is_internal_transfer: bool = False
    is_discretionary: Optional[bool] = None
    is_recurring: bool = False
    
    # Metadata
    txn_source: str = "manual"  # manual, import, screenshot
    confidence: str = "low"  # low, medium, high
    category_confirmed: bool = False
    
    def __init__(self, **data):
        if not data.get("correlation_id"):
            data["correlation_id"] = str(uuid4())[:8]
        # Handle 'date' -> 'txn_date' mapping
        if "date" in data and "txn_date" not in data:
            data["txn_date"] = data.pop("date")
        # Handle 'source' -> 'txn_source' mapping
        if "source" in data and "txn_source" not in data:
            data["txn_source"] = data.pop("source")
        super().__init__(**data)


class TransactionIngest(BaseModel):
    """Batch transaction ingest request"""
    transactions: List[Transaction]
    ingest_source: str = "import"
    deduplicate: bool = True


# ============ TASKS ============

class Task(BaseModel):
    """Task/job model"""
    id: Optional[int] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    
    title: str
    description: Optional[str] = None
    category: str = "general"  # maintenance, finance, contractor, etc.
    
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    
    assigned_agent: Optional[str] = None
    assigned_contractor: Optional[str] = None
    
    scheduled_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    cost_approved: bool = False
    cost_approval_id: Optional[int] = None
    
    evidence: Optional[str] = None
    notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskCreate(BaseModel):
    """Task creation request"""
    title: str
    description: Optional[str] = None
    category: str = "general"
    priority: Priority = Priority.MEDIUM
    scheduled_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_cost: Optional[float] = None
    assigned_agent: Optional[str] = None
    assigned_contractor: Optional[str] = None


class TaskUpdate(BaseModel):
    """Task update request"""
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    scheduled_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    actual_cost: Optional[float] = None
    evidence: Optional[str] = None
    notes: Optional[str] = None


# ============ CONTRACTOR WORKFLOW ============

class ContractorJob(BaseModel):
    """Contractor job with full lifecycle"""
    id: Optional[int] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    
    # Job details
    description: str
    scope: Optional[str] = None
    originating_request: str = "user"  # user, maintenance, project
    request_id: Optional[int] = None
    
    # Contractor
    contractor_id: Optional[int] = None
    contractor_name: Optional[str] = None
    contractor_role: Optional[str] = None
    contact_method: Optional[str] = None
    
    # Scheduling
    proposed_start: Optional[date] = None
    proposed_end: Optional[date] = None
    confirmed_start: Optional[date] = None
    confirmed_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    
    # Cost
    estimated_cost: Optional[float] = None
    approved_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    cost_status: str = "unreviewed"  # unreviewed, pending_approval, approved, rejected
    
    # Status
    status: TaskStatus = TaskStatus.PROPOSED
    urgency: Priority = Priority.MEDIUM
    blocked_reason: Optional[str] = None
    
    # Audit
    evidence: Optional[str] = None
    notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContractorJobCreate(BaseModel):
    """Create contractor job request"""
    description: str
    scope: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_role: Optional[str] = None
    proposed_start: Optional[date] = None
    proposed_end: Optional[date] = None
    estimated_cost: Optional[float] = None
    urgency: Priority = Priority.MEDIUM


# ============ EVENTS ============

class Event(BaseModel):
    """System event for audit trail"""
    id: Optional[int] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    
    event_type: str  # task_created, cost_approved, job_scheduled, etc.
    agent: Optional[str] = None
    user_id: str = "lamido"
    
    entity_type: Optional[str] = None  # task, job, transaction, etc.
    entity_id: Optional[int] = None
    
    action: str
    details: Dict[str, Any] = {}
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ COST TRACKING ============

class CostRecord(BaseModel):
    """AI/system cost record"""
    id: Optional[int] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    run_id: Optional[str] = None
    prompt_id: Optional[str] = None
    
    model_name: str
    tokens_in: int = 0
    tokens_out: int = 0
    
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None
    
    category: str = "ai_api"  # ai_api, hosting, storage, integrations
    service_name: Optional[str] = None
    
    tool_calls: List[str] = []
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CostSummary(BaseModel):
    """Cost summary for a period"""
    period: str  # "today", "month", "all"
    total_cost: float = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    by_model: Dict[str, float] = {}
    by_category: Dict[str, float] = {}
    budget_limit: float = 1000.0  # $1000/month system cap
    budget_used_pct: float = 0


# ============ INBOX / MESSAGES ============

class InboxMessage(BaseModel):
    """Unified inbox message"""
    id: Optional[int] = None
    external_id: str
    source: Literal["gmail", "whatsapp"]
    
    thread_id: Optional[str] = None
    sender_name: str
    sender_id: str
    
    subject: Optional[str] = None
    body: Optional[str] = None
    
    timestamp: datetime
    
    domain: str = "unknown"  # finance, maintenance, contractors, etc.
    urgency: Priority = Priority.MEDIUM
    
    is_read: bool = False
    required_action: Optional[str] = None
    
    linked_task_id: Optional[int] = None
    assigned_agent: Optional[str] = None


# ============ BACKUP ============

class BackupMetadata(BaseModel):
    """Backup snapshot metadata"""
    backup_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    tables_included: List[str] = []
    record_counts: Dict[str, int] = {}
    
    checksum: Optional[str] = None
    size_bytes: int = 0
    
    notes: Optional[str] = None


class BackupRestore(BaseModel):
    """Backup restore request"""
    backup_path: str
    verify_checksum: bool = True
    dry_run: bool = False


# ============ INTAKE ============

class IntakeRequest(BaseModel):
    """Initial system intake/setup request"""
    primary_income_source: IncomeSource
    monthly_spend_limit: float = 10000.0
    daily_spend_limit: float = 150.0
    system_cost_limit: float = 1000.0
    
    enable_gmail: bool = True
    enable_whatsapp: bool = True
    
    notification_channels: List[str] = ["whatsapp"]


class IntakeStatus(BaseModel):
    """Intake completion status"""
    intake_complete: bool = False
    intake_completed_at: Optional[datetime] = None
    
    primary_income_configured: bool = False
    budgets_configured: bool = False
    connectors_configured: bool = False
    
    missing_items: List[str] = []
