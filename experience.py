import sqlite3
from mental_state import STATE_DIR

DB_PATH = STATE_DIR / "experiences.db"

CATEGORIES = (
    "preference",
    "knowledge",
    "project",
    "feedback"
)


def initialize_memory():

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, content)
            )
        """)


def remember(category, content):

    if category not in CATEGORIES:
        return

    content = content.strip()

    if not content or len(content) > 500:
        return

    initialize_memory()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO experiences
            (category, content)
            VALUES (?, ?)
        """, (category, content))


def recall(limit=20):

    initialize_memory()

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id, category, content
            FROM experiences
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [
        {
            "id": memory_id,
            "category": category,
            "content": content
        }
        for memory_id, category, content in rows
    ]


def forget(memory_id):

    initialize_memory()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            DELETE FROM experiences
            WHERE id = ?
        """, (memory_id,))

        return cursor.rowcount


def forget_all():

    initialize_memory()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            DELETE FROM experiences
        """)

        return cursor.rowcount


def count_memories():

    initialize_memory()

    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("""
            SELECT COUNT(*) FROM experiences
        """).fetchone()[0]


if __name__ == "__main__":

    initialize_memory()

    print("\nATLAS EXPERIENTIAL MEMORY")
    print("-------------------------")
    print("Total memories:", count_memories())

    for memory in recall(limit=-1):
        print(
            f"[{memory['id']}] "
            f"{memory['category']}: "
            f"{memory['content']}"
        )