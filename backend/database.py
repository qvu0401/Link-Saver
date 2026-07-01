import sqlite3

def get_db():
    conn = sqlite3.connect("links.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            tags TEXT,
            status TEXT NOT NULL DEFAULT 'read_later',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()