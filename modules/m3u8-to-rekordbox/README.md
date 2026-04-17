# m3u8-to-rekordbox

Sync a folder of `.m3u8` playlist files into a Rekordbox XML library, scoped entirely
under a folder called `mamuma`. Running the script again is always safe — it wipes and
rebuilds the `mamuma` subtree from scratch while leaving every other playlist and folder
untouched.

## Requirements

- Python 3.10+
- No external dependencies (stdlib only)

## Usage

```bash
python main.py <m3u8_folder> <rekordbox.xml>
```

**Example:**

```bash
python main.py "D:\Music\Playlists" "D:\backups\rekordbox\collection.xml"
```

## How It Works

### Folder structure → playlist paths

Your `.m3u8` folder structure maps directly to the `mamuma/` subtree in Rekordbox:

```
Playlists/
├── garage.m3u8            →  mamuma/garage
├── techno/
│   ├── hard.m3u8          →  mamuma/techno/hard
│   └── soft.m3u8          →  mamuma/techno/soft
└── dnb/
    └── liquid/
        └── chill.m3u8     →  mamuma/dnb/liquid/chill
```

### Track matching

Each non-comment line in an `.m3u8` is matched against the `Location` URI of tracks
already in your Rekordbox `<COLLECTION>`. Unmatched paths are silently skipped.

> **Tracks must already be imported into Rekordbox** before running this script.

### Upsert behaviour

On every run the entire `mamuma` folder is deleted and rebuilt. Stale playlists are
automatically removed. Everything outside `mamuma/` is never touched.

## After Running

1. In Rekordbox go to **Preferences → Advanced → rekordbox xml**
2. Re-point it to your updated XML file (or toggle it off/on) to force a refresh
3. The `mamuma` folder will appear in the XML source panel on the left
