"""Image handling utilities for clipboard images."""

import hashlib
from pathlib import Path
from typing import Optional, Tuple

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib


def texture_to_pixbuf(texture: Gdk.Texture) -> Optional[GdkPixbuf.Pixbuf]:
    """Convert a GdkTexture to a GdkPixbuf."""
    try:
        # Save texture to PNG bytes
        png_bytes = texture.save_to_png_bytes()

        # Load from bytes into pixbuf
        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(png_bytes.get_data())
        loader.close()

        return loader.get_pixbuf()
    except Exception as e:
        print(f"Error converting texture to pixbuf: {e}")
        return None


def get_pixbuf_hash(pixbuf: GdkPixbuf.Pixbuf) -> str:
    """Generate a hash for a pixbuf based on its pixel data."""
    try:
        pixels = pixbuf.get_pixels()
        return hashlib.sha256(pixels).hexdigest()[:16]
    except Exception:
        # Fallback to dimensions-based hash
        return f"{pixbuf.get_width()}x{pixbuf.get_height()}_{id(pixbuf)}"


def save_image_to_cache(pixbuf: GdkPixbuf.Pixbuf, cache_dir: Path) -> Tuple[str, str]:
    """
    Save a pixbuf to the cache directory.

    Returns:
        Tuple of (file_path, content_hash)
    """
    content_hash = get_pixbuf_hash(pixbuf)
    filename = f"{content_hash}.png"
    filepath = cache_dir / filename

    # Only save if doesn't exist
    if not filepath.exists():
        try:
            pixbuf.savev(str(filepath), "png", [], [])
        except Exception as e:
            print(f"Error saving image to cache: {e}")

    return str(filepath), content_hash


def load_image_from_cache(image_path: str) -> Optional[GdkPixbuf.Pixbuf]:
    """Load a pixbuf from the cache."""
    try:
        return GdkPixbuf.Pixbuf.new_from_file(image_path)
    except Exception as e:
        print(f"Error loading image from cache: {e}")
        return None


def create_thumbnail(pixbuf: GdkPixbuf.Pixbuf, size: int = 48) -> GdkPixbuf.Pixbuf:
    """Create a scaled thumbnail from a pixbuf."""
    width = pixbuf.get_width()
    height = pixbuf.get_height()

    if width > height:
        new_width = size
        new_height = max(1, int(height * size / width))
    else:
        new_height = size
        new_width = max(1, int(width * size / height))

    return pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)


def get_image_dimensions(pixbuf: GdkPixbuf.Pixbuf) -> Tuple[int, int]:
    """Get the dimensions of a pixbuf."""
    return pixbuf.get_width(), pixbuf.get_height()
