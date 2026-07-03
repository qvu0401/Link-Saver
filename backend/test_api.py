import sqlite3
import pytest
from fastapi.testclient import TestClient
 
 
@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_links.db"
 
    import database
    import main
 
    real_connect = sqlite3.connect
 
    def temp_connect(path, *args, **kwargs):
        if path == "links.db":
            path = str(db_file)
        return real_connect(path, *args, **kwargs)
 
    monkeypatch.setattr(sqlite3, "connect", temp_connect)
 
    database.init_db()
    return TestClient(main.app)
 
#Result: PASSED
def test_full_lifecycle(client):
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
    assert patched["tags"] == ["a"]  # partial update left tags alone
 
    # delete
    assert client.delete(f"/api/links/{link_id}").status_code == 204
 
    # check it's gone from list
    listed_after = client.get("/api/links").json()
    assert not any(link["id"] == link_id for link in listed_after)