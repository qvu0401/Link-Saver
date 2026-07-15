import json
import sqlite3

from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_db
from models import LinkCreate, LinkUpdate
from fetcher import fetch_title

app = FastAPI()
init_db()

origins = [
    "http://localhost",
    "http://localhost:80",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(sqlite3.IntegrityError)
def sqlite_integrity_exception_handler(request: Request, exc: sqlite3.IntegrityError):
    error_msg = str(exc)

    if "UNIQUE constraint failed" in error_msg:
        return JSONResponse(
            status_code = 409,
            content={"detail": f"This URL already exists"},
        )

    return JSONResponse(
        status_code=400,
        content={"detail:": f"Database constraint violation: {error_msg}"},
    )

@app.post("/api/links", status_code=201)
def create_link(link: LinkCreate):
    date = datetime.now(timezone.utc).isoformat()
    url = str(link.url)
    title = fetch_title(url)

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO links (url, title, tags, status, date) VALUES (?, ?, ?, ?, ?)",
            (url, title, json.dumps(link.tags), link.status.value, date)
        )
        conn.commit()
        new_id = cursor.lastrowid

    return {
        "id": new_id,
        "url": url,
        "title": title,
        "tags": link.tags,
        "status": link.status.value,
        "date": date,
    }

@app.get("/api/links")
def list_links(status: str | None = None, tag: str | None = None):
    with get_db() as conn:

        if status:
            rows = conn.execute(
                "SELECT * FROM links where status = ? ORDER BY date DESC",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM links ORDER BY date DESC").fetchall()

    result = [
        {
            "id": row["id"],
            "url": row["url"],
            "title": row["title"],
            "tags": json.loads(row["tags"]),
            "status": row["status"],
            "date": row["date"],
        }
        for row in rows
    ]

    if tag:
        result = [link for link in result if tag in link["tags"]]

    return result

@app.delete("/api/links/{link_id}", status_code=204)
def delete_link(link_id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")

@app.patch("/api/links/{link_id}")
def update_link(link_id: int, update: LinkUpdate):
    fields = update.model_dump(exclude_unset=True)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "status" in fields: #get value from enum
        fields["status"] = fields["status"].value

    if "tags" in fields:
        fields["tags"] = json.dumps(fields["tags"])

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [link_id]

    with get_db() as conn:
        cursor = conn.execute(f"UPDATE links SET {set_clause} WHERE id = ?", values)

        conn.commit()
        row = conn.execute("SELECT * FROM links WHERE id = ?", (link_id,)).fetchone()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")

    return {
        "id": row["id"],
        "url": row["url"],
        "title": row["title"],
        "tags": json.loads(row["tags"]),
        "status": row["status"],
        "date": row["date"],
    }
