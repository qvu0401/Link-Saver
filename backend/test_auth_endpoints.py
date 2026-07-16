import os
import sqlite3
import tempfile
import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db

@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    # Set up environment
    os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-minimum-"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    # Use a temporary database
    fd, db_path = tempfile.mkstemp()
    os.close(fd)

    # Monkey-patch get_db to use temp database
    original_get_db = get_db
    def mock_get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    import database
    import main
    import router_auth
    import dependencies
    database.get_db = mock_get_db
    main.get_db = mock_get_db
    router_auth.get_db = mock_get_db

    # Initialize database
    from database import init_db
    init_db()

    yield TestClient(app)

    # Cleanup
    database.get_db = original_get_db
    main.get_db = original_get_db
    router_auth.get_db = original_get_db
    os.unlink(db_path)

def test_register_first_user(client):
    """Test registering the first user."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"

def test_register_multiple_users(client):
    """Test that multiple users can register (multi-user support)."""
    # Register first user
    response1 = client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "SecurePassword123!"
        }
    )
    assert response1.status_code == 201

    # Register second user (should succeed now with multi-user support)
    response2 = client.post(
        "/api/auth/register",
        json={
            "email": "user2@example.com",
            "password": "SecurePassword456!"
        }
    )
    assert response2.status_code == 201
    assert response2.json()["email"] == "user2@example.com"

def test_register_weak_password(client):
    """Test that weak passwords are rejected."""
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "weak"
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "at least 12 characters" in data["detail"]

def test_register_duplicate_email(client):
    """Test that duplicate emails are rejected."""
    # Register first user
    client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "SecurePassword123!"
        }
    )

    # Try to register with same email
    response = client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "SecurePassword456!"
        }
    )

    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]

def test_login_success(client):
    """Test successful login."""
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

    # Check that cookie is set
    assert "access_token" in response.cookies

def test_login_case_insensitive_email(client):
    """Test that login is case-insensitive for email."""
    # Register with lowercase
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    # Login with uppercase
    response = client.post(
        "/api/auth/login",
        json={
            "email": "TEST@EXAMPLE.COM",
            "password": "SecurePassword123!"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.cookies

def test_login_wrong_password(client):
    """Test login with wrong password."""
    # Register user
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    # Try wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword"
        }
    )

    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]

def test_login_unknown_email(client):
    """Test login with unknown email returns generic error."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "SomePassword123!"
        }
    )

    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]

def test_logout(client):
    """Test logout clears the cookie."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    assert "access_token" in login_response.cookies

    # Logout
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200

def test_me_authenticated(client):
    """Test /me endpoint with valid token."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
    )

    # Get current user
    response = client.get("/api/auth/me", cookies=login_response.cookies)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_me_unauthenticated(client):
    """Test /me endpoint without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "Not authenticated" in data["detail"]
