"""Settings dialog for ClipNote."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from typing import Callable, Optional

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .config import Config, ConfigManager
from .hotkey_manager import format_keybinding, parse_keybinding, validate_keybinding


class SettingsDialog(Adw.PreferencesWindow):
    """Settings/Preferences dialog for ClipNote."""

    def __init__(
        self,
        parent: Gtk.Window,
        config_manager: ConfigManager,
        hotkey_backend_name: Optional[str] = None,
        hotkey_registered: bool = False
    ):
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.config
        self.hotkey_backend_name = hotkey_backend_name or "Not Available"
        self.hotkey_registered = hotkey_registered

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Settings")
        self.set_default_size(500, 600)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the settings UI."""
        # ===== GENERAL PAGE =====
        general_page = Adw.PreferencesPage()
        general_page.set_title("General")
        general_page.set_icon_name("preferences-system-symbolic")

        # History group
        history_group = Adw.PreferencesGroup()
        history_group.set_title("Clipboard History")
        history_group.set_description("Configure how clipboard history is stored")

        # Max history items
        self.history_size_row = Adw.SpinRow.new_with_range(10, 500, 10)
        self.history_size_row.set_title("Maximum Items")
        self.history_size_row.set_subtitle("Number of clipboard items to keep")
        self.history_size_row.set_value(self.config.max_history_items)
        self.history_size_row.connect("notify::value", self._on_history_size_changed)
        history_group.add(self.history_size_row)

        # Auto-expire days
        self.auto_expire_row = Adw.SpinRow.new_with_range(0, 365, 1)
        self.auto_expire_row.set_title("Auto-Expire (Days)")
        self.auto_expire_row.set_subtitle("Delete items older than this (0 = never)")
        self.auto_expire_row.set_value(self.config.auto_expire_days)
        self.auto_expire_row.connect("notify::value", self._on_auto_expire_changed)
        history_group.add(self.auto_expire_row)

        general_page.add(history_group)

        # Behavior group
        behavior_group = Adw.PreferencesGroup()
        behavior_group.set_title("Behavior")
        behavior_group.set_description("Configure app behavior")

        # Close on paste
        self.close_on_paste_row = Adw.SwitchRow()
        self.close_on_paste_row.set_title("Close on Paste")
        self.close_on_paste_row.set_subtitle("Close window after pasting an item")
        self.close_on_paste_row.set_active(self.config.close_on_paste)
        self.close_on_paste_row.connect("notify::active", self._on_close_on_paste_changed)
        behavior_group.add(self.close_on_paste_row)

        # Clear on paste
        self.clear_on_paste_row = Adw.SwitchRow()
        self.clear_on_paste_row.set_title("Remove After Paste")
        self.clear_on_paste_row.set_subtitle("Remove item from history after pasting")
        self.clear_on_paste_row.set_active(self.config.clear_on_paste)
        self.clear_on_paste_row.connect("notify::active", self._on_clear_on_paste_changed)
        behavior_group.add(self.clear_on_paste_row)

        general_page.add(behavior_group)

        self.add(general_page)

        # ===== PRIVACY PAGE =====
        privacy_page = Adw.PreferencesPage()
        privacy_page.set_title("Privacy")
        privacy_page.set_icon_name("security-high-symbolic")

        # Privacy mode group
        privacy_group = Adw.PreferencesGroup()
        privacy_group.set_title("Privacy Mode")
        privacy_group.set_description("Control clipboard monitoring")

        # Private mode toggle
        self.private_mode_row = Adw.SwitchRow()
        self.private_mode_row.set_title("Private Mode")
        self.private_mode_row.set_subtitle("Pause clipboard monitoring temporarily")
        self.private_mode_row.set_active(self.config.private_mode)
        self.private_mode_row.connect("notify::active", self._on_private_mode_changed)
        privacy_group.add(self.private_mode_row)

        privacy_page.add(privacy_group)

        # Excluded apps group
        excluded_group = Adw.PreferencesGroup()
        excluded_group.set_title("Excluded Applications")
        excluded_group.set_description("Ignore clipboard content from these apps")

        # Add app button
        add_app_row = Adw.ActionRow()
        add_app_row.set_title("Add Application")
        add_app_row.set_subtitle("Add an app to the exclusion list")
        add_app_row.set_activatable(True)
        add_app_btn = Gtk.Button()
        add_app_btn.set_icon_name("list-add-symbolic")
        add_app_btn.set_valign(Gtk.Align.CENTER)
        add_app_btn.add_css_class("flat")
        add_app_btn.connect("clicked", self._on_add_excluded_app)
        add_app_row.add_suffix(add_app_btn)
        add_app_row.set_activatable_widget(add_app_btn)
        excluded_group.add(add_app_row)

        # List current excluded apps
        self.excluded_apps_group = excluded_group
        self._populate_excluded_apps()

        privacy_page.add(excluded_group)

        self.add(privacy_page)

        # ===== APPEARANCE PAGE =====
        appearance_page = Adw.PreferencesPage()
        appearance_page.set_title("Appearance")
        appearance_page.set_icon_name("applications-graphics-symbolic")

        # Display group
        display_group = Adw.PreferencesGroup()
        display_group.set_title("Display")
        display_group.set_description("Configure how items are displayed")

        # Show previews
        self.show_previews_row = Adw.SwitchRow()
        self.show_previews_row.set_title("Show Previews")
        self.show_previews_row.set_subtitle("Show image thumbnails in the list")
        self.show_previews_row.set_active(self.config.show_previews)
        self.show_previews_row.connect("notify::active", self._on_show_previews_changed)
        display_group.add(self.show_previews_row)

        # Compact mode
        self.compact_mode_row = Adw.SwitchRow()
        self.compact_mode_row.set_title("Compact Mode")
        self.compact_mode_row.set_subtitle("Use smaller row height for more items")
        self.compact_mode_row.set_active(self.config.compact_mode)
        self.compact_mode_row.connect("notify::active", self._on_compact_mode_changed)
        display_group.add(self.compact_mode_row)

        appearance_page.add(display_group)

        self.add(appearance_page)

        # ===== SHORTCUTS PAGE =====
        shortcuts_page = Adw.PreferencesPage()
        shortcuts_page.set_title("Shortcuts")
        shortcuts_page.set_icon_name("preferences-desktop-keyboard-shortcuts-symbolic")

        # Global hotkey group
        hotkey_group = Adw.PreferencesGroup()
        hotkey_group.set_title("Global Hotkey")
        hotkey_group.set_description("System-wide keyboard shortcut to open ClipNote")

        # Enable hotkey toggle
        self.hotkey_enabled_row = Adw.SwitchRow()
        self.hotkey_enabled_row.set_title("Enable Global Hotkey")
        self.hotkey_enabled_row.set_subtitle("Register a system-wide shortcut")
        self.hotkey_enabled_row.set_active(self.config.global_hotkey_enabled)
        self.hotkey_enabled_row.connect("notify::active", self._on_hotkey_enabled_changed)
        hotkey_group.add(self.hotkey_enabled_row)

        # Current hotkey display
        self.hotkey_row = Adw.ActionRow()
        self.hotkey_row.set_title("Shortcut")
        self._update_hotkey_display()

        change_btn = Gtk.Button(label="Change")
        change_btn.set_valign(Gtk.Align.CENTER)
        change_btn.connect("clicked", self._on_change_hotkey)
        self.hotkey_row.add_suffix(change_btn)
        hotkey_group.add(self.hotkey_row)

        shortcuts_page.add(hotkey_group)

        # Status group
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Status")
        status_group.set_description("Current hotkey backend and registration status")

        # Backend info
        backend_row = Adw.ActionRow()
        backend_row.set_title("Backend")
        backend_row.set_subtitle(self.hotkey_backend_name)
        status_group.add(backend_row)

        # Registration status
        self.status_row = Adw.ActionRow()
        self.status_row.set_title("Status")
        self._update_status_display()
        status_group.add(self.status_row)

        shortcuts_page.add(status_group)

        self.add(shortcuts_page)

        # ===== ABOUT PAGE =====
        about_page = Adw.PreferencesPage()
        about_page.set_title("About")
        about_page.set_icon_name("help-about-symbolic")

        about_group = Adw.PreferencesGroup()

        # App info
        app_info_row = Adw.ActionRow()
        app_info_row.set_title("ClipNote")
        app_info_row.set_subtitle("Clipboard History & Quick Notes for GNOME")

        # Version
        version_row = Adw.ActionRow()
        version_row.set_title("Version")
        version_row.set_subtitle("0.1.0 (Phase 2 MVP)")

        about_group.add(app_info_row)
        about_group.add(version_row)

        about_page.add(about_group)

        # Data management group
        data_group = Adw.PreferencesGroup()
        data_group.set_title("Data Management")

        # Clear all data
        clear_data_row = Adw.ActionRow()
        clear_data_row.set_title("Clear All Data")
        clear_data_row.set_subtitle("Delete all clipboard history and notes")
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.add_css_class("destructive-action")
        clear_btn.connect("clicked", self._on_clear_all_data)
        clear_data_row.add_suffix(clear_btn)
        data_group.add(clear_data_row)

        about_page.add(data_group)

        self.add(about_page)

    def _populate_excluded_apps(self) -> None:
        """Populate the excluded apps list."""
        for app_id in self.config.excluded_apps:
            self._add_excluded_app_row(app_id)

    def _add_excluded_app_row(self, app_id: str) -> None:
        """Add a row for an excluded app."""
        row = Adw.ActionRow()
        row.set_title(app_id)

        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("user-trash-symbolic")
        remove_btn.set_valign(Gtk.Align.CENTER)
        remove_btn.add_css_class("flat")
        remove_btn.connect("clicked", lambda b: self._on_remove_excluded_app(app_id, row))
        row.add_suffix(remove_btn)

        self.excluded_apps_group.add(row)

    def _on_history_size_changed(self, row: Adw.SpinRow, param) -> None:
        """Handle history size change."""
        value = int(row.get_value())
        self.config_manager.update(max_history_items=value)

    def _on_auto_expire_changed(self, row: Adw.SpinRow, param) -> None:
        """Handle auto-expire change."""
        value = int(row.get_value())
        self.config_manager.update(auto_expire_days=value)

    def _on_close_on_paste_changed(self, row: Adw.SwitchRow, param) -> None:
        """Handle close on paste change."""
        self.config_manager.update(close_on_paste=row.get_active())

    def _on_clear_on_paste_changed(self, row: Adw.SwitchRow, param) -> None:
        """Handle clear on paste change."""
        self.config_manager.update(clear_on_paste=row.get_active())

    def _on_private_mode_changed(self, row: Adw.SwitchRow, param) -> None:
        """Handle private mode change."""
        self.config_manager.update(private_mode=row.get_active())

    def _on_show_previews_changed(self, row: Adw.SwitchRow, param) -> None:
        """Handle show previews change."""
        self.config_manager.update(show_previews=row.get_active())

    def _on_compact_mode_changed(self, row: Adw.SwitchRow, param) -> None:
        """Handle compact mode change."""
        self.config_manager.update(compact_mode=row.get_active())

    def _on_add_excluded_app(self, button: Gtk.Button) -> None:
        """Show dialog to add excluded app."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Add Excluded Application",
        )

        entry = Gtk.Entry()
        entry.set_placeholder_text("e.g., org.keepassxc.KeePassXC")
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)

        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("add")

        def on_response(dialog, response):
            if response == "add":
                app_id = entry.get_text().strip()
                if app_id and app_id not in self.config.excluded_apps:
                    self.config_manager.add_excluded_app(app_id)
                    self._add_excluded_app_row(app_id)

        dialog.connect("response", on_response)
        dialog.present()

    def _on_remove_excluded_app(self, app_id: str, row: Adw.ActionRow) -> None:
        """Remove an app from the exclusion list."""
        self.config_manager.remove_excluded_app(app_id)
        self.excluded_apps_group.remove(row)

    def _on_clear_all_data(self, button: Gtk.Button) -> None:
        """Show confirmation dialog to clear all data."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Clear All Data?",
            body="This will permanently delete all clipboard history and notes. This action cannot be undone.",
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear All")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def on_response(dialog, response):
            if response == "clear":
                # Emit signal or callback to clear data
                print("Clearing all data...")
                # This will be handled by the parent window

        dialog.connect("response", on_response)
        dialog.present()

    def _update_hotkey_display(self) -> None:
        """Update the hotkey row subtitle with current binding."""
        keybinding = self.config.global_hotkey
        display_text = format_keybinding(keybinding)
        self.hotkey_row.set_subtitle(display_text)

    def _update_status_display(self) -> None:
        """Update the status row subtitle."""
        if not self.config.global_hotkey_enabled:
            self.status_row.set_subtitle("Disabled")
        elif self.hotkey_registered:
            self.status_row.set_subtitle("Registered")
        else:
            self.status_row.set_subtitle("Not registered (backend unavailable)")

    def _on_hotkey_enabled_changed(self, row: Adw.SwitchRow, param) -> None:
        """Handle hotkey enabled toggle."""
        self.config_manager.update(global_hotkey_enabled=row.get_active())
        self._update_status_display()

    def _on_change_hotkey(self, button: Gtk.Button) -> None:
        """Show dialog to change hotkey."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Change Shortcut",
            body="Press the new key combination, or type it manually.\nExamples: Super + V, Ctrl + Alt + V",
        )

        # Entry for manual input
        entry = Gtk.Entry()
        current_display = format_keybinding(self.config.global_hotkey)
        entry.set_text(current_display)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)

        # Key press handler
        key_controller = Gtk.EventControllerKey()

        def on_key_pressed(controller, keyval, keycode, state):
            # Build key combination from modifiers
            parts = []
            if state & Gdk.ModifierType.SUPER_MASK:
                parts.append("Super")
            if state & Gdk.ModifierType.CONTROL_MASK:
                parts.append("Ctrl")
            if state & Gdk.ModifierType.ALT_MASK:
                parts.append("Alt")
            if state & Gdk.ModifierType.SHIFT_MASK:
                parts.append("Shift")

            # Get key name
            key_name = Gdk.keyval_name(keyval)
            if key_name and key_name not in ("Super_L", "Super_R", "Control_L", "Control_R",
                                              "Alt_L", "Alt_R", "Shift_L", "Shift_R",
                                              "Meta_L", "Meta_R", "ISO_Level3_Shift"):
                if parts:  # Only if there's at least one modifier
                    parts.append(key_name.upper())
                    display = " + ".join(parts)
                    entry.set_text(display)
                    return True

            return False

        key_controller.connect("key-pressed", on_key_pressed)
        entry.add_controller(key_controller)

        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("apply", "Apply")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("apply")

        def on_response(dialog, response):
            if response == "apply":
                display_text = entry.get_text().strip()
                gtk_binding = parse_keybinding(display_text)

                if validate_keybinding(gtk_binding):
                    self.config_manager.update(global_hotkey=gtk_binding)
                    self._update_hotkey_display()
                    # Note: actual re-registration happens via config listener in main.py
                else:
                    # Show error
                    error_dialog = Adw.MessageDialog(
                        transient_for=self,
                        heading="Invalid Shortcut",
                        body=f"'{display_text}' is not a valid shortcut.\nUse format: Modifier + Key (e.g., Super + V)",
                    )
                    error_dialog.add_response("ok", "OK")
                    error_dialog.present()

        dialog.connect("response", on_response)
        dialog.present()
