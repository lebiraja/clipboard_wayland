"""Main popup window UI for ClipNote."""

import gi
import time
import uuid

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from typing import Callable, Optional

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

from .clip_item import ClipItem, ClipType
from .clip_store import ClipStore
from .database import Database
from .image_utils import create_thumbnail, load_image_from_cache


class ClipItemRow(Gtk.ListBoxRow):
    """A row widget representing a single clipboard item."""

    def __init__(
        self,
        clip_item: ClipItem,
        on_delete: Optional[Callable[[str], None]] = None,
        on_pin: Optional[Callable[[str], None]] = None
    ):
        super().__init__()
        self.clip_item = clip_item
        self._on_delete = on_delete
        self._on_pin = on_pin

        # Main horizontal box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Pin indicator (shown if pinned)
        if clip_item.pinned:
            pin_icon = Gtk.Image.new_from_icon_name("view-pin-symbolic")
            pin_icon.set_pixel_size(16)
            pin_icon.add_css_class("accent")
            box.append(pin_icon)

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
            label.set_max_width_chars(45)
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
            label.set_max_width_chars(45)
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
        time_label.set_margin_end(4)
        box.append(time_label)

        # Pin button
        pin_btn = Gtk.Button()
        pin_btn.set_icon_name("view-pin-symbolic" if not clip_item.pinned else "view-unpin-symbolic")
        pin_btn.add_css_class("flat")
        pin_btn.add_css_class("circular")
        pin_btn.set_tooltip_text("Unpin" if clip_item.pinned else "Pin")
        pin_btn.connect("clicked", self._on_pin_clicked)
        box.append(pin_btn)

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

    def _on_pin_clicked(self, button: Gtk.Button) -> None:
        """Handle pin button click."""
        if self._on_pin:
            self._on_pin(self.clip_item.id)


class NoteRow(Gtk.ListBoxRow):
    """A row widget representing a single note."""

    def __init__(
        self,
        note: dict,
        on_delete: Optional[Callable[[str], None]] = None,
        on_edit: Optional[Callable[[dict], None]] = None,
        on_pin: Optional[Callable[[str], None]] = None
    ):
        super().__init__()
        self.note = note
        self._on_delete = on_delete
        self._on_edit = on_edit
        self._on_pin = on_pin

        # Main horizontal box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Pin indicator (shown if pinned)
        if note.get("pinned"):
            pin_icon = Gtk.Image.new_from_icon_name("view-pin-symbolic")
            pin_icon.set_pixel_size(16)
            pin_icon.add_css_class("accent")
            box.append(pin_icon)

        # Note icon
        icon = Gtk.Image.new_from_icon_name("accessories-text-editor-symbolic")
        icon.set_pixel_size(24)
        box.append(icon)

        # Text content (title + preview of body)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)

        title_label = Gtk.Label(label=note.get("title", "Untitled"))
        title_label.set_xalign(0)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_max_width_chars(40)
        title_label.add_css_class("heading")
        text_box.append(title_label)

        body_preview = note.get("body", "")[:50].replace("\n", " ")
        if len(note.get("body", "")) > 50:
            body_preview += "..."
        body_label = Gtk.Label(label=body_preview)
        body_label.set_xalign(0)
        body_label.set_ellipsize(Pango.EllipsizeMode.END)
        body_label.set_max_width_chars(40)
        body_label.add_css_class("dim-label")
        text_box.append(body_label)

        box.append(text_box)

        # Pin button
        pin_btn = Gtk.Button()
        pin_btn.set_icon_name("view-pin-symbolic" if not note.get("pinned") else "view-unpin-symbolic")
        pin_btn.add_css_class("flat")
        pin_btn.add_css_class("circular")
        pin_btn.set_tooltip_text("Unpin" if note.get("pinned") else "Pin")
        pin_btn.connect("clicked", self._on_pin_clicked)
        box.append(pin_btn)

        # Edit button
        edit_btn = Gtk.Button()
        edit_btn.set_icon_name("document-edit-symbolic")
        edit_btn.add_css_class("flat")
        edit_btn.add_css_class("circular")
        edit_btn.set_tooltip_text("Edit")
        edit_btn.connect("clicked", self._on_edit_clicked)
        box.append(edit_btn)

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
            self._on_delete(self.note["id"])

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        """Handle edit button click."""
        if self._on_edit:
            self._on_edit(self.note)

    def _on_pin_clicked(self, button: Gtk.Button) -> None:
        """Handle pin button click."""
        if self._on_pin:
            self._on_pin(self.note["id"])


class PopupWindow(Adw.ApplicationWindow):
    """Main popup window for ClipNote."""

    def __init__(self, app: Adw.Application, store: ClipStore, database: Optional[Database] = None):
        super().__init__(application=app)
        self.store = store
        self.db = database or Database()
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        self._current_filter = ""
        self._current_tab = "clipboard"  # "clipboard" or "notes"

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

        # Clear all button (start of header)
        self.clear_btn = Gtk.Button()
        self.clear_btn.set_icon_name("user-trash-symbolic")
        self.clear_btn.set_tooltip_text("Clear all (keep pinned)")
        self.clear_btn.connect("clicked", self._on_clear_all_clicked)
        header.pack_start(self.clear_btn)

        # Add note button (for notes tab)
        self.add_note_btn = Gtk.Button()
        self.add_note_btn.set_icon_name("list-add-symbolic")
        self.add_note_btn.set_tooltip_text("Add new note")
        self.add_note_btn.connect("clicked", self._on_add_note_clicked)
        self.add_note_btn.set_visible(False)  # Hidden by default
        header.pack_start(self.add_note_btn)

        # Search entry in header
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search clipboard history...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        header.set_title_widget(self.search_entry)

        main_box.append(header)

        # Tab bar for switching between Clipboard and Notes
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tab_box.add_css_class("linked")
        tab_box.set_halign(Gtk.Align.CENTER)
        tab_box.set_margin_top(8)
        tab_box.set_margin_bottom(8)

        self.clipboard_tab_btn = Gtk.ToggleButton(label="Clipboard")
        self.clipboard_tab_btn.set_active(True)
        self.clipboard_tab_btn.connect("toggled", self._on_clipboard_tab_toggled)
        tab_box.append(self.clipboard_tab_btn)

        self.notes_tab_btn = Gtk.ToggleButton(label="Notes")
        self.notes_tab_btn.connect("toggled", self._on_notes_tab_toggled)
        tab_box.append(self.notes_tab_btn)

        main_box.append(tab_box)

        # Content stack for clipboard vs notes
        self.content_stack = Gtk.Stack()
        self.content_stack.set_vexpand(True)
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # ===== CLIPBOARD TAB =====
        clipboard_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Scrolled window for clipboard list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # List box for clipboard items
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(False)
        self.listbox.add_css_class("boxed-list")
        self.listbox.connect("row-activated", self._on_row_activated)
        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect("pressed", self._on_list_click)
        self.listbox.add_controller(gesture)
        scrolled.set_child(self.listbox)

        # Empty state for clipboard
        self.clip_empty_label = Gtk.Label(label="No clipboard history yet.\nCopy something to get started.")
        self.clip_empty_label.add_css_class("dim-label")
        self.clip_empty_label.set_margin_top(50)
        self.clip_empty_label.set_justify(Gtk.Justification.CENTER)

        # Stack for clipboard empty state vs list
        self.clip_stack = Gtk.Stack()
        self.clip_stack.set_vexpand(True)
        self.clip_stack.add_named(scrolled, "list")
        self.clip_stack.add_named(self.clip_empty_label, "empty")
        self.clip_stack.set_visible_child_name("empty")

        clipboard_box.append(self.clip_stack)
        self.content_stack.add_named(clipboard_box, "clipboard")

        # ===== NOTES TAB =====
        notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Scrolled window for notes list
        notes_scrolled = Gtk.ScrolledWindow()
        notes_scrolled.set_vexpand(True)
        notes_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # List box for notes
        self.notes_listbox = Gtk.ListBox()
        self.notes_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.notes_listbox.set_activate_on_single_click(False)
        self.notes_listbox.add_css_class("boxed-list")
        self.notes_listbox.connect("row-activated", self._on_note_row_activated)
        notes_gesture = Gtk.GestureClick()
        notes_gesture.set_button(1)
        notes_gesture.connect("pressed", self._on_notes_list_click)
        self.notes_listbox.add_controller(notes_gesture)
        notes_scrolled.set_child(self.notes_listbox)

        # Empty state for notes
        self.notes_empty_label = Gtk.Label(label="No notes yet.\nClick + to add a note.")
        self.notes_empty_label.add_css_class("dim-label")
        self.notes_empty_label.set_margin_top(50)
        self.notes_empty_label.set_justify(Gtk.Justification.CENTER)

        # Stack for notes empty state vs list
        self.notes_stack = Gtk.Stack()
        self.notes_stack.set_vexpand(True)
        self.notes_stack.add_named(notes_scrolled, "list")
        self.notes_stack.add_named(self.notes_empty_label, "empty")
        self.notes_stack.set_visible_child_name("empty")

        notes_box.append(self.notes_stack)
        self.content_stack.add_named(notes_box, "notes")

        main_box.append(self.content_stack)

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
            if self._current_tab == "clipboard":
                selected_row = self.listbox.get_selected_row()
                if selected_row and hasattr(selected_row, "clip_item"):
                    self._restore_item(selected_row.clip_item)
            else:
                selected_row = self.notes_listbox.get_selected_row()
                if selected_row and hasattr(selected_row, "note"):
                    self._copy_note_to_clipboard(selected_row.note)
            return True
        elif keyval == Gdk.KEY_Delete:
            # Delete key - delete selected item
            if self._current_tab == "clipboard":
                selected_row = self.listbox.get_selected_row()
                if selected_row and hasattr(selected_row, "clip_item"):
                    self._delete_item(selected_row.clip_item.id)
            else:
                selected_row = self.notes_listbox.get_selected_row()
                if selected_row and hasattr(selected_row, "note"):
                    self._delete_note(selected_row.note["id"])
            return True
        elif keyval == Gdk.KEY_Tab:
            # Tab key - switch between tabs
            if self._current_tab == "clipboard":
                self.notes_tab_btn.set_active(True)
            else:
                self.clipboard_tab_btn.set_active(True)
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
        if self._current_tab == "clipboard":
            self._populate_list()
        else:
            self._populate_notes_list()

    def _on_row_activated(self, listbox: Gtk.ListBox, row) -> None:
        """Handle row activation - only triggers on Enter key, not single click."""
        # This is called when Enter is pressed on a row
        # We handle this via keyboard handler instead, so do nothing here
        pass

    def _delete_item(self, item_id: str) -> None:
        """Delete an item from the store."""
        self.store.remove_item(item_id)
        print(f"Deleted item: {item_id}")

    def _pin_item(self, item_id: str) -> None:
        """Toggle pin status of an item."""
        new_state = self.store.toggle_pinned(item_id)
        print(f"{'Pinned' if new_state else 'Unpinned'} item: {item_id}")

    def _on_clear_all_clicked(self, button: Gtk.Button) -> None:
        """Clear all non-pinned items."""
        count = self.store.clear(keep_pinned=True)
        print(f"Cleared {count} items")

    def _restore_item(self, item: ClipItem) -> None:
        """Copy item back to clipboard."""
        try:
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
                # Restore file URIs to clipboard using Gio.File objects
                files = [Gio.File.new_for_uri(uri) for uri in item.file_uris]
                file_list = Gdk.FileList.new_from_list(files)
                content = Gdk.ContentProvider.new_for_value(file_list)
                self.clipboard.set_content(content)
                print(f"Restored files: {item.preview}")
        except Exception as e:
            print(f"Error restoring item: {e}")

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
            row = ClipItemRow(item, on_delete=self._delete_item, on_pin=self._pin_item)
            self.listbox.append(row)

        # Show empty state or list
        if len(items) == 0:
            self.clip_stack.set_visible_child_name("empty")
        else:
            self.clip_stack.set_visible_child_name("list")
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
        if self._current_tab == "notes":
            self._populate_notes_list()

    # ===== TAB SWITCHING =====

    def _on_clipboard_tab_toggled(self, button: Gtk.ToggleButton) -> None:
        """Handle clipboard tab toggle."""
        if button.get_active():
            self._current_tab = "clipboard"
            self.notes_tab_btn.set_active(False)
            self.content_stack.set_visible_child_name("clipboard")
            self.search_entry.set_placeholder_text("Search clipboard history...")
            self.clear_btn.set_visible(True)
            self.add_note_btn.set_visible(False)
            self._populate_list()

    def _on_notes_tab_toggled(self, button: Gtk.ToggleButton) -> None:
        """Handle notes tab toggle."""
        if button.get_active():
            self._current_tab = "notes"
            self.clipboard_tab_btn.set_active(False)
            self.content_stack.set_visible_child_name("notes")
            self.search_entry.set_placeholder_text("Search notes...")
            self.clear_btn.set_visible(False)
            self.add_note_btn.set_visible(True)
            self._populate_notes_list()

    # ===== NOTES METHODS =====

    def _populate_notes_list(self) -> None:
        """Populate the notes list."""
        # Clear existing rows
        while True:
            row = self.notes_listbox.get_row_at_index(0)
            if row is None:
                break
            self.notes_listbox.remove(row)

        # Get notes from database
        notes = self.db.get_all_notes()

        # Filter if search is active
        if self._current_filter:
            query = self._current_filter.lower()
            notes = [n for n in notes if query in n.get("title", "").lower() or query in n.get("body", "").lower()]

        # Add rows
        for note in notes:
            row = NoteRow(
                note,
                on_delete=self._delete_note,
                on_edit=self._edit_note,
                on_pin=self._pin_note
            )
            self.notes_listbox.append(row)

        # Show empty state or list
        if len(notes) == 0:
            self.notes_stack.set_visible_child_name("empty")
        else:
            self.notes_stack.set_visible_child_name("list")
            # Select first row
            first_row = self.notes_listbox.get_row_at_index(0)
            if first_row:
                self.notes_listbox.select_row(first_row)

    def _on_add_note_clicked(self, button: Gtk.Button) -> None:
        """Show dialog to add a new note."""
        self._show_note_dialog(None)

    def _edit_note(self, note: dict) -> None:
        """Show dialog to edit an existing note."""
        self._show_note_dialog(note)

    def _show_note_dialog(self, note: Optional[dict]) -> None:
        """Show a dialog to create or edit a note."""
        is_edit = note is not None

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Edit Note" if is_edit else "New Note",
        )

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)

        # Title entry
        title_entry = Gtk.Entry()
        title_entry.set_placeholder_text("Title")
        if is_edit:
            title_entry.set_text(note.get("title", ""))
        content_box.append(title_entry)

        # Body text view
        body_frame = Gtk.Frame()
        body_scrolled = Gtk.ScrolledWindow()
        body_scrolled.set_min_content_height(150)
        body_scrolled.set_min_content_width(300)
        body_text = Gtk.TextView()
        body_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        body_text.set_top_margin(8)
        body_text.set_bottom_margin(8)
        body_text.set_left_margin(8)
        body_text.set_right_margin(8)
        if is_edit:
            body_text.get_buffer().set_text(note.get("body", ""))
        body_scrolled.set_child(body_text)
        body_frame.set_child(body_scrolled)
        content_box.append(body_frame)

        dialog.set_extra_child(content_box)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")

        def on_response(dialog, response):
            if response == "save":
                title = title_entry.get_text().strip() or "Untitled"
                buffer = body_text.get_buffer()
                start, end = buffer.get_bounds()
                body = buffer.get_text(start, end, False)

                if is_edit:
                    self.db.update_note(note["id"], title, body)
                    print(f"Updated note: {title}")
                else:
                    note_id = str(uuid.uuid4())
                    self.db.add_note(note_id, title, body, time.time())
                    print(f"Created note: {title}")

                self._populate_notes_list()

        dialog.connect("response", on_response)
        dialog.present()

    def _delete_note(self, note_id: str) -> None:
        """Delete a note."""
        self.db.delete_note(note_id)
        print(f"Deleted note: {note_id}")
        self._populate_notes_list()

    def _pin_note(self, note_id: str) -> None:
        """Toggle pin status of a note."""
        new_state = self.db.toggle_note_pinned(note_id)
        print(f"{'Pinned' if new_state else 'Unpinned'} note: {note_id}")
        self._populate_notes_list()

    def _on_note_row_activated(self, listbox: Gtk.ListBox, row) -> None:
        """Handle note row activation."""
        pass

    def _on_notes_list_click(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        """Handle click on notes list - double-click to copy note body."""
        if n_press == 2:  # Double-click
            selected_row = self.notes_listbox.get_selected_row()
            if selected_row and hasattr(selected_row, "note"):
                self._copy_note_to_clipboard(selected_row.note)

    def _copy_note_to_clipboard(self, note: dict) -> None:
        """Copy note body to clipboard."""
        body = note.get("body", "")
        if body:
            content = Gdk.ContentProvider.new_for_value(body)
            self.clipboard.set_content(content)
            print(f"Copied note to clipboard: {note.get('title', 'Untitled')}")
        self.close()
