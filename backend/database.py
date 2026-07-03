import sqlite3
import os

def get_db():
    conn = sqlite3.connect("data/links.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            tags TEXT,
            status TEXT NOT NULL DEFAULT 'unread',
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()