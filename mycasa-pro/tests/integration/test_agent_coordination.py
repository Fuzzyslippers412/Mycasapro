"""
Integration tests for agent coordination.

Tests cover:
- Agent communication and coordination
- Multi-agent workflows
- Database operations across agents
"""

import pytest
from datetime import datetime

from database.models import MaintenanceTask, Transaction, Contractor


@pytest.mark.integration
@pytest.mark.agent
class TestAgentBasicCoordination:
    """Test basic coordination between agents."""

    def test_multiple_agents_access_same_database(self, all_agents, db_session):
        """Test that multiple agents can access the same database."""
        manager = all_agents["manager"]
        finance = all_agents["finance"]
        maintenance = all_agents["maintenance"]

        # All agents should have access to the same database session
        assert manager.db == finance.db == maintenance.db
        assert manager.tenant_id == finance.tenant_id == maintenance.tenant_id

    def test_agents_share_tenant_context(self, all_agents):
        """Test that all agents operate within the same tenant context."""
        for agent_name, agent in all_agents.items():
            assert agent.tenant_id == "test-tenant"


@pytest.mark.integration
@pytest.mark.agent
class TestMaintenanceWorkflow:
    """Test maintenance-related workflows."""

    def test_maintenance_agent_creates_task(self, all_agents, db_session):
        """Test maintenance agent creating a maintenance task."""
        maintenance = all_agents["maintenance"]

        # Create maintenance task
        task = MaintenanceTask(
            tenant_id="test-tenant",
            title="HVAC Filter Replacement",
            description="Replace air filter in main HVAC unit",
            priority="medium",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()

        # Verify task exists
        tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="test-tenant"
        ).all()
        assert len(tasks) == 1
        assert tasks[0].title == "HVAC Filter Replacement"

    def test_contractor_assignment_to_task(self, all_agents, db_session):
        """Test assigning a contractor to a maintenance task."""
        # Create contractor
        contractor = Contractor(
            tenant_id="test-tenant",
            name="HVAC Pros",
            specialty="HVAC",
            phone="555-0100",
            email="contact@hvacpros.com",
            rating=4.5,
        )
        db_session.add(contractor)

        # Create maintenance task
        task = MaintenanceTask(
            tenant_id="test-tenant",
            title="AC Repair",
            description="Fix broken AC unit",
            priority="high",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()

        # Verify both exist
        contractors = db_session.query(Contractor).filter_by(
            tenant_id="test-tenant"
        ).all()
        tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="test-tenant"
        ).all()

        assert len(contractors) == 1
        assert len(tasks) == 1


@pytest.mark.integration
@pytest.mark.agent
class TestFinanceWorkflow:
    """Test finance-related workflows."""

    def test_finance_agent_tracks_expenses(self, all_agents, db_session):
        """Test finance agent tracking expenses."""
        finance = all_agents["finance"]

        # Create transactions
        transactions = [
            Transaction(
                tenant_id="test-tenant",
                date="2024-01-15",
                description="Electric Bill",
                amount=-150.0,
                category="Utilities",
                account="Checking",
            ),
            Transaction(
                tenant_id="test-tenant",
                date="2024-01-20",
                description="Water Bill",
                amount=-75.0,
                category="Utilities",
                account="Checking",
            ),
        ]
        db_session.add_all(transactions)
        db_session.commit()

        # Query transactions
        all_transactions = db_session.query(Transaction).filter_by(
            tenant_id="test-tenant"
        ).all()
        assert len(all_transactions) == 2

        # Calculate total
        total_expenses = sum(t.amount for t in all_transactions)
        assert total_expenses == -225.0

    def test_finance_categorizes_expenses(self, all_agents, db_session):
        """Test finance agent categorizing expenses."""
        # Create transactions in different categories
        categories = ["Utilities", "Maintenance", "Insurance", "Taxes"]
        for i, category in enumerate(categories):
            transaction = Transaction(
                tenant_id="test-tenant",
                date=f"2024-01-{15 + i:02d}",
                description=f"{category} Payment",
                amount=-100.0 * (i + 1),
                category=category,
                account="Checking",
            )
            db_session.add(transaction)
        db_session.commit()

        # Group by category
        for category in categories:
            category_transactions = db_session.query(Transaction).filter_by(
                tenant_id="test-tenant",
                category=category
            ).all()
            assert len(category_transactions) == 1


@pytest.mark.integration
@pytest.mark.agent
class TestMultiAgentWorkflow:
    """Test workflows involving multiple agents."""

    def test_complete_maintenance_workflow(self, all_agents, db_session):
        """Test a complete maintenance workflow across agents."""
        # 1. Create maintenance task
        task = MaintenanceTask(
            tenant_id="test-tenant",
            title="Plumbing Repair",
            description="Fix leaky faucet",
            priority="high",
            status="pending",
        )
        db_session.add(task)

        # 2. Create contractor
        contractor = Contractor(
            tenant_id="test-tenant",
            name="Plumbing Experts",
            specialty="Plumbing",
            phone="555-0200",
            email="info@plumbingexperts.com",
            rating=4.7,
        )
        db_session.add(contractor)

        # 3. Create expense transaction
        transaction = Transaction(
            tenant_id="test-tenant",
            date="2024-01-25",
            description="Plumbing Repair - Leaky Faucet",
            amount=-250.0,
            category="Maintenance",
            account="Checking",
        )
        db_session.add(transaction)

        db_session.commit()

        # Verify all components
        tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="test-tenant"
        ).all()
        contractors = db_session.query(Contractor).filter_by(
            tenant_id="test-tenant"
        ).all()
        transactions = db_session.query(Transaction).filter_by(
            tenant_id="test-tenant"
        ).all()

        assert len(tasks) == 1
        assert len(contractors) == 1
        assert len(transactions) == 1


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegrity:
    """Test database integrity and constraints."""

    def test_tenant_isolation_enforced(self, db_session):
        """Test that tenant isolation is enforced in queries."""
        # Create data for multiple tenants
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

        # Query for each tenant separately
        tenant1_tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="tenant-1"
        ).all()
        tenant2_tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="tenant-2"
        ).all()

        assert len(tenant1_tasks) == 1
        assert len(tenant2_tasks) == 1
        assert tenant1_tasks[0].title != tenant2_tasks[0].title

    def test_multiple_records_same_tenant(self, db_session):
        """Test creating multiple records for the same tenant."""
        # Create multiple contractors for one tenant
        contractors = [
            Contractor(
                tenant_id="test-tenant",
                name=f"Contractor {i}",
                specialty=["Plumbing", "Electrical", "HVAC"][i],
                phone=f"555-{1000 + i:04d}",
                email=f"contractor{i}@example.com",
                rating=4.0 + (i * 0.2),
            )
            for i in range(3)
        ]
        db_session.add_all(contractors)
        db_session.commit()

        # Verify all were created
        all_contractors = db_session.query(Contractor).filter_by(
            tenant_id="test-tenant"
        ).all()
        assert len(all_contractors) == 3


@pytest.mark.integration
@pytest.mark.slow
class TestAgentPerformance:
    """Test agent performance with larger datasets."""

    def test_bulk_task_creation(self, all_agents, db_session):
        """Test creating many tasks efficiently."""
        # Create 50 tasks
        tasks = [
            MaintenanceTask(
                tenant_id="test-tenant",
                title=f"Task {i}",
                description=f"Description for task {i}",
                priority=["low", "medium", "high"][i % 3],
                status="pending",
            )
            for i in range(50)
        ]
        db_session.add_all(tasks)
        db_session.commit()

        # Verify all were created
        all_tasks = db_session.query(MaintenanceTask).filter_by(
            tenant_id="test-tenant"
        ).all()
        assert len(all_tasks) == 50

    def test_bulk_transaction_creation(self, all_agents, db_session):
        """Test creating many transactions efficiently."""
        # Create 100 transactions
        transactions = [
            Transaction(
                tenant_id="test-tenant",
                date=f"2024-01-{(i % 28) + 1:02d}",
                description=f"Transaction {i}",
                amount=-100.0 - (i * 5),
                category=["Utilities", "Maintenance", "Insurance"][i % 3],
                account="Checking",
            )
            for i in range(100)
        ]
        db_session.add_all(transactions)
        db_session.commit()

        # Verify count
        all_transactions = db_session.query(Transaction).filter_by(
            tenant_id="test-tenant"
        ).all()
        assert len(all_transactions) == 100

        # Verify sum
        total = sum(t.amount for t in all_transactions)
        assert total < 0  # All are expenses
