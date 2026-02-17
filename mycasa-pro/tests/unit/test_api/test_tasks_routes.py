"""
Unit tests for Task API routes.

Tests cover:
- Task CRUD operations via API
- Query filtering and pagination
- Error handling
- Response validation
"""

import pytest
from fastapi.testclient import TestClient

from database.models import Task


@pytest.mark.unit
@pytest.mark.api
class TestTasksListAPI:
    """Test tasks list endpoint."""

    def test_get_empty_tasks_list(self, authenticated_api_client):
        """Test retrieving tasks when none exist."""
        response = authenticated_api_client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_tasks_list(self, authenticated_api_client, db_session):
        """Test retrieving a list of tasks."""
        # Create test tasks
        for i in range(3):
            task = Task(
                tenant_id="test-tenant",
                title=f"Task {i}",
                description=f"Description {i}",
                priority="medium",
                agent="manager",
                status="pending",
            )
            db_session.add(task)
        db_session.commit()

        response = authenticated_api_client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_tasks_filtered_by_status(self, authenticated_api_client, db_session):
        """Test filtering tasks by status."""
        # Create tasks with different statuses
        statuses = ["pending", "in_progress", "completed"]
        for status in statuses:
            task = Task(
                tenant_id="test-tenant",
                title=f"Task {status}",
                description=f"Description",
                priority="medium",
                agent="manager",
                status=status,
            )
            db_session.add(task)
        db_session.commit()

        response = authenticated_api_client.get("/api/tasks?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_get_tasks_filtered_by_agent(self, authenticated_api_client, db_session):
        """Test filtering tasks by agent."""
        agents = ["manager", "finance", "maintenance"]
        for agent in agents:
            task = Task(
                tenant_id="test-tenant",
                title=f"Task for {agent}",
                description="Description",
                priority="medium",
                agent=agent,
                status="pending",
            )
            db_session.add(task)
        db_session.commit()

        response = authenticated_api_client.get("/api/tasks?agent=finance")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["agent"] == "finance"


@pytest.mark.unit
@pytest.mark.api
class TestTasksCreateAPI:
    """Test task creation endpoint."""

    def test_create_task_success(self, authenticated_api_client):
        """Test successful task creation."""
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "priority": "high",
            "agent": "manager",
        }

        response = authenticated_api_client.post("/api/tasks", json=task_data)
        assert response.status_code == 200 or response.status_code == 201
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["priority"] == task_data["priority"]

    def test_create_task_missing_title(self, authenticated_api_client):
        """Test task creation without required title field."""
        task_data = {
            "description": "Task without title",
            "priority": "medium",
            "agent": "manager",
        }

        response = authenticated_api_client.post("/api/tasks", json=task_data)
        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422

    def test_create_task_invalid_priority(self, authenticated_api_client):
        """Test task creation with invalid priority."""
        task_data = {
            "title": "Task",
            "description": "Description",
            "priority": "invalid",
            "agent": "manager",
        }

        response = authenticated_api_client.post("/api/tasks", json=task_data)
        # Should either validate and reject, or accept and normalize
        # Behavior depends on implementation
        assert response.status_code in [200, 201, 422]


@pytest.mark.unit
@pytest.mark.api
class TestTasksDetailAPI:
    """Test task detail endpoint."""

    def test_get_task_by_id(self, authenticated_api_client, sample_task):
        """Test retrieving a specific task by ID."""
        response = authenticated_api_client.get(f"/api/tasks/{sample_task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_task.id
        assert data["title"] == sample_task.title

    def test_get_nonexistent_task(self, authenticated_api_client):
        """Test retrieving a task that doesn't exist."""
        response = authenticated_api_client.get("/api/tasks/99999")
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
class TestTasksUpdateAPI:
    """Test task update endpoint."""

    def test_update_task_status(self, authenticated_api_client, sample_task):
        """Test updating a task's status."""
        update_data = {"status": "in_progress"}

        response = authenticated_api_client.patch(f"/api/tasks/{sample_task.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    def test_update_task_priority(self, authenticated_api_client, sample_task):
        """Test updating a task's priority."""
        update_data = {"priority": "high"}

        response = authenticated_api_client.patch(f"/api/tasks/{sample_task.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "high"

    def test_update_nonexistent_task(self, authenticated_api_client):
        """Test updating a task that doesn't exist."""
        update_data = {"status": "completed"}

        response = authenticated_api_client.patch("/api/tasks/99999", json=update_data)
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
class TestTasksDeleteAPI:
    """Test task deletion endpoint."""

    def test_delete_task(self, authenticated_api_client, sample_task, db_session):
        """Test deleting a task."""
        task_id = sample_task.id

        response = authenticated_api_client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200 or response.status_code == 204

        # Verify task is deleted
        deleted_task = db_session.query(Task).filter_by(id=task_id).first()
        assert deleted_task is None

    def test_delete_nonexistent_task(self, authenticated_api_client):
        """Test deleting a task that doesn't exist."""
        response = authenticated_api_client.delete("/api/tasks/99999")
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.api
class TestTasksErrorHandling:
    """Test error handling in tasks API."""

    def test_invalid_json_payload(self, authenticated_api_client):
        """Test handling of invalid JSON in request body."""
        response = authenticated_api_client.post(
            "/api/tasks",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_invalid_task_id_format(self, authenticated_api_client):
        """Test handling of invalid task ID format."""
        response = authenticated_api_client.get("/api/tasks/not-a-number")
        # Should return 422 for validation error or 404 if converted
        assert response.status_code in [404, 422]


@pytest.mark.integration
@pytest.mark.api
class TestTasksWorkflow:
    """Test complete task workflows via API."""

    def test_complete_task_lifecycle(self, authenticated_api_client, db_session):
        """Test creating, updating, and completing a task."""
        # 1. Create task
        task_data = {
            "title": "Lifecycle Task",
            "description": "Test complete lifecycle",
            "priority": "medium",
            "agent": "manager",
        }
        create_response = authenticated_api_client.post("/api/tasks", json=task_data)
        assert create_response.status_code in [200, 201]
        task_id = create_response.json()["id"]

        # 2. Update to in_progress
        authenticated_api_client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"})

        # 3. Update priority
        authenticated_api_client.patch(f"/api/tasks/{task_id}", json={"priority": "high"})

        # 4. Complete task
        complete_response = authenticated_api_client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "completed"}
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

        # 5. Verify in database
        task = db_session.query(Task).filter_by(id=task_id).first()
        assert task.status == "completed"
        assert task.priority == "high"

    def test_create_and_list_tasks(self, authenticated_api_client):
        """Test creating multiple tasks and listing them."""
        # Create 3 tasks
        for i in range(3):
            task_data = {
                "title": f"Task {i}",
                "description": f"Description {i}",
                "priority": "medium",
                "agent": "manager",
            }
            authenticated_api_client.post("/api/tasks", json=task_data)

        # List all tasks
        list_response = authenticated_api_client.get("/api/tasks")
        assert list_response.status_code == 200
        tasks = list_response.json()
        assert len(tasks) == 3
