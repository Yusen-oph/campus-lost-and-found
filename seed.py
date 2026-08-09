from db import get_connection

items = [
    ("Blue Water Bottle", "Metal flask, small dent on the base.", "lost", "https://placehold.co/300x200"),
    ("Black Umbrella", "Left near the Main Hall entrance.", "found", "https://placehold.co/300x200"),
    ("Casio Calculator", "Scientific calculator, name inked on back.", "found", "https://placehold.co/300x200"),
    ("Textbook: Physics AS", "Good condition, willing to trade.", "trade", "https://placehold.co/300x200"),
    ("Set of Keys", "Three keys on a red lanyard.", "lost", "https://placehold.co/300x200"),
    ("Wired Earphones", "Found in the library, second floor.", "found", "https://placehold.co/300x200"),
]

connection = get_connection()
cursor = connection.cursor()

cursor.executemany(
    "INSERT INTO items (title, description, category, image_url) VALUES (?, ?, ?, ?)",
    items,
)

connection.commit()
connection.close()
print(f"Inserted {len(items)} items.")