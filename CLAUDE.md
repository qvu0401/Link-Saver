# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Link Saver** is a full-stack web application for saving, organizing, and managing URLs with automatic title fetching. Multi-user authentication with email/password login and per-user link isolation.

- **Frontend**: Vanilla HTML/CSS/JavaScript with login/register UI, served by Nginx
- **Backend**: Python FastAPI REST API with JWT authentication and multi-user support
- **Database**: SQLite with users and links tables, persisted in Docker volume
- **Deployment**: Docker Compose
- **Authentication**: JWT in HttpOnly SameSite=Strict cookies, bcrypt password hashing, rate-limited login

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────┐
│ Browser (localhost)                                 │
│ - Login/Register form on first load                │
│ - Links UI after authentication                    │
└────────────────┬──────────────────────────────────┘
                 │ HTTP/CORS + Credentials
    ┌────────────▼───────────────────────┐
    │ Nginx (frontend)                   │
    │ - Serves index.html with auth UI  │
    │ - Proxies /api/* to backend       │
    │ - Security headers                │
    └────────────┬───────────────────────┘
                 │ Proxied to Backend
    ┌────────────▼───────────────────────┐
    │ FastAPI Backend                    │
    │ - JWT auth dependency injection   │
    │ - /api/auth/* endpoints           │
    │ - /api/links/* with user_id       │
    │   filtering                        │
    │ - Rate limiting on login          │
    └────────────┬───────────────────────┘
                 │
    ┌────────────▼───────────────────────┐
    │ SQLite Database                    │
    │ (data/links.db)                   │
    │ - users table (email, password)   │
    │ - links table (user_id FK)        │
    └────────────────────────────────────┘
```

**Data Flow**:
1. User lands on frontend → `checkAuth()` calls `GET /api/auth/me`
2. If 401 unauthenticated → show login/register form
3. On register/login → receive JWT in HttpOnly cookie, redirected to links UI
4. Frontend fetches links via `GET /api/links` (cookie automatically sent)
5. All link operations filtered by `user_id` — users can only see/modify their own links

### Backend Structure

```
backend/
├── main.py                # FastAPI app, link endpoints with user_id filtering
├── models.py              # Pydantic: LinkCreate, LinkUpdate, Status enum
├── database.py            # SQLite init_db() with users + links tables
├── fetcher.py             # fetch_title() using httpx
├── auth.py                # JWT + bcrypt utilities (NEW)
├── dependencies.py        # get_current_user FastAPI dependency (NEW)
├── router_auth.py         # Auth endpoints: register, login, logout, me (NEW)
├── test_api.py            # 11 tests: lifecycle, multi-user, authorization
├── test_auth_endpoints.py # 10 integration tests for auth router
├── test_auth.py           # 5 unit tests for auth utilities
├── requirements.txt       # + passlib[bcrypt], python-jose, slowapi, email-validator
└── Dockerfile             # Python 3.11-slim, CMD runs uvicorn on :8000
```

### Frontend Structure

```
frontend/
├── index.html            # Single-page app with auth UI (login/register)
├── style.css             # Responsive design, cards, badges
├── nginx.conf            # Reverse proxy + security headers
├── config.template.js    # Template: window.APP_CONFIG.BACKEND_URL
├── Dockerfile            # Nginx alpine, envsubst to config.js
```

**Frontend Logic Patterns**:
- `checkAuth()`: Calls `GET /api/auth/me`, shows app if 200, login if 401
- `login()` / `register()`: POST to `/api/auth/login` or `/api/auth/register`, stores JWT in cookie
- `logout()`: POST to `/api/auth/logout`, clears cookie, shows login form
- `loadLinks()`: Fetch from API (user_id filtering done server-side), store in `allLinks`
- `applyFilters()`: Read input fields, filter `allLinks`, call `renderLinks()`
- `renderLinks()`: Clear DOM, create link cards with actions (displays user email in header)
- Action handlers (`addLink()`, `toggleRead()`, `deleteLink()`, etc.): POST/PATCH/DELETE to API, then `loadLinks()`
- All fetch requests include `credentials: 'include'` for cookie handling
- 401 interception: Any API endpoint returning 401 triggers login form display

### Database Schema

**Users Table** (NEW):
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,          -- Lowercase, max 254 chars
    password_hash TEXT NOT NULL,         -- Bcrypt hash, never raw password
    created_at TEXT NOT NULL             -- ISO 8601 UTC timestamp
);
```

**Links Table** (Updated):
```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,            -- Foreign key to users(id)
    url TEXT NOT NULL,                   -- Not UNIQUE anymore
    title TEXT,                          -- Auto-fetched or fallback to URL
    tags TEXT,                           -- JSON array string: '["tag1","tag2"]'
    status TEXT NOT NULL DEFAULT 'unread',  -- "unread" or "read"
    date TEXT NOT NULL,                  -- ISO 8601 UTC timestamp
    UNIQUE(user_id, url),                -- Each user can't add duplicate URL
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Key Differences from v1**:
- Each link now belongs to a `user_id` — same URL can be in multiple users' lists
- `UNIQUE(user_id, url)` prevents duplicate URLs within ONE user's list
- `ON DELETE CASCADE` — deleting a user deletes all their links

## Common Commands

### Build & Run (Development)
```bash
cd "Link Saver"
docker compose up
```
- Frontend: http://localhost (Nginx on :80)
- Backend API: http://localhost:8000/api
- On code changes: rebuild containers with `docker compose up --build`

### Stop & Clean
```bash
docker compose down          # Stop containers, keep data
docker compose down -v       # Stop containers, delete data volume
```

### Backend Development (Local, without Docker)

```bash
# Setup
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Set required environment variables
export SECRET_KEY="dev-secret-key-32-bytes-minimum-"
export ACCESS_TOKEN_EXPIRE_MINUTES="60"

# Run tests
pytest

# Run all tests with coverage
pytest --cov=.

# Run with hot-reload (requires installing uvicorn[standard])
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Note**:
- `SECRET_KEY` is REQUIRED. App will fail at startup without it.
- If running backend locally, frontend needs `BACKEND_URL=http://localhost:8000`. Docker Compose handles this automatically.
- Test fixture uses monkeypatch to mock database and environment variables, so tests don't require actual SECRET_KEY export.

### Frontend Development (Local, static files only)

Frontend is static HTML/CSS/JS — can be opened directly in browser or served with any HTTP server:
```bash
cd frontend
python -m http.server 8080
```
Then visit http://localhost:8080, but API calls will fail unless backend is running.

## Key Implementation Details

### Authentication System

**JWT Token Strategy**:
- Tokens issued as HttpOnly SameSite=Strict cookies (never accessible to JavaScript)
- HS256 algorithm with `SECRET_KEY` environment variable
- Token claims: `sub` (email), `exp` (expiry), `iat` (issued at)
- Default lifetime: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)

**Password Security**:
- Bcrypt hashing via `passlib[bcrypt]` library
- Constant-time comparison for verification (prevents timing attacks)
- Minimum password length: 12 characters (enforced at registration)

**API Endpoints** (in `router_auth.py`):
- `POST /api/auth/register` (201): Email, password → creates new user
- `POST /api/auth/login` (200): Email, password → issues JWT cookie, rate-limited 5/minute
- `POST /api/auth/logout` (200): Clears JWT cookie
- `GET /api/auth/me` (200): Returns authenticated user email (requires valid JWT)

**Protected Endpoints** (in `main.py`):
- All link endpoints (`POST/GET/PATCH/DELETE /api/links*`) require valid JWT
- Missing/invalid token returns 401 Unauthorized
- Backend uses `get_current_user` FastAPI dependency to extract email from JWT
- All queries filtered by `user_id` — users can only access their own links

### Multi-User Data Isolation

**Authorization Checks**:
- Link creation: Inserted with authenticated user's `user_id`
- Link retrieval: Filtered with `WHERE user_id = ?`
- Link update (PATCH): Checks ownership, returns 403 if user attempts cross-user modification
- Link deletion: Checks ownership, returns 403 if user attempts cross-user deletion

**Duplicate Prevention**:
- `UNIQUE(user_id, url)` constraint allows same URL across users but not within one user
- Returns 409 Conflict if duplicate URL for same user

### CORS Setup

Backend allows origins:
- `http://localhost`
- `http://localhost:80`

Configured in `main.py` with `CORSMiddleware(allow_credentials=True)`. Credentials mode required for cookie handling. Safe for development only; update before production.

### Environment Variables

**Frontend** (Nginx container):
- `BACKEND_URL`: e.g., `http://localhost:8000`
- Injected into `config.js` at startup via `envsubst` in Dockerfile

**Backend** (FastAPI) — REQUIRED:
- `SECRET_KEY`: Min 32 random bytes for JWT signing. Must be set at startup or app will raise RuntimeError.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token lifetime in minutes (default: 60)

Set in `docker-compose.yml` backend service or `.env` file for local development.

### Title Fetching

`fetcher.py:fetch_title()`:
- Uses `httpx` with 5-second timeout and redirect following
- Regex extracts `<title>` tag (case-insensitive, multiline)
- Falls back to URL if fetch fails, timeout, or no title found
- **Limitation**: Will fail on blocked requests or paywalled sites

### Database Constraints

- **UNIQUE on url**: Prevents duplicate links
- **Integrity Error Handling**: Returns 409 Conflict with message "This URL already exists"

### Tags Storage

- Stored as JSON string: `json.dumps(["tag1", "tag2"])` when inserting
- Parsed back: `json.loads(row["tags"])` when reading
- Frontend splits/joins with commas for UI

### Status Enum

- `Status.unread` and `Status.read` defined in `models.py`
- Pydantic automatically validates incoming values
- Stored as string in database ("unread" or "read")

## Testing

### Test Coverage (21 Total Tests)

**Unit Tests** (`test_auth.py` — 5 tests):
- Hash password and verify with bcrypt
- Create and decode JWT tokens
- Token expiry and invalid signature handling

**Authentication Integration Tests** (`test_auth_endpoints.py` — 10 tests):
- Register first user (201)
- Register multiple users (201 for 2nd+ users)
- Reject weak passwords (<12 chars)
- Reject duplicate emails (409)
- Login with correct password (200)
- Login case-insensitive email
- Login with wrong password (401)
- Login with unknown email (401, generic message)
- Logout clears cookie
- /me endpoint with valid/invalid token (200 / 401)

**Link Endpoints & Multi-User Tests** (`test_api.py` — 11 tests):
- Full lifecycle: create → list → update → delete
- Unauthenticated access returns 401
- Multi-user data isolation: User1 and User2 see only their own links
- User cannot modify other user's links (403 on PATCH/DELETE)
- Duplicate URL prevention per user (409 per user, 201 across users)

**Approach**:
- Pytest with `TestClient` for FastAPI
- Monkeypatch to redirect SQLite path to temp file for isolation
- Multi-user fixtures create separate users with separate cookies

**Run**:
```bash
cd backend
pytest                              # Run all 21 tests
pytest test_api.py test_auth_endpoints.py test_auth.py -v  # Verbose
pytest -k test_multi_user           # Run specific test
pytest --cov=.                      # Coverage report
```

**Coverage**: 80%+ achieved across all modules (auth, dependencies, routers, database)

### Frontend Testing

Manual browser testing via Playwright or similar:
1. Register new account (password >= 12 chars)
2. Verify redirect to links UI
3. Add/edit/delete links
4. Logout and verify login form shown
5. Login as different user, verify data isolation

## Development Workflow

1. **Backend changes**:
   - Edit Python files (`main.py`, `models.py`, `database.py`, `fetcher.py`, `auth.py`, `dependencies.py`, `router_auth.py`)
   - Run tests: `pytest` (runs all 21 tests)
   - Rebuild Docker: `docker compose up --build backend`
   - If SECRET_KEY not set, app will fail at startup with RuntimeError

2. **Authentication changes**:
   - Modify auth logic in `auth.py` (hash, verify, token functions)
   - Modify token dependency in `dependencies.py` (get_current_user)
   - Modify endpoints in `router_auth.py` (register, login, logout, me)
   - Run auth tests: `pytest test_auth.py test_auth_endpoints.py`
   - Remember: All link endpoints already protected with `Depends(get_current_user)`

3. **Multi-user / Authorization changes**:
   - Add `user_id` filtering to queries in `main.py` link endpoints
   - Add ownership checks before PATCH/DELETE (raise 403 if unauthorized)
   - Test with multi-user fixture in `test_api.py`

4. **Frontend changes**:
   - Edit HTML/CSS/JS in `frontend/index.html` (login form, auth checks, logout button)
   - Rebuild Docker: `docker compose up --build frontend`
   - Or use local HTTP server for instant reload: `cd frontend && python -m http.server 8080`
   - Remember: All fetch requests must include `credentials: 'include'` for cookies

5. **Database schema changes**:
   - Modify `init_db()` in `database.py`
   - Remove volume to reset: `docker compose down -v`
   - Rebuild: `docker compose up --build`

6. **Adding new API endpoints**:
   - Define Pydantic model in `models.py`
   - Add endpoint in `main.py` with `Depends(get_current_user)` dependency and user_id filtering
   - Add test in `test_api.py` or `test_auth_endpoints.py`
   - Update frontend to call new endpoint with `credentials: 'include'`

## Known Limitations & Future Work

- **Title fetching limitations**: Fails on paywalled/blocked sites, timeouts after 5s
- **Client-side filtering**: All links always sent to frontend (inefficient at scale)
- **No server-side filtering**: Even with status filter query param, backend returns all links (frontend filters locally)
- **No pagination**: Entire link list loaded at startup
- **No edit history**: Modifications overwrite without tracking
- **No password reset**: Users cannot recover forgotten passwords (implement email verification)
- **No profile editing**: Users cannot change email or password after registration

## New Dependencies (v2)

Added to `backend/requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| `passlib[bcrypt]` | `>=1.7.4` | Bcrypt password hashing |
| `python-jose[cryptography]` | `>=3.3.0` | JWT encode/decode |
| `python-dotenv` | `>=1.0.0` | Load `.env` in local dev |
| `slowapi` | `>=0.1.9` | Rate limiting (5 logins/min per IP) |
| `email-validator` | `>=2.2.0` | Email format validation |
| `bcrypt` | `>=4.1.2` | Pinned for passlib compatibility |

## Security Features

**Password Storage**:
- Bcrypt hashing with passlib CryptContext
- Minimum 12 characters enforced
- No plaintext passwords ever stored or logged

**Session Management**:
- JWT tokens in HttpOnly SameSite=Strict cookies
- Automatic browser sending, never accessible to JavaScript
- HS256 signing with environment SECRET_KEY
- Token expiry enforced, default 60 minutes

**Authorization**:
- User ID filtering on all link queries
- Ownership checks on update/delete (403 Forbidden if unauthorized)
- User cannot see/modify other users' links

**Rate Limiting**:
- Login endpoint limited to 5 attempts per minute per IP
- Returns 429 Too Many Requests when exceeded

**Nginx Security Headers** (in `frontend/nginx.conf`):
- `X-Frame-Options: DENY` — prevent clickjacking
- `X-Content-Type-Options: nosniff` — prevent MIME sniffing
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-XSS-Protection: 1; mode=block` — legacy XSS protection
- `Set-Cookie` with `secure`, `httponly`, `samesite=strict` flags

**Input Validation**:
- Email format validated with `email-validator`
- Password strength checked (>= 12 chars)
- URLs validated through Pydantic HttpUrl

**Error Messages**:
- Login errors return generic "Invalid credentials" (prevents email enumeration)
- Duplicate email returns 409 with clear message

## Startup Requirements

Backend requires `SECRET_KEY` environment variable:
```bash
# Generate a new SECRET_KEY (32+ random bytes)
python -c "import secrets; print(secrets.token_hex(32))"

# Set in docker-compose.yml or .env
export SECRET_KEY="<generated-value>"
docker compose up
```

If `SECRET_KEY` is missing, the app will fail at startup with:
```
RuntimeError: SECRET_KEY environment variable is not set. Cannot start.
```

## Useful References

- FastAPI docs: https://fastapi.tiangolo.com/
- Pydantic docs: https://docs.pydantic.dev/
- SQLite docs: https://www.sqlite.org/docs.html
- Pytest docs: https://docs.pytest.org/
- Docker Compose docs: https://docs.docker.com/compose/
- Passlib docs: https://passlib.readthedocs.io/
- Python-JOSE docs: https://python-jose.readthedocs.io/
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
