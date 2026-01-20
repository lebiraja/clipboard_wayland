"""SQLite database for persistent clipboard storage."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from .clip_item import ClipItem, ClipType


class Database:
    """SQLite database manager for ClipNote."""

    # Current database schema version
    DB_VERSION = 2

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".local" / "share" / "clipnote" / "clipnote.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        self._migrate_db()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with context management."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clips table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clips (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    item_type TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    text_content TEXT,
                    image_path TEXT,
                    file_uris TEXT,
                    content_hash TEXT,
                    pinned INTEGER DEFAULT 0
                )
            """)

            # Notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    pinned INTEGER DEFAULT 0,
                    color TEXT DEFAULT 'blue'
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_clips_timestamp
                ON clips(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_clips_pinned
                ON clips(pinned DESC, timestamp DESC)
            """)

            # DB version table for migrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS db_version (
                    version INTEGER PRIMARY KEY
                )
            """)

    def _migrate_db(self) -> None:
        """Run database migrations if needed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get current version
            cursor.execute("SELECT version FROM db_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row['version'] if row else 1

            if current_version < 2:
                # Migration 2: Add color column to notes table
                try:
                    cursor.execute("ALTER TABLE notes ADD COLUMN color TEXT DEFAULT 'blue'")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
                cursor.execute("INSERT OR REPLACE INTO db_version (version) VALUES (2)")

    # ============ CLIPS METHODS ============

    def add_clip(self, item: ClipItem) -> None:
        """Add a clip to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            file_uris_json = json.dumps(item.file_uris) if item.file_uris else None

            cursor.execute("""
                INSERT OR REPLACE INTO clips
                (id, timestamp, item_type, preview, text_content, image_path, file_uris, content_hash, pinned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id,
                item.timestamp,
                item.item_type.value,
                item.preview,
                item.text_content,
                item.image_path,
                file_uris_json,
                item.content_hash,
                getattr(item, 'pinned', False)
            ))

    def get_all_clips(self, limit: int = 100) -> List[ClipItem]:
        """Get all clips, pinned first, then by timestamp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM clips
                ORDER BY pinned DESC, timestamp DESC
                LIMIT ?
            """, (limit,))

            return [self._row_to_clip(row) for row in cursor.fetchall()]

    def get_clip_by_id(self, clip_id: str) -> Optional[ClipItem]:
        """Get a specific clip by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
            row = cursor.fetchone()
            return self._row_to_clip(row) if row else None

    def get_clip_by_hash(self, content_hash: str) -> Optional[ClipItem]:
        """Get a clip by content hash."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clips WHERE content_hash = ?", (content_hash,))
            row = cursor.fetchone()
            return self._row_to_clip(row) if row else None

    def update_clip_timestamp(self, clip_id: str, timestamp: float) -> None:
        """Update a clip's timestamp (for moving duplicates to top)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE clips SET timestamp = ? WHERE id = ?",
                (timestamp, clip_id)
            )

    def toggle_clip_pinned(self, clip_id: str) -> bool:
        """Toggle the pinned status of a clip. Returns new pinned state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pinned FROM clips WHERE id = ?", (clip_id,))
            row = cursor.fetchone()
            if row:
                new_pinned = not bool(row['pinned'])
                cursor.execute(
                    "UPDATE clips SET pinned = ? WHERE id = ?",
                    (new_pinned, clip_id)
                )
                return new_pinned
            return False

    def delete_clip(self, clip_id: str) -> bool:
        """Delete a clip by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
            return cursor.rowcount > 0

    def clear_all_clips(self, keep_pinned: bool = True) -> int:
        """Clear all clips. Returns count of deleted items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if keep_pinned:
                cursor.execute("DELETE FROM clips WHERE pinned = 0")
            else:
                cursor.execute("DELETE FROM clips")
            return cursor.rowcount

    def search_clips(self, query: str, limit: int = 100) -> List[ClipItem]:
        """Search clips by text content or preview."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM clips
                WHERE preview LIKE ? OR text_content LIKE ?
                ORDER BY pinned DESC, timestamp DESC
                LIMIT ?
            """, (search_pattern, search_pattern, limit))

            return [self._row_to_clip(row) for row in cursor.fetchall()]

    def delete_clips_before(self, timestamp: float) -> int:
        """Delete clips older than timestamp (except pinned). Returns count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM clips WHERE timestamp < ? AND pinned = 0",
                (timestamp,)
            )
            return cursor.rowcount

    def trim_clips(self, max_items: int) -> int:
        """Delete oldest non-pinned clips to stay within limit. Returns count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Get IDs of clips to keep (pinned + newest up to limit)
            cursor.execute("""
                DELETE FROM clips WHERE id NOT IN (
                    SELECT id FROM clips
                    ORDER BY pinned DESC, timestamp DESC
                    LIMIT ?
                )
            """, (max_items,))
            return cursor.rowcount

    def _row_to_clip(self, row: sqlite3.Row) -> ClipItem:
        """Convert a database row to a ClipItem."""
        file_uris = json.loads(row['file_uris']) if row['file_uris'] else None

        item = ClipItem(
            id=row['id'],
            timestamp=row['timestamp'],
            item_type=ClipType(row['item_type']),
            preview=row['preview'],
            text_content=row['text_content'],
            image_path=row['image_path'],
            file_uris=file_uris,
            content_hash=row['content_hash'] or ""
        )
        item.pinned = bool(row['pinned'])
        return item

    # ============ NOTES METHODS ============

    def add_note(self, note_id: str, title: str, body: str, timestamp: float, color: str = 'blue') -> None:
        """Add a note to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO notes (id, timestamp, title, body, pinned, color)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (note_id, timestamp, title, body, color))

    def get_all_notes(self) -> List[dict]:
        """Get all notes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                ORDER BY pinned DESC, timestamp DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_note_by_id(self, note_id: str) -> Optional[dict]:
        """Get a specific note by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_note(self, note_id: str, title: str, body: str, color: Optional[str] = None) -> bool:
        """Update a note."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if color is not None:
                cursor.execute(
                    "UPDATE notes SET title = ?, body = ?, color = ? WHERE id = ?",
                    (title, body, color, note_id)
                )
            else:
                cursor.execute(
                    "UPDATE notes SET title = ?, body = ? WHERE id = ?",
                    (title, body, note_id)
                )
            return cursor.rowcount > 0

    def update_note_color(self, note_id: str, color: str) -> bool:
        """Update a note's color."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE notes SET color = ? WHERE id = ?",
                (color, note_id)
            )
            return cursor.rowcount > 0

    def delete_note(self, note_id: str) -> bool:
        """Delete a note by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cursor.rowcount > 0

    def toggle_note_pinned(self, note_id: str) -> bool:
        """Toggle the pinned status of a note."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pinned FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if row:
                new_pinned = not bool(row['pinned'])
                cursor.execute(
                    "UPDATE notes SET pinned = ? WHERE id = ?",
                    (new_pinned, note_id)
                )
                return new_pinned
            return False
