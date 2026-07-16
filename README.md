# Link Saver

A full-stack web app for saving, organizing, and managing URLs with automatic title fetching. Features multi-user authentication, per-user link isolation, and a clean responsive UI.

## Setup

**Prerequisites:** Docker and Docker Compose installed.

```bash
git clone https://github.com/qvu0401/Link-Saver.git
cd "Link Saver"
docker compose up
```

Then open **http://localhost** in your browser (port 80).
- Frontend: http://localhost
- Backend API: http://localhost:8000/api

To stop the app:
```bash
docker compose down
```

To clear all data:
```bash
docker compose down -v
```

## Features

- **Multi-user authentication** — Email/password registration and login with JWT tokens
- **Per-user link isolation** — Each user only sees and manages their own links
- **Automatic title fetching** — URLs are fetched and their `<title>` tag is extracted
- **Link management** — Save, organize with tags, mark as read/unread, delete
- **Secure sessions** — HttpOnly SameSite=Strict cookies, bcrypt password hashing

## API Endpoints

### Base URL
```text
http://localhost:8000/api
```

#### Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/auth/register` | Create new account |
| **POST** | `/auth/login` | Login with email/password |
| **POST** | `/auth/logout` | Logout and clear session |
| **GET** | `/auth/me` | Get current user info |

#### Links (all require authentication)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/links` | Save a new link (title auto-fetched) |
| **GET** | `/links` | List user's links |
| **PATCH** | `/links/:id` | Update title, status, or tags |
| **DELETE** | `/links/:id` | Delete a link |

## Local Development

See [CLAUDE.md](./CLAUDE.md) for detailed development setup and commands.

Quick start:
```bash
# Docker (recommended)
docker compose up

# Or local backend development
cd backend
pip install -r requirements.txt pytest pytest-cov
export SECRET_KEY="dev-key-min-32-bytes"
pytest
uvicorn main:app --reload
```

## Known Limitations

- **Title fetching** — Fails on paywalled/blocked sites, timeouts after 5 seconds
- **No pagination** — All user links loaded at startup
- **No password reset** — Users cannot recover forgotten passwords
- **No profile editing** — Users cannot change email/password after registration
