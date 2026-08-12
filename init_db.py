import sqlite3

DB_NAME = "lostfound.db"

def init_db():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        image_url TEXT,
        status TEXT NOT NULL DEFAULT 'available',
        posted_by INTEGER REFERENCES users(id)
    );
    """)

    connection.commit()
    connection.close()
    print("Database initialised.")

if __name__ == "__main__":
    init_db()