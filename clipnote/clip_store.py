"""In-memory storage for clipboard items."""

from typing import Callable, List, Optional

from .clip_item import ClipItem, ClipType


class ClipStore:
    """Manages clipboard history in memory."""

    def __init__(self, max_items: int = 100):
        self._items: List[ClipItem] = []
        self._max_items = max_items
        self._listeners: List[Callable[[], None]] = []

    def add_item(self, item: ClipItem) -> None:
        """Add a new item to the store (newest first)."""
        # Check for duplicate based on content hash
        if item.content_hash:
            for existing in self._items:
                if existing.content_hash == item.content_hash:
                    # Move existing to front instead of adding duplicate
                    self._items.remove(existing)
                    existing.timestamp = item.timestamp
                    self._items.insert(0, existing)
                    self._notify_listeners()
                    return

        self._items.insert(0, item)

        # Trim if exceeds max
        if len(self._items) > self._max_items:
            self._items = self._items[: self._max_items]

        self._notify_listeners()

    def get_all_items(self) -> List[ClipItem]:
        """Get all items (newest first)."""
        return self._items.copy()

    def search_items(self, query: str) -> List[ClipItem]:
        """Filter items by search query."""
        if not query:
            return self.get_all_items()

        query_lower = query.lower()
        results = []

        for item in self._items:
            if item.item_type == ClipType.TEXT:
                if item.text_content and query_lower in item.text_content.lower():
                    results.append(item)
            elif item.item_type == ClipType.IMAGE:
                # Images can be searched by their preview text
                if query_lower in item.preview.lower():
                    results.append(item)

        return results

    def get_item_by_id(self, item_id: str) -> Optional[ClipItem]:
        """Get a specific item by ID."""
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
        self._notify_listeners()

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
