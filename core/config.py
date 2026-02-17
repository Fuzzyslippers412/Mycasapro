"""
Centralized configuration management for MyCasa Pro.

This module provides a single source of truth for all configuration values,
loaded from environment variables with validation and type safety.

Usage:
    from core.config import get_config

    config = get_config()
    print(config.TENANT_ID)
    print(config.API_BASE_URL)
"""

import os
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """
    Main configuration class for MyCasa Pro.

    All values are loaded from environment variables with sensible defaults.
    """

    # ============ TENANT CONFIGURATION ============
    TENANT_ID: str = field(
        default_factory=lambda: os.getenv("MYCASA_TENANT_ID", "default-tenant")
    )

    # ============ DEPLOYMENT ============
    ENVIRONMENT: str = field(
        default_factory=lambda: os.getenv("MYCASA_ENVIRONMENT", "development")
    )

    API_BASE_URL: str = field(
        default_factory=lambda: os.getenv("MYCASA_API_BASE_URL", "http://127.0.0.1:6709")
    )

    FRONTEND_URL: str = field(
        default_factory=lambda: os.getenv("MYCASA_FRONTEND_URL", "http://localhost:3000")
    )

    BACKEND_PORT: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_BACKEND_PORT", "6709"))
    )

    FRONTEND_PORT: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_FRONTEND_PORT", "3000"))
    )

    # ============ DATABASE ============
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "MYCASA_DATABASE_URL", "sqlite:///data/mycasa.db"
        )
    )

    DB_POOL_SIZE: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_DB_POOL_SIZE", "5"))
    )

    DB_MAX_OVERFLOW: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_DB_MAX_OVERFLOW", "10"))
    )

    # ============ SECURITY ============
    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv(
            "MYCASA_SECRET_KEY", "change-me-in-production-use-strong-random-key"
        )
    )

    JWT_EXPIRATION: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_JWT_EXPIRATION", "60"))
    )

    JWT_REFRESH_EXPIRATION: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_JWT_REFRESH_EXPIRATION", "30"))
    )

    CORS_ORIGINS: List[str] = field(
        default_factory=lambda: os.getenv(
            "MYCASA_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
        ).split(",")
    )
    CORS_ALLOW_LAN: bool = field(
        default_factory=lambda: os.getenv("MYCASA_CORS_ALLOW_LAN", "1") == "1"
    )
    CORS_ORIGIN_REGEX: Optional[str] = field(
        default_factory=lambda: os.getenv("MYCASA_CORS_ORIGIN_REGEX")
    )

    # ============ API KEYS ============
    ANTHROPIC_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )

    OPENAI_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )

    ELEVENLABS_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("ELEVENLABS_API_KEY")
    )

    # ============ GMAIL CONNECTOR ============
    GMAIL_CLIENT_ID: Optional[str] = field(
        default_factory=lambda: os.getenv("GMAIL_CLIENT_ID")
    )

    GMAIL_CLIENT_SECRET: Optional[str] = field(
        default_factory=lambda: os.getenv("GMAIL_CLIENT_SECRET")
    )

    GMAIL_REDIRECT_URI: str = field(
        default_factory=lambda: os.getenv(
            "GMAIL_REDIRECT_URI", "http://127.0.0.1:6709/oauth/gmail/callback"
        )
    )

    GMAIL_SCOPES: List[str] = field(
        default_factory=lambda: os.getenv(
            "GMAIL_SCOPES",
            "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send"
        ).split(",")
    )

    # ============ CALENDAR CONNECTOR ============
    CALENDAR_CLIENT_ID: Optional[str] = field(
        default_factory=lambda: os.getenv("CALENDAR_CLIENT_ID")
    )

    CALENDAR_CLIENT_SECRET: Optional[str] = field(
        default_factory=lambda: os.getenv("CALENDAR_CLIENT_SECRET")
    )

    CALENDAR_REDIRECT_URI: str = field(
        default_factory=lambda: os.getenv(
            "CALENDAR_REDIRECT_URI", "http://127.0.0.1:6709/oauth/calendar/callback"
        )
    )

    # ============ WHATSAPP CONNECTOR ============
    WACLI_DATA_DIR: str = field(
        default_factory=lambda: os.getenv("WACLI_DATA_DIR", "~/.wacli")
    )

    # ============ BANK CONNECTOR ============
    BANK_IMPORT_MAX_SIZE_MB: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_BANK_IMPORT_MAX_SIZE_MB", "10"))
    )

    BANK_AUTO_CATEGORIZE: bool = field(
        default_factory=lambda: os.getenv("MYCASA_BANK_AUTO_CATEGORIZE", "true").lower() == "true"
    )

    # ============ FEATURES ============
    ENABLE_WEBSOCKET: bool = field(
        default_factory=lambda: os.getenv("MYCASA_ENABLE_WEBSOCKET", "true").lower() == "true"
    )

    ENABLE_SEMANTIC_SEARCH: bool = field(
        default_factory=lambda: os.getenv("MYCASA_ENABLE_SEMANTIC_SEARCH", "true").lower() == "true"
    )

    EMBEDDING_MODEL: str = field(
        default_factory=lambda: os.getenv("MYCASA_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )

    ENABLE_AGENTS: bool = field(
        default_factory=lambda: os.getenv("MYCASA_ENABLE_AGENTS", "true").lower() == "true"
    )

    ENABLE_SECONDBRAIN: bool = field(
        default_factory=lambda: os.getenv("MYCASA_ENABLE_SECONDBRAIN", "true").lower() == "true"
    )

    # ============ SYSTEM SETTINGS ============
    MONTHLY_COST_CAP: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_MONTHLY_COST_CAP", "1000"))
    )

    LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv("MYCASA_LOG_LEVEL", "INFO")
    )

    LOG_FILE: str = field(
        default_factory=lambda: os.getenv("MYCASA_LOG_FILE", "logs/mycasa.log")
    )

    DEBUG: bool = field(
        default_factory=lambda: os.getenv("MYCASA_DEBUG", "false").lower() == "true"
    )

    # ============ PERFORMANCE ============
    CACHE_TTL: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_CACHE_TTL", "300"))
    )

    ENABLE_CACHE: bool = field(
        default_factory=lambda: os.getenv("MYCASA_ENABLE_CACHE", "true").lower() == "true"
    )

    # ============ AGENT CONFIGURATION ============
    DEFAULT_MODEL: str = field(
        default_factory=lambda: os.getenv("MYCASA_DEFAULT_MODEL", "claude-opus-4-5")
    )

    AGENT_TIMEOUT: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_AGENT_TIMEOUT", "60"))
    )

    MAX_CONCURRENT_AGENTS: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_MAX_CONCURRENT_AGENTS", "5"))
    )

    # ============ NOTIFICATIONS ============
    ENABLE_EMAIL_NOTIFICATIONS: bool = field(
        default_factory=lambda: os.getenv("MYCASA_ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
    )

    SMTP_HOST: str = field(
        default_factory=lambda: os.getenv("MYCASA_SMTP_HOST", "smtp.gmail.com")
    )

    SMTP_PORT: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_SMTP_PORT", "587"))
    )

    SMTP_USERNAME: Optional[str] = field(
        default_factory=lambda: os.getenv("MYCASA_SMTP_USERNAME")
    )

    SMTP_PASSWORD: Optional[str] = field(
        default_factory=lambda: os.getenv("MYCASA_SMTP_PASSWORD")
    )

    SMTP_FROM: str = field(
        default_factory=lambda: os.getenv("MYCASA_SMTP_FROM", "noreply@mycasa.local")
    )

    # ============ BACKUP & RECOVERY ============
    BACKUP_FREQUENCY: str = field(
        default_factory=lambda: os.getenv("MYCASA_BACKUP_FREQUENCY", "daily")
    )

    BACKUP_RETENTION_DAYS: int = field(
        default_factory=lambda: int(os.getenv("MYCASA_BACKUP_RETENTION_DAYS", "30"))
    )

    BACKUP_PATH: str = field(
        default_factory=lambda: os.getenv("MYCASA_BACKUP_PATH", "backups/")
    )

    # ============ DEVELOPMENT ============
    DEBUG_TOOLBAR: bool = field(
        default_factory=lambda: os.getenv("MYCASA_DEBUG_TOOLBAR", "false").lower() == "true"
    )

    AUTO_RELOAD: bool = field(
        default_factory=lambda: os.getenv("MYCASA_AUTO_RELOAD", "true").lower() == "true"
    )

    SQL_ECHO: bool = field(
        default_factory=lambda: os.getenv("MYCASA_SQL_ECHO", "false").lower() == "true"
    )

    # ============ TESTING ============
    TEST_DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("MYCASA_TEST_DATABASE_URL", "sqlite:///:memory:")
    )

    TEST_MOCK_APIS: bool = field(
        default_factory=lambda: os.getenv("MYCASA_TEST_MOCK_APIS", "true").lower() == "true"
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        # Check required fields in production
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "change-me-in-production-use-strong-random-key":
                raise ValueError(
                    "MYCASA_SECRET_KEY must be changed in production! "
                    "Generate a strong random key and set it in your environment."
                )

            if not self.ANTHROPIC_API_KEY:
                raise ValueError(
                    "ANTHROPIC_API_KEY is required in production! "
                    "Set it in your environment variables."
                )

            if "localhost" in self.API_BASE_URL:
                raise ValueError(
                    "MYCASA_API_BASE_URL must not contain 'localhost' in production! "
                    "Set the correct production URL."
                )

            if "localhost" in self.FRONTEND_URL:
                raise ValueError(
                    "MYCASA_FRONTEND_URL must not contain 'localhost' in production! "
                    "Set the correct production URL."
                )

        # Validate environment
        valid_environments = ["development", "staging", "production", "testing"]
        if self.ENVIRONMENT not in valid_environments:
            raise ValueError(
                f"MYCASA_ENVIRONMENT must be one of {valid_environments}, "
                f"got '{self.ENVIRONMENT}'"
            )

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ValueError(
                f"MYCASA_LOG_LEVEL must be one of {valid_log_levels}, "
                f"got '{self.LOG_LEVEL}'"
            )

        # Ensure log directory exists
        log_file_path = Path(self.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure backup directory exists
        backup_path = Path(self.BACKUP_PATH)
        backup_path.mkdir(parents=True, exist_ok=True)

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment."""
        if self.is_testing():
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL


# ============ SINGLETON INSTANCE ============

_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance (singleton pattern).

    Returns:
        Config: The global configuration object

    Example:
        >>> from core.config import get_config
        >>> config = get_config()
        >>> print(config.TENANT_ID)
        default-tenant
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = Config()

    return _config_instance


def reset_config():
    """
    Reset the configuration instance (mainly for testing).

    Warning:
        This should only be used in tests to reset configuration between test runs.
    """
    global _config_instance
    _config_instance = None


# ============ CONVENIENCE FUNCTIONS ============

def get_tenant_id() -> str:
    """Get the current tenant ID."""
    return get_config().TENANT_ID


def get_api_base_url() -> str:
    """Get the API base URL."""
    return get_config().API_BASE_URL


def get_frontend_url() -> str:
    """Get the frontend URL."""
    return get_config().FRONTEND_URL


def is_feature_enabled(feature: str) -> bool:
    """
    Check if a feature is enabled.

    Args:
        feature: Feature name (e.g., 'websocket', 'semantic_search', 'agents')

    Returns:
        bool: True if feature is enabled, False otherwise
    """
    feature = feature.upper()
    config = get_config()

    feature_map = {
        "WEBSOCKET": config.ENABLE_WEBSOCKET,
        "SEMANTIC_SEARCH": config.ENABLE_SEMANTIC_SEARCH,
        "AGENTS": config.ENABLE_AGENTS,
        "SECONDBRAIN": config.ENABLE_SECONDBRAIN,
        "CACHE": config.ENABLE_CACHE,
        "EMAIL_NOTIFICATIONS": config.ENABLE_EMAIL_NOTIFICATIONS,
    }

    return feature_map.get(feature, False)


# ============ EXPORTS ============

__all__ = [
    "Config",
    "get_config",
    "reset_config",
    "get_tenant_id",
    "get_api_base_url",
    "get_frontend_url",
    "is_feature_enabled",
]
