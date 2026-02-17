"""
Pytest configuration and shared fixtures for MyCasa Pro test suite.

This module provides:
- Database fixtures (in-memory SQLite for testing)
- Agent fixtures (mocked and real agents)
- API client fixtures (FastAPI TestClient)
- Connector fixtures (mocked external services)
- Sample data fixtures
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from database.models import Base


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, test interactions)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (slowest, test full workflows)"
    )


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    # Use in-memory SQLite with StaticPool for thread safety
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def db_session_factory(db_engine):
    """Factory for creating multiple database sessions."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    return SessionLocal


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def api_client(db_session) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with database override."""
    from api.main import app
    from database.connection import get_db

    # Override database dependency
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_api_client(api_client, test_user, test_user_password):
    """Create an authenticated API client with JWT token."""
    response = api_client.post(
        "/api/auth/login",
        json={"username": test_user.username, "password": test_user_password},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    return api_client


# ============================================================================
# SETTINGS FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def test_settings():
    """Create test settings with safe defaults."""
    # For now, return a simple dict-like object
    # TODO: Use proper MyCasaSettings after config system is updated
    class TestSettings:
        TENANT_ID = "test-tenant"
        DATABASE_URL = "sqlite:///:memory:"
        ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "test-key")
        ENABLE_SEMANTIC_SEARCH = False
        LOG_LEVEL = "ERROR"
        ENVIRONMENT = "testing"

    return TestSettings()


@pytest.fixture(scope="function")
def mock_settings(test_settings):
    """Mock settings for tests that need custom configuration."""
    return test_settings


# ============================================================================
# AGENT FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def mock_anthropic_client():
    """Mock Anthropic API client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Mock AI response")]
    mock_client.messages.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture(scope="function")
def mock_agent_manager(db_session, mock_anthropic_client):
    """Create a mocked agent manager."""
    from agents.manager import ManagerAgent

    manager = ManagerAgent(db_session, tenant_id="test-tenant")
    manager.client = mock_anthropic_client
    return manager


@pytest.fixture(scope="function")
def mock_finance_agent(db_session, mock_anthropic_client):
    """Create a mocked finance agent."""
    from agents.finance import FinanceAgent

    agent = FinanceAgent(db_session, tenant_id="test-tenant")
    agent.client = mock_anthropic_client
    return agent


@pytest.fixture(scope="function")
def mock_maintenance_agent(db_session, mock_anthropic_client):
    """Create a mocked maintenance agent."""
    from agents.maintenance import MaintenanceAgent

    agent = MaintenanceAgent(db_session, tenant_id="test-tenant")
    agent.client = mock_anthropic_client
    return agent


@pytest.fixture(scope="function")
def all_agents(db_session, mock_anthropic_client):
    """Create all agents for integration testing."""
    from agents.manager import ManagerAgent
    from agents.finance import FinanceAgent
    from agents.maintenance import MaintenanceAgent
    from agents.janitor import JanitorAgent
    from agents.security import SecurityAgent
    from agents.contractors import ContractorsAgent
    from agents.projects import ProjectsAgent

    return {
        "manager": ManagerAgent(db_session, tenant_id="test-tenant"),
        "finance": FinanceAgent(db_session, tenant_id="test-tenant"),
        "maintenance": MaintenanceAgent(db_session, tenant_id="test-tenant"),
        "janitor": JanitorAgent(db_session, tenant_id="test-tenant"),
        "security": SecurityAgent(db_session, tenant_id="test-tenant"),
        "contractors": ContractorsAgent(db_session, tenant_id="test-tenant"),
        "projects": ProjectsAgent(db_session, tenant_id="test-tenant"),
    }


# ============================================================================
# CONNECTOR FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def mock_whatsapp_connector():
    """Mock WhatsApp connector."""
    mock = MagicMock()
    mock.send_message = AsyncMock(return_value={"success": True})
    mock.get_messages = AsyncMock(return_value=[])
    mock.is_connected = MagicMock(return_value=True)
    return mock


@pytest.fixture(scope="function")
def mock_gmail_connector():
    """Mock Gmail connector."""
    mock = MagicMock()
    mock.send_email = AsyncMock(return_value={"success": True})
    mock.get_emails = AsyncMock(return_value=[])
    mock.is_authenticated = MagicMock(return_value=True)
    return mock


@pytest.fixture(scope="function")
def mock_calendar_connector():
    """Mock Calendar connector."""
    mock = MagicMock()
    mock.create_event = AsyncMock(return_value={"id": "test-event-id"})
    mock.get_events = AsyncMock(return_value=[])
    mock.is_authenticated = MagicMock(return_value=True)
    return mock


@pytest.fixture(scope="function")
def mock_bank_connector():
    """Mock Bank connector."""
    mock = MagicMock()
    mock.parse_csv = MagicMock(return_value=[])
    mock.parse_ofx = MagicMock(return_value=[])
    mock.categorize_transaction = MagicMock(return_value="Uncategorized")
    return mock


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def sample_contractor(db_session):
    """Create a sample contractor for testing."""
    from database.models import Contractor

    contractor = Contractor(
        tenant_id="test-tenant",
        name="Test Contractor LLC",
        specialty="HVAC",
        phone="555-0100",
        email="test@contractor.com",
        rating=4.5,
    )
    db_session.add(contractor)
    db_session.commit()
    db_session.refresh(contractor)
    return contractor


@pytest.fixture(scope="function")
def sample_maintenance_task(db_session):
    """Create a sample maintenance task for testing."""
    from database.models import MaintenanceTask

    task = MaintenanceTask(
        tenant_id="test-tenant",
        title="Test Maintenance Task",
        description="This is a test maintenance task",
        priority="medium",
        status="pending",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture(scope="function")
def sample_transaction(db_session):
    """Create a sample financial transaction for testing."""
    from database.models import Transaction

    transaction = Transaction(
        tenant_id="test-tenant",
        date="2024-01-15",
        description="Test Transaction",
        amount=-100.0,
        category="Utilities",
        account="Checking",
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction


@pytest.fixture(scope="function")
def sample_maintenance_item(db_session, sample_property):
    """Create a sample maintenance item for testing."""
    from database.models import MaintenanceItem

    item = MaintenanceItem(
        tenant_id="test-tenant",
        property_id=sample_property.id,
        title="Replace HVAC Filter",
        description="Monthly filter replacement",
        priority="medium",
        status="pending",
        frequency="monthly",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture(scope="function")
def sample_contractor(db_session):
    """Create a sample contractor for testing."""
    from database.models import Contractor

    contractor = Contractor(
        tenant_id="test-tenant",
        name="Test Contractor LLC",
        specialty="HVAC",
        phone="555-0100",
        email="test@contractor.com",
        rating=4.5,
        is_verified=True,
    )
    db_session.add(contractor)
    db_session.commit()
    db_session.refresh(contractor)
    return contractor


@pytest.fixture(scope="function")
def sample_secondbrain_note(db_session):
    """Create a sample SecondBrain note for testing."""
    from database.models import SecondBrainNote

    note = SecondBrainNote(
        tenant_id="test-tenant",
        title="Test Note",
        content="This is test content for the note.",
        tags=["test", "sample"],
        note_type="text",
        metadata={"source": "test"},
    )
    db_session.add(note)
    db_session.commit()
    db_session.refresh(note)
    return note


@pytest.fixture(scope="function")
def test_user_password():
    """Password for the test user."""
    return "test-password-123"


@pytest.fixture(scope="function")
def test_user(db_session, test_user_password):
    """Create a test user for authentication testing."""
    from auth.security import get_password_hash
    from database.models import User

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash(test_user_password),
        is_active=True,
        is_admin=True,
        tenant_id="test-tenant",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# FILE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def temp_csv_file(tmp_path):
    """Create a temporary CSV file for bank import testing."""
    csv_content = """Date,Description,Amount,Balance
2024-01-15,Grocery Store,-45.67,1000.00
2024-01-16,Salary Deposit,2000.00,3000.00
2024-01-17,Electric Bill,-120.00,2880.00
"""
    csv_file = tmp_path / "transactions.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture(scope="function")
def temp_ofx_file(tmp_path):
    """Create a temporary OFX file for bank import testing."""
    ofx_content = """<?xml version="1.0" encoding="UTF-8"?>
<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKTRANLIST>
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20240115</DTPOSTED>
            <TRNAMT>-45.67</TRNAMT>
            <NAME>Grocery Store</NAME>
          </STMTTRN>
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
"""
    ofx_file = tmp_path / "transactions.ofx"
    ofx_file.write_text(ofx_content)
    return ofx_file


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_environment():
    """Cleanup environment after each test."""
    yield
    # Reset any environment variables or global state if needed
    pass


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # TODO: Add singleton reset logic if needed
    # For example, clearing any cached agent instances
    yield
    pass
