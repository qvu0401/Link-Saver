from fastapi import Request, HTTPException
from auth import decode_access_token

async def get_current_user(request: Request) -> str:
    """Extract and validate JWT from cookie, return email or raise 401."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return email
