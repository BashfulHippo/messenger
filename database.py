# database.py
"""SQLite database module for persistent message storage."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from security import hash_password, verify_password


class MessageDatabase:
    """handles all database operations for the messaging app."""

    def __init__(self, db_path='messenger.db'):
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        """context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """create tables if they don't exist."""
        with self.get_connection() as conn:
            conn.executescript('''
                -- users table
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    server TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- contacts table
                CREATE TABLE IF NOT EXISTS contacts (
                    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    friend_username TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, friend_username)
                );

                -- messages table
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    is_sent BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                -- pending messages (offline queue)
                CREATE TABLE IF NOT EXISTS pending_messages (
                    pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                -- indexes for performance
                CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_contacts_user ON contacts(user_id);
            ''')

    # user operations
    def get_or_create_user(self, username, password, server=None):
        """get existing user or create new one. returns user_id."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT user_id, password_hash FROM users WHERE username = ?',
                (username,)
            )
            row = cursor.fetchone()
            if row:
                # update password hash if it's plain text (migration)
                if row['password_hash'] == password:
                    hashed = hash_password(password)
                    conn.execute(
                        'UPDATE users SET password_hash = ? WHERE user_id = ?',
                        (hashed, row['user_id'])
                    )
                return row['user_id']

            # new user - hash the password
            hashed = hash_password(password)
            cursor = conn.execute(
                'INSERT INTO users (username, password_hash, server) VALUES (?, ?, ?)',
                (username, hashed, server)
            )
            return cursor.lastrowid

    def get_user(self, username):
        """get user by username."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM users WHERE username = ?',
                (username,)
            )
            return cursor.fetchone()

    def update_user_password(self, username, password_hash):
        """update user password hash."""
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE users SET password_hash = ? WHERE username = ?',
                (password_hash, username)
            )

    # contact operations
    def add_contact(self, user_id, friend_username):
        """add a contact for a user."""
        with self.get_connection() as conn:
            try:
                conn.execute(
                    'INSERT OR IGNORE INTO contacts (user_id, friend_username) VALUES (?, ?)',
                    (user_id, friend_username)
                )
            except sqlite3.IntegrityError:
                pass  # already exists

    def get_contacts(self, user_id):
        """get all contacts for a user."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT friend_username FROM contacts WHERE user_id = ? ORDER BY friend_username',
                (user_id,)
            )
            return [row['friend_username'] for row in cursor.fetchall()]

    def remove_contact(self, user_id, friend_username):
        """remove a contact."""
        with self.get_connection() as conn:
            conn.execute(
                'DELETE FROM contacts WHERE user_id = ? AND friend_username = ?',
                (user_id, friend_username)
            )

    # message operations
    def add_message(self, user_id, sender, recipient, content, timestamp):
        """add a message to the database."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO messages (user_id, sender, recipient, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, sender, recipient, content, timestamp))

            # auto-add contacts from message participants
            other_user = recipient if sender != recipient else sender
            self.add_contact(user_id, other_user)

    def get_messages(self, user_id, other_username=None, limit=500):
        """get messages for a user, optionally filtered by conversation partner."""
        with self.get_connection() as conn:
            if other_username:
                cursor = conn.execute('''
                    SELECT * FROM messages
                    WHERE user_id = ? AND (sender = ? OR recipient = ?)
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (user_id, other_username, other_username, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM messages
                    WHERE user_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (user_id, limit))
            return cursor.fetchall()

    def get_all_messages(self, user_id):
        """get all messages for a user."""
        return self.get_messages(user_id)

    # pending message operations (offline queue)
    def add_pending_message(self, user_id, recipient, content, timestamp):
        """add a message to the offline queue."""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO pending_messages (user_id, recipient, content, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user_id, recipient, content, timestamp))

    def get_pending_messages(self, user_id):
        """get all pending messages for a user."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM pending_messages
                WHERE user_id = ? AND attempts < 3
                ORDER BY timestamp ASC
            ''', (user_id,))
            return cursor.fetchall()

    def mark_pending_sent(self, pending_id):
        """remove a pending message after successful send."""
        with self.get_connection() as conn:
            conn.execute(
                'DELETE FROM pending_messages WHERE pending_id = ?',
                (pending_id,)
            )

    def increment_pending_attempts(self, pending_id):
        """increment the attempt counter for a pending message."""
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE pending_messages SET attempts = attempts + 1 WHERE pending_id = ?',
                (pending_id,)
            )

    def clear_pending_messages(self, user_id):
        """clear all pending messages for a user."""
        with self.get_connection() as conn:
            conn.execute(
                'DELETE FROM pending_messages WHERE user_id = ?',
                (user_id,)
            )
