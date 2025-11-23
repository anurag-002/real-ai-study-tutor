import os
import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

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
            user_id TEXT,
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
    # New table for user statistics
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            total_messages INTEGER DEFAULT 0,
            total_files_uploaded INTEGER DEFAULT 0,
            total_study_time INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_activity TEXT,
            created_at TEXT
        )
        """
    )
    # Table for daily activity tracking
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            activity_date TEXT,
            messages_sent INTEGER DEFAULT 0,
            files_uploaded INTEGER DEFAULT 0,
            study_time INTEGER DEFAULT 0,
            UNIQUE(user_id, activity_date)
        )
        """
    )
    
    # Migrate existing sessions table if needed
    try:
        cur.execute("SELECT user_id FROM sessions LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        cur.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
    
    DB_CONN.commit()


def ensure_session(session_id: str, user_id: str = None) -> None:
    cur = DB_CONN.cursor()
    cur.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO sessions(session_id, user_id, created_at) VALUES(?, ?, ?)",
            (session_id, user_id, datetime.now(timezone.utc).isoformat()),
        )
        DB_CONN.commit()
    elif user_id and row:
        # Update user_id if provided and session exists but user_id is null
        cur.execute("UPDATE sessions SET user_id = ? WHERE session_id = ? AND user_id IS NULL", (user_id, session_id))
        DB_CONN.commit()


def append_message(session_id: str, sender: str, content: str, audio_url: str, timestamp: str) -> None:
    cur = DB_CONN.cursor()
    cur.execute(
        "INSERT INTO messages(session_id, sender, content, audio_url, timestamp) VALUES(?,?,?,?,?)",
        (session_id, sender, content, audio_url, timestamp),
    )
    DB_CONN.commit()
    
    # Update user stats if it's a user message
    if sender == 'user':
        update_user_activity(session_id, 'message')


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
    """Get all sessions with their first message for display, filtered by user"""
    cur = DB_CONN.cursor()
    
    if user_id:
        # Get sessions for specific user
        cur.execute("""
            SELECT s.session_id, s.user_id, s.created_at,
                   (SELECT content FROM messages WHERE session_id = s.session_id AND sender = 'user' ORDER BY id ASC LIMIT 1) as first_message,
                   (SELECT COUNT(*) FROM messages WHERE session_id = s.session_id) as message_count
            FROM sessions s
            WHERE s.user_id = ? AND EXISTS (SELECT 1 FROM messages WHERE session_id = s.session_id)
            ORDER BY s.created_at DESC
        """, (user_id,))
    else:
        # Get all sessions (for backwards compatibility)
        cur.execute("""
            SELECT s.session_id, s.user_id, s.created_at,
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


# Scoreboard functions
def get_or_create_user_stats(user_id: str, username: str = None) -> Dict[str, Any]:
    """Get user stats, create if doesn't exist"""
    cur = DB_CONN.cursor()
    cur.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    
    if not row:
        now = datetime.now(timezone.utc).isoformat()
        username = username or f"User_{user_id[:8]}"
        cur.execute(
            """INSERT INTO user_stats 
            (user_id, username, total_messages, total_files_uploaded, total_study_time, 
             points, current_streak, longest_streak, last_activity, created_at)
            VALUES (?, ?, 0, 0, 0, 0, 0, 0, ?, ?)""",
            (user_id, username, now, now)
        )
        DB_CONN.commit()
        cur.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    
    return dict(row)


def update_user_activity(user_id: str, activity_type: str, value: int = 1) -> None:
    """Update user activity and calculate points/streaks"""
    cur = DB_CONN.cursor()
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    
    # Ensure user stats exist
    get_or_create_user_stats(user_id)
    
    # Update daily activity
    cur.execute(
        """INSERT INTO daily_activity (user_id, activity_date, messages_sent, files_uploaded, study_time)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, activity_date) DO UPDATE SET
        messages_sent = messages_sent + ?,
        files_uploaded = files_uploaded + ?,
        study_time = study_time + ?""",
        (user_id, today, 
         value if activity_type == 'message' else 0,
         value if activity_type == 'file' else 0,
         value if activity_type == 'study_time' else 0,
         value if activity_type == 'message' else 0,
         value if activity_type == 'file' else 0,
         value if activity_type == 'study_time' else 0)
    )
    
    # Calculate points (1 point per message, 5 points per file, 1 point per 5 minutes study)
    points_to_add = 0
    if activity_type == 'message':
        points_to_add = value
    elif activity_type == 'file':
        points_to_add = value * 5
    elif activity_type == 'study_time':
        points_to_add = value // 5
    
    # Update user stats
    if activity_type == 'message':
        cur.execute(
            """UPDATE user_stats SET 
            total_messages = total_messages + ?,
            points = points + ?,
            last_activity = ?
            WHERE user_id = ?""",
            (value, points_to_add, now.isoformat(), user_id)
        )
    elif activity_type == 'file':
        cur.execute(
            """UPDATE user_stats SET 
            total_files_uploaded = total_files_uploaded + ?,
            points = points + ?,
            last_activity = ?
            WHERE user_id = ?""",
            (value, points_to_add, now.isoformat(), user_id)
        )
    elif activity_type == 'study_time':
        cur.execute(
            """UPDATE user_stats SET 
            total_study_time = total_study_time + ?,
            points = points + ?,
            last_activity = ?
            WHERE user_id = ?""",
            (value, points_to_add, now.isoformat(), user_id)
        )
    
    # Update streak
    update_streak(user_id)
    
    DB_CONN.commit()


def update_streak(user_id: str) -> None:
    """Calculate and update user's study streak"""
    cur = DB_CONN.cursor()
    
    # Get last 30 days of activity
    cur.execute(
        """SELECT activity_date FROM daily_activity 
        WHERE user_id = ? 
        ORDER BY activity_date DESC LIMIT 30""",
        (user_id,)
    )
    rows = cur.fetchall()
    
    if not rows:
        return
    
    dates = [datetime.fromisoformat(row['activity_date']).date() for row in rows]
    today = datetime.now(timezone.utc).date()
    
    # Calculate current streak
    current_streak = 0
    check_date = today
    
    for date in dates:
        if date == check_date or date == check_date - timedelta(days=1):
            current_streak += 1
            check_date = date - timedelta(days=1)
        else:
            break
    
    # Update longest streak if current is higher
    cur.execute("SELECT longest_streak FROM user_stats WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    longest_streak = row['longest_streak'] if row else 0
    
    if current_streak > longest_streak:
        longest_streak = current_streak
    
    cur.execute(
        """UPDATE user_stats SET 
        current_streak = ?,
        longest_streak = ?
        WHERE user_id = ?""",
        (current_streak, longest_streak, user_id)
    )
    DB_CONN.commit()


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top users by points"""
    cur = DB_CONN.cursor()
    cur.execute(
        """SELECT user_id, username, points, current_streak, 
        total_messages, total_files_uploaded, total_study_time
        FROM user_stats 
        ORDER BY points DESC 
        LIMIT ?""",
        (limit,)
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_user_rank(user_id: str) -> Dict[str, Any]:
    """Get user's rank and stats"""
    cur = DB_CONN.cursor()
    
    # Get user's rank
    cur.execute(
        """SELECT COUNT(*) + 1 as rank FROM user_stats 
        WHERE points > (SELECT points FROM user_stats WHERE user_id = ?)""",
        (user_id,)
    )
    rank_row = cur.fetchone()
    rank = rank_row['rank'] if rank_row else 0
    
    # Get user stats
    stats = get_or_create_user_stats(user_id)
    stats['rank'] = rank
    
    return stats


