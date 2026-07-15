# Link Saver

A web app to save URLs with titles, tags, and read/unread status. Paste a link and the title is fetched automatically.

## Setup

**Prerequisites:** Docker and Docker Compose installed.

```bash
git clone https://github.com/qvu0401/Link-Saver.git
cd "Link Saver"
docker compose up
```

Then open http://localhost in your browser (port 80).
The backend API is available at http://localhost:8000/api.

To stop the app:
```bash
docker compose down
```

To clear all data (links)
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
| **PATCH** | `/links/:id` | Update title, status, or tags |
| **DELETE** | `/links/:id` | Delete a link |

## Known Limitations

- No authentication, all links are visible to anyone who can reach port 8000.
- Title fetching can fail. If a URL blocks HTTP requests or times out, the URL itself is used as the title.
- Links filtering done on frontend, so less GET requests required, but client always receive every links.
