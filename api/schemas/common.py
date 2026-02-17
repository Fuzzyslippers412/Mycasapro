"""
MyCasa Pro API - Common Schemas
Consistent response formats and error handling.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime
import uuid


# ============ BASE RESPONSE ============

class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional["APIError"] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class APIError(BaseModel):
    """Standard error format"""
    error_code: str
    message: str
    detail: Optional[str] = None
    correlation_id: Optional[str] = None


# ============ PAGINATION ============

class PaginationParams(BaseModel):
    """Pagination parameters"""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class PaginatedResponse(APIResponse):
    """Response with pagination info"""
    total: int = 0
    offset: int = 0
    limit: int = 50
    has_more: bool = False


# ============ SYSTEM SCHEMAS ============

class SystemStatusResponse(BaseModel):
    """System status response"""
    running: bool
    state: str
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    last_backup: Optional[str]
    agents_enabled: Dict[str, bool]
    agents_enabled_count: int
    agents_running_count: int
    personal_mode: Optional[bool] = None
    auth_mode: Optional[str] = None
    identity: Optional[Dict[str, Any]] = None
    heartbeat: Optional[Dict[str, Any]] = None


class StartupRequest(BaseModel):
    """System startup request"""
    force: bool = False


class StartupResponse(APIResponse):
    """System startup response"""
    already_running: bool = False
    agents_started: List[str] = []
    restored_from: Optional[datetime] = None


class ShutdownRequest(BaseModel):
    """System shutdown request"""
    create_backup: bool = True
    agents_enabled: Optional[Dict[str, bool]] = None
    settings: Optional[Dict[str, Any]] = None


class ShutdownResponse(APIResponse):
    """System shutdown response"""
    already_stopped: bool = False
    backup: Optional[Dict[str, Any]] = None


# ============ HEALTH CHECK ============

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.now)
    system_running: bool = False
    database: str = "ok"
    event_bus: str = "ok"


# ============ BACKUP SCHEMAS ============

class BackupInfo(BaseModel):
    """Backup information"""
    name: str
    timestamp: str
    path: str
    files: List[str]
    size_bytes: int


class BackupListResponse(APIResponse):
    """List of backups"""
    backups: List[BackupInfo] = []


class BackupCreateResponse(APIResponse):
    """Backup creation response"""
    timestamp: str
    backup_path: str
    files: List[str]


class BackupRestoreRequest(BaseModel):
    """Backup restore request"""
    backup_name: str


class BackupRestoreResponse(APIResponse):
    """Backup restore response"""
    backup_name: str
    restored_files: List[str] = []
