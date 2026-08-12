import os
from init_db import init_db
from seed import seed

DB_NAME = "lostfound.db"

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)
    print(f"Removed old {DB_NAME}.")

init_db()
seed()
print("Reset complete.")