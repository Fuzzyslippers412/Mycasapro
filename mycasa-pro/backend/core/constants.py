"""
MyCasa Pro Constants
"""

# Budget Defaults
DEFAULT_MONTHLY_SPEND_LIMIT = 10000.0  # $10k/month
DEFAULT_DAILY_SPEND_LIMIT = 150.0       # $150/day
DEFAULT_SYSTEM_COST_LIMIT = 1000.0      # $1000/month

# Warn thresholds (percentage)
WARN_THRESHOLD_70 = 0.70
WARN_THRESHOLD_85 = 0.85
WARN_THRESHOLD_100 = 1.00

# AI Model Costs (per 1K tokens)
MODEL_COSTS = {
    "claude-opus-4": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4": {"input": 0.003, "output": 0.015},
    "claude-haiku-3.5": {"input": 0.00025, "output": 0.00125},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}

# Manager IDs
MANAGER_FINANCE = "finance"
MANAGER_CONTRACTOR = "contractor"
MANAGER_MAINTENANCE = "maintenance"
MANAGER_MAIL = "mail"
MANAGER_JANITOR = "janitor"
MANAGER_BACKUP = "backup"
MANAGER_SECURITY = "security"

ALL_MANAGERS = [
    MANAGER_FINANCE,
    MANAGER_CONTRACTOR,
    MANAGER_MAINTENANCE,
    MANAGER_MAIL,
    MANAGER_JANITOR,
    MANAGER_BACKUP,
    MANAGER_SECURITY,
]

# Task Categories
CATEGORY_GENERAL = "general"
CATEGORY_MAINTENANCE = "maintenance"
CATEGORY_FINANCE = "finance"
CATEGORY_CONTRACTOR = "contractor"
CATEGORY_SECURITY = "security"

# Event Types
EVENT_TASK_CREATED = "task_created"
EVENT_TASK_UPDATED = "task_updated"
EVENT_TASK_COMPLETED = "task_completed"
EVENT_COST_RECORDED = "cost_recorded"
EVENT_COST_APPROVED = "cost_approved"
EVENT_COST_DENIED = "cost_denied"
EVENT_JOB_PROPOSED = "job_proposed"
EVENT_JOB_SCHEDULED = "job_scheduled"
EVENT_JOB_STARTED = "job_started"
EVENT_JOB_COMPLETED = "job_completed"
EVENT_BUDGET_WARNING = "budget_warning"
EVENT_BUDGET_EXCEEDED = "budget_exceeded"
EVENT_BACKUP_CREATED = "backup_created"
EVENT_BACKUP_RESTORED = "backup_restored"
EVENT_INTAKE_COMPLETED = "intake_completed"
EVENT_MESSAGE_RECEIVED = "message_received"

# Connector Types
CONNECTOR_GMAIL = "gmail"
CONNECTOR_WHATSAPP = "whatsapp"

# Database
DEFAULT_DB_PATH = "data/mycasa.db"

# Backup
BACKUP_DIR = "backups"
