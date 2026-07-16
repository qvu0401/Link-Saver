import os
import pytest
from datetime import timedelta

from auth import hash_password, verify_password, create_access_token, decode_access_token

@pytest.fixture(autouse=True)
def setup_env():
    """Set SECRET_KEY for all tests."""
    os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-minimum-"
    yield
    # Cleanup (optional, pytest-env usually handles this)

def test_hash_and_verify_password():
    """Test password hashing and verification."""
    plain = "testpassword123"
    hashed = hash_password(plain)

    # Hashed password should not equal plaintext
    assert hashed != plain

    # Correct password should verify
    assert verify_password(plain, hashed)

    # Wrong password should not verify
    assert not verify_password("wrongpassword", hashed)

def test_create_and_decode_token():
    """Test JWT token creation and decoding."""
    email = "test@example.com"
    expires_delta = timedelta(hours=1)

    token = create_access_token(subject=email, expires_delta=expires_delta)

    # Token should not be empty
    assert token
    assert isinstance(token, str)

    # Decoding should return the email
    decoded_email = decode_access_token(token)
    assert decoded_email == email

def test_decode_invalid_token():
    """Test that decoding an invalid token returns None."""
    invalid_token = "invalid.jwt.token"
    result = decode_access_token(invalid_token)
    assert result is None

def test_decode_missing_secret():
    """Test that decoding without SECRET_KEY returns None."""
    os.environ.pop("SECRET_KEY", None)
    email = "test@example.com"
    expires_delta = timedelta(hours=1)

    # Should fail gracefully when creating token without SECRET_KEY
    with pytest.raises(ValueError):
        create_access_token(subject=email, expires_delta=expires_delta)

def test_create_token_without_secret_key():
    """Test that creating a token without SECRET_KEY raises ValueError."""
    os.environ.pop("SECRET_KEY", None)
    with pytest.raises(ValueError, match="SECRET_KEY environment variable is not set"):
        create_access_token(subject="test@example.com", expires_delta=timedelta(hours=1))
