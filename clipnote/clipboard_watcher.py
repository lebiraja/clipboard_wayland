"""Clipboard watcher for monitoring clipboard changes."""

import hashlib
from pathlib import Path
from typing import List, Optional

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib

from .clip_item import ClipItem
from .clip_store import ClipStore
from .image_utils import (
    get_image_dimensions,
    save_image_to_cache,
    texture_to_pixbuf,
)


class ClipboardWatcher:
    """Watches the system clipboard for changes."""

    def __init__(self, store: ClipStore, cache_dir: Path):
        self.store = store
        self.cache_dir = cache_dir
        self.clipboard: Optional[Gdk.Clipboard] = None
        self._last_content_hash: Optional[str] = None
        self._handler_id: Optional[int] = None

    def start_watching(self, clipboard: Gdk.Clipboard) -> None:
        """Start monitoring the clipboard for changes."""
        self.clipboard = clipboard
        self._handler_id = clipboard.connect("changed", self._on_clipboard_changed)
        print("ClipboardWatcher: Started monitoring clipboard")

    def stop_watching(self) -> None:
        """Stop monitoring the clipboard."""
        if self.clipboard and self._handler_id:
            self.clipboard.disconnect(self._handler_id)
            self._handler_id = None
        print("ClipboardWatcher: Stopped monitoring clipboard")

    def _on_clipboard_changed(self, clipboard: Gdk.Clipboard) -> None:
        """Handle clipboard change event."""
        self._process_clipboard_content()

    def _process_clipboard_content(self) -> None:
        """Process the current clipboard content."""
        if not self.clipboard:
            return

        formats = self.clipboard.get_formats()

        # Check for file URIs first (file copies may also contain text)
        if formats.contain_mime_type("text/uri-list"):
            self._read_files_async()
        # Check for image
        elif formats.contain_mime_type("image/png") or formats.contain_mime_type("image/jpeg"):
            self._read_image_async()
        # Then check for text
        elif formats.contain_mime_type("text/plain") or formats.contain_mime_type("text/plain;charset=utf-8"):
            self._read_text_async()

    def _read_text_async(self) -> None:
        """Read text content from clipboard asynchronously."""
        self.clipboard.read_text_async(None, self._on_text_ready)

    def _on_text_ready(self, clipboard: Gdk.Clipboard, result: Gio.AsyncResult) -> None:
        """Handle async text read completion."""
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self._handle_text_content(text)
        except Exception as e:
            print(f"ClipboardWatcher: Error reading text: {e}")

    def _handle_text_content(self, text: str) -> None:
        """Process text content from clipboard."""
        # Skip empty or whitespace-only
        if not text or not text.strip():
            return

        # Generate content hash
        content_hash = self._get_content_hash(text)

        # Skip if same as last content
        if content_hash == self._last_content_hash:
            return

        self._last_content_hash = content_hash

        # Create clip item
        item = ClipItem.from_text(text, content_hash=content_hash)
        self.store.add_item(item)
        print(f"ClipboardWatcher: Added text clip - {item.preview[:50]}")

    def _read_image_async(self) -> None:
        """Read image content from clipboard asynchronously."""
        self.clipboard.read_texture_async(None, self._on_texture_ready)

    def _on_texture_ready(self, clipboard: Gdk.Clipboard, result: Gio.AsyncResult) -> None:
        """Handle async texture read completion."""
        try:
            texture = clipboard.read_texture_finish(result)
            if texture:
                self._handle_image_content(texture)
        except Exception as e:
            print(f"ClipboardWatcher: Error reading image: {e}")

    def _handle_image_content(self, texture: Gdk.Texture) -> None:
        """Process image content from clipboard."""
        # Convert texture to pixbuf
        pixbuf = texture_to_pixbuf(texture)
        if not pixbuf:
            return

        # Save to cache
        image_path, content_hash = save_image_to_cache(pixbuf, self.cache_dir)

        # Skip if same as last content
        if content_hash == self._last_content_hash:
            return

        self._last_content_hash = content_hash

        # Get dimensions
        width, height = get_image_dimensions(pixbuf)

        # Create clip item
        item = ClipItem.from_image(image_path, width, height, content_hash=content_hash)
        self.store.add_item(item)
        print(f"ClipboardWatcher: Added image clip - {item.preview}")

    def _get_content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _read_files_async(self) -> None:
        """Read file URIs from clipboard asynchronously."""
        # Read as text since text/uri-list is text-based
        self.clipboard.read_text_async(None, self._on_files_text_ready)

    def _on_files_text_ready(self, clipboard: Gdk.Clipboard, result: Gio.AsyncResult) -> None:
        """Handle async file URI text read completion."""
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self._handle_files_content(text)
        except Exception as e:
            print(f"ClipboardWatcher: Error reading file URIs: {e}")

    def _handle_files_content(self, uri_text: str) -> None:
        """Process file URI list from clipboard."""
        # Parse URI list (one URI per line, may have comments starting with #)
        uris: List[str] = []
        for line in uri_text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Handle potential \r from Windows-style line endings
                line = line.rstrip("\r")
                if line.startswith("file://"):
                    uris.append(line)

        if not uris:
            return

        # Generate content hash from sorted URIs
        content_hash = self._get_content_hash("\n".join(sorted(uris)))

        # Skip if same as last content
        if content_hash == self._last_content_hash:
            return

        self._last_content_hash = content_hash

        # Create clip item
        item = ClipItem.from_files(uris, content_hash=content_hash)
        self.store.add_item(item)
        print(f"ClipboardWatcher: Added files clip - {item.preview}")
