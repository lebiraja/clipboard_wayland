"""Data model for clipboard items."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import uuid
import time


class ClipType(Enum):
    TEXT = "text"
    IMAGE = "image"


@dataclass
class ClipItem:
    """Represents a single clipboard entry."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    item_type: ClipType = ClipType.TEXT
    preview: str = ""
    text_content: Optional[str] = None
    image_path: Optional[str] = None
    content_hash: str = ""

    @classmethod
    def from_text(cls, text: str, content_hash: str = "") -> "ClipItem":
        """Create a ClipItem from text content."""
        preview = text[:100].replace("\n", " ").strip()
        if len(text) > 100:
            preview += "..."

        return cls(
            item_type=ClipType.TEXT,
            preview=preview,
            text_content=text,
            content_hash=content_hash,
        )

    @classmethod
    def from_image(cls, image_path: str, width: int, height: int, content_hash: str = "") -> "ClipItem":
        """Create a ClipItem from an image."""
        return cls(
            item_type=ClipType.IMAGE,
            preview=f"Image ({width}x{height})",
            image_path=image_path,
            content_hash=content_hash,
        )

    def get_display_text(self) -> str:
        """Get text for display in list."""
        return self.preview

    def get_relative_time(self) -> str:
        """Get human-readable relative timestamp."""
        delta = time.time() - self.timestamp

        if delta < 60:
            return "just now"
        elif delta < 3600:
            mins = int(delta / 60)
            return f"{mins}m ago"
        elif delta < 86400:
            hours = int(delta / 3600)
            return f"{hours}h ago"
        else:
            days = int(delta / 86400)
            return f"{days}d ago"
