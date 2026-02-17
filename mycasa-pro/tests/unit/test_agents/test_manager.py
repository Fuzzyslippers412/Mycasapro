"""
Unit tests for the Manager Agent.

Tests cover:
- Agent initialization
- Basic agent functionality
- Database connectivity
"""

import pytest
from unittest.mock import Mock, MagicMock


@pytest.mark.unit
@pytest.mark.agent
class TestManagerAgentInitialization:
    """Test Manager Agent initialization."""

    def test_agent_initializes(self):
        """Test that agent initializes correctly."""
        from agents.manager import ManagerAgent

        agent = ManagerAgent()

        assert agent is not None
        assert hasattr(agent, "name")
        assert agent.name == "manager"

    def test_agent_has_required_attributes(self):
        """Test that agent has all required attributes."""
        from agents.manager import ManagerAgent

        agent = ManagerAgent()

        # Check agent has required attributes
        assert hasattr(agent, "name")
        assert hasattr(agent, "tenant_id")
        assert hasattr(agent, "logger")

    def test_agent_default_tenant_id(self):
        """Test that agent has a default tenant ID."""
        from agents.manager import ManagerAgent

        agent = ManagerAgent()
        assert agent.tenant_id is not None


@pytest.mark.unit
@pytest.mark.agent
class TestManagerAgentDatabaseAccess:
    """Test Manager Agent database operations."""

    def test_agent_can_query_database(self, db_session):
        """Test that agent can query the database."""
        from database.models import MaintenanceTask

        # Create a maintenance task
        task = MaintenanceTask(
            tenant_id="test-tenant",
            title="Test Task",
            description="Test Description",
            priority="medium",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()

        # Query tasks
        tasks = db_session.query(MaintenanceTask).filter_by(tenant_id="test-tenant").all()
        assert len(tasks) == 1
        assert tasks[0].title == "Test Task"

    def test_tenant_isolation(self, db_session):
        """Test that tenant isolation works in queries."""
        from database.models import MaintenanceTask

        # Create tasks for different tenants
        task1 = MaintenanceTask(
            tenant_id="tenant-1",
            title="Task 1",
            description="Description 1",
            priority="medium",
            status="pending",
        )
        task2 = MaintenanceTask(
            tenant_id="tenant-2",
            title="Task 2",
            description="Description 2",
            priority="medium",
            status="pending",
        )
        db_session.add_all([task1, task2])
        db_session.commit()

        # Query for tenant-1 only
        tenant1_tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="tenant-1"
        ).all()

        assert len(tenant1_tasks) == 1
        assert tenant1_tasks[0].title == "Task 1"


@pytest.mark.unit
@pytest.mark.agent
class TestManagerAgentComponents:
    """Test Manager Agent internal components."""

    def test_agent_has_team_router(self):
        """Test that manager has team router for agent coordination."""
        from agents.manager import ManagerAgent

        agent = ManagerAgent()
        assert hasattr(agent, "_team_router")

    def test_agent_tracks_sub_agents(self):
        """Test that manager tracks sub-agents."""
        from agents.manager import ManagerAgent

        agent = ManagerAgent()
        assert hasattr(agent, "_sub_agents")
        assert isinstance(agent._sub_agents, dict)

    def test_agent_has_agent_registry(self):
        """Test that manager has agent registry."""
        from agents.manager import ManagerAgent

        agent = ManagerAgent()
        assert hasattr(agent, "_AGENT_REGISTRY")


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseModels:
    """Test basic database model operations."""

    def test_create_maintenance_task(self, db_session):
        """Test creating a maintenance task."""
        from database.models import MaintenanceTask

        task = MaintenanceTask(
            tenant_id="test-tenant",
            title="HVAC Maintenance",
            description="Replace filters",
            priority="high",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()

        saved_task = db_session.query(MaintenanceTask).filter_by(
            title="HVAC Maintenance"
        ).first()

        assert saved_task is not None
        assert saved_task.priority == "high"
        assert saved_task.status == "pending"

    def test_create_transaction(self, db_session, sample_transaction):
        """Test that transaction fixture works."""
        from database.models import Transaction

        transactions = db_session.query(Transaction).filter_by(
            tenant_id="test-tenant"
        ).all()

        assert len(transactions) == 1
        assert sample_transaction.category == "Utilities"

    def test_create_contractor(self, db_session, sample_contractor):
        """Test that contractor fixture works."""
        from database.models import Contractor

        contractors = db_session.query(Contractor).filter_by(
            tenant_id="test-tenant"
        ).all()

        assert len(contractors) == 1
        assert sample_contractor.specialty == "HVAC"

    def test_query_by_status(self, db_session):
        """Test querying tasks by status."""
        from database.models import MaintenanceTask

        # Create tasks with different statuses
        for status in ["pending", "in_progress", "completed"]:
            task = MaintenanceTask(
                tenant_id="test-tenant",
                title=f"Task {status}",
                description="Description",
                priority="medium",
                status=status,
            )
            db_session.add(task)
        db_session.commit()

        # Query pending tasks
        pending = db_session.query(MaintenanceTask).filter_by(
            tenant_id="test-tenant",
            status="pending"
        ).all()

        assert len(pending) == 1
        assert pending[0].status == "pending"

    def test_query_by_priority(self, db_session):
        """Test querying tasks by priority."""
        from database.models import MaintenanceTask

        # Create tasks with different priorities
        for priority in ["low", "medium", "high"]:
            task = MaintenanceTask(
                tenant_id="test-tenant",
                title=f"Task {priority}",
                description="Description",
                priority=priority,
                status="pending",
            )
            db_session.add(task)
        db_session.commit()

        # Query high priority tasks
        high_priority = db_session.query(MaintenanceTask).filter_by(
            tenant_id="test-tenant",
            priority="high"
        ).all()

        assert len(high_priority) == 1
        assert high_priority[0].priority == "high"


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseConstraints:
    """Test database constraints and data integrity."""

    def test_multiple_tenants_isolated(self, db_session):
        """Test that data from different tenants is isolated."""
        from database.models import Contractor

        # Create contractors for different tenants
        for i in range(3):
            contractor = Contractor(
                tenant_id=f"tenant-{i}",
                name=f"Contractor {i}",
                specialty="General",
                phone=f"555-{1000+i:04d}",
                email=f"contractor{i}@example.com",
                rating=4.0,
            )
            db_session.add(contractor)
        db_session.commit()

        # Each tenant should only see their own data
        for i in range(3):
            tenant_contractors = db_session.query(Contractor).filter_by(
                tenant_id=f"tenant-{i}"
            ).all()
            assert len(tenant_contractors) == 1
            assert tenant_contractors[0].name == f"Contractor {i}"

    def test_bulk_insert_performance(self, db_session):
        """Test bulk inserting records efficiently."""
        from database.models import Transaction

        # Create 100 transactions
        transactions = [
            Transaction(
                tenant_id="test-tenant",
                date=f"2024-01-{(i % 28) + 1:02d}",
                description=f"Transaction {i}",
                amount=-100.0 - i,
                category="Utilities",
                account="Checking",
            )
            for i in range(100)
        ]

        db_session.add_all(transactions)
        db_session.commit()

        # Verify count
        count = db_session.query(Transaction).filter_by(
            tenant_id="test-tenant"
        ).count()
        assert count == 100
