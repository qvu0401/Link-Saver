# Authentication Implementation Guide

## Overview

This guide documents the complete implementation of email/password authentication for Link Saver, including JWT tokens, secure password hashing, and protected API endpoints.

## What Was Implemented

### 1. Database Schema (backend/database.py)

Added a new `users` table with:
- `id`: Primary key (auto-increment)
- `email`: Unique, normalized to lowercase
- `password_hash`: Bcrypt hash (never stores plaintext)
- `created_at`: ISO 8601 UTC timestamp

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

### 2. Security Module (backend/auth.py)

Pure utility functions for authentication:
- `hash_password(plain: str) -> str`: Bcrypt hash using passlib
- `verify_password(plain: str, hashed: str) -> bool`: Constant-time comparison
- `create_access_token(subject: str, expires_delta: timedelta) -> str`: HS256 JWT
- `decode_access_token(token: str) -> str | None`: Validates and decodes JWT

### 3. FastAPI Dependency (backend/dependencies.py)

`get_current_user(request: Request) -> str`
- Extracts JWT from `access_token` HttpOnly cookie
- Returns user email on success
- Raises `HTTPException(401)` if missing or invalid
- Used with `Depends()` on protected endpoints

### 4. Authentication Router (backend/router_auth.py)

Four endpoints under `/api/auth/`:

#### POST `/api/auth/register` (201)
- **When**: Only allowed if no users exist (first-user bootstrap)
- **Body**: `{ "email": "...", "password": "..." }`
- **Validation**: Email format, password ≥ 12 chars
- **Response**: `{ "email": "..." }`
- **Errors**:
  - `400`: Validation failed (weak password, invalid email)
  - `403`: Registration closed (user already exists)
  - `409`: Email already exists

#### POST `/api/auth/login` (200)
- **Rate limit**: 5 requests/minute per IP (via slowapi)
- **Body**: `{ "email": "...", "password": "..." }`
- **Action**: Lookup user → verify password (constant-time) → issue JWT
- **Response**: `{ "email": "..." }` + HttpOnly cookie
- **Cookie**: `Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=Strict; Path=/api; Max-Age=3600`
- **Errors**:
  - `401`: Invalid credentials (same message for unknown email or wrong password — prevents email enumeration)

#### POST `/api/auth/logout` (200)
- **Auth**: Not required (safe to call when unauthenticated)
- **Action**: Clears cookie with `Max-Age=0`
- **Response**: `{ "message": "Logged out" }`

#### GET `/api/auth/me` (200)
- **Auth**: Required (uses `Depends(get_current_user)`)
- **Response**: `{ "email": "..." }`
- **Errors**: `401` if unauthenticated

### 5. Protected Link Endpoints

All link endpoints now require authentication:
- `POST /api/links` - Create link
- `GET /api/links` - List links
- `PATCH /api/links/{link_id}` - Update link
- `DELETE /api/links/{link_id}` - Delete link

Returns `401 Unauthorized` if request lacks valid token.

### 6. Frontend Authentication UI (frontend/index.html)

Complete redesign with:

#### Login Form
- Email and password inputs
- Toggle to register new account (first user only)
- Error messages displayed to user
- Form validation (required fields)

#### Session Management
- `checkAuth()`: Verifies current session on page load
- Shows login form if unauthenticated
- Shows app if authenticated with user email in header
- Logout button clears session and redirects to login

#### API Integration
- All fetch requests include `credentials: 'include'` for automatic cookie handling
- Automatic redirect to login on 401 responses
- Generic error messages to users (no info leakage)

#### Styling
- Embedded CSS in HTML for login form
- Gradient background, centered card layout
- Error message styling with red background
- Responsive design (max-width: 400px)

### 7. Nginx Security (frontend/nginx.conf)

Added headers:
- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME-type sniffing
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referer leakage
- `X-XSS-Protection: 1; mode=block` - Legacy XSS protection

Cookie handling through proxy:
- `proxy_pass_header Set-Cookie` - Passes Set-Cookie headers
- `proxy_cookie_flags ~ secure httponly samesite=strict` - Enforces cookie security

### 8. Environment Configuration

**docker-compose.yml**:
```yaml
backend:
  environment:
    - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
    - ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**.env.example**:
```
SECRET_KEY=your-random-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**Startup validation**:
Main.py checks that `SECRET_KEY` is set on startup — raises `RuntimeError` if missing.

### 9. Dependencies Added (backend/requirements.txt)

- `passlib[bcrypt]>=1.7.4` - Password hashing
- `python-jose[cryptography]>=3.3.0` - JWT encoding/decoding
- `python-dotenv>=1.0.0` - Load .env in local dev
- `slowapi>=0.1.9` - Rate limiting
- `email-validator>=2.0.0` - Email validation in Pydantic

### 10. Testing

#### Unit Tests (backend/test_auth.py)
- Password hashing and verification
- JWT creation and decoding
- Token expiry handling
- Error cases (invalid token, missing SECRET_KEY)

#### Integration Tests (backend/test_auth_endpoints.py)
- Register first user only (bootstrap)
- Weak password rejection
- Login with valid/invalid credentials
- Case-insensitive email handling
- Email enumeration prevention
- Logout clears cookie
- GET /me with/without token

#### API Tests (backend/test_api.py) - Updated
- All tests now authenticate before accessing protected endpoints
- Verifies 401 response for unauthenticated requests
- Uses authenticated client fixture with login session

## Security Guarantees

### Password Security
✓ Bcrypt hashing with passlib (automatic salt generation)
✓ Constant-time verification to prevent timing attacks
✓ Minimum 12 characters enforced

### Token Security
✓ HS256 JWT with strong SECRET_KEY
✓ HttpOnly cookie prevents JavaScript access
✓ SameSite=Strict prevents CSRF
✓ Expiration claim enforced
✓ Secure path `/api` limits scope

### API Security
✓ All endpoints check authentication
✓ Email enumeration prevented (same message for all login failures)
✓ Rate limiting on login (5/minute per IP)
✓ Case-insensitive email normalization

### Network Security
✓ Cookie secure flag in production (Nginx proxy enforces)
✓ Security headers on all responses
✓ CORS allows credentials only on same origin

## Local Development

### Setup

1. **Generate SECRET_KEY**:
   ```bash
   python3 -c "import os; print(os.urandom(32).hex())"
   ```

2. **Create .env in backend/**:
   ```
   SECRET_KEY=<generated-key>
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

3. **Or set in shell**:
   ```bash
   export SECRET_KEY=<generated-key>
   ```

### Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest test_auth.py          # Unit tests
pytest test_auth_endpoints.py # Integration tests
pytest test_api.py            # Updated lifecycle tests
pytest                         # All tests
```

### Running with Docker Compose

```bash
# Generate a SECRET_KEY
SECRET_KEY=$(python3 -c "import os; print(os.urandom(32).hex())")

# Run with environment variable
docker compose up --build -e SECRET_KEY="$SECRET_KEY"

# Or set in docker-compose.override.yml (git-ignored)
# (not needed — defaults to "change-me-in-production" for dev)
```

Visit http://localhost:
1. Login form appears
2. No users yet — choose "Create Account"
3. Register with email + password (≥12 chars)
4. Auto-logged in, redirected to links UI
5. Use app normally
6. Click "Logout" to clear session

## Production Deployment

### Before Going Live

1. **Generate strong SECRET_KEY**:
   ```bash
   # Use a password manager or:
   openssl rand -hex 32
   ```

2. **Update docker-compose.yml** (do NOT commit the key):
   ```yaml
   backend:
     environment:
       - SECRET_KEY=<your-production-key>
   ```

3. **Or use Docker secrets** (recommended for orchestration):
   ```yaml
   secrets:
     secret_key:
       file: /run/secrets/secret_key
   services:
     backend:
       secrets:
         - secret_key
       environment:
         - SECRET_KEY=/run/secrets/secret_key
   ```

4. **Verify settings**:
   - `SECRET_KEY` is set and strong (32+ bytes)
   - `ACCESS_TOKEN_EXPIRE_MINUTES` appropriate for use case
   - HTTPS enabled in Nginx (add `ssl` directives to `nginx.conf`)
   - Cookie `Secure` flag enforced (HTTPS-only)

5. **Enable HTTPS**:
   ```nginx
   server {
       listen 80;
       return 301 https://$server_name$request_uri;
   }
   server {
       listen 443 ssl http2;
       ssl_certificate /etc/ssl/certs/cert.pem;
       ssl_certificate_key /etc/ssl/private/key.pem;
       # ... rest of config
   }
   ```

6. **Database backups**:
   - `data/links.db` now contains both users and links
   - Back up regularly — losing SECRET_KEY invalidates all sessions

7. **Monitor login attempts**:
   - Rate limiting logs (5 requests/minute per IP)
   - Watch for brute force patterns

## Common Questions

### Q: How do I change a user's password?
**A**: Not implemented yet (add a `PUT /api/auth/password` endpoint if needed).

### Q: What if SECRET_KEY is lost?
**A**: All existing tokens become invalid. Restarting the app with a new key forces re-login.

### Q: Can I have multiple users?
**A**: Yes, after the first user registers, others can click "Create Account" (registration never closes — only the first registration is checked to ensure at least one user exists). To restrict to one user, modify `_user_exists()` check.

### Q: How do I reset to multi-user mode if I accidentally created wrong user?
**A**: Delete `data/links.db` (loses all links too) — next restart will recreate schema and allow new registration.

## File Structure Summary

```
backend/
├── auth.py                 # New: Utility functions
├── dependencies.py         # New: FastAPI dependency
├── router_auth.py         # New: Auth endpoints
├── test_auth.py           # New: Unit tests
├── test_auth_endpoints.py # New: Integration tests
├── main.py                # Updated: Mount router, protect endpoints
├── database.py            # Updated: Added users table
├── models.py              # Unchanged
├── fetcher.py             # Unchanged
├── test_api.py            # Updated: Authenticate in fixture
├── requirements.txt       # Updated: Added 5 packages
├── .env.example           # New: Reference for env vars
└── Dockerfile             # Unchanged

frontend/
├── index.html             # Updated: Complete auth UI
├── nginx.conf             # Updated: Security headers
├── style.css              # Unchanged
├── config.template.js     # Unchanged
└── Dockerfile             # Unchanged

docker-compose.yml         # Updated: Added env vars
```

## Next Steps / Future Work

- [ ] Password reset flow (email verification)
- [ ] User profile / settings page
- [ ] Multiple user workspaces
- [ ] Admin dashboard (user management, audit logs)
- [ ] OAuth2 integration (GitHub, Google login)
- [ ] Session history / login audit log
- [ ] IP-based geolocation alerts
