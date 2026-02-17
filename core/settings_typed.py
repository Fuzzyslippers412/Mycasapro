"""
MyCasa Pro - Typed Settings System
Pydantic models for all settings with validation and per-agent scoping.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import os


# ============ ENUMS ============

class InvestmentStyle(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


class RecommendationStyle(str, Enum):
    """
    Finance agent recommendation framing style.
    Controls how recommendations are presented and what timeframes are emphasized.
    """
    QUICK_FLIP = "quick_flip"        # Buy cheap, sell fast (days to weeks)
    ONE_YEAR_PLAN = "one_year_plan"  # Medium-term growth (1 year horizon)
    LONG_TERM_HOLD = "long_term_hold"  # Buy and hold (3-5+ years)
    BALANCED = "balanced"            # Mix of strategies based on position


class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationChannel(str, Enum):
    NONE = "none"
    INAPP = "inapp"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class BackupFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ============ BASE SETTINGS ============

class AgentSettings(BaseModel):
    """Base class for all agent settings"""
    enabled: bool = True
    notification_channel: NotificationChannel = NotificationChannel.INAPP
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


# ============ SYSTEM SETTINGS ============

class NotificationSettings(BaseModel):
    """Notification preferences"""
    in_app: bool = True
    push: bool = False
    email: bool = False
    alert_email: str = ""
    whatsapp: bool = False
    alert_phone: str = ""
    
    # What to notify about
    urgent_only: bool = False
    daily_summary: bool = True
    weekly_report: bool = True


class SystemSettings(BaseModel):
    """Global system settings"""
    running: bool = False
    auto_refresh: bool = True
    monthly_cost_cap: float = Field(default=1000.0, ge=0)
    daily_spend_limit: float = Field(default=350.0, ge=0)
    approval_threshold: float = Field(default=500.0, ge=0)
    timezone: str = "America/Los_Angeles"
    household_name: str = "My Home"
    locale: str = "en-US"
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai-compatible"))
    llm_base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.venice.ai/api/v1"))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL") or os.getenv("QWEN_MODEL", "qwen2.5-72b-instruct"))
    llm_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LLM_API_KEY") or os.getenv("VENICE_API_KEY") or os.getenv("QWEN_API_KEY"))
    llm_auth_type: str = Field(default_factory=lambda: os.getenv("LLM_AUTH_TYPE", "api_key"))
    llm_oauth: Optional[Dict[str, Any]] = None
    
    @field_validator('monthly_cost_cap', 'daily_spend_limit', 'approval_threshold')
    @classmethod
    def must_be_positive(cls, v):
        if v < 0:
            raise ValueError('must be non-negative')
        return v


# ============ AGENT-SPECIFIC SETTINGS ============

class FinanceSettings(AgentSettings):
    """Finance agent settings"""
    # Investment approach
    investment_style: InvestmentStyle = InvestmentStyle.MODERATE
    recommendation_style: RecommendationStyle = RecommendationStyle.BALANCED
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    
    # Constraints
    target_annual_return: float = Field(default=12.0, ge=1, le=50)
    max_single_position_pct: float = Field(default=15.0, ge=5, le=50)
    min_holding_days: int = Field(default=30, ge=1, le=1825)  # 1 day to 5 years
    
    # Spending limits
    monthly_spend_cap: float = Field(default=10000.0, ge=0)
    daily_spend_cap: float = Field(default=150.0, ge=0)
    
    # Income source
    primary_income_source: str = "JP Morgan Brokerage"
    
    # Sectors
    focus_sectors: List[str] = Field(default_factory=lambda: ["balanced"])
    
    # Alerts
    rebalancing_alerts: bool = True
    buy_recommendations: bool = True
    sell_alerts: bool = True
    earnings_warnings: bool = True
    bill_due_days_ahead: int = Field(default=7, ge=1, le=30)
    
    # Notes
    investment_notes: str = ""
    
    # Disclaimer requirement
    include_disclaimer: bool = True  # Always include "not financial advice"
    
    @field_validator('recommendation_style', mode='after')
    @classmethod
    def validate_recommendation_risk_combo(cls, v, info):
        """Validate that recommendation style and risk tolerance are compatible"""
        # This runs after the field is set
        return v
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration for contradictions.
        Returns list of error messages (empty if valid).
        """
        errors = []
        
        # QUICK_FLIP with LOW risk is contradictory
        if self.recommendation_style == RecommendationStyle.QUICK_FLIP:
            if self.risk_tolerance == RiskTolerance.LOW:
                errors.append("QUICK_FLIP recommendation style requires at least MEDIUM risk tolerance")
            if self.min_holding_days > 30:
                errors.append("QUICK_FLIP style typically has min_holding_days <= 30")
        
        # LONG_TERM_HOLD with HIGH target return is unrealistic
        if self.recommendation_style == RecommendationStyle.LONG_TERM_HOLD:
            if self.target_annual_return > 25:
                errors.append("LONG_TERM_HOLD style with >25% target return is unrealistic")
        
        # Spending caps sanity check
        if self.daily_spend_cap * 30 > self.monthly_spend_cap:
            errors.append("daily_spend_cap * 30 exceeds monthly_spend_cap (impossible to stay under)")
        
        return errors
    
    def get_recommendation_framing(self) -> Dict[str, Any]:
        """
        Get recommendation framing based on style.
        Used by Finance agent to adjust output.
        """
        framing = {
            RecommendationStyle.QUICK_FLIP: {
                "timeframe": "days to weeks",
                "focus": "momentum, volatility, quick gains",
                "exit_strategy": "take profits early, cut losses fast",
                "typical_holding": "1-30 days",
            },
            RecommendationStyle.ONE_YEAR_PLAN: {
                "timeframe": "1 year",
                "focus": "growth catalysts, earnings potential",
                "exit_strategy": "review quarterly, rebalance annually",
                "typical_holding": "3-12 months",
            },
            RecommendationStyle.LONG_TERM_HOLD: {
                "timeframe": "3-5+ years",
                "focus": "fundamentals, competitive moat, dividends",
                "exit_strategy": "hold through volatility, trim on overvaluation",
                "typical_holding": "years",
            },
            RecommendationStyle.BALANCED: {
                "timeframe": "mixed",
                "focus": "diversification, risk-adjusted returns",
                "exit_strategy": "position-specific based on thesis",
                "typical_holding": "varies by position",
            },
        }
        return framing.get(self.recommendation_style, framing[RecommendationStyle.BALANCED])
    
    def get_disclaimer(self) -> str:
        """Standard disclaimer for all recommendations"""
        if self.include_disclaimer:
            return (
                "⚠️ NOT FINANCIAL ADVICE: This is for informational purposes only. "
                "Always do your own research and consult a qualified financial advisor "
                "before making investment decisions."
            )
        return ""


class MaintenanceSettings(AgentSettings):
    """Maintenance agent settings"""
    auto_schedule_recurring: bool = True
    reminder_days_ahead: int = Field(default=3, ge=1, le=14)
    overdue_alert_threshold_days: int = Field(default=7, ge=1, le=30)


class ContractorsSettings(AgentSettings):
    """Contractors agent settings"""
    auto_rate_after_service: bool = True
    preferred_contact_method: str = "phone"


class ProjectsSettings(AgentSettings):
    """Projects agent settings"""
    milestone_reminders: bool = True
    budget_overage_alert_pct: float = Field(default=10.0, ge=0, le=100)


class SecuritySettings(AgentSettings):
    """Security agent settings"""
    threat_monitoring: bool = True
    credential_rotation_days: int = Field(default=90, ge=30, le=365)
    audit_logging: bool = True


class JanitorSettings(AgentSettings):
    """Janitor (telemetry) agent settings"""
    log_retention_days: int = Field(default=30, ge=7, le=365)
    cleanup_frequency: BackupFrequency = BackupFrequency.DAILY
    collect_telemetry: bool = True


class BackupSettings(AgentSettings):
    """Backup & recovery settings"""
    enabled: bool = True  # On by default
    frequency: BackupFrequency = BackupFrequency.DAILY
    retention_count: int = Field(default=10, ge=1, le=100)
    include_database: bool = True
    include_state: bool = True


class MailSettings(AgentSettings):
    """Mail/Inbox agent settings"""
    gmail_enabled: bool = True
    whatsapp_enabled: bool = True
    sync_interval_minutes: int = Field(default=15, ge=5, le=60)
    auto_triage: bool = True
    allow_agent_replies: bool = False
    allow_whatsapp_replies: bool = False
    allow_email_replies: bool = False


class ManagerSettings(AgentSettings):
    """Manager (Galidima) agent settings - always on by default"""
    enabled: bool = True
    model: str = "claude-opus-4"
    thinking: str = "medium"


# ============ AGGREGATED SETTINGS ============

class AllAgentSettings(BaseModel):
    """Container for all agent settings"""
    manager: ManagerSettings = Field(default_factory=ManagerSettings)
    finance: FinanceSettings = Field(default_factory=FinanceSettings)
    maintenance: MaintenanceSettings = Field(default_factory=MaintenanceSettings)
    contractors: ContractorsSettings = Field(default_factory=ContractorsSettings)
    projects: ProjectsSettings = Field(default_factory=ProjectsSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    janitor: JanitorSettings = Field(default_factory=JanitorSettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    mail: MailSettings = Field(default_factory=MailSettings)


class MyCasaSettings(BaseModel):
    """Complete settings model for MyCasa Pro"""
    version: str = "1.1.1"
    updated_at: datetime = Field(default_factory=datetime.now)
    system: SystemSettings = Field(default_factory=SystemSettings)
    agents: AllAgentSettings = Field(default_factory=AllAgentSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    
    def get_enabled_agents(self) -> Dict[str, bool]:
        """Return dict of agent_name -> enabled status"""
        return {
            "finance": self.agents.finance.enabled,
            "maintenance": self.agents.maintenance.enabled,
            "contractors": self.agents.contractors.enabled,
            "projects": self.agents.projects.enabled,
            "security": self.agents.security.enabled,
            "janitor": self.agents.janitor.enabled,
            "backup": self.agents.backup.enabled,
            "mail": self.agents.mail.enabled,
        }
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dict for legacy compatibility"""
        return {
            "running": self.system.running,
            "agents_enabled": self.get_enabled_agents(),
            "settings": self.model_dump(exclude={"version", "updated_at"}),
        }


# ============ SETTINGS STORAGE ============

class SettingsStore:
    """
    Settings storage with DB persistence and validation.
    Uses system_state.json for now, can be migrated to DB later.
    """
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self._settings: Optional[MyCasaSettings] = None
        self._mtime: Optional[float] = None
    
    def load(self) -> MyCasaSettings:
        """Load settings from disk, return defaults if not found"""
        import json
        from pathlib import Path
        
        raw_data: Optional[Dict[str, Any]] = None
        path = Path(self.state_file)
        if path.exists():
            try:
                try:
                    self._mtime = path.stat().st_mtime
                except Exception:
                    self._mtime = None
                with open(path) as f:
                    data = json.load(f)
                raw_data = data
                
                # Try to parse as new format
                if "version" in data and "system" in data:
                    self._settings = MyCasaSettings.model_validate(data)
                else:
                    # Legacy format - migrate
                    self._settings = self._migrate_legacy(data)
            except Exception as e:
                print(f"[SettingsStore] Error loading settings: {e}, using defaults")
                self._settings = MyCasaSettings()
        else:
            self._settings = MyCasaSettings()
            self._mtime = None

        self._apply_migrations(raw_data)
        return self._settings

    def _apply_migrations(self, raw_data: Optional[Dict[str, Any]]) -> None:
        """Apply targeted migrations for settings changes."""
        if self._settings is None:
            return

        def _version_tuple(value: str) -> tuple[int, int, int]:
            try:
                parts = [int(p) for p in value.split(".")]
                while len(parts) < 3:
                    parts.append(0)
                return (parts[0], parts[1], parts[2])
            except Exception:
                return (0, 0, 0)

        current_version = _version_tuple(self._settings.version)
        if current_version >= (1, 1, 1):
            return

        # Determine if backup/mail were explicitly set in stored data
        backup_explicit: Optional[bool] = None
        mail_explicit: Optional[bool] = None
        if isinstance(raw_data, dict):
            if isinstance(raw_data.get("agents"), dict):
                backup_explicit = raw_data["agents"].get("backup", {}).get("enabled")
                mail_explicit = raw_data["agents"].get("mail", {}).get("enabled")
            elif isinstance(raw_data.get("agents_enabled"), dict):
                backup_explicit = raw_data["agents_enabled"].get("backup")
                mail_explicit = raw_data["agents_enabled"].get("mail")

        changed = False
        if backup_explicit is None:
            self._settings.agents.backup.enabled = True
            changed = True
        if mail_explicit is None:
            self._settings.agents.mail.enabled = True
            changed = True

        if self._settings.agents.backup.enabled is False:
            self._settings.agents.backup.enabled = True
            changed = True

        if changed:
            self._settings.version = "1.1.1"
            self.save(self._settings)
    
    def save(self, settings: MyCasaSettings) -> bool:
        """Save settings to disk"""
        import json
        from pathlib import Path
        
        try:
            settings.updated_at = datetime.now()
            path = Path(self.state_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(settings.model_dump(mode='json'), f, indent=2, default=str)
            try:
                self._mtime = path.stat().st_mtime
            except Exception:
                self._mtime = None
            
            self._settings = settings
            return True
        except Exception as e:
            print(f"[SettingsStore] Error saving settings: {e}")
            return False
    
    def get(self) -> MyCasaSettings:
        """Get current settings (loads if not cached)"""
        from pathlib import Path
        if self._settings is None:
            return self.load()
        try:
            path = Path(self.state_file)
            if path.exists():
                mtime = path.stat().st_mtime
                if self._mtime is None or (mtime and mtime > self._mtime):
                    settings = self.load()
                    try:
                        from core.llm_client import reset_llm_client
                        reset_llm_client()
                    except Exception:
                        pass
                    return settings
        except Exception:
            pass
        return self._settings
    
    def update_system(self, **kwargs) -> MyCasaSettings:
        """Update system settings"""
        settings = self.get()
        for key, value in kwargs.items():
            if hasattr(settings.system, key):
                setattr(settings.system, key, value)
        self.save(settings)
        return settings
    
    def update_agent(self, agent_name: str, **kwargs) -> MyCasaSettings:
        """Update specific agent settings"""
        settings = self.get()
        agent_settings = getattr(settings.agents, agent_name, None)
        if agent_settings:
            for key, value in kwargs.items():
                if hasattr(agent_settings, key):
                    setattr(agent_settings, key, value)
            self.save(settings)
        return settings
    
    def _migrate_legacy(self, data: Dict) -> MyCasaSettings:
        """Migrate legacy settings format to new typed format"""
        settings = MyCasaSettings()
        
        # Migrate system state
        settings.system.running = data.get("running", False)
        
        # Migrate agents_enabled
        agents_enabled = data.get("agents_enabled", {})
        if "finance" in agents_enabled:
            settings.agents.finance.enabled = agents_enabled["finance"]
        if "maintenance" in agents_enabled:
            settings.agents.maintenance.enabled = agents_enabled["maintenance"]
        if "contractors" in agents_enabled:
            settings.agents.contractors.enabled = agents_enabled["contractors"]
        if "projects" in agents_enabled:
            settings.agents.projects.enabled = agents_enabled["projects"]
        if "security" in agents_enabled:
            settings.agents.security.enabled = agents_enabled["security"]
        if "janitor" in agents_enabled:
            settings.agents.janitor.enabled = agents_enabled["janitor"]
        if "backup" in agents_enabled:
            settings.agents.backup.enabled = agents_enabled["backup"]
        if "mail" in agents_enabled:
            settings.agents.mail.enabled = agents_enabled["mail"]
        
        return settings


# Singleton instance
_settings_store: Optional[SettingsStore] = None

def get_settings_store() -> SettingsStore:
    """Get global settings store instance"""
    global _settings_store
    if _settings_store is None:
        from config.settings import STATE_FILE
        _settings_store = SettingsStore(str(STATE_FILE).replace("system_state.json", "settings.json"))
    return _settings_store
