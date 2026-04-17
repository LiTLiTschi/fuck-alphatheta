import sys
from pathlib import Path

from m3u8_reader import scan_folder
from xml_merger import upsert_mamuma


def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <m3u8_folder> <rekordbox.xml>", file=sys.stderr)
        sys.exit(1)

    m3u8_folder = Path(sys.argv[1])
    xml_path = Path(sys.argv[2])

    if not xml_path.exists():
        print(f"Error: XML file not found: {xml_path}", file=sys.stderr)
        sys.exit(1)

    if not m3u8_folder.is_dir():
        print(f"Error: m3u8 folder not found: {m3u8_folder}", file=sys.stderr)
        sys.exit(1)

    playlists = scan_folder(m3u8_folder)
    if not playlists:
        print("Warning: no .m3u8 files found — nothing to import.")
        sys.exit(0)

    upsert_mamuma(xml_path, playlists)
    print(f"Done. Imported {len(playlists)} playlist(s) into mamuma/")


if __name__ == "__main__":
    main()
