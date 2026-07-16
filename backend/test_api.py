import sqlite3
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Set required environment variables
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-bytes-minimum-")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    db_file = tmp_path / "test_links.db"

    import database
    import main

    real_connect = sqlite3.connect

    def temp_connect(path, *args, **kwargs):
        if path == "data/links.db":
            path = str(db_file)
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", temp_connect)

    database.init_db()

    test_client = TestClient(main.app)

    # Register and login first user
    test_client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123!"
        }
    )

    login_response = test_client.post(
        "/api/auth/login",
        json={
            "email": "user1@example.com",
            "password": "TestPassword123!"
        }
    )

    # Store cookies for authenticated requests
    test_client.cookies.update(login_response.cookies)

    return test_client

@pytest.fixture
def multi_user_setup(tmp_path, monkeypatch):
    """Setup with two users logged in separately."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-bytes-minimum-")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    db_file = tmp_path / "test_links.db"

    import database
    import main

    real_connect = sqlite3.connect

    def temp_connect(path, *args, **kwargs):
        if path == "data/links.db":
            path = str(db_file)
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", temp_connect)
    database.init_db()

    # Create two users
    test_client = TestClient(main.app)

    # User 1 registration and login
    test_client.post(
        "/api/auth/register",
        json={"email": "user1@example.com", "password": "TestPassword123!"}
    )
    user1_login = test_client.post(
        "/api/auth/login",
        json={"email": "user1@example.com", "password": "TestPassword123!"}
    )
    user1_cookies = user1_login.cookies

    # User 2 registration and login
    test_client.post(
        "/api/auth/register",
        json={"email": "user2@example.com", "password": "TestPassword456!"}
    )
    user2_login = test_client.post(
        "/api/auth/login",
        json={"email": "user2@example.com", "password": "TestPassword456!"}
    )
    user2_cookies = user2_login.cookies

    return test_client, user1_cookies, user2_cookies

# Result: PASSED
def test_full_lifecycle(client):
    """Test full lifecycle: create, list, update, delete link."""
    # create
    created = client.post(
        "/api/links",
        json={"url": "https://www.python.org", "tags": ["a"], "status": "unread"},
    ).json()
    link_id = created["id"]

    # check that list contains it
    listed = client.get("/api/links").json()
    assert any(link["id"] == link_id for link in listed)

    # patch status
    patched = client.patch(f"/api/links/{link_id}", json={"status": "read"}).json()
    assert patched["status"] == "read"
    assert patched["tags"] == ["a"]

    # delete
    assert client.delete(f"/api/links/{link_id}").status_code == 204

    # check it's gone from list
    listed_after = client.get("/api/links").json()
    assert not any(link["id"] == link_id for link in listed_after)

def test_unauthenticated_access(tmp_path, monkeypatch):
    """Test that unauthenticated requests to protected endpoints return 401."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-bytes-minimum-")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    db_file = tmp_path / "test_links.db"

    import database
    import main

    real_connect = sqlite3.connect

    def temp_connect(path, *args, **kwargs):
        if path == "data/links.db":
            path = str(db_file)
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", temp_connect)
    database.init_db()

    test_client = TestClient(main.app)

    # Try to access protected endpoint without authentication
    response = test_client.get("/api/links")
    assert response.status_code == 401

def test_multi_user_data_isolation(multi_user_setup):
    """Test that users can only see their own links."""
    test_client, user1_cookies, user2_cookies = multi_user_setup

    # User 1 creates a link
    user1_client = TestClient(test_client.app)
    user1_client.cookies.update(user1_cookies)
    created1 = user1_client.post(
        "/api/links",
        json={"url": "https://example.com", "tags": ["user1"], "status": "unread"}
    ).json()
    link1_id = created1["id"]

    # User 2 creates a different link
    user2_client = TestClient(test_client.app)
    user2_client.cookies.update(user2_cookies)
    created2 = user2_client.post(
        "/api/links",
        json={"url": "https://example.org", "tags": ["user2"], "status": "unread"}
    ).json()
    link2_id = created2["id"]

    # User 1 should only see their own link
    user1_links = user1_client.get("/api/links").json()
    assert len(user1_links) == 1
    assert user1_links[0]["id"] == link1_id
    assert "example.com" in user1_links[0]["url"]

    # User 2 should only see their own link
    user2_links = user2_client.get("/api/links").json()
    assert len(user2_links) == 1
    assert user2_links[0]["id"] == link2_id
    assert "example.org" in user2_links[0]["url"]

def test_user_cannot_modify_other_users_links(multi_user_setup):
    """Test that users cannot update or delete other users' links."""
    test_client, user1_cookies, user2_cookies = multi_user_setup

    # User 1 creates a link
    user1_client = TestClient(test_client.app)
    user1_client.cookies.update(user1_cookies)
    created = user1_client.post(
        "/api/links",
        json={"url": "https://example.com", "tags": ["secure"], "status": "unread"}
    ).json()
    link_id = created["id"]

    # User 2 tries to update User 1's link (should fail)
    user2_client = TestClient(test_client.app)
    user2_client.cookies.update(user2_cookies)
    response = user2_client.patch(
        f"/api/links/{link_id}",
        json={"status": "read"}
    )
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

    # User 2 tries to delete User 1's link (should fail)
    response = user2_client.delete(f"/api/links/{link_id}")
    assert response.status_code == 403

    # User 1 can still see and modify their link
    user1_links = user1_client.get("/api/links").json()
    assert user1_links[0]["status"] == "unread"

def test_duplicate_url_per_user_only(multi_user_setup):
    """Test that users can add the same URL but not twice in same account."""
    test_client, user1_cookies, user2_cookies = multi_user_setup

    url = "https://example.com"

    # User 1 adds URL
    user1_client = TestClient(test_client.app)
    user1_client.cookies.update(user1_cookies)
    response1 = user1_client.post(
        "/api/links",
        json={"url": url, "tags": ["test"], "status": "unread"}
    )
    assert response1.status_code == 201

    # User 1 tries to add same URL again (should fail)
    response1_dup = user1_client.post(
        "/api/links",
        json={"url": url, "tags": ["test"], "status": "unread"}
    )
    assert response1_dup.status_code == 409

    # User 2 can add the same URL (different user)
    user2_client = TestClient(test_client.app)
    user2_client.cookies.update(user2_cookies)
    response2 = user2_client.post(
        "/api/links",
        json={"url": url, "tags": ["test"], "status": "unread"}
    )
    assert response2.status_code == 201

    # Both users should have one link
    user1_links = user1_client.get("/api/links").json()
    user2_links = user2_client.get("/api/links").json()
    assert len(user1_links) == 1
    assert len(user2_links) == 1
