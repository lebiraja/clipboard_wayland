"""Main application entry point for ClipNote."""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .clip_store import ClipStore
from .clipboard_watcher import ClipboardWatcher
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

        # Create shared database instance
        self.database = Database()

        # Core components
        self.store = ClipStore(max_items=100, database=self.database)
        self.watcher: ClipboardWatcher = None
        self.window: PopupWindow = None

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
            self.window = PopupWindow(self, self.store, self.database)

            # Start clipboard monitoring
            clipboard = Gdk.Display.get_default().get_clipboard()
            self.watcher = ClipboardWatcher(self.store, self.cache_dir)
            self.watcher.start_watching(clipboard)

        # Present window (existing or new)
        self.window.present()

    def do_shutdown(self) -> None:
        """Handle application shutdown."""
        if self.watcher:
            self.watcher.stop_watching()

        Adw.Application.do_shutdown(self)


def main() -> int:
    """Application entry point."""
    app = ClipNoteApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
