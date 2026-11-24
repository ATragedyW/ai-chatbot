import sqlite3
from pathlib import Path

DATABASE = Path(__file__).with_name("atlas.db")

# Connect to database
connection = sqlite3.connect(DATABASE)

# Create a table
connection.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL
    )
""")

connection.commit()
connection.close()

print("Atlas database created!")