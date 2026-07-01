import json
from datetime import datetime, timezone
from fastapi import FastAPI
from database import init_db, get_db
from models import LinkCreate

app = FastAPI()
init_db()

@app.post("/api/links", status_code=201)
def create_link(link: LinkCreate):
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO links (url, title, tags, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (link.url, link.url, json.dumps(link.tags), link.status.value, created_at)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {
        "id": new_id,
        "url": link.url,
        "title": link.url,
        "tags": link.tags,
        "status": link.status.value,
        "created_at": created_at,
    }

@app.get("/")
def read_root():
    return {"message": "Link Saver alive"}