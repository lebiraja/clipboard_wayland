"""Hotkey manager for global keyboard shortcut support.

Provides cross-platform hotkey registration for Wayland (GNOME) and X11.
"""

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, Gio, GLib


def detect_display_server() -> str:
    """Detect the display server type.

    Returns:
        'wayland', 'x11', or 'unknown'
    """
    # Method 1: Check XDG_SESSION_TYPE environment variable
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type in ("wayland", "x11"):
        return session_type

    # Method 2: Check WAYLAND_DISPLAY
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"

    # Method 3: Check GDK backend
    try:
        display = Gdk.Display.get_default()
        if display:
            backend_type = type(display).__name__
            if "Wayland" in backend_type:
                return "wayland"
            elif "X11" in backend_type:
                return "x11"
    except Exception:
        pass

    # Method 4: Check DISPLAY variable (X11 legacy)
    if os.environ.get("DISPLAY"):
        return "x11"

    return "unknown"


def get_desktop_environment() -> str:
    """Detect the desktop environment.

    Returns:
        'gnome', 'kde', 'xfce', or 'unknown'
    """
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in desktop:
        return "gnome"
    elif "kde" in desktop or "plasma" in desktop:
        return "kde"
    elif "xfce" in desktop:
        return "xfce"
    return "unknown"


class HotkeyBackend(ABC):
    """Abstract base class for hotkey backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name for display."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this backend is available on the current system."""
        pass

    @abstractmethod
    def register_hotkey(self, keybinding: str, callback: Callable[[], None]) -> bool:
        """Register a global hotkey.

        Args:
            keybinding: Key combination (e.g., "<Super>v", "<Control><Alt>v")
            callback: Function to call when hotkey is pressed

        Returns:
            True if registration was successful
        """
        pass

    @abstractmethod
    def unregister_hotkey(self, keybinding: str) -> bool:
        """Unregister a hotkey.

        Returns:
            True if unregistration was successful
        """
        pass

    @abstractmethod
    def get_current_binding(self) -> Optional[str]:
        """Get the currently registered keybinding, if any."""
        pass

    def cleanup(self) -> None:
        """Clean up resources."""
        pass


class GnomeHotkeyBackend(HotkeyBackend):
    """GNOME-based hotkey backend using custom keybindings.

    Works on both Wayland and X11 when running GNOME.
    """

    SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
    CUSTOM_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
    CUSTOM_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/clipnote/"

    def __init__(self, app_command: Optional[str] = None):
        self._app_command = app_command or self._get_default_command()
        self._callback: Optional[Callable[[], None]] = None

    @property
    def name(self) -> str:
        return "GNOME Custom Keybindings"

    @property
    def is_available(self) -> bool:
        """Check if GNOME settings schema is available."""
        try:
            schema_source = Gio.SettingsSchemaSource.get_default()
            if schema_source is None:
                return False
            schema = schema_source.lookup(self.SCHEMA, True)
            return schema is not None
        except Exception:
            return False

    def _get_default_command(self) -> str:
        """Get the command to launch ClipNote."""
        # Try to find run.py relative to this module
        module_dir = Path(__file__).parent.parent
        run_script = module_dir / "run.py"
        if run_script.exists():
            return f"python3 {run_script}"
        return "python3 -m clipnote"

    def register_hotkey(self, keybinding: str, callback: Callable[[], None]) -> bool:
        """Register hotkey via GNOME custom keybindings."""
        try:
            self._callback = callback

            # Get or create custom keybinding settings
            custom_settings = Gio.Settings.new_with_path(
                self.CUSTOM_SCHEMA, self.CUSTOM_PATH
            )

            # Set keybinding properties
            custom_settings.set_string("name", "ClipNote")
            custom_settings.set_string("command", self._app_command)
            custom_settings.set_string("binding", keybinding)

            # Add to custom-keybindings list if not already present
            media_keys = Gio.Settings.new(self.SCHEMA)
            existing = list(media_keys.get_strv("custom-keybindings"))
            if self.CUSTOM_PATH not in existing:
                existing.append(self.CUSTOM_PATH)
                media_keys.set_strv("custom-keybindings", existing)

            # Sync settings
            Gio.Settings.sync()

            print(f"GnomeHotkeyBackend: Registered {keybinding}")
            return True

        except Exception as e:
            print(f"GnomeHotkeyBackend: Failed to register hotkey: {e}")
            return False

    def unregister_hotkey(self, keybinding: str) -> bool:
        """Remove the custom keybinding."""
        try:
            # Remove from custom-keybindings list
            media_keys = Gio.Settings.new(self.SCHEMA)
            existing = list(media_keys.get_strv("custom-keybindings"))
            if self.CUSTOM_PATH in existing:
                existing.remove(self.CUSTOM_PATH)
                media_keys.set_strv("custom-keybindings", existing)

            # Reset the custom keybinding settings
            custom_settings = Gio.Settings.new_with_path(
                self.CUSTOM_SCHEMA, self.CUSTOM_PATH
            )
            custom_settings.reset("name")
            custom_settings.reset("command")
            custom_settings.reset("binding")

            Gio.Settings.sync()

            print(f"GnomeHotkeyBackend: Unregistered {keybinding}")
            return True

        except Exception as e:
            print(f"GnomeHotkeyBackend: Failed to unregister hotkey: {e}")
            return False

    def get_current_binding(self) -> Optional[str]:
        """Get the currently configured keybinding."""
        try:
            custom_settings = Gio.Settings.new_with_path(
                self.CUSTOM_SCHEMA, self.CUSTOM_PATH
            )
            binding = custom_settings.get_string("binding")
            return binding if binding else None
        except Exception:
            return None


class X11HotkeyBackend(HotkeyBackend):
    """X11-based hotkey backend using keybinder3 or python-xlib."""

    def __init__(self):
        self._keybinder = None
        self._xlib_display = None
        self._current_binding: Optional[str] = None
        self._callback: Optional[Callable[[], None]] = None
        self._event_check_id: Optional[int] = None
        self._backend_type = self._detect_backend()

    @property
    def name(self) -> str:
        if self._backend_type == "keybinder":
            return "X11 (keybinder3)"
        elif self._backend_type == "xlib":
            return "X11 (python-xlib)"
        return "X11 (unavailable)"

    @property
    def is_available(self) -> bool:
        return self._backend_type is not None

    def _detect_backend(self) -> Optional[str]:
        """Detect available X11 hotkey backend."""
        # Try keybinder3 first (more reliable)
        try:
            gi.require_version("Keybinder", "3.0")
            from gi.repository import Keybinder
            Keybinder.init()
            self._keybinder = Keybinder
            return "keybinder"
        except (ValueError, ImportError):
            pass

        # Try python-xlib
        try:
            from Xlib import display as xlib_display
            self._xlib_display = xlib_display.Display()
            return "xlib"
        except ImportError:
            pass

        return None

    def register_hotkey(self, keybinding: str, callback: Callable[[], None]) -> bool:
        """Register hotkey using available backend."""
        if self._backend_type == "keybinder":
            return self._register_keybinder(keybinding, callback)
        elif self._backend_type == "xlib":
            return self._register_xlib(keybinding, callback)
        return False

    def _register_keybinder(self, keybinding: str, callback: Callable[[], None]) -> bool:
        """Register using keybinder3."""
        try:
            # Convert GTK format to keybinder format if needed
            kb = keybinding.replace("<Super>", "<Mod4>")

            def wrapper(keystr, user_data):
                callback()

            success = self._keybinder.bind(kb, wrapper, None)
            if success:
                self._current_binding = keybinding
                self._callback = callback
                print(f"X11HotkeyBackend (keybinder): Registered {keybinding}")
            return success

        except Exception as e:
            print(f"X11HotkeyBackend (keybinder): Failed: {e}")
            return False

    def _register_xlib(self, keybinding: str, callback: Callable[[], None]) -> bool:
        """Register using python-xlib."""
        try:
            from Xlib import X, XK

            # Parse keybinding
            modifiers, keycode = self._parse_keybinding_xlib(keybinding)
            if keycode is None:
                print(f"X11HotkeyBackend (xlib): Invalid keybinding: {keybinding}")
                return False

            root = self._xlib_display.screen().root

            # Grab the key
            root.grab_key(
                keycode,
                modifiers,
                True,
                X.GrabModeAsync,
                X.GrabModeAsync
            )

            # Also grab with Num Lock and Caps Lock variations
            for extra_mod in [0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask]:
                try:
                    root.grab_key(keycode, modifiers | extra_mod, True,
                                  X.GrabModeAsync, X.GrabModeAsync)
                except Exception:
                    pass

            self._xlib_display.sync()

            self._current_binding = keybinding
            self._callback = callback
            self._keycode = keycode

            # Start event checking loop
            self._event_check_id = GLib.timeout_add(100, self._check_xlib_events)

            print(f"X11HotkeyBackend (xlib): Registered {keybinding}")
            return True

        except Exception as e:
            print(f"X11HotkeyBackend (xlib): Failed: {e}")
            return False

    def _parse_keybinding_xlib(self, keybinding: str):
        """Parse keybinding string to Xlib modifiers and keycode."""
        from Xlib import X, XK

        modifiers = 0
        key = keybinding

        # Parse modifiers
        modifier_map = {
            "<Super>": X.Mod4Mask,
            "<Control>": X.ControlMask,
            "<Alt>": X.Mod1Mask,
            "<Shift>": X.ShiftMask,
        }

        for mod_str, mod_mask in modifier_map.items():
            if mod_str in key:
                modifiers |= mod_mask
                key = key.replace(mod_str, "")

        # Get keycode
        key = key.lower()
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            return 0, None

        keycode = self._xlib_display.keysym_to_keycode(keysym)
        return modifiers, keycode

    def _check_xlib_events(self) -> bool:
        """Check for X11 key events."""
        from Xlib import X

        try:
            while self._xlib_display.pending_events():
                event = self._xlib_display.next_event()
                if event.type == X.KeyPress:
                    if event.detail == self._keycode and self._callback:
                        self._callback()
        except Exception as e:
            print(f"X11HotkeyBackend: Event check error: {e}")

        return True  # Continue timeout

    def unregister_hotkey(self, keybinding: str) -> bool:
        """Unregister the hotkey."""
        if self._backend_type == "keybinder" and self._current_binding:
            try:
                kb = self._current_binding.replace("<Super>", "<Mod4>")
                self._keybinder.unbind(kb)
                self._current_binding = None
                print(f"X11HotkeyBackend: Unregistered {keybinding}")
                return True
            except Exception as e:
                print(f"X11HotkeyBackend: Unbind failed: {e}")
                return False

        elif self._backend_type == "xlib":
            # Stop event loop
            if self._event_check_id:
                GLib.source_remove(self._event_check_id)
                self._event_check_id = None
            self._current_binding = None
            return True

        return False

    def get_current_binding(self) -> Optional[str]:
        return self._current_binding

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._event_check_id:
            GLib.source_remove(self._event_check_id)
            self._event_check_id = None

        if self._xlib_display:
            try:
                self._xlib_display.close()
            except Exception:
                pass


class FallbackHotkeyBackend(HotkeyBackend):
    """Fallback backend when no hotkey support is available."""

    @property
    def name(self) -> str:
        return "Not Available"

    @property
    def is_available(self) -> bool:
        return True  # Always "available" as fallback

    def register_hotkey(self, keybinding: str, callback: Callable[[], None]) -> bool:
        print("FallbackHotkeyBackend: No hotkey support available")
        return False

    def unregister_hotkey(self, keybinding: str) -> bool:
        return True

    def get_current_binding(self) -> Optional[str]:
        return None


class HotkeyManager:
    """Factory for creating appropriate hotkey backend."""

    @staticmethod
    def create_backend(
        display_server: Optional[str] = None,
        app_command: Optional[str] = None
    ) -> HotkeyBackend:
        """Create the appropriate hotkey backend.

        Args:
            display_server: Override display server detection
            app_command: Command to run when hotkey is pressed

        Returns:
            Appropriate HotkeyBackend instance
        """
        if display_server is None:
            display_server = detect_display_server()

        desktop_env = get_desktop_environment()

        print(f"HotkeyManager: Display server: {display_server}, Desktop: {desktop_env}")

        # For GNOME (works on both Wayland and X11)
        if desktop_env == "gnome":
            backend = GnomeHotkeyBackend(app_command)
            if backend.is_available:
                print("HotkeyManager: Using GNOME backend")
                return backend

        # For X11 (non-GNOME or GNOME X11 fallback)
        if display_server == "x11":
            backend = X11HotkeyBackend()
            if backend.is_available:
                print(f"HotkeyManager: Using {backend.name}")
                return backend

        # Fallback
        print("HotkeyManager: Using fallback (no hotkey support)")
        return FallbackHotkeyBackend()


def format_keybinding(keybinding: str) -> str:
    """Format keybinding for display.

    Args:
        keybinding: GTK-style binding like "<Super>v"

    Returns:
        Human-readable format like "Super + V"
    """
    result = keybinding
    result = result.replace("<Super>", "Super + ")
    result = result.replace("<Control>", "Ctrl + ")
    result = result.replace("<Alt>", "Alt + ")
    result = result.replace("<Shift>", "Shift + ")
    result = result.replace("><", " + <")  # Handle multiple modifiers
    result = result.strip(" +")
    # Capitalize the key
    if result and not result.endswith("+"):
        parts = result.rsplit(" ", 1)
        if len(parts) == 2:
            result = parts[0] + " " + parts[1].upper()
        else:
            result = result.upper()
    return result


def parse_keybinding(display_str: str) -> str:
    """Parse display format to GTK keybinding format.

    Args:
        display_str: Human-readable like "Super + V"

    Returns:
        GTK-style binding like "<Super>v"
    """
    result = display_str.lower()
    result = result.replace("super + ", "<Super>")
    result = result.replace("ctrl + ", "<Control>")
    result = result.replace("alt + ", "<Alt>")
    result = result.replace("shift + ", "<Shift>")
    result = result.replace(" + ", "")
    return result


def validate_keybinding(keybinding: str) -> bool:
    """Validate keybinding format.

    Args:
        keybinding: GTK-style binding like "<Super>v"

    Returns:
        True if valid format
    """
    import re
    # Must have at least one modifier and one key
    pattern = r"^(<(Super|Control|Alt|Shift)>)+[a-zA-Z0-9]$"
    return bool(re.match(pattern, keybinding, re.IGNORECASE))
