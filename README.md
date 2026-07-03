# Link Saver

A web app to save URLs with titles, tags, and read/unread status. Paste a link and the title is fetched automatically.

## Setup

**Prerequisites:** Docker and Docker Compose installed.

```bash
git clone <your-repo-url>
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

## API Examples

**Save a link**
```bash
curl -X POST http://localhost:8000/api/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "tags": ["reading"], "status": "unread"}'
```

**Get all links**
```bash
curl http://localhost:8000/api/links
```

**Filter by status**
```bash
curl http://localhost:8000/api/links?status=unread
```

**Filter by tag**
```bash
curl http://localhost:8000/api/links?tag=reading
```

**Update a link (mark as read, edit title, or change tags)**
```bash
curl -X PATCH http://localhost:8000/api/links/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "read"}'
```

**Delete a link**
```bash
curl -X DELETE http://localhost:8000/api/links/1
```

## Known Limitations

- **SQLite is local to each host** — each machine that runs the app has its own separate database. There is no shared or synced data between machines.
- **Not suitable for multiple backend instances** — SQLite is a file-based database. Running more than one backend container pointing at the same file will cause conflicts.
- **No authentication** — all links are visible to anyone who can reach port 8000.
- **Title fetching can fail** — if a URL blocks HTTP requests or times out, the URL itself is used as the title.
