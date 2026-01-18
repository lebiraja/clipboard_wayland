"""Data model for clipboard items."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from urllib.parse import unquote, urlparse
import os
import uuid
import time


class ClipType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILES = "files"


@dataclass
class ClipItem:
    """Represents a single clipboard entry."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    item_type: ClipType = ClipType.TEXT
    preview: str = ""
    text_content: Optional[str] = None
    image_path: Optional[str] = None
    file_uris: Optional[List[str]] = None
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

    @classmethod
    def from_files(cls, uris: List[str], content_hash: str = "") -> "ClipItem":
        """Create a ClipItem from file URIs."""
        # Extract filenames from URIs
        filenames = []
        for uri in uris:
            parsed = urlparse(uri)
            if parsed.scheme == "file":
                path = unquote(parsed.path)
                filenames.append(os.path.basename(path))
            else:
                filenames.append(uri)

        # Create preview text
        count = len(filenames)
        if count == 1:
            preview = filenames[0]
        elif count <= 3:
            preview = f"{count} files: {', '.join(filenames)}"
        else:
            preview = f"{count} files: {', '.join(filenames[:2])}, ..."

        # Truncate if too long
        if len(preview) > 100:
            preview = preview[:97] + "..."

        return cls(
            item_type=ClipType.FILES,
            preview=preview,
            file_uris=uris,
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
