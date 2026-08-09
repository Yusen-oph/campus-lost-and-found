import sqlite3

# --- SCHEMA ------------------------------------------------------
# items: every lost, found, or trade listing on the platform
#   id          unique row id, auto-assigned
#   title       short name of the item (required)
#   description longer detail about the item
#   category    lost / found / trade (required)
#   image_url   optional link to a picture
#   status      available / claimed, defaults to available
# -----------------------------------------------------------------

connection = sqlite3.connect("lostfound.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    image_url TEXT,
    status TEXT NOT NULL DEFAULT 'available'
);
""")

connection.commit()
connection.close()
print("Database initialised.")