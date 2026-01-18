"""Persistent storage for clipboard items using SQLite."""

from typing import Callable, List, Optional

from .clip_item import ClipItem, ClipType
from .database import Database


class ClipStore:
    """Manages clipboard history with SQLite persistence."""

    def __init__(self, max_items: int = 100, database: Optional[Database] = None):
        self._max_items = max_items
        self._listeners: List[Callable[[], None]] = []
        self._db = database or Database()

        # Load existing items from database
        self._items: List[ClipItem] = self._db.get_all_clips(limit=max_items)

    def add_item(self, item: ClipItem) -> None:
        """Add a new item to the store."""
        # Check for duplicate based on content hash
        if item.content_hash:
            existing = self._db.get_clip_by_hash(item.content_hash)
            if existing:
                # Update timestamp and move to top
                self._db.update_clip_timestamp(existing.id, item.timestamp)
                self._reload_items()
                self._notify_listeners()
                return

        # Add new item
        self._db.add_clip(item)
        self._reload_items()
        self._notify_listeners()

    def get_all_items(self) -> List[ClipItem]:
        """Get all items (pinned first, then newest)."""
        return self._items.copy()

    def search_items(self, query: str) -> List[ClipItem]:
        """Search items by query."""
        if not query:
            return self.get_all_items()

        return self._db.search_clips(query, limit=self._max_items)

    def get_item_by_id(self, item_id: str) -> Optional[ClipItem]:
        """Get a specific item by ID."""
        return self._db.get_clip_by_id(item_id)

    def remove_item(self, item_id: str) -> bool:
        """Remove an item by ID."""
        result = self._db.delete_clip(item_id)
        if result:
            self._reload_items()
            self._notify_listeners()
        return result

    def toggle_pinned(self, item_id: str) -> bool:
        """Toggle pinned status of an item. Returns new pinned state."""
        new_state = self._db.toggle_clip_pinned(item_id)
        self._reload_items()
        self._notify_listeners()
        return new_state

    def clear(self, keep_pinned: bool = True) -> int:
        """Clear all items. Returns count of deleted items."""
        count = self._db.clear_all_clips(keep_pinned=keep_pinned)
        self._reload_items()
        self._notify_listeners()
        return count

    def _reload_items(self) -> None:
        """Reload items from database."""
        self._items = self._db.get_all_clips(limit=self._max_items)

    def add_listener(self, callback: Callable[[], None]) -> None:
        """Add a listener to be notified when store changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[], None]) -> None:
        """Remove a change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all listeners of a change."""
        for callback in self._listeners:
            callback()

    def __len__(self) -> int:
        return len(self._items)

    def set_max_items(self, max_items: int) -> None:
        """Update the maximum items limit."""
        self._max_items = max_items
        # Trim excess items if needed
        self._db.trim_clips(max_items)
        self._reload_items()
        self._notify_listeners()
