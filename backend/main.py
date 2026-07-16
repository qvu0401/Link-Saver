import json
import sqlite3
import os

from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import init_db, get_db
from models import LinkCreate, LinkUpdate
from fetcher import fetch_title
from router_auth import router as auth_router
from dependencies import get_current_user

app = FastAPI()

# Create limiter for rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"detail": "Too many requests"}
))
init_db()

# Startup validation for SECRET_KEY
@app.on_event("startup")
def startup_event():
    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY environment variable is not set. Cannot start.")

# Mount auth router
app.include_router(auth_router)

origins = [
    "http://localhost",
    "http://localhost:80",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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

def get_user_id(email: str) -> int:
    """Get user ID from email."""
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user["id"]

@app.post("/api/links", status_code=201)
def create_link(link: LinkCreate, current_user: str = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    date = datetime.now(timezone.utc).isoformat()
    url = str(link.url)
    title = fetch_title(url)

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO links (user_id, url, title, tags, status, date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, url, title, json.dumps(link.tags), link.status.value, date)
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
def list_links(status: str | None = None, tag: str | None = None, current_user: str = Depends(get_current_user)):
    user_id = get_user_id(current_user)

    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM links WHERE user_id = ? AND status = ? ORDER BY date DESC",
                (user_id, status)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM links WHERE user_id = ? ORDER BY date DESC",
                (user_id,)
            ).fetchall()

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
def delete_link(link_id: int, current_user: str = Depends(get_current_user)):
    user_id = get_user_id(current_user)

    with get_db() as conn:
        # Verify link belongs to user before deleting
        link = conn.execute("SELECT user_id FROM links WHERE id = ?", (link_id,)).fetchone()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        if link["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this link")

        cursor = conn.execute("DELETE FROM links WHERE id = ? AND user_id = ?", (link_id, user_id))
        conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")

@app.patch("/api/links/{link_id}")
def update_link(link_id: int, update: LinkUpdate, current_user: str = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    fields = update.model_dump(exclude_unset=True)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "status" in fields:
        fields["status"] = fields["status"].value

    if "tags" in fields:
        fields["tags"] = json.dumps(fields["tags"])

    # Verify link belongs to user before updating
    with get_db() as conn:
        link = conn.execute("SELECT user_id FROM links WHERE id = ?", (link_id,)).fetchone()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        if link["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this link")

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [link_id, user_id]

    with get_db() as conn:
        cursor = conn.execute(f"UPDATE links SET {set_clause} WHERE id = ? AND user_id = ?", values)
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
