import os
import sqlite3
from typing import List, Dict, Any

DB_CONN = None
DB_PATH = None


def init_db(db_path: str) -> None:
    global DB_CONN, DB_PATH
    DB_PATH = db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    DB_CONN = sqlite3.connect(db_path, check_same_thread=False)
    DB_CONN.row_factory = sqlite3.Row
    cur = DB_CONN.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sender TEXT,
            content TEXT,
            audio_url TEXT,
            timestamp TEXT
        )
        """
    )
    DB_CONN.commit()


def ensure_session(session_id: str) -> None:
    cur = DB_CONN.cursor()
    cur.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    if not row:
        from datetime import datetime, timezone
        cur.execute(
            "INSERT INTO sessions(session_id, created_at) VALUES(?, ?)",
            (session_id, datetime.now(timezone.utc).isoformat()),
        )
        DB_CONN.commit()


def append_message(session_id: str, sender: str, content: str, audio_url: str, timestamp: str) -> None:
    cur = DB_CONN.cursor()
    cur.execute(
        "INSERT INTO messages(session_id, sender, content, audio_url, timestamp) VALUES(?,?,?,?,?)",
        (session_id, sender, content, audio_url, timestamp),
    )
    DB_CONN.commit()


def get_history(session_id: str) -> List[Dict[str, Any]]:
    cur = DB_CONN.cursor()
    cur.execute("SELECT sender, content, audio_url, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def reset_history_if_exists(session_id: str) -> None:
    cur = DB_CONN.cursor()
    cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    DB_CONN.commit()


def get_all_sessions(user_id: str = None) -> List[Dict[str, Any]]:
    """Get all sessions with their first message for display, optionally filtered by user"""
    cur = DB_CONN.cursor()
    
    # If we add user_id to sessions table later, we can filter by it
    # For now, just get all sessions
    cur.execute("""
        SELECT s.session_id, s.created_at,
               (SELECT content FROM messages WHERE session_id = s.session_id AND sender = 'user' ORDER BY id ASC LIMIT 1) as first_message,
               (SELECT COUNT(*) FROM messages WHERE session_id = s.session_id) as message_count
        FROM sessions s
        WHERE EXISTS (SELECT 1 FROM messages WHERE session_id = s.session_id)
        ORDER BY s.created_at DESC
    """)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: str) -> None:
    """Delete a session and all its messages"""
    cur = DB_CONN.cursor()
    cur.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    DB_CONN.commit()


