import sqlite3

DB_NAME = "lostfound.db"

def create_dismissed_notifications_table(cursor):
    # notif_id looks like "incoming-5-pending": direction, claim request id, status.
    # Including the status means a request that changes status shows up again.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dismissed_notifications (
        user_id INTEGER NOT NULL REFERENCES users(id),
        notif_id TEXT NOT NULL,
        PRIMARY KEY (user_id, notif_id)
    );
    """)

def init_db():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS dismissed_notifications")
    cursor.execute("DROP TABLE IF EXISTS claim_requests")
    cursor.execute("DROP TABLE IF EXISTS items")
    cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        institution TEXT,
        user_id TEXT,
        profile_photo TEXT,
        availability TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        image_url TEXT,
        status TEXT NOT NULL DEFAULT 'available',
        posted_by INTEGER REFERENCES users(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE claim_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES items(id),
        requested_by INTEGER NOT NULL REFERENCES users(id),
        status TEXT NOT NULL DEFAULT 'pending',
        proof_details TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    create_dismissed_notifications_table(cursor)

    connection.commit()
    connection.close()
    print("Database initialised.")

if __name__ == "__main__":
    init_db()