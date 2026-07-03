# Link Saver

A web app to save URLs with titles, tags, and read/unread status. Paste a link and the title is fetched automatically.

## Setup

**Prerequisites:** Docker and Docker Compose installed.

```bash
git clone https://github.com/qvu0401/Link-Saver.git
cd "Link Saver"
docker compose up --build
```

Then open http://localhost:8000 in your browser.

To stop the app:
```bash
docker compose down
```

Your saved links persist in a Docker volume and survive restarts. To wipe all data:
```bash
docker compose down -v
```

## API Endpoints

### Base URL
```text
http://localhost:8000/api
```

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/links` | Save a new link (title auto-fetched) |
| **GET** | `/links` | List all links |
| **GET** | `/links?status=unread` | Filter by status (`read` or `unread`) |
| **GET** | `/links?tag=reading` | Filter by tag |
| **PATCH** | `/links/:id` | Update title, status, or tags |
| **DELETE** | `/links/:id` | Delete a link |

## Known Limitations

- No authentication, all links are visible to anyone who can reach port 8000.
- Title fetching can fail. If a URL blocks HTTP requests or times out, the URL itself is used as the title.
