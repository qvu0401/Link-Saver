import sqlite3
import os

def get_db():
    conn = sqlite3.connect("data/links.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Create links table with user_id (or migrate if exists)
    cursor.execute("PRAGMA table_info(links)")
    columns = {row[1] for row in cursor.fetchall()}

    if 'links' not in [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        # Create new links table with user_id
        cursor.execute("""
            CREATE TABLE links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                tags TEXT,
                status TEXT NOT NULL DEFAULT 'unread',
                date TEXT NOT NULL,
                UNIQUE(user_id, url),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
    elif 'user_id' not in columns:
        # Migrate existing table to add user_id
        cursor.execute("ALTER TABLE links ADD COLUMN user_id INTEGER DEFAULT 1")

    conn.commit()
    conn.close()
