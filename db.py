import os
import sqlite3

# Always the lostfound.db next to this file, whichever folder the app is started from
# (on PythonAnywhere the app doesn't start in the project folder).
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lostfound.db")

def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row   # rows behave like dicts
    return connection