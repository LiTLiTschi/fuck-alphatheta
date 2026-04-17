# rb-playlist-browser

Interactive TUI for browsing and managing playlists in a Rekordbox XML file.

## Requirements

```bash
pip install textual
```

## Usage

```bash
python main.py <rekordbox.xml>
```

**Example:**

```bash
python main.py "D:\backups\rekordbox\collection.xml"
```

## Keys

| Key | Action |
|-----|--------|
| `↑↓` | Navigate tree |
| `r` | Rename selected playlist/folder |
| `d` | Delete selected playlist/folder |
| `s` | Save changes to XML |
| `Esc` | Cancel rename |
| `q` | Quit (warns if unsaved, second `q` force quits) |

## Layout

Left pane: full playlist/folder tree from the XML.
Right pane: track list for the selected playlist (Artist, Title, Path).
