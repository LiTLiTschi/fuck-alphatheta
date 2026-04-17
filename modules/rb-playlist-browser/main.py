import sys
from pathlib import Path

from tui import PlaylistBrowserApp


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <rekordbox.xml>", file=sys.stderr)
        sys.exit(1)

    xml_path = Path(sys.argv[1])
    if not xml_path.exists():
        print(f"Error: file not found: {xml_path}", file=sys.stderr)
        sys.exit(1)

    app = PlaylistBrowserApp(xml_path)
    app.run()


if __name__ == "__main__":
    main()
