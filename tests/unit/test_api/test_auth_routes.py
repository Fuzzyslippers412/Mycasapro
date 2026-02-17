"""
Unit tests for Auth API routes.
"""
import pytest


@pytest.mark.unit
@pytest.mark.api
def test_login_success(api_client, test_user_password):
    response = api_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": test_user_password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "testuser"


@pytest.mark.unit
@pytest.mark.api
def test_login_invalid_password(api_client):
    response = api_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.api
def test_login_with_email_case_insensitive(api_client, test_user_password):
    response = api_client.post(
        "/api/auth/login",
        json={"username": "TEST@EXAMPLE.COM", "password": test_user_password},
    )
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
def test_login_with_username_case_insensitive(api_client, test_user_password):
    response = api_client.post(
        "/api/auth/login",
        json={"username": "TestUser", "password": test_user_password},
    )
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
def test_refresh_token(api_client, test_user_password):
    login = api_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": test_user_password},
    )
    refresh_token = login.json()["refresh_token"]
    response = api_client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data


@pytest.mark.unit
@pytest.mark.api
def test_me_requires_auth(api_client):
    response = api_client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.api
def test_me_returns_user(authenticated_api_client):
    response = authenticated_api_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.unit
@pytest.mark.api
def test_register_success(api_client):
    response = api_client.post(
        "/api/auth/register",
        json={"username": "NewUser", "email": "NewUser@Example.com", "password": "test-password-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "NewUser"
    assert data["user"]["email"] == "newuser@example.com"


@pytest.mark.unit
@pytest.mark.api
def test_register_duplicate_case_insensitive(api_client):
    response = api_client.post(
        "/api/auth/register",
        json={"username": "TESTUSER", "email": "TEST@EXAMPLE.COM", "password": "test-password-123"},
    )
    assert response.status_code == 409


@pytest.mark.unit
@pytest.mark.api
def test_register_rejects_invalid_username(api_client):
    response = api_client.post(
        "/api/auth/register",
        json={"username": "12..bad", "email": "valid@example.com", "password": "test-password-123"},
    )
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.api
def test_register_rejects_invalid_email(api_client):
    response = api_client.post(
        "/api/auth/register",
        json={"username": "ValidUser", "email": "invalid-email", "password": "test-password-123"},
    )
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.api
def test_login_lockout_after_failures(api_client, test_user_password):
    for _ in range(5):
        response = api_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = api_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": test_user_password},
    )
    assert response.status_code == 429


@pytest.mark.unit
@pytest.mark.api
def test_forgot_password_returns_success(api_client):
    response = api_client.post(
        "/api/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 200
    assert response.json().get("success") is True


@pytest.mark.unit
@pytest.mark.api
def test_admin_users_requires_permission(api_client, db_session):
    from auth.security import get_password_hash
    from database.models import User

    user = User(
        username="regularuser",
        email="regular@example.com",
        hashed_password=get_password_hash("password-123"),
        is_active=True,
        is_admin=False,
        tenant_id="test-tenant",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    login = api_client.post("/api/auth/login", json={"username": "regularuser", "password": "password-123"})
    assert login.status_code == 200
    token = login.json()["token"]
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    response = api_client.get("/api/admin/users")
    assert response.status_code == 403
