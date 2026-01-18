"""Main application entry point for ClipNote."""

import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .clip_store import ClipStore
from .clipboard_watcher import ClipboardWatcher
from .config import ConfigManager
from .database import Database
from .popup_window import PopupWindow


class ClipNoteApp(Adw.Application):
    """Main ClipNote application."""

    def __init__(self):
        super().__init__(
            application_id="com.github.clipnote.poc",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

        # Setup cache directory
        self.cache_dir = Path.home() / ".cache" / "clipnote" / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create config manager
        self.config_manager = ConfigManager()

        # Create shared database instance
        self.database = Database()

        # Core components
        self.store = ClipStore(
            max_items=self.config_manager.config.max_history_items,
            database=self.database
        )
        self.watcher: ClipboardWatcher = None
        self.window: PopupWindow = None

        # Listen for config changes
        self.config_manager.add_listener(self._on_config_changed)

        # Setup auto-expire timer
        self._expire_timer_id: int = None
        self._setup_auto_expire()

    def do_startup(self) -> None:
        """Handle application startup - load CSS."""
        Adw.Application.do_startup(self)
        self._load_css()

    def _load_css(self) -> None:
        """Load custom CSS stylesheet."""
        css_provider = Gtk.CssProvider()

        # Get the path to the CSS file relative to this module
        css_path = Path(__file__).parent / "style.css"

        if css_path.exists():
            css_provider.load_from_path(str(css_path))

            # Add the CSS provider to the default display
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            print(f"ClipNote: Loaded custom CSS from {css_path}")
        else:
            print(f"ClipNote: CSS file not found at {css_path}")

    def do_activate(self) -> None:
        """Handle application activation."""
        if not self.window:
            # First activation - create window and start watcher
            self.window = PopupWindow(
                self,
                self.store,
                self.database,
                self.config_manager
            )

            # Start clipboard monitoring (if not in private mode)
            if not self.config_manager.config.private_mode:
                self._start_watcher()

        # Present window (existing or new)
        self.window.present()

    def _start_watcher(self) -> None:
        """Start clipboard monitoring."""
        if not self.watcher:
            clipboard = Gdk.Display.get_default().get_clipboard()
            self.watcher = ClipboardWatcher(
                self.store,
                self.cache_dir,
                self.config_manager
            )
            self.watcher.start_watching(clipboard)
            print("ClipNote: Clipboard monitoring started")

    def _stop_watcher(self) -> None:
        """Stop clipboard monitoring."""
        if self.watcher:
            self.watcher.stop_watching()
            self.watcher = None
            print("ClipNote: Clipboard monitoring stopped")

    def _on_config_changed(self, config) -> None:
        """Handle config changes."""
        # Update store max items
        self.store.set_max_items(config.max_history_items)

        # Handle private mode toggle
        if config.private_mode:
            self._stop_watcher()
        else:
            self._start_watcher()

        # Update auto-expire
        self._setup_auto_expire()

    def _setup_auto_expire(self) -> None:
        """Setup auto-expire timer."""
        # Cancel existing timer
        if self._expire_timer_id:
            GLib.source_remove(self._expire_timer_id)
            self._expire_timer_id = None

        # If auto-expire is enabled, run cleanup periodically
        if self.config_manager.config.auto_expire_days > 0:
            # Run every hour
            self._expire_timer_id = GLib.timeout_add_seconds(
                3600,  # 1 hour
                self._run_auto_expire
            )
            # Also run immediately
            self._run_auto_expire()

    def _run_auto_expire(self) -> bool:
        """Delete expired items. Returns True to continue timer."""
        expire_days = self.config_manager.config.auto_expire_days
        if expire_days > 0:
            expire_before = time.time() - (expire_days * 86400)
            count = self.database.delete_clips_before(expire_before)
            if count > 0:
                print(f"ClipNote: Auto-expired {count} items older than {expire_days} days")
                self.store._reload_items()
        return True  # Continue timer

    def do_shutdown(self) -> None:
        """Handle application shutdown."""
        if self._expire_timer_id:
            GLib.source_remove(self._expire_timer_id)

        if self.watcher:
            self.watcher.stop_watching()

        Adw.Application.do_shutdown(self)


def main() -> int:
    """Application entry point."""
    app = ClipNoteApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
