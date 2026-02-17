"""
Unit tests for the configuration system.

Tests cover:
- Configuration loading from environment
- Default values
- Validation logic
- Environment-specific behavior
"""

import pytest
import os
from unittest.mock import patch


@pytest.mark.unit
class TestConfigBasics:
    """Test basic configuration functionality."""

    def test_config_loads_with_defaults(self):
        """Test that config loads with default values."""
        from core.config import get_config, reset_config

        # Reset to ensure clean state
        reset_config()

        config = get_config()
        assert config is not None
        assert config.TENANT_ID == "default-tenant"
        assert config.ENVIRONMENT == "development"

    def test_config_singleton_pattern(self):
        """Test that get_config returns the same instance."""
        from core.config import get_config

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_config_reset(self):
        """Test that reset_config clears the singleton."""
        from core.config import get_config, reset_config

        config1 = get_config()
        reset_config()
        config2 = get_config()
        # Should be different instances after reset
        assert config1 is not config2


@pytest.mark.unit
class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_tenant_id(self):
        """Test default tenant ID."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert config.TENANT_ID == "default-tenant"

    def test_default_urls(self):
        """Test default URL configuration."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert "localhost" in config.API_BASE_URL
        assert "localhost" in config.FRONTEND_URL

    def test_default_ports(self):
        """Test default port configuration."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert config.BACKEND_PORT == 8000
        assert config.FRONTEND_PORT == 3000

    def test_default_features_enabled(self):
        """Test that features are enabled by default."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert config.ENABLE_WEBSOCKET is True
        assert config.ENABLE_AGENTS is True
        assert config.ENABLE_SECONDBRAIN is True


@pytest.mark.unit
class TestConfigEnvironmentDetection:
    """Test environment detection methods."""

    def test_is_development(self):
        """Test development environment detection."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert config.is_development() is True
        assert config.is_production() is False
        assert config.is_testing() is False

    @patch.dict(os.environ, {"MYCASA_ENVIRONMENT": "production"})
    def test_is_production(self):
        """Test production environment detection."""
        from core.config import reset_config, Config

        reset_config()
        # Override environment just for this test
        with patch.dict(os.environ, {
            "MYCASA_ENVIRONMENT": "production",
            "MYCASA_SECRET_KEY": "test-secret-key-for-testing",
            "ANTHROPIC_API_KEY": "test-api-key",
            "MYCASA_API_BASE_URL": "https://api.example.com",
            "MYCASA_FRONTEND_URL": "https://example.com",
        }):
            config = Config()
            assert config.is_production() is True
            assert config.is_development() is False

    @patch.dict(os.environ, {"MYCASA_ENVIRONMENT": "testing"})
    def test_is_testing(self):
        """Test testing environment detection."""
        from core.config import reset_config, Config

        reset_config()
        config = Config()
        assert config.is_testing() is True
        assert config.is_production() is False


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation logic."""

    def test_invalid_environment_raises_error(self):
        """Test that invalid environment raises ValueError."""
        from core.config import Config

        with patch.dict(os.environ, {"MYCASA_ENVIRONMENT": "invalid"}):
            with pytest.raises(ValueError, match="MYCASA_ENVIRONMENT must be one of"):
                Config()

    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises ValueError."""
        from core.config import Config

        with patch.dict(os.environ, {"MYCASA_LOG_LEVEL": "INVALID"}):
            with pytest.raises(ValueError, match="MYCASA_LOG_LEVEL must be one of"):
                Config()

    def test_production_requires_secret_key(self):
        """Test that production environment requires custom secret key."""
        from core.config import Config

        with patch.dict(os.environ, {
            "MYCASA_ENVIRONMENT": "production",
            "ANTHROPIC_API_KEY": "test-key",
            "MYCASA_API_BASE_URL": "https://api.example.com",
            "MYCASA_FRONTEND_URL": "https://example.com",
        }):
            with pytest.raises(ValueError, match="MYCASA_SECRET_KEY must be changed"):
                Config()

    def test_production_requires_api_key(self):
        """Test that production environment requires API key."""
        from core.config import Config

        with patch.dict(os.environ, {
            "MYCASA_ENVIRONMENT": "production",
            "MYCASA_SECRET_KEY": "test-secret-key",
            "MYCASA_API_BASE_URL": "https://api.example.com",
            "MYCASA_FRONTEND_URL": "https://example.com",
        }):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
                Config()

    def test_production_disallows_localhost_urls(self):
        """Test that production environment disallows localhost URLs."""
        from core.config import Config

        with patch.dict(os.environ, {
            "MYCASA_ENVIRONMENT": "production",
            "MYCASA_SECRET_KEY": "test-secret-key",
            "ANTHROPIC_API_KEY": "test-key",
            "MYCASA_API_BASE_URL": "http://localhost:8000",  # Should fail
        }):
            with pytest.raises(ValueError, match="must not contain 'localhost'"):
                Config()


@pytest.mark.unit
class TestConfigConvenienceFunctions:
    """Test convenience functions."""

    def test_get_tenant_id(self):
        """Test get_tenant_id convenience function."""
        from core.config import get_tenant_id, reset_config

        reset_config()
        tenant_id = get_tenant_id()
        assert tenant_id == "default-tenant"

    def test_get_api_base_url(self):
        """Test get_api_base_url convenience function."""
        from core.config import get_api_base_url, reset_config

        reset_config()
        url = get_api_base_url()
        assert "localhost" in url

    def test_get_frontend_url(self):
        """Test get_frontend_url convenience function."""
        from core.config import get_frontend_url, reset_config

        reset_config()
        url = get_frontend_url()
        assert "localhost" in url

    def test_is_feature_enabled(self):
        """Test is_feature_enabled convenience function."""
        from core.config import is_feature_enabled, reset_config

        reset_config()
        assert is_feature_enabled("websocket") is True
        assert is_feature_enabled("agents") is True
        assert is_feature_enabled("secondbrain") is True


@pytest.mark.unit
class TestConfigDatabaseURL:
    """Test database URL configuration."""

    def test_development_database_url(self):
        """Test database URL in development."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert "sqlite" in config.get_database_url()

    def test_testing_uses_memory_database(self):
        """Test that testing environment uses in-memory database."""
        from core.config import Config

        with patch.dict(os.environ, {"MYCASA_ENVIRONMENT": "testing"}):
            config = Config()
            assert config.get_database_url() == "sqlite:///:memory:"


@pytest.mark.unit
class TestConfigFeatureFlags:
    """Test feature flag functionality."""

    def test_feature_flags_default_enabled(self):
        """Test that feature flags are enabled by default."""
        from core.config import get_config, reset_config

        reset_config()
        config = get_config()
        assert config.ENABLE_WEBSOCKET is True
        assert config.ENABLE_SEMANTIC_SEARCH is True
        assert config.ENABLE_AGENTS is True
        assert config.ENABLE_SECONDBRAIN is True
        assert config.ENABLE_CACHE is True

    @patch.dict(os.environ, {"MYCASA_ENABLE_WEBSOCKET": "false"})
    def test_disable_websocket_feature(self):
        """Test disabling WebSocket feature."""
        from core.config import Config

        config = Config()
        assert config.ENABLE_WEBSOCKET is False

    @patch.dict(os.environ, {"MYCASA_ENABLE_AGENTS": "false"})
    def test_disable_agents_feature(self):
        """Test disabling agents feature."""
        from core.config import Config

        config = Config()
        assert config.ENABLE_AGENTS is False


@pytest.mark.unit
class TestConfigCustomValues:
    """Test loading custom values from environment."""

    @patch.dict(os.environ, {"MYCASA_TENANT_ID": "custom-tenant"})
    def test_custom_tenant_id(self):
        """Test loading custom tenant ID."""
        from core.config import Config

        config = Config()
        assert config.TENANT_ID == "custom-tenant"

    @patch.dict(os.environ, {"MYCASA_BACKEND_PORT": "9000"})
    def test_custom_backend_port(self):
        """Test loading custom backend port."""
        from core.config import Config

        config = Config()
        assert config.BACKEND_PORT == 9000

    @patch.dict(os.environ, {"MYCASA_MONTHLY_COST_CAP": "2000"})
    def test_custom_cost_cap(self):
        """Test loading custom cost cap."""
        from core.config import Config

        config = Config()
        assert config.MONTHLY_COST_CAP == 2000
