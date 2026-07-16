import sqlite3
import os
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, EmailStr

from database import get_db
from auth import hash_password, verify_password, create_access_token
from dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    email: str

@router.post("/register", status_code=201, response_model=UserResponse)
def register(user: UserCreate):
    """Register a new user account."""
    # Validate password length
    if len(user.password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")

    email = user.email.lower()
    password_hash = hash_password(user.password)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, password_hash, created_at)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already exists")

    return UserResponse(email=email)

@router.post("/login", response_model=UserResponse)
def login(request: Request, user: UserCreate, response: Response):
    """Authenticate user and issue JWT in HttpOnly cookie."""
    email = user.email.lower()

    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not row or not verify_password(user.password, row["password_hash"]):
        # Same message for both cases to prevent email enumeration
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create JWT token
    token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    expires_delta = timedelta(minutes=token_expire_minutes)
    token = create_access_token(subject=email, expires_delta=expires_delta)

    # Set HttpOnly, SameSite=Strict cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        path="/api",
        max_age=token_expire_minutes * 60,
    )

    return UserResponse(email=email)

@router.post("/logout", response_model=dict)
def logout(response: Response):
    """Clear the access_token cookie."""
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        samesite="strict",
        path="/api",
        max_age=0,
    )
    return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: str = Depends(get_current_user)):
    """Return the authenticated user's email."""
    return UserResponse(email=current_user)
