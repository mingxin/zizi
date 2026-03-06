"""
Database connection and operations for zizi user system
Supports SQLite for development, easy to migrate to MySQL
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime

# Database file path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "zizi.db")


def init_db():
    """Initialize database with schema"""
    schema_path = os.path.join(DB_DIR, "schema.sql")

    with get_db() as db:
        with open(schema_path, 'r') as f:
            schema = f.read()
        db.executescript(schema)
        db.commit()
        print(f"Database initialized at {DB_PATH}")


@contextmanager
def get_db():
    """Get database connection context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# User operations
class UserDB:
    @staticmethod
    def create_user(phone: str, password_hash: str, nickname: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            with get_db() as db:
                cursor = db.execute(
                    """
                    INSERT INTO users (phone, password_hash, nickname, last_login_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (phone, password_hash, nickname, datetime.utcnow())
                )
                db.commit()
                user_id = cursor.lastrowid

                # Create default settings
                db.execute(
                    "INSERT INTO user_settings (user_id) VALUES (?)",
                    (user_id,)
                )
                db.commit()

                return UserDB.get_user_by_id(user_id)
        except sqlite3.IntegrityError:
            return None  # Phone already exists

    @staticmethod
    def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        with get_db() as db:
            row = db.execute(
                "SELECT * FROM users WHERE phone = ?",
                (phone,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with get_db() as db:
            row = db.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_last_login(user_id: int):
        """Update last login time"""
        with get_db() as db:
            db.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (datetime.utcnow(), user_id)
            )
            db.commit()

    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """Update user fields"""
        allowed_fields = ['nickname']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]

        with get_db() as db:
            db.execute(
                f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?",
                [datetime.utcnow()] + values
            )
            db.commit()
            return True


# Settings operations
class SettingsDB:
    @staticmethod
    def get_settings(user_id: int) -> Dict[str, Any]:
        """Get user settings"""
        with get_db() as db:
            row = db.execute(
                "SELECT * FROM user_settings WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                return {
                    'preferred_voice': row['preferred_voice'],
                    'current_library': row['current_library'],
                    'settings_json': row['settings_json']
                }
            return {
                'preferred_voice': 'serena',
                'current_library': 'infant',
                'settings_json': None
            }

    @staticmethod
    def update_settings(user_id: int, preferred_voice: Optional[str] = None,
                       current_library: Optional[str] = None) -> bool:
        """Update user settings"""
        updates = []
        values = []

        if preferred_voice is not None:
            updates.append("preferred_voice = ?")
            values.append(preferred_voice)
        if current_library is not None:
            updates.append("current_library = ?")
            values.append(current_library)

        if not updates:
            return False

        values.extend([datetime.utcnow(), user_id])

        with get_db() as db:
            db.execute(
                f"""
                UPDATE user_settings
                SET {', '.join(updates)}, updated_at = ?
                WHERE user_id = ?
                """,
                values
            )
            db.commit()
            return True


# Learning record operations
class LearningDB:
    @staticmethod
    def record_learning(user_id: int, char: str, action_type: str,
                       library_id: Optional[str] = None,
                       context: Optional[Dict] = None,
                       duration_sec: int = 0) -> bool:
        """Record a learning activity"""
        import json

        with get_db() as db:
            db.execute(
                """
                INSERT INTO learning_records
                (user_id, char, library_id, action_type, context, duration_sec)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, char, library_id, action_type,
                 json.dumps(context) if context else None, duration_sec)
            )
            db.commit()
            return True

    @staticmethod
    def get_learning_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get learning history for user"""
        with get_db() as db:
            rows = db.execute(
                """
                SELECT * FROM learning_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_learned_chars(user_id: int) -> List[str]:
        """Get list of learned characters"""
        with get_db() as db:
            rows = db.execute(
                """
                SELECT DISTINCT char FROM learning_records
                WHERE user_id = ? AND action_type = 'char_viewed'
                ORDER BY created_at DESC
                """,
                (user_id,)
            ).fetchall()
            return [row['char'] for row in rows]


# Character mastery operations
class MasteryDB:
    @staticmethod
    def record_view(user_id: int, char: str):
        """Record character view and update mastery"""
        with get_db() as db:
            # Check if exists
            row = db.execute(
                "SELECT * FROM char_mastery WHERE user_id = ? AND char = ?",
                (user_id, char)
            ).fetchone()

            if row:
                # Update
                new_count = row['view_count'] + 1
                # Simple mastery logic: view_count >= 3 -> mastery 1, >= 5 -> mastery 2, >= 10 -> mastery 3
                mastery = min(3, new_count // 3)
                db.execute(
                    """
                    UPDATE char_mastery
                    SET view_count = ?, mastery_level = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (new_count, mastery, datetime.utcnow(), row['id'])
                )
            else:
                # Insert new
                db.execute(
                    """
                    INSERT INTO char_mastery (user_id, char, view_count, mastery_level)
                    VALUES (?, ?, 1, 0)
                    """,
                    (user_id, char)
                )
            db.commit()

    @staticmethod
    def get_mastery_stats(user_id: int) -> Dict[str, Any]:
        """Get mastery statistics for user"""
        with get_db() as db:
            total = db.execute(
                "SELECT COUNT(*) as count FROM char_mastery WHERE user_id = ?",
                (user_id,)
            ).fetchone()['count']

            mastered = db.execute(
                """SELECT COUNT(*) as count FROM char_mastery
                   WHERE user_id = ? AND mastery_level >= 3""",
                (user_id,)
            ).fetchone()['count']

            learning = db.execute(
                """SELECT COUNT(*) as count FROM char_mastery
                   WHERE user_id = ? AND mastery_level BETWEEN 1 AND 2""",
                (user_id,)
            ).fetchone()['count']

            return {
                'total': total,
                'mastered': mastered,
                'learning': learning,
                'new': total - mastered - learning
            }


# Initialize database on module import
if not os.path.exists(DB_PATH):
    init_db()
