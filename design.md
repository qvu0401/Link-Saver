## Tech Stack

- **Frontend:** Plain HTML/CSS/JS
- **Backend:** FastAPI
- **Database:** SQLite



## Data Model

This represents a single link saved by a user.


| Field Name | Data Type |
| --- | --- | 
| `id` | int |
| `url` | String | 
| `title` | String | 
| `tags` | String Array | 
| `status` | String |
| `created_at` | Date |



## API Endpoints

- ### POST /api/links
    - **Example Request:**
    ```json
    {
        "int": "1",
        "url": "https://example.com",
        "title": "Fetched Title",
        "tags": ["documentation", "learning"],
        "status": "read_later",
        "created_at": "2026-05-27T16:00:00Z"
    }
    ```

- ### GET /api/links
    - **Parameters (if filter by tags):** `?status=read_later&tag=learning`
    - **Example Response:**
    ```json
    [
        {
        "id": "1",
        "url": "https://example.com",
        "title": "Example Domain",
        "tags": ["documentation", "learning"],
        "status": "read_later",
        "created_at": "2026-05-27T23:00:00Z"
        }
    ]
    ```

- ### PATCH /api/links/:id
    - **Example Request:** 
    ```json
    {
        "status": "read",
        "title": "Updated Custom Title"
    }
    ```

- ### DELETE /api/links/:id


## Architecture Diagram

![diagram](./arch_diagram.png)