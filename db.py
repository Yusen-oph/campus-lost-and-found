import sqlite3

DB_NAME = "lostfound.db"

def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row   # rows behave like dicts
    return connection