"""Main popup window UI for ClipNote."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from typing import Callable, Optional

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

from .clip_item import ClipItem, ClipType
from .clip_store import ClipStore
from .image_utils import create_thumbnail, load_image_from_cache


class ClipItemRow(Gtk.ListBoxRow):
    """A row widget representing a single clipboard item."""

    def __init__(self, clip_item: ClipItem, on_delete: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.clip_item = clip_item
        self._on_delete = on_delete

        # Main horizontal box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Icon based on type
        if clip_item.item_type == ClipType.TEXT:
            icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
            icon.set_pixel_size(24)
            box.append(icon)

            # Text preview
            label = Gtk.Label(label=clip_item.get_display_text())
            label.set_xalign(0)
            label.set_hexpand(True)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(50)
            box.append(label)
        elif clip_item.item_type == ClipType.FILES:
            # File icon
            icon = Gtk.Image.new_from_icon_name("folder-documents-symbolic")
            icon.set_pixel_size(24)
            box.append(icon)

            # File preview
            label = Gtk.Label(label=clip_item.get_display_text())
            label.set_xalign(0)
            label.set_hexpand(True)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(50)
            box.append(label)
        else:
            # Image thumbnail
            if clip_item.image_path:
                pixbuf = load_image_from_cache(clip_item.image_path)
                if pixbuf:
                    thumbnail = create_thumbnail(pixbuf, size=48)
                    texture = Gdk.Texture.new_for_pixbuf(thumbnail)
                    picture = Gtk.Picture.new_for_paintable(texture)
                    picture.set_size_request(48, 48)
                    box.append(picture)
                else:
                    icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
                    icon.set_pixel_size(24)
                    box.append(icon)
            else:
                icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
                icon.set_pixel_size(24)
                box.append(icon)

            # Image description
            label = Gtk.Label(label=clip_item.get_display_text())
            label.set_xalign(0)
            label.set_hexpand(True)
            box.append(label)

        # Relative timestamp
        time_label = Gtk.Label(label=clip_item.get_relative_time())
        time_label.add_css_class("dim-label")
        time_label.set_margin_end(8)
        box.append(time_label)

        # Delete button
        delete_btn = Gtk.Button()
        delete_btn.set_icon_name("window-close-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("circular")
        delete_btn.set_tooltip_text("Delete")
        delete_btn.connect("clicked", self._on_delete_clicked)
        box.append(delete_btn)

        self.set_child(box)

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        """Handle delete button click."""
        if self._on_delete:
            self._on_delete(self.clip_item.id)


class PopupWindow(Adw.ApplicationWindow):
    """Main popup window for ClipNote."""

    def __init__(self, app: Adw.Application, store: ClipStore):
        super().__init__(application=app)
        self.store = store
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        self._current_filter = ""

        self._build_ui()
        self._setup_keyboard()
        self._populate_list()

        # Listen for store changes
        self.store.add_listener(self._on_store_changed)

    def _build_ui(self) -> None:
        """Build the UI components."""
        self.set_title("ClipNote")
        self.set_default_size(600, 500)
        self.set_hide_on_close(True)

        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar with search
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)

        # Search entry in header
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search clipboard history...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        header.set_title_widget(self.search_entry)

        main_box.append(header)

        # Scrolled window for list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # List box for items
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("boxed-list")
        # Don't connect row-activated - we handle Enter key separately
        # Add double-click gesture to listbox
        gesture = Gtk.GestureClick()
        gesture.set_button(1)  # Left mouse button
        gesture.connect("pressed", self._on_list_click)
        self.listbox.add_controller(gesture)
        scrolled.set_child(self.listbox)

        # Empty state placeholder
        self.empty_label = Gtk.Label(label="No clipboard history yet.\nCopy something to get started.")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_margin_top(50)
        self.empty_label.set_justify(Gtk.Justification.CENTER)

        # Stack for empty state vs list
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.add_named(scrolled, "list")
        self.stack.add_named(self.empty_label, "empty")
        self.stack.set_visible_child_name("empty")

        main_box.append(self.stack)

        self.set_content(main_box)

    def _setup_keyboard(self) -> None:
        """Set up keyboard shortcuts."""
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        """Handle key press events."""
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            # Enter key - paste selected item
            selected_row = self.listbox.get_selected_row()
            if selected_row and hasattr(selected_row, "clip_item"):
                self._restore_item(selected_row.clip_item)
            return True
        elif keyval == Gdk.KEY_Delete:
            # Delete key - delete selected item
            selected_row = self.listbox.get_selected_row()
            if selected_row and hasattr(selected_row, "clip_item"):
                self._delete_item(selected_row.clip_item.id)
            return True
        return False

    def _on_list_click(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        """Handle click on list - double-click to paste."""
        if n_press == 2:  # Double-click
            selected_row = self.listbox.get_selected_row()
            if selected_row and hasattr(selected_row, "clip_item"):
                self._restore_item(selected_row.clip_item)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Handle search text changes."""
        self._current_filter = entry.get_text()
        self._populate_list()

    def _delete_item(self, item_id: str) -> None:
        """Delete an item from the store."""
        self.store.remove_item(item_id)
        print(f"Deleted item: {item_id}")

    def _restore_item(self, item: ClipItem) -> None:
        """Copy item back to clipboard."""
        if item.item_type == ClipType.TEXT and item.text_content:
            content = Gdk.ContentProvider.new_for_value(item.text_content)
            self.clipboard.set_content(content)
            print(f"Restored text: {item.preview}")
        elif item.item_type == ClipType.IMAGE and item.image_path:
            pixbuf = load_image_from_cache(item.image_path)
            if pixbuf:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                content = Gdk.ContentProvider.new_for_value(texture)
                self.clipboard.set_content(content)
                print(f"Restored image: {item.preview}")
        elif item.item_type == ClipType.FILES and item.file_uris:
            # Restore file URIs to clipboard
            uri_list = "\n".join(item.file_uris)
            content = Gdk.ContentProvider.new_for_bytes(
                "text/uri-list",
                GLib.Bytes.new(uri_list.encode("utf-8"))
            )
            self.clipboard.set_content(content)
            print(f"Restored files: {item.preview}")

        self.close()

    def _populate_list(self) -> None:
        """Populate the list with items from store."""
        # Clear existing rows
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        # Get items (filtered or all)
        if self._current_filter:
            items = self.store.search_items(self._current_filter)
        else:
            items = self.store.get_all_items()

        # Add rows
        for item in items:
            row = ClipItemRow(item, on_delete=self._delete_item)
            self.listbox.append(row)

        # Show empty state or list
        if len(items) == 0:
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("list")
            # Select first row
            first_row = self.listbox.get_row_at_index(0)
            if first_row:
                self.listbox.select_row(first_row)

    def _on_store_changed(self) -> None:
        """Handle store updates."""
        self._populate_list()

    def present(self) -> None:
        """Show the window and focus search."""
        super().present()
        self.search_entry.grab_focus()
        self._populate_list()
