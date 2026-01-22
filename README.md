# ClipNote

A modern, lightweight clipboard manager for Linux with support for text, images, and files. Built with GTK4 and Libadwaita for a native GNOME experience.

## Features

### 📋 Enhanced Clipboard History
- **Automatic tracking** of clipboard content (text, images, and files)
- **Persistent storage** using SQLite database
- **Duplicate detection** with content hashing
- **Search functionality** for quick filtering
- **Pin important items** to keep them at the top
- **Smart timestamps** showing relative time (e.g., "2 mins ago")

### 🖼️ Multi-format Support
- **Text**: Full text content with preview truncation
- **Images**: PNG/JPEG support with thumbnail previews and caching
- **Files**: File URI tracking with metadata

### 💾 Data Persistence
- SQLite database for reliable storage
- Image caching in `~/.cache/clipnote/images/`
- Database stored in `~/.local/share/clipnote/clipnote.db`
- Automatic duplicate prevention using content hashing

### 🎨 Modern UI
- Built with **GTK4** and **Libadwaita**
- Clean, native GNOME appearance
- Keyboard-first navigation
- Pin/unpin items
- Quick delete functionality
- Search as you type

## Architecture

### Core Components

```
clipnote/
├── main.py              # Application entry point and GTK app
├── clipboard_watcher.py # Monitors clipboard changes
├── clip_store.py        # In-memory store with database sync
├── clip_item.py         # Data model for clipboard items
├── database.py          # SQLite persistence layer
├── popup_window.py      # Main UI window
└── image_utils.py       # Image handling utilities
```

### Component Details

#### 1. **ClipNoteApp** ([main.py](clipnote/main.py))
- Main GTK4/Adwaita application
- Manages application lifecycle
- Initializes core components
- Handles window activation and shutdown

#### 2. **ClipboardWatcher** ([clipboard_watcher.py](clipnote/clipboard_watcher.py))
- Monitors system clipboard for changes
- Handles async content reading (text, images, files)
- Generates content hashes for duplicate detection
- Manages image caching
- Supports multiple MIME types

#### 3. **ClipStore** ([clip_store.py](clipnote/clip_store.py))
- In-memory clipboard item management
- Interfaces with database for persistence
- Implements observer pattern for UI updates
- Handles search, filtering, and item operations
- Enforces max items limit (default: 100)

#### 4. **Database** ([database.py](clipnote/database.py))
- SQLite-based persistence layer
- CRUD operations for clips and notes
- Full-text search capabilities
- Pin/unpin functionality
- Timestamp management for duplicate updates

#### 5. **PopupWindow** ([popup_window.py](clipnote/popup_window.py))
- Main UI window with GTK4/Libadwaita
- Displays clipboard history in list format
- Search functionality
- Keyboard shortcuts (ESC to close, Enter to paste)
- Row actions: pin, delete, restore to clipboard

#### 6. **Image Utilities** ([image_utils.py](clipnote/image_utils.py))
- Texture to Pixbuf conversion
- Image hashing for deduplication
- Thumbnail generation
- Cache management
- PNG encoding/decoding

## Installation

### System Requirements
- Python 3.8 or higher
- GTK4
- Libadwaita
- GObject Introspection bindings

### Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adwaita-1 gir1.2-gdkpixbuf-2.0
```

#### Fedora
```bash
sudo dnf install python3-gobject gtk4 libadwaita
```

#### Arch Linux
```bash
sudo pacman -S python-gobject gtk4 libadwaita
```

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install PyGObject>=3.42.0
```

## Usage

### Running the Application

```bash
./run.py
```

Or:
```bash
python3 run.py
```

### Keyboard Shortcuts

- **Escape**: Close the window
- **Enter**: Restore selected item to clipboard and close
- **Double-click**: Restore item to clipboard
- **Type to search**: Filter clipboard history in real-time

### UI Actions

- **Pin icon**: Pin/unpin items to keep them at the top
- **Delete icon**: Remove items from history
- **Clear all button**: Delete all items (keeps pinned ones)

## Data Storage

### Database Location
```
~/.local/share/clipnote/clipnote.db
```

### Image Cache
```
~/.cache/clipnote/images/
```

Images are stored with SHA256 hash-based filenames to prevent duplicates.

## Configuration

### Maximum Items
Default: 100 items in history

To change, modify the `ClipStore` initialization in [main.py](clipnote/main.py):
```python
self.store = ClipStore(max_items=200)  # Change to desired limit
```

### Cache Directory
To use a custom cache directory, modify the `cache_dir` in [main.py](clipnote/main.py):
```python
self.cache_dir = Path.home() / ".custom" / "path"
```

## Development

### Project Structure
```
clipboard/
├── run.py                # Launcher script
├── requirements.txt      # Python dependencies
├── clipnote/            # Main package
│   ├── __init__.py
│   ├── main.py          # Application entry point
│   ├── clipboard_watcher.py
│   ├── clip_store.py
│   ├── clip_item.py
│   ├── database.py
│   ├── popup_window.py
│   └── image_utils.py
├── clipnote_report.md   # Technical design documentation
├── .gitignore
└── README.md
```

### Key Design Patterns

#### Observer Pattern
`ClipStore` implements an observer pattern where `PopupWindow` subscribes to changes:
```python
self.store.add_listener(self._on_store_changed)
```

#### Async/Await
Clipboard reading uses GTK's async API to prevent blocking:
```python
self.clipboard.read_text_async(None, self._on_text_ready)
```

#### Content Hashing
Prevents duplicates by comparing SHA256 hashes:
```python
content_hash = hashlib.sha256(content).hexdigest()[:16]
```

### Adding New Features

#### To add a new clipboard format:
1. Add MIME type check in `ClipboardWatcher._process_clipboard_content()`
2. Create async reader method (e.g., `_read_format_async()`)
3. Add callback handler (e.g., `_on_format_ready()`)
4. Create new `ClipType` in [clip_item.py](clipnote/clip_item.py)
5. Update UI rendering in `ClipItemRow` in [popup_window.py](clipnote/popup_window.py)

## Database Schema

### Clips Table
```sql
CREATE TABLE clips (
    id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    item_type TEXT NOT NULL,
    preview TEXT NOT NULL,
    text_content TEXT,
    image_path TEXT,
    file_uris TEXT,
    content_hash TEXT,
    pinned INTEGER DEFAULT 0
)
```

### Notes Table
```sql
CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    pinned INTEGER DEFAULT 0
)
```

### Indexes
- `idx_clips_timestamp`: Speeds up timestamp-based queries
- `idx_clips_pinned`: Optimizes pinned + timestamp ordering

## Testing

### Manual Testing Checklist
- [ ] Copy text and verify it appears in history
- [ ] Copy image (screenshot) and verify thumbnail
- [ ] Copy files from file manager
- [ ] Search functionality works
- [ ] Pin/unpin items
- [ ] Delete items
- [ ] Clear all (verify pinned items remain)
- [ ] Restore item to clipboard
- [ ] Keyboard shortcuts work
- [ ] Application survives clipboard changes while closed
- [ ] Duplicate detection works

## Known Limitations

1. **Maximum items**: Currently limited to 100 items (configurable)
2. **Image formats**: Only PNG and JPEG are fully supported
3. **File operations**: Tracks file URIs, not actual file copies
4. **GNOME-focused**: Designed primarily for GNOME desktop environment
5. **No keyboard shortcut registration**: Manual setup required for global hotkey

## Future Enhancements

### Planned Features
- [ ] Global keyboard shortcut integration
- [ ] Notes/snippets functionality
- [ ] Rich text formatting preview
- [ ] Code syntax highlighting
- [ ] Export/import clipboard history
- [ ] Cloud sync capabilities
- [ ] Item categories/tags
- [ ] Clipboard actions (URL shortening, QR codes, etc.)
- [ ] Multi-select operations
- [ ] Favorites/starred items

### Technical Improvements
- [ ] Unit tests
- [ ] CI/CD pipeline
- [ ] Packaging (Flatpak, AppImage, .deb)
- [ ] Performance optimization for large histories
- [ ] Memory usage profiling
- [ ] Wayland native clipboard monitoring

## Troubleshooting

### Application won't start
- Verify GTK4 and Libadwaita are installed
- Check Python version is 3.8+
- Ensure PyGObject is properly installed

### Images not showing
- Verify cache directory permissions: `~/.cache/clipnote/images/`
- Check if GdkPixbuf is installed
- Ensure sufficient disk space

### Database errors
- Check database file permissions: `~/.local/share/clipnote/clipnote.db`
- Try removing the database to rebuild: `rm ~/.local/share/clipnote/clipnote.db`

### High memory usage
- Reduce `max_items` in configuration
- Clear image cache periodically: `rm -rf ~/.cache/clipnote/images/*`

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Code style**: Follow PEP 8
2. **Type hints**: Use type annotations
3. **Documentation**: Update docstrings and README
4. **Testing**: Test manually before submitting
5. **Commits**: Use clear, descriptive commit messages

## License

This project is open source. See LICENSE file for details.

## Credits

- Built with [GTK4](https://gtk.org/) and [Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- Inspired by clipboard managers like Clipboard Indicator and Pano
- Technical design documented in [clipnote_report.md](clipnote_report.md)

## Support

For issues, questions, or suggestions, please file an issue in the project repository.

---

**Note**: This is a proof-of-concept implementation. Production use may require additional hardening, testing, and optimization.
