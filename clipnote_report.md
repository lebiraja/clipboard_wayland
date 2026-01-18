# ClipNote (Linux) — Clipboard + Notes Popup App (GNOME-focused)

A detailed technical report + build plan for a **Linux clipboard history + quick notes app** that appears via a **keyboard shortcut**, showing **copied text, images, and files** in a clean, searchable UI, and allowing **one-click restore + instant paste**.

This report focuses on GNOME, but the same architecture can be generalized for other desktop environments.

---

## 1) Why this app is worth building

Linux power users copy/paste constantly: code snippets, commands, links, paths, screenshots. The default clipboard only remembers the **last** thing. Clipboard managers solve this, but most are either:

- heavy / complex,
- not GNOME-native,
- tray-dependent (GNOME removed legacy tray icons by default),
- or not designed as a “quick keyboard launcher” tool.

**ClipNote** is designed as a modern, GNOME-friendly utility:

- **Super fast pop-up** via shortcut (like Spotlight / Alfred).
- **Keyboard-first** navigation.
- Clean UI that feels native.
- Stores **text + images + file references**.
- Includes **Quick Notes** (persistent snippets you can paste repeatedly).

---

## 2) What GNOME clipboard extensions/apps are made of

There are two major implementation styles on GNOME:

### A) GNOME Shell Extension (pure extension)
Examples: **Clipboard Indicator**, **Gnome Clipboard History**, **Pano**.

**Key facts:**
- Written in **JavaScript using GJS** (GNOME JavaScript). citeturn0search26
- Runs *inside the GNOME Shell process*.
- UI uses GNOME Shell toolkits: **St** (Shell Toolkit) and **Clutter**.
- Extensions integrate via panel indicators, popup menus, and shell components.
- Preferences UI uses **GTK/Adw** in a *separate process* (`prefs.js`). GNOME extension review guidelines explicitly require not mixing GTK libs in the shell process. citeturn0search15

**Pros**
- Best integration with GNOME top bar.
- No extra tray requirements.
- Native look/feel.

**Cons**
- Performance and stability risks: if extension is buggy, it can affect GNOME Shell.
- More sensitive to GNOME version changes.

GNOME shell architecture and how extensions fit is documented in the GJS guide. citeturn0search0

---

### B) Background app + UI launcher (daemon-based app)
Examples: CopyQ, Diodon, GPaste, tray apps.

**Key facts:**
- Runs as normal desktop app (Python/GTK, Vala/GTK, Qt, etc.)
- Tracks clipboard continuously via system clipboard APIs.
- Shows UI via tray icon, hotkey window, or app launcher.

**GNOME complication:**
GNOME does not display legacy tray icons by default. Many apps require **AppIndicator support extension** to show tray icons. citeturn0search17turn0search24

**Pros**
- Desktop-environment portable.
- Can do heavy processing without risking GNOME Shell.

**Cons**
- Tray dependency on GNOME unless you avoid tray.

---

## 3) Competitive analysis (what exists)

### Clipboard Indicator extension
- One of the most popular GNOME clipboard managers (multi-million downloads).
- Stores history + supports images.
- Code is available on GitHub. citeturn0search1turn0search2

### Gnome Clipboard History extension
- Rewrite of Clipboard Indicator focused on performance/features. citeturn0search5turn0search34

### Pano extension
- “Next-gen clipboard manager for GNOME Shell” and relies on dependencies such as libgda/gsound. citeturn0search19

### Traditional Linux clipboard managers
- **CopyQ** (Qt, powerful, scripting, multi-format).
- **GPaste** (GNOME oriented).
- **Diodon** (lightweight, GNOME-ish integration).
These are often recommended in Linux communities. citeturn0search7turn0search14turn0search32

---

## 4) Best architecture for ClipNote

You want:
- shortcut popup,
- clean UI,
- images + file items,
- notes.

### Recommended architecture: Hybrid GNOME-native app (daemon + popup)
This avoids GNOME Shell extension fragility, but still feels GNOME-native.

**Core components:**
1) **Background clipboard daemon**
   - Watches clipboard changes.
   - Normalizes items into a common internal format.
   - Stores them in local DB.

2) **Popup UI (GTK/Libadwaita)**
   - Triggered by shortcut.
   - Search + navigate.
   - Restore item to clipboard.
   - Optional “paste into active window”.

3) **Hotkey / launcher integration**
   - Either GNOME settings keybinding (easy MVP)
   - Or system-level global hotkey handling (later).

4) **Optional GNOME Shell extension (Phase 3)**
   - Provides better GNOME top bar integration.
   - Communicates with daemon via DBus.

This strategy is common: extension becomes a thin UI layer; daemon does heavy work.

---

## 5) Clipboard internals (Linux reality)

### X11 has two selections
- **CLIPBOARD** = Ctrl+C / Ctrl+V
- **PRIMARY** = mouse selection + middle click

Many clipboard managers allow syncing PRIMARY ↔ CLIPBOARD.

### Wayland constraints
Wayland is more secure:
- Clipboard access works, but
- “paste into current app by simulating keys” is harder.

**Design consequence:**
- On Wayland, prefer **copy-to-clipboard** and let user paste manually.
- Optional: use portals or compositor-specific tools (future).

---

## 6) Data formats ClipNote must support

### Clipboard item types
1) **Text**
   - MIME: `text/plain`, `text/plain;charset=utf-8`
2) **Image**
   - MIME: `image/png`, `image/jpeg`
   - Store as file in cache + thumbnail
3) **File references**
   - MIME: `text/uri-list`
   - Store file paths/URIs
4) (Optional) **HTML / Rich text**
   - MIME: `text/html`

### Internal model
Use a single normalized record:

```json
{
  "id": "uuid",
  "ts": 1730000000,
  "type": "text|image|files",
  "preview": "short string",
  "text": "...",
  "image_path": "...",
  "files": ["file:///..."],
  "app_id": "org.gnome.Terminal",
  "title": "window/app name",
  "pinned": false,
  "tags": ["code", "url"],
  "source": "clipboard|primary"
}
```

---

## 7) Storage layer

### Recommended: SQLite
Why:
- Fast search
- Works well with history
- Stable

Tables:
- `clips(id, ts, type, preview, payload, pinned, source, app_id)`
- `notes(id, ts, title, body, pinned)`

Payload handling:
- text clips: store plain text in DB
- images: store image file path + hashed thumbnail
- files: store JSON list

---

## 8) UI/UX spec (end product)

### Shortcut behavior
- Press hotkey → popup appears centered or near cursor.
- Typing immediately filters results.
- Enter → paste selected
- Esc → close

### Layout (recommended)
**Two-tab UI**:
- **Clipboard**
- **Notes**

Clipboard tab:
- Search bar
- List view with:
  - icon (text/image/file)
  - preview
  - timestamp (relative)
  - pin button

Notes tab:
- quick note list
- selected note details
- button: “Copy / Paste”

### “Clean UI” guideline
Use **Libadwaita** (GNOME modern UI), round corners, spacing, proper typography.

---

## 9) Tech stack options (choose one)

### Option 1 (fast + strong): Python + GTK4 + Libadwaita
- Clipboard daemon: Python
- UI: GTK4 + libadwaita
- DB: SQLite

Libraries:
- `PyGObject` (`gi.repository`)
- `libadwaita` bindings
- `sqlite3` (built-in)
- `watchdog` optional (file events)

### Option 2 (GNOME-native JS): GJS + GTK4
- Pure JS using GJS
- Best if you later also build a GNOME shell extension

GNOME explicitly supports building GTK apps with GJS. citeturn0search26

### Option 3 (pro): Rust + GTK4
- Best for performance and packaging
- Slower build speed

---

## 10) Implementation plan (what we planned to build)

### Phase 0 — Proof of concept (30–60 min)
- Clipboard watcher (text only)
- Popup list with search
- Click/Enter restores clipboard

### Phase 1 — MVP (1–3 days)
**Core**
- Text + image + file items
- SQLite storage
- Search + keyboard nav
- Pin items

**UX**
- Libadwaita clean UI
- Preview thumbnails

**Integration**
- Shortcut trigger (GNOME keybinding to run `clipnote --toggle`)

### Phase 2 — Polished App (1–2 weeks)
- Background daemon + UI separated
- System tray optional (AppIndicator extension requirement noted) citeturn0search17turn0search24
- Settings page: history size, sync primary, exclude passwords
- Per-app exclusion list

### Phase 3 — GNOME extension integration (advanced)
- GNOME shell extension provides panel icon + quick menu
- Communicates with daemon via DBus
- Extension written in GJS; preferences in GTK process (review guideline). citeturn0search15turn0search0

---

## 11) Detailed component design

### A) Clipboard daemon
Responsibilities:
- Subscribe/poll clipboard changes
- Identify MIME type
- Sanitize and store

Implementation notes:
- Use `Gdk.Clipboard` / `Gtk.Clipboard` depending GTK3/4.
- Keep last hash of clipboard content to avoid duplicates.
- For images: save to `~/.cache/clipnote/images/<sha>.png`

### B) Search engine
SQLite full-text search (FTS5) recommended:
- `clips_fts(preview, text)`

### C) Popup UI
Widgets:
- `Adw.ApplicationWindow`
- `Adw.HeaderBar`
- `Gtk.SearchEntry`
- `Gtk.ListView` / `Gtk.ListBox`

### D) Paste action
Modes:
- **copy-only** (safe on Wayland)
- **copy + auto-paste** (X11)

Auto paste options:
- `xdotool` (X11)
- On Wayland, auto-paste is limited.

---

## 12) Security + privacy
Clipboard managers can capture sensitive data.

Must-have protections:
- “Private mode” toggle
- Exclude certain apps (password managers)
- Auto-expire history
- Encrypt notes optional

---

## 13) Packaging & distribution

### For Linux
- **Flatpak** recommended (GNOME ecosystem)
- Or native packages (deb/rpm)

Flatpak advantages:
- Easy GNOME store distribution
- Sandboxing (with clipboard permissions)

---

## 14) What the end product should be like (final vision)

### ClipNote v1.0
- Press `Ctrl+Shift+V` → popup
- You instantly see your last copies:
  - code snippets
  - links
  - file paths
  - images (thumbnails)
- Type to search
- Enter to paste
- Pin items
- Notes tab for reusable templates/snippets

### GNOME-level polish
- Smooth animations
- Zero lag
- Native theme
- Optional top-bar indicator

---

## 15) References

- GNOME Shell extension architecture (GJS guide) citeturn0search0
- GNOME extension review rules (GTK vs Shell libs separation) citeturn0search15
- Clipboard Indicator extension (popular reference implementation) citeturn0search1turn0search2
- Gnome Clipboard History extension (performance-focused rewrite) citeturn0search5turn0search34
- Pano extension (modern clipboard manager) citeturn0search19
- AppIndicator support extension (tray icons on GNOME) citeturn0search17turn0search24
- Linux clipboard manager ecosystem overview (CopyQ/GPaste/Diodon) citeturn0search7turn0search14turn0search32

---

If you want, I can now generate:
- the complete upgraded codebase (daemon + GTK4 popup)
- SQLite schema
- Flatpak manifest
- README + screenshots plan
