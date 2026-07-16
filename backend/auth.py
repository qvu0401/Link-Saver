from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    """Hash a plain text password using bcrypt."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain text password against a bcrypt hash using constant-time comparison."""
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str, expires_delta: timedelta) -> str:
    """Create a JWT access token with HS256 algorithm."""
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("SECRET_KEY environment variable is not set")

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt

def decode_access_token(token: str) -> str | None:
    """Decode a JWT access token and return the subject (email) or None if invalid."""
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        return None

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None
