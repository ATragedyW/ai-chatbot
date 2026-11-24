import sqlite3
from pathlib import Path

DATABASE = Path(__file__).with_name("atlas.db")

def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)

def save_message(role, content):
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content)
        )

def load_recent_messages(limit=10):
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            """
            SELECT role, content
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()

    return [
        {"role": role, "content": content}
        for role, content in reversed(rows)
    ]


def search_memories(keyword, limit=5):
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            """
            SELECT role, content
            FROM messages
            WHERE content LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (f"%{keyword}%", limit)
        )

        rows = cursor.fetchall()

    return [
        {"role": role, "content": content}
        for role, content in rows
    ]


    return [
        {"role": role, "content": content}
        for role, content in reversed(rows)
    ]

def clear_memory():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("DELETE FROM messages")
    
    print("Atlas memory has been cleared!")


initialize_database()


if __name__ == "__main__":
    confirmation = input(
        "Delete ALL Atlas memories? Type CLEAR to confirm: "
    )

    if confirmation == "CLEAR":
        clear_memory()
    else:
        print("Memory was not cleared.")
