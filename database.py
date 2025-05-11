import sqlite3
from datetime import datetime

DB_NAME = "messages.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            message TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(user_id: int, role: str, message: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Сохраняем новое сообщение
    cursor.execute("""
        INSERT INTO messages (user_id, role, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, (user_id, role, message, datetime.now().isoformat()))
    conn.commit()

    # Удаляем старые сообщения, оставляя только 10 последних для этого пользователя
    cursor.execute("""
        DELETE FROM messages
        WHERE id NOT IN (
            SELECT id FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        ) AND user_id = ?
    """, (user_id, user_id))

    conn.commit()
    conn.close()

def load_history(user_id: int, limit: int = 30) -> list:
    """
    Загружает последние `limit` сообщений пользователя из базы.
    Возвращает список в формате [{'role': 'user', 'content': '...'}, ...]
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, message FROM messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()

    return [{"role": role, "content": msg} for role, msg in reversed(rows)]
