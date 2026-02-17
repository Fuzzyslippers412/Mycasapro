"""
MyCasa Pro - Connector Base Class
Abstract interface for all external service connectors
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging


class ConnectorStatus(Enum):
    """Connector health states"""
    DISABLED = "disabled"
    AUTHENTICATING = "authenticating"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class ConnectorCredentials:
    """Stored credentials for a connector"""
    connector_id: str
    tenant_id: str
    credentials: Dict[str, Any]  # Encrypted in storage
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_token_expired(self) -> bool:
        if self.token_expires_at is None:
            return False
        return datetime.utcnow() > self.token_expires_at


@dataclass
class ConnectorEvent:
    """
    Unified event from any connector.
    All connectors emit events in this format for the unified inbox.
    """
    event_id: str
    connector_id: str
    tenant_id: str
    
    # Event type
    event_type: str  # "message", "calendar", "transaction", "alert"
    
    # Source info
    source_id: str  # Original ID in source system
    source_thread_id: Optional[str] = None
    
    # Sender/origin
    sender_name: Optional[str] = None
    sender_id: Optional[str] = None
    
    # Content
    subject: Optional[str] = None
    body: Optional[str] = None
    preview: Optional[str] = None
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    received_at: datetime = field(default_factory=datetime.utcnow)
    
    # Classification
    domain: Optional[str] = None  # "finance", "maintenance", "security"
    urgency: str = "medium"  # "low", "medium", "high", "critical"
    
    # State
    is_read: bool = False
    is_actionable: bool = False
    required_action: Optional[str] = None
    
    # Raw data for debugging
    raw_data: Optional[Dict] = None
    
    # Attachments
    attachments: List[Dict] = field(default_factory=list)


class BaseConnector(ABC):
    """
    Abstract base class for all MyCasa Pro connectors.
    
    Connectors are pluggable adapters that:
    - Authenticate with external services
    - Sync data into the unified inbox
    - Send outbound messages/actions
    - Track health and handle failures
    
    Each connector must implement the abstract methods.
    """
    
    # ─── Connector Metadata (override in subclass) ──────────────────────
    connector_id: str = "base"
    display_name: str = "Base Connector"
    description: str = "Abstract base connector"
    version: str = "1.0.0"
    icon: str = "🔌"
    
    # Capabilities
    can_receive: bool = True   # Can receive/sync inbound events
    can_send: bool = True      # Can send outbound messages
    requires_auth: bool = True
    
    def __init__(self):
        self.logger = logging.getLogger(f"mycasa.connector.{self.connector_id}")
        self._status: Dict[str, ConnectorStatus] = {}  # Per-tenant status
        self._last_sync: Dict[str, datetime] = {}
        self._error_count: Dict[str, int] = {}
    
    # ─── Abstract Methods (must implement) ──────────────────────────────
    
    @abstractmethod
    async def authenticate(self, tenant_id: str, credentials: Dict[str, Any]) -> ConnectorCredentials:
        """
        Authenticate with the external service.
        
        Args:
            tenant_id: Tenant requesting auth
            credentials: Auth credentials (API keys, OAuth tokens, etc.)
        
        Returns:
            ConnectorCredentials with tokens stored
        
        Raises:
            AuthenticationError if auth fails
        """
    
    @abstractmethod
    async def refresh_auth(self, tenant_id: str, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """
        Refresh expired authentication tokens.
        
        Args:
            tenant_id: Tenant ID
            credentials: Current credentials with refresh token
        
        Returns:
            Updated ConnectorCredentials
        """
    
    @abstractmethod
    async def health_check(self, tenant_id: str) -> ConnectorStatus:
        """
        Check connector health for a tenant.
        
        Returns:
            ConnectorStatus indicating current state
        """
    
    @abstractmethod
    async def sync(
        self, 
        tenant_id: str, 
        since: datetime = None,
        limit: int = 100
    ) -> List[ConnectorEvent]:
        """
        Sync new events from the external service.
        
        Args:
            tenant_id: Tenant to sync for
            since: Only fetch events after this time
            limit: Max events to fetch
        
        Returns:
            List of ConnectorEvent objects
        """
    
    @abstractmethod
    async def send(
        self, 
        tenant_id: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an outbound message/action via the connector.
        
        Args:
            tenant_id: Tenant ID
            payload: Message payload (connector-specific format)
        
        Returns:
            Result dict with success status and any response data
        """
    
    @abstractmethod
    def get_auth_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for authentication credentials.
        Used to generate auth UI dynamically.
        
        Returns:
            JSON Schema dict describing required credentials
        """
    
    @abstractmethod
    def get_settings_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for connector settings.
        
        Returns:
            JSON Schema dict describing configurable settings
        """
    
    # ─── Built-in Methods (can override) ────────────────────────────────
    
    def get_status(self, tenant_id: str) -> ConnectorStatus:
        """Get current status for a tenant"""
        return self._status.get(tenant_id, ConnectorStatus.DISABLED)
    
    def set_status(self, tenant_id: str, status: ConnectorStatus) -> None:
        """Update status for a tenant"""
        self._status[tenant_id] = status
        self.logger.info(f"[{tenant_id}] Status changed to {status.value}")
    
    def get_last_sync(self, tenant_id: str) -> Optional[datetime]:
        """Get last sync time for a tenant"""
        return self._last_sync.get(tenant_id)
    
    def record_sync(self, tenant_id: str) -> None:
        """Record successful sync"""
        self._last_sync[tenant_id] = datetime.utcnow()
        self._error_count[tenant_id] = 0
    
    def record_error(self, tenant_id: str) -> int:
        """Record an error, returns error count"""
        self._error_count[tenant_id] = self._error_count.get(tenant_id, 0) + 1
        return self._error_count[tenant_id]
    
    def get_retry_policy(self) -> Dict[str, Any]:
        """
        Get retry policy for failed operations.
        Override to customize.
        """
        return {
            "max_retries": 3,
            "backoff_base": 2,      # Exponential backoff base (seconds)
            "backoff_max": 300,     # Max backoff (5 minutes)
            "retry_on": ["timeout", "rate_limit", "server_error"]
        }
    
    def get_sync_schedule(self) -> str:
        """
        Get cron expression for sync schedule.
        Override to customize.
        """
        return "*/5 * * * *"  # Every 5 minutes
    
    def get_info(self) -> Dict[str, Any]:
        """Get connector info for display"""
        return {
            "id": self.connector_id,
            "name": self.display_name,
            "description": self.description,
            "version": self.version,
            "icon": self.icon,
            "capabilities": {
                "receive": self.can_receive,
                "send": self.can_send,
                "requires_auth": self.requires_auth
            }
        }
    
    async def test_connection(self, tenant_id: str) -> Dict[str, Any]:
        """
        Test the connection for a tenant.
        Useful for setup validation.
        """
        try:
            status = await self.health_check(tenant_id)
            return {
                "success": status in [ConnectorStatus.HEALTHY, ConnectorStatus.DEGRADED],
                "status": status.value,
                "message": "Connection successful" if status == ConnectorStatus.HEALTHY else f"Connection {status.value}"
            }
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "status": ConnectorStatus.FAILED.value,
                "message": str(e)
            }
    
    # ─── Lifecycle Hooks ────────────────────────────────────────────────
    
    async def on_enable(self, tenant_id: str) -> None:
        """Called when connector is enabled for a tenant"""
        self.logger.info(f"[{tenant_id}] Connector enabled")
    
    async def on_disable(self, tenant_id: str) -> None:
        """Called when connector is disabled for a tenant"""
        self.logger.info(f"[{tenant_id}] Connector disabled")
        self.set_status(tenant_id, ConnectorStatus.DISABLED)
    
    async def on_auth_success(self, tenant_id: str) -> None:
        """Called after successful authentication"""
        self.set_status(tenant_id, ConnectorStatus.HEALTHY)
    
    async def on_auth_failure(self, tenant_id: str, error: Exception) -> None:
        """Called after failed authentication"""
        self.set_status(tenant_id, ConnectorStatus.FAILED)
        self.logger.error(f"[{tenant_id}] Auth failed: {error}")


class ConnectorError(Exception):
    """Base exception for connector errors"""


class AuthenticationError(ConnectorError):
    """Authentication failed"""


class RateLimitError(ConnectorError):
    """Rate limit exceeded"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class SyncError(ConnectorError):
    """Sync operation failed"""


class SendError(ConnectorError):
    """Send operation failed"""
