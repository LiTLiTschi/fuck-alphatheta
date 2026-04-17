# m3u8-to-rekordbox

Imports m3u8 playlists into a Rekordbox XML collection under a `mamuma/` folder.

## Usage

```bash
python main.py <m3u8_folder> <input.xml> <output.xml>
```

- `<m3u8_folder>` — folder containing `.m3u8` files (scanned recursively)
- `<input.xml>` — your original Rekordbox XML export (read-only, never modified)
- `<output.xml>` — path to write the modified XML to (created/overwritten)

## Example

```powershell
python main.py D:\music\scdl\m3u8 D:\backups\rekordbox\collection_original.xml D:\backups\rekordbox\collection_with_playlists.xml
```

Then import `collection_with_playlists.xml` into Rekordbox via
**Preferences → Advanced → Database → rekordbox xml**.
