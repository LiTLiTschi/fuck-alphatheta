import shutil
import sys
from pathlib import Path

from m3u8_reader import scan_folder
from xml_merger import upsert_mamuma


def main():
    if len(sys.argv) != 4:
        print("Usage: python main.py <m3u8_folder> <input.xml> <output.xml>", file=sys.stderr)
        sys.exit(1)

    m3u8_folder = Path(sys.argv[1])
    input_xml   = Path(sys.argv[2])
    output_xml  = Path(sys.argv[3])

    if not input_xml.exists():
        print(f"Error: input XML not found: {input_xml}", file=sys.stderr)
        sys.exit(1)

    if not m3u8_folder.is_dir():
        print(f"Error: m3u8 folder not found: {m3u8_folder}", file=sys.stderr)
        sys.exit(1)

    playlists = scan_folder(m3u8_folder)
    if not playlists:
        print("Warning: no .m3u8 files found — nothing to import.")
        sys.exit(0)

    # Copy input to output first so upsert_mamuma works on the output file
    output_xml.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_xml, output_xml)

    upsert_mamuma(output_xml, playlists)
    print(f"Done. Imported {len(playlists)} playlist(s) into mamuma/ -> {output_xml}")


if __name__ == "__main__":
    main()
