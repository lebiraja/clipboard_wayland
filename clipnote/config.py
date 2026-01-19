"""Configuration management for ClipNote."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Config:
    """Application configuration settings."""

    # History settings
    max_history_items: int = 100
    auto_expire_days: int = 0  # 0 = never expire

    # Privacy settings
    private_mode: bool = False
    excluded_apps: List[str] = field(default_factory=list)

    # UI settings
    show_previews: bool = True
    compact_mode: bool = False

    # Behavior settings
    close_on_paste: bool = True
    clear_on_paste: bool = False  # Clear from history after pasting

    # Hotkey settings
    global_hotkey_enabled: bool = True
    global_hotkey: str = "<Super>v"  # Default: Super+V

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        # Filter only valid fields
        valid_fields = {
            "max_history_items", "auto_expire_days", "private_mode",
            "excluded_apps", "show_previews", "compact_mode",
            "close_on_paste", "clear_on_paste",
            "global_hotkey_enabled", "global_hotkey"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class ConfigManager:
    """Manages loading and saving configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".config" / "clipnote" / "config.json"

        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._config = self._load_config()
        self._listeners: List[Callable[[Config], None]] = []

    def _load_config(self) -> Config:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                return Config.from_dict(data)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"ConfigManager: Error loading config: {e}")
                return Config()
        return Config()

    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self._config.to_dict(), f, indent=2)
            print(f"ConfigManager: Saved config to {self.config_path}")
        except Exception as e:
            print(f"ConfigManager: Error saving config: {e}")

    @property
    def config(self) -> Config:
        """Get current configuration."""
        return self._config

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save_config()
        self._notify_listeners()

    def add_listener(self, callback: Callable[[Config], None]) -> None:
        """Add a listener for config changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Config], None]) -> None:
        """Remove a config change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all listeners of config change."""
        for callback in self._listeners:
            callback(self._config)

    # Convenience methods for common operations

    def toggle_private_mode(self) -> bool:
        """Toggle private mode. Returns new state."""
        new_state = not self._config.private_mode
        self.update(private_mode=new_state)
        return new_state

    def add_excluded_app(self, app_id: str) -> None:
        """Add an app to the exclusion list."""
        if app_id not in self._config.excluded_apps:
            self._config.excluded_apps.append(app_id)
            self.save_config()
            self._notify_listeners()

    def remove_excluded_app(self, app_id: str) -> None:
        """Remove an app from the exclusion list."""
        if app_id in self._config.excluded_apps:
            self._config.excluded_apps.remove(app_id)
            self.save_config()
            self._notify_listeners()

    def is_app_excluded(self, app_id: str) -> bool:
        """Check if an app is in the exclusion list."""
        return app_id in self._config.excluded_apps
