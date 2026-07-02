import json
import sqlite3
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from database import init_db, get_db
from models import LinkCreate

app = FastAPI()
init_db()

@app.exception_handler(sqlite3.IntegrityError)
def sqlite_integrity_exception_handler(request: Request, exc: sqlite3.IntegrityError):
    error_msg = str(exc)

    if "UNIQUE constraint failed" in error_msg:
        return JSONResponse(
            status_code = 409,
            content={"detail": f"Duplicate value error: {error_msg.split(': ')[-1]} already exists"},
        )

    return JSONResponse(
        status_code=400,
        content={"detail:": f"Database constraint violation: {error_msg}"},
    )

@app.post("/links", status_code=201)
def create_link(link: LinkCreate):
    date = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO links (url, title, tags, status, date) VALUES (?, ?, ?, ?, ?)",
            (link.url, link.url, json.dumps(link.tags), link.status.value, date)
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
        "date": date,
    }

@app.get("/")
def read_root():
    return {"message": "Link Saver alive"}