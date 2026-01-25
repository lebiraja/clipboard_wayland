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
from .config import ConfigManager
from .database import Database
from .emoji_data import EMOJI_DATA
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

        # Card container with styling
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.add_css_class("item-card")
        card.set_margin_start(4)
        card.set_margin_end(4)
        card.set_margin_top(2)
        card.set_margin_bottom(2)

        # Inner content box
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(8)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_hexpand(True)

        # Pin indicator (shown if pinned)
        if clip_item.pinned:
            pin_icon = Gtk.Image.new_from_icon_name("view-pin-symbolic")
            pin_icon.set_pixel_size(14)
            pin_icon.add_css_class("pin-indicator")
            pin_icon.add_css_class("accent")
            box.append(pin_icon)

        # Icon based on type
        icon_box = Gtk.Box()
        icon_box.set_size_request(40, 40)
        icon_box.set_valign(Gtk.Align.CENTER)
        icon_box.set_halign(Gtk.Align.CENTER)

        if clip_item.item_type == ClipType.TEXT:
            icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
            icon.set_pixel_size(22)
            icon.add_css_class("type-icon")
            icon_box.append(icon)
            box.append(icon_box)

            # Text content box
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            content_box.set_hexpand(True)
            content_box.set_valign(Gtk.Align.CENTER)

            label = Gtk.Label(label=clip_item.get_display_text())
            label.set_xalign(0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(50)
            label.add_css_class("preview-text")
            content_box.append(label)

            box.append(content_box)

        elif clip_item.item_type == ClipType.FILES:
            icon = Gtk.Image.new_from_icon_name("folder-symbolic")
            icon.set_pixel_size(22)
            icon.add_css_class("type-icon")
            icon_box.append(icon)
            box.append(icon_box)

            # File content box
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            content_box.set_hexpand(True)
            content_box.set_valign(Gtk.Align.CENTER)

            label = Gtk.Label(label=clip_item.get_display_text())
            label.set_xalign(0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(50)
            label.add_css_class("preview-text")
            content_box.append(label)

            box.append(content_box)

        else:  # IMAGE
            if clip_item.image_path:
                pixbuf = load_image_from_cache(clip_item.image_path)
                if pixbuf:
                    thumbnail = create_thumbnail(pixbuf, size=40)
                    texture = Gdk.Texture.new_for_pixbuf(thumbnail)
                    picture = Gtk.Picture.new_for_paintable(texture)
                    picture.set_size_request(40, 40)
                    picture.add_css_class("image-thumbnail")
                    picture.set_content_fit(Gtk.ContentFit.COVER)
                    box.append(picture)
                else:
                    icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
                    icon.set_pixel_size(22)
                    icon.add_css_class("type-icon")
                    icon_box.append(icon)
                    box.append(icon_box)
            else:
                icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
                icon.set_pixel_size(22)
                icon.add_css_class("type-icon")
                icon_box.append(icon)
                box.append(icon_box)

            # Image description
            content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            content_box.set_hexpand(True)
            content_box.set_valign(Gtk.Align.CENTER)

            label = Gtk.Label(label=clip_item.get_display_text())
            label.set_xalign(0)
            label.add_css_class("preview-text")
            content_box.append(label)

            box.append(content_box)

        # Right side: timestamp and action buttons
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        right_box.set_valign(Gtk.Align.CENTER)

        # Relative timestamp
        time_label = Gtk.Label(label=clip_item.get_relative_time())
        time_label.add_css_class("timestamp")
        time_label.add_css_class("dim-label")
        time_label.set_margin_end(8)
        right_box.append(time_label)

        # Action buttons container
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        action_box.add_css_class("action-buttons")

        # Pin button
        pin_btn = Gtk.Button()
        pin_btn.set_icon_name("pin-symbolic" if not clip_item.pinned else "unpin-symbolic")
        pin_btn.add_css_class("flat")
        pin_btn.add_css_class("circular")
        pin_btn.set_tooltip_text("Unpin" if clip_item.pinned else "Pin")
        pin_btn.connect("clicked", self._on_pin_clicked)
        action_box.append(pin_btn)

        # Delete button
        delete_btn = Gtk.Button()
        delete_btn.set_icon_name("user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("circular")
        delete_btn.add_css_class("destructive")
        delete_btn.set_tooltip_text("Delete")
        delete_btn.connect("clicked", self._on_delete_clicked)
        action_box.append(delete_btn)

        right_box.append(action_box)
        box.append(right_box)

        card.append(box)
        self.set_child(card)

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        """Handle delete button click."""
        if self._on_delete:
            self._on_delete(self.clip_item.id)

    def _on_pin_clicked(self, button: Gtk.Button) -> None:
        """Handle pin button click."""
        if self._on_pin:
            self._on_pin(self.clip_item.id)


# Note color palette
NOTE_COLORS = {
    'blue': '#3584e4',
    'green': '#33d17a',
    'yellow': '#f6d32d',
    'orange': '#ff7800',
    'red': '#e01b24',
    'purple': '#9141ac',
}


class NoteRow(Gtk.ListBoxRow):
    """A row widget representing a single note with inline editing."""

    def __init__(
        self,
        note: dict,
        on_delete: Optional[Callable[[str], None]] = None,
        on_save: Optional[Callable[[str, str, str], None]] = None,
        on_pin: Optional[Callable[[str], None]] = None,
        on_color_change: Optional[Callable[[str, str], None]] = None,
        on_expand: Optional[Callable[['NoteRow'], None]] = None
    ):
        super().__init__()
        self.note = note
        self._on_delete = on_delete
        self._on_save = on_save
        self._on_pin = on_pin
        self._on_color_change = on_color_change
        self._on_expand = on_expand
        self.is_expanded = False

        # Main container with color bar
        self.container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.container.add_css_class("note-row-container")
        self.container.set_margin_start(4)
        self.container.set_margin_end(4)
        self.container.set_margin_top(2)
        self.container.set_margin_bottom(2)

        # Color bar on left
        color = note.get("color", "blue") or "blue"
        self.color_bar = Gtk.Box()
        self.color_bar.set_size_request(4, -1)
        self.color_bar.add_css_class("note-color-bar")
        self.color_bar.add_css_class(f"note-color-bar-{color}")
        self.container.append(self.color_bar)

        # Stack for switching between collapsed and expanded views
        self.view_stack = Gtk.Stack()
        self.view_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.view_stack.set_transition_duration(150)
        self.view_stack.set_hexpand(True)

        # Build both views
        self.collapsed_view = self._build_collapsed_view()
        self.expanded_view = self._build_expanded_view()

        self.view_stack.add_named(self.collapsed_view, "collapsed")
        self.view_stack.add_named(self.expanded_view, "expanded")
        self.view_stack.set_visible_child_name("collapsed")

        self.container.append(self.view_stack)
        self.set_child(self.container)

    def _build_collapsed_view(self) -> Gtk.Box:
        """Build the collapsed view with larger preview."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(8)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_hexpand(True)

        # Pin indicator
        if self.note.get("pinned"):
            pin_icon = Gtk.Image.new_from_icon_name("view-pin-symbolic")
            pin_icon.set_pixel_size(14)
            pin_icon.add_css_class("pin-indicator")
            pin_icon.add_css_class("accent")
            box.append(pin_icon)

        # Note icon
        icon_box = Gtk.Box()
        icon_box.set_size_request(40, 40)
        icon_box.set_valign(Gtk.Align.START)
        icon_box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name("notepad-symbolic")
        icon.set_pixel_size(22)
        icon.add_css_class("type-icon")
        icon_box.append(icon)
        box.append(icon_box)

        # Content box (title + body preview)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content_box.set_hexpand(True)
        content_box.set_valign(Gtk.Align.CENTER)

        # Title
        self.title_label = Gtk.Label(label=self.note.get("title", "Untitled"))
        self.title_label.set_xalign(0)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_max_width_chars(50)
        self.title_label.add_css_class("note-title")
        content_box.append(self.title_label)

        # Body preview - now 200-250 chars with wrapping
        body = self.note.get("body", "")
        preview_length = 220
        body_preview = body[:preview_length].replace("\n", " ")
        if len(body) > preview_length:
            body_preview += "..."

        if body_preview:
            self.body_label = Gtk.Label(label=body_preview)
            self.body_label.set_xalign(0)
            self.body_label.set_wrap(True)
            self.body_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self.body_label.set_max_width_chars(70)
            self.body_label.set_lines(5)
            self.body_label.set_ellipsize(Pango.EllipsizeMode.END)
            self.body_label.add_css_class("note-body-preview-large")
            self.body_label.add_css_class("dim-label")
            content_box.append(self.body_label)

        box.append(content_box)

        # Action buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        action_box.add_css_class("action-buttons")
        action_box.set_valign(Gtk.Align.START)
        action_box.set_margin_top(4)

        # Color picker button
        color_btn = Gtk.MenuButton()
        color_btn.set_icon_name("color-select-symbolic")
        color_btn.add_css_class("flat")
        color_btn.add_css_class("circular")
        color_btn.set_tooltip_text("Change color")
        color_btn.set_popover(self._build_color_popover())
        action_box.append(color_btn)

        # Pin button
        pin_btn = Gtk.Button()
        pin_btn.set_icon_name("pin-symbolic" if not self.note.get("pinned") else "unpin-symbolic")
        pin_btn.add_css_class("flat")
        pin_btn.add_css_class("circular")
        pin_btn.set_tooltip_text("Unpin" if self.note.get("pinned") else "Pin")
        pin_btn.connect("clicked", self._on_pin_clicked)
        action_box.append(pin_btn)

        # Edit button
        edit_btn = Gtk.Button()
        edit_btn.set_icon_name("document-edit-symbolic")
        edit_btn.add_css_class("flat")
        edit_btn.add_css_class("circular")
        edit_btn.set_tooltip_text("Edit")
        edit_btn.connect("clicked", self._on_edit_clicked)
        action_box.append(edit_btn)

        # Delete button
        delete_btn = Gtk.Button()
        delete_btn.set_icon_name("user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.add_css_class("circular")
        delete_btn.add_css_class("destructive")
        delete_btn.set_tooltip_text("Delete")
        delete_btn.connect("clicked", self._on_delete_clicked)
        action_box.append(delete_btn)

        box.append(action_box)
        return box

    def _build_expanded_view(self) -> Gtk.Box:
        """Build the expanded inline editor view."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("note-editor-container")
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        # Title entry
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Enter title...")
        self.title_entry.add_css_class("note-editor-title")
        self.title_entry.set_text(self.note.get("title", ""))
        box.append(self.title_entry)

        # Body text view in scrolled window
        body_frame = Gtk.Frame()
        body_scrolled = Gtk.ScrolledWindow()
        body_scrolled.set_min_content_height(180)
        body_scrolled.set_vexpand(True)

        self.body_textview = Gtk.TextView()
        self.body_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.body_textview.set_top_margin(12)
        self.body_textview.set_bottom_margin(12)
        self.body_textview.set_left_margin(12)
        self.body_textview.set_right_margin(12)
        self.body_textview.add_css_class("note-editor-body")
        self.body_textview.get_buffer().set_text(self.note.get("body", ""))

        body_scrolled.set_child(self.body_textview)
        body_frame.set_child(body_scrolled)
        box.append(body_frame)

        # Action buttons (Cancel / Save)
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.add_css_class("note-editor-actions")
        action_box.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("flat")
        cancel_btn.connect("clicked", self._on_cancel_clicked)
        action_box.append(cancel_btn)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        action_box.append(save_btn)

        box.append(action_box)

        # Set up keyboard shortcuts
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        box.add_controller(key_controller)

        return box

    def _build_color_popover(self) -> Gtk.Popover:
        """Build the color picker popover."""
        popover = Gtk.Popover()
        popover.add_css_class("color-picker-popover")

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(3)
        flow.set_min_children_per_line(3)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(4)
        flow.set_column_spacing(4)

        current_color = self.note.get("color", "blue") or "blue"

        for color_name in NOTE_COLORS.keys():
            btn = Gtk.Button()
            btn.set_size_request(28, 28)
            btn.add_css_class("color-picker-button")
            btn.add_css_class(f"color-btn-{color_name}")
            if color_name == current_color:
                btn.add_css_class("selected")
            btn.set_tooltip_text(color_name.capitalize())
            btn.connect("clicked", self._on_color_selected, color_name, popover)
            flow.append(btn)

        popover.set_child(flow)
        return popover

    def expand(self) -> None:
        """Expand the note for inline editing."""
        if self.is_expanded:
            return

        self.is_expanded = True
        self.container.add_css_class("note-row-expanded")

        # Populate editor with current values
        self.title_entry.set_text(self.note.get("title", ""))
        self.body_textview.get_buffer().set_text(self.note.get("body", ""))

        self.view_stack.set_visible_child_name("expanded")

        # Focus the title entry
        GLib.idle_add(self.title_entry.grab_focus)

        # Notify parent
        if self._on_expand:
            self._on_expand(self)

    def collapse(self) -> None:
        """Collapse the editor without saving."""
        if not self.is_expanded:
            return

        self.is_expanded = False
        self.container.remove_css_class("note-row-expanded")
        self.view_stack.set_visible_child_name("collapsed")

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        """Handle keyboard shortcuts in expanded mode."""
        if keyval == Gdk.KEY_Escape:
            self.collapse()
            return True
        elif keyval == Gdk.KEY_Return and state & Gdk.ModifierType.CONTROL_MASK:
            self._save_and_collapse()
            return True
        return False

    def _save_and_collapse(self) -> None:
        """Save the note and collapse."""
        title = self.title_entry.get_text().strip() or "Untitled"
        buffer = self.body_textview.get_buffer()
        start, end = buffer.get_bounds()
        body = buffer.get_text(start, end, False)

        # Update local note data
        self.note["title"] = title
        self.note["body"] = body

        # Update collapsed view labels
        self.title_label.set_text(title)
        preview_length = 220
        body_preview = body[:preview_length].replace("\n", " ")
        if len(body) > preview_length:
            body_preview += "..."
        if hasattr(self, 'body_label'):
            self.body_label.set_text(body_preview)

        # Call save callback
        if self._on_save:
            self._on_save(self.note["id"], title, body)

        self.collapse()

    def _update_color_bar(self, color: str) -> None:
        """Update the color bar to a new color."""
        # Remove old color class
        for c in NOTE_COLORS.keys():
            self.color_bar.remove_css_class(f"note-color-bar-{c}")
        # Add new color class
        self.color_bar.add_css_class(f"note-color-bar-{color}")
        self.note["color"] = color

    def _on_color_selected(self, button: Gtk.Button, color: str, popover: Gtk.Popover) -> None:
        """Handle color selection."""
        self._update_color_bar(color)
        popover.popdown()
        if self._on_color_change:
            self._on_color_change(self.note["id"], color)

    def _on_delete_clicked(self, button: Gtk.Button) -> None:
        if self._on_delete:
            self._on_delete(self.note["id"])

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        self.expand()

    def _on_pin_clicked(self, button: Gtk.Button) -> None:
        if self._on_pin:
            self._on_pin(self.note["id"])

    def _on_cancel_clicked(self, button: Gtk.Button) -> None:
        self.collapse()

    def _on_save_clicked(self, button: Gtk.Button) -> None:
        self._save_and_collapse()


class EmptyState(Gtk.Box):
    """Empty state widget with icon and message."""

    def __init__(self, icon_name: str, title: str, subtitle: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_top(60)
        self.set_margin_bottom(60)
        self.add_css_class("empty-state")

        # Icon
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(64)
        icon.add_css_class("empty-state-icon")
        self.append(icon)

        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("empty-state-title")
        self.append(title_label)

        # Subtitle
        subtitle_label = Gtk.Label(label=subtitle)
        subtitle_label.add_css_class("empty-state-subtitle")
        subtitle_label.add_css_class("dim-label")
        self.append(subtitle_label)


class PopupWindow(Adw.ApplicationWindow):
    """Main popup window for ClipNote."""

    def __init__(
        self,
        app: Adw.Application,
        store: ClipStore,
        database: Optional[Database] = None,
        config_manager: Optional[ConfigManager] = None
    ):
        super().__init__(application=app)
        self.store = store
        self.db = database or Database()
        self.config_manager = config_manager or ConfigManager()
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        self._current_filter = ""
        self._current_tab = "clipboard"
        self._expanded_note_row: Optional[NoteRow] = None

        # Hotkey info (set by main.py after creation)
        self.hotkey_backend_name: Optional[str] = None
        self.hotkey_registered: bool = False

        self._build_ui()
        self._setup_keyboard()
        self._populate_list()
        self._populate_emoji_list()

        # Listen for store changes
        self.store.add_listener(self._on_store_changed)

        # Listen for config changes
        self.config_manager.add_listener(self._on_config_changed)

    def _build_ui(self) -> None:
        """Build the UI components."""
        self.set_title("ClipNote")
        self.set_default_size(550, 520)
        self.set_hide_on_close(True)
        self.add_css_class("clipnote-window")

        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)

        # Clear all button (clipboard tab)
        self.clear_btn = Gtk.Button()
        self.clear_btn.set_icon_name("user-trash-symbolic")
        self.clear_btn.set_tooltip_text("Clear all (keep pinned)")
        self.clear_btn.add_css_class("flat")
        self.clear_btn.connect("clicked", self._on_clear_all_clicked)
        header.pack_start(self.clear_btn)

        # Add note button (notes tab)
        self.add_note_btn = Gtk.Button()
        self.add_note_btn.set_icon_name("list-add-symbolic")
        self.add_note_btn.set_tooltip_text("Add new note")
        self.add_note_btn.add_css_class("flat")
        self.add_note_btn.add_css_class("suggested-action")
        self.add_note_btn.connect("clicked", self._on_add_note_clicked)
        self.add_note_btn.set_visible(False)
        header.pack_start(self.add_note_btn)

        # Search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search clipboard...")
        self.search_entry.set_hexpand(True)
        self.search_entry.set_max_width_chars(40)
        self.search_entry.add_css_class("search-entry")
        self.search_entry.connect("search-changed", self._on_search_changed)
        header.set_title_widget(self.search_entry)

        # Private mode indicator (end of header)
        self.private_mode_btn = Gtk.ToggleButton()
        self.private_mode_btn.set_icon_name("security-high-symbolic")
        self.private_mode_btn.set_tooltip_text("Private Mode (pauses clipboard monitoring)")
        self.private_mode_btn.add_css_class("flat")
        self.private_mode_btn.set_active(self.config_manager.config.private_mode)
        self.private_mode_btn.connect("toggled", self._on_private_mode_toggled)
        header.pack_end(self.private_mode_btn)

        # Settings button (end of header)
        settings_btn = Gtk.Button()
        settings_btn.set_icon_name("emblem-system-symbolic")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.add_css_class("flat")
        settings_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(settings_btn)

        main_box.append(header)

        # Tab bar container
        tab_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tab_container.set_halign(Gtk.Align.CENTER)
        tab_container.set_margin_top(8)
        tab_container.set_margin_bottom(12)

        # Tab bar with linked buttons
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tab_box.add_css_class("linked")
        tab_box.add_css_class("tab-bar")

        self.clipboard_tab_btn = Gtk.ToggleButton()
        clip_tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        clip_tab_icon = Gtk.Image.new_from_icon_name("edit-paste-symbolic")
        clip_tab_icon.set_pixel_size(16)
        clip_tab_content.append(clip_tab_icon)
        clip_tab_content.append(Gtk.Label(label="Clipboard"))
        self.clipboard_tab_btn.set_child(clip_tab_content)
        self.clipboard_tab_btn.set_active(True)
        self.clipboard_tab_btn.connect("toggled", self._on_clipboard_tab_toggled)
        tab_box.append(self.clipboard_tab_btn)

        self.notes_tab_btn = Gtk.ToggleButton()
        notes_tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        notes_tab_icon = Gtk.Image.new_from_icon_name("notepad-symbolic")
        notes_tab_icon.set_pixel_size(16)
        notes_tab_content.append(notes_tab_icon)
        notes_tab_content.append(Gtk.Label(label="Notes"))
        self.notes_tab_btn.set_child(notes_tab_content)
        self.notes_tab_btn.connect("toggled", self._on_notes_tab_toggled)
        tab_box.append(self.notes_tab_btn)

        self.emoji_tab_btn = Gtk.ToggleButton()
        emoji_tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        emoji_tab_icon = Gtk.Image.new_from_icon_name("face-smile-symbolic")
        emoji_tab_icon.set_pixel_size(16)
        emoji_tab_content.append(emoji_tab_icon)
        emoji_tab_content.append(Gtk.Label(label="Emojis"))
        self.emoji_tab_btn.set_child(emoji_tab_content)
        self.emoji_tab_btn.connect("toggled", self._on_emoji_tab_toggled)
        tab_box.append(self.emoji_tab_btn)

        tab_container.append(tab_box)
        main_box.append(tab_container)

        # Content stack
        self.content_stack = Gtk.Stack()
        self.content_stack.set_vexpand(True)
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.content_stack.set_transition_duration(200)

        # ===== CLIPBOARD TAB =====
        clipboard_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        clip_scrolled = Gtk.ScrolledWindow()
        clip_scrolled.set_vexpand(True)
        clip_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(False)
        self.listbox.add_css_class("clip-list")
        self.listbox.add_css_class("background")
        self.listbox.connect("row-activated", self._on_row_activated)
        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect("pressed", self._on_list_click)
        self.listbox.add_controller(gesture)
        clip_scrolled.set_child(self.listbox)

        # Empty state for clipboard
        self.clip_empty = EmptyState(
            "edit-paste-symbolic",
            "No clipboard history",
            "Copy something to get started"
        )

        self.clip_stack = Gtk.Stack()
        self.clip_stack.set_vexpand(True)
        self.clip_stack.add_named(clip_scrolled, "list")
        self.clip_stack.add_named(self.clip_empty, "empty")
        self.clip_stack.set_visible_child_name("empty")

        clipboard_box.append(self.clip_stack)
        self.content_stack.add_named(clipboard_box, "clipboard")

        # ===== NOTES TAB =====
        notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        notes_scrolled = Gtk.ScrolledWindow()
        notes_scrolled.set_vexpand(True)
        notes_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.notes_listbox = Gtk.ListBox()
        self.notes_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.notes_listbox.set_activate_on_single_click(False)
        self.notes_listbox.add_css_class("clip-list")
        self.notes_listbox.add_css_class("background")
        self.notes_listbox.connect("row-activated", self._on_note_row_activated)
        notes_gesture = Gtk.GestureClick()
        notes_gesture.set_button(1)
        notes_gesture.connect("pressed", self._on_notes_list_click)
        self.notes_listbox.add_controller(notes_gesture)
        notes_scrolled.set_child(self.notes_listbox)

        # Empty state for notes
        self.notes_empty = EmptyState(
            "notepad-symbolic",
            "No notes yet",
            "Click + to create a quick note"
        )

        self.notes_stack = Gtk.Stack()
        self.notes_stack.set_vexpand(True)
        self.notes_stack.add_named(notes_scrolled, "list")
        self.notes_stack.add_named(self.notes_empty, "empty")
        self.notes_stack.set_visible_child_name("empty")

        notes_box.append(self.notes_stack)
        self.content_stack.add_named(notes_box, "notes")

        # ===== EMOJI TAB =====
        emoji_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        emoji_scrolled = Gtk.ScrolledWindow()
        emoji_scrolled.set_vexpand(True)

        self.emoji_flowbox = Gtk.FlowBox()
        self.emoji_flowbox.set_valign(Gtk.Align.START)
        self.emoji_flowbox.set_max_children_per_line(10)
        self.emoji_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.emoji_flowbox.set_homogeneous(True)
        self.emoji_flowbox.add_css_class("emoji-flowbox")
        self.emoji_flowbox.set_margin_start(12)
        self.emoji_flowbox.set_margin_end(12)
        self.emoji_flowbox.set_margin_top(12)
        self.emoji_flowbox.set_margin_bottom(12)

        emoji_scrolled.set_child(self.emoji_flowbox)
        emoji_box.append(emoji_scrolled)
        self.content_stack.add_named(emoji_box, "emojis")

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
            if self._current_tab == "clipboard":
                self.notes_tab_btn.set_active(True)
            elif self._current_tab == "notes":
                self.emoji_tab_btn.set_active(True)
            else:
                self.clipboard_tab_btn.set_active(True)
            return True
        return False

    def _on_list_click(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        """Handle click on list - double-click to paste."""
        if n_press == 2:
            selected_row = self.listbox.get_selected_row()
            if selected_row and hasattr(selected_row, "clip_item"):
                self._restore_item(selected_row.clip_item)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Handle search text changes."""
        self._current_filter = entry.get_text()
        if self._current_tab == "clipboard":
            self._populate_list()
        elif self._current_tab == "notes":
            self._populate_notes_list()
        elif self._current_tab == "emojis":
            self._filter_emojis()

    def _on_row_activated(self, listbox: Gtk.ListBox, row) -> None:
        pass

    def _delete_item(self, item_id: str) -> None:
        """Delete an item from the store."""
        self.store.remove_item(item_id)

    def _pin_item(self, item_id: str) -> None:
        """Toggle pin status of an item."""
        self.store.toggle_pinned(item_id)

    def _on_clear_all_clicked(self, button: Gtk.Button) -> None:
        """Clear all non-pinned items."""
        self.store.clear(keep_pinned=True)

    def _restore_item(self, item: ClipItem) -> None:
        """Copy item back to clipboard."""
        try:
            if item.item_type == ClipType.TEXT and item.text_content:
                content = Gdk.ContentProvider.new_for_value(item.text_content)
                self.clipboard.set_content(content)
            elif item.item_type == ClipType.IMAGE and item.image_path:
                pixbuf = load_image_from_cache(item.image_path)
                if pixbuf:
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    content = Gdk.ContentProvider.new_for_value(texture)
                    self.clipboard.set_content(content)
            elif item.item_type == ClipType.FILES and item.file_uris:
                files = [Gio.File.new_for_uri(uri) for uri in item.file_uris]
                file_list = Gdk.FileList.new_from_list(files)
                content = Gdk.ContentProvider.new_for_value(file_list)
                self.clipboard.set_content(content)
        except Exception as e:
            print(f"Error restoring item: {e}")

        self.close()

    def _populate_list(self) -> None:
        """Populate the list with items from store."""
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        if self._current_filter:
            items = self.store.search_items(self._current_filter)
        else:
            items = self.store.get_all_items()

        for item in items:
            row = ClipItemRow(item, on_delete=self._delete_item, on_pin=self._pin_item)
            self.listbox.append(row)

        if len(items) == 0:
            self.clip_stack.set_visible_child_name("empty")
        else:
            self.clip_stack.set_visible_child_name("list")
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
        if button.get_active():
            self._current_tab = "clipboard"
            self.notes_tab_btn.set_active(False)
            self.emoji_tab_btn.set_active(False)
            self.content_stack.set_visible_child_name("clipboard")
            self.search_entry.set_placeholder_text("Search clipboard...")
            self.clear_btn.set_visible(True)
            self.add_note_btn.set_visible(False)
            self._populate_list()

    def _on_notes_tab_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active():
            self._current_tab = "notes"
            self.clipboard_tab_btn.set_active(False)
            self.emoji_tab_btn.set_active(False)
            self.content_stack.set_visible_child_name("notes")
            self.search_entry.set_placeholder_text("Search notes...")
            self.clear_btn.set_visible(False)
            self.add_note_btn.set_visible(True)
            self._populate_notes_list()

    def _on_emoji_tab_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active():
            self._current_tab = "emojis"
            self.clipboard_tab_btn.set_active(False)
            self.notes_tab_btn.set_active(False)
            self.content_stack.set_visible_child_name("emojis")
            self.search_entry.set_placeholder_text("Search emojis...")
            self.clear_btn.set_visible(False)
            self.add_note_btn.set_visible(False)
            self._filter_emojis()

    # ===== EMOJI METHODS =====

    def _populate_emoji_list(self) -> None:
        """Populate the emoji list."""
        for emoji in EMOJI_DATA:
            btn = Gtk.Button(label=emoji["char"])
            btn.add_css_class("emoji-button")
            btn.add_css_class("flat")
            # Store metadata for filtering
            btn.emoji_name = emoji["name"].lower()
            btn.emoji_keywords = [k.lower() for k in emoji["keywords"]]
            btn.emoji_char = emoji["char"]

            # Use partial to capture the emoji char in lambda/callback
            btn.connect("clicked", self._on_emoji_clicked, emoji["char"])
            self.emoji_flowbox.append(btn)

    def _filter_emojis(self) -> None:
        """Filter emojis based on search query."""
        query = self._current_filter.lower()
        child = self.emoji_flowbox.get_first_child()
        while child:
            # child is a Gtk.FlowBoxChild, child.get_child() is our Button
            btn = child.get_child()
            if isinstance(btn, Gtk.Button):
                visible = not query or (
                    query in btn.emoji_name or
                    query in btn.emoji_char or
                    any(query in k for k in btn.emoji_keywords)
                )
                child.set_visible(visible)
            child = child.get_next_sibling()

    def _on_emoji_clicked(self, button: Gtk.Button, emoji_char: str) -> None:
        """Handle emoji click."""
        content = Gdk.ContentProvider.new_for_value(emoji_char)
        self.clipboard.set_content(content)
        self.close()

    # ===== NOTES METHODS =====

    def _populate_notes_list(self) -> None:
        """Populate the notes list."""
        # Reset expanded note tracking
        self._expanded_note_row = None

        while True:
            row = self.notes_listbox.get_row_at_index(0)
            if row is None:
                break
            self.notes_listbox.remove(row)

        notes = self.db.get_all_notes()

        if self._current_filter:
            query = self._current_filter.lower()
            notes = [n for n in notes if query in n.get("title", "").lower() or query in n.get("body", "").lower()]

        for note in notes:
            row = NoteRow(
                note,
                on_delete=self._delete_note,
                on_save=self._save_note,
                on_pin=self._pin_note,
                on_color_change=self._change_note_color,
                on_expand=self._on_note_expand
            )
            self.notes_listbox.append(row)

        if len(notes) == 0:
            self.notes_stack.set_visible_child_name("empty")
        else:
            self.notes_stack.set_visible_child_name("list")
            first_row = self.notes_listbox.get_row_at_index(0)
            if first_row:
                self.notes_listbox.select_row(first_row)

    def _on_note_expand(self, note_row: NoteRow) -> None:
        """Handle note expansion - ensure only one is expanded at a time."""
        if self._expanded_note_row and self._expanded_note_row != note_row:
            self._expanded_note_row.collapse()
        self._expanded_note_row = note_row

    def _save_note(self, note_id: str, title: str, body: str) -> None:
        """Save a note (from inline editing)."""
        self.db.update_note(note_id, title, body)

    def _change_note_color(self, note_id: str, color: str) -> None:
        """Change a note's color."""
        self.db.update_note_color(note_id, color)

    def _on_add_note_clicked(self, button: Gtk.Button) -> None:
        self._show_new_note_dialog()

    def _show_new_note_dialog(self) -> None:
        """Show a dialog to create a new note."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="New Note",
        )

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)
        content_box.set_margin_start(8)
        content_box.set_margin_end(8)
        content_box.add_css_class("note-dialog-content")

        # Title entry
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_label = Gtk.Label(label="Title")
        title_label.set_xalign(0)
        title_label.add_css_class("dim-label")
        title_box.append(title_label)

        title_entry = Gtk.Entry()
        title_entry.set_placeholder_text("Enter title...")
        title_entry.add_css_class("note-title-entry")
        title_box.append(title_entry)
        content_box.append(title_box)

        # Body text view
        body_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body_label = Gtk.Label(label="Content")
        body_label.set_xalign(0)
        body_label.add_css_class("dim-label")
        body_box.append(body_label)

        body_frame = Gtk.Frame()
        body_scrolled = Gtk.ScrolledWindow()
        body_scrolled.set_min_content_height(180)
        body_scrolled.set_min_content_width(350)
        body_text = Gtk.TextView()
        body_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        body_text.set_top_margin(12)
        body_text.set_bottom_margin(12)
        body_text.set_left_margin(12)
        body_text.set_right_margin(12)
        body_text.add_css_class("note-body-view")
        body_scrolled.set_child(body_text)
        body_frame.set_child(body_scrolled)
        body_box.append(body_frame)
        content_box.append(body_box)

        # Color picker for new notes
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        color_box.set_margin_top(8)
        color_label = Gtk.Label(label="Color:")
        color_label.add_css_class("dim-label")
        color_box.append(color_label)

        selected_color = ["blue"]  # Use list to allow modification in nested function

        for color_name in NOTE_COLORS.keys():
            btn = Gtk.ToggleButton()
            btn.set_size_request(24, 24)
            btn.add_css_class("color-picker-button")
            btn.add_css_class(f"color-btn-{color_name}")
            btn.set_tooltip_text(color_name.capitalize())
            if color_name == "blue":
                btn.set_active(True)
                btn.add_css_class("selected")

            def on_color_toggle(button, color=color_name):
                if button.get_active():
                    selected_color[0] = color
                    # Deselect other buttons
                    child = color_box.get_first_child()
                    while child:
                        if isinstance(child, Gtk.ToggleButton) and child != button:
                            child.set_active(False)
                            child.remove_css_class("selected")
                        child = child.get_next_sibling()
                    button.add_css_class("selected")

            btn.connect("toggled", on_color_toggle)
            color_box.append(btn)

        content_box.append(color_box)
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

                note_id = str(uuid.uuid4())
                self.db.add_note(note_id, title, body, time.time(), selected_color[0])
                self._populate_notes_list()

        dialog.connect("response", on_response)
        dialog.present()

    def _delete_note(self, note_id: str) -> None:
        self.db.delete_note(note_id)
        self._populate_notes_list()

    def _pin_note(self, note_id: str) -> None:
        self.db.toggle_note_pinned(note_id)
        self._populate_notes_list()

    def _on_note_row_activated(self, listbox: Gtk.ListBox, row) -> None:
        pass

    def _on_notes_list_click(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if n_press == 2:
            selected_row = self.notes_listbox.get_selected_row()
            if selected_row and hasattr(selected_row, "note"):
                self._copy_note_to_clipboard(selected_row.note)

    def _copy_note_to_clipboard(self, note: dict) -> None:
        body = note.get("body", "")
        if body:
            content = Gdk.ContentProvider.new_for_value(body)
            self.clipboard.set_content(content)
        self.close()

    # ===== SETTINGS & CONFIG =====

    def _on_settings_clicked(self, button: Gtk.Button) -> None:
        """Open settings dialog."""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(
            self,
            self.config_manager,
            hotkey_backend_name=self.hotkey_backend_name,
            hotkey_registered=self.hotkey_registered
        )
        dialog.present()

    def _on_private_mode_toggled(self, button: Gtk.ToggleButton) -> None:
        """Toggle private mode."""
        self.config_manager.update(private_mode=button.get_active())

    def _on_config_changed(self, config) -> None:
        """Handle config changes."""
        # Update private mode button state
        self.private_mode_btn.set_active(config.private_mode)

        # Update UI based on config (e.g., compact mode)
        if config.private_mode:
            self.private_mode_btn.add_css_class("warning")
        else:
            self.private_mode_btn.remove_css_class("warning")
