import argparse
import shutil
import sys
from pathlib import Path

from m3u8_reader import scan_folder
from xml_merger import upsert_mamuma


def _prompt(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    val = input(f"{label}{hint}: ").strip()
    return val or default


def _prompt_yn(label: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    val = input(f"{label} [{hint}]: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")


def main():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Import m3u8 playlists into a Rekordbox XML collection under mamuma/.",
    )
    parser.add_argument("m3u8_folder", nargs="?", help="Folder containing .m3u8 files (scanned recursively)")
    parser.add_argument("xml", nargs="?", help="Rekordbox XML file (input)")
    parser.add_argument("-o", "--output", metavar="OUTPUT_XML",
                        help="Write result to OUTPUT_XML (copy mode - input is not modified)")
    parser.add_argument("-i", "--inplace", action="store_true",
                        help="Modify the XML file in-place (overwrites input)")
    parser.add_argument("-s", "--simple", action="store_true",
                        help="Match tracks by filename only (ignores path differences - more reliable)")
    args = parser.parse_args()

    # --- m3u8 folder ---
    if args.m3u8_folder:
        m3u8_folder = Path(args.m3u8_folder)
    else:
        m3u8_folder = Path(_prompt("m3u8 folder"))

    if not m3u8_folder.is_dir():
        print(f"Error: m3u8 folder not found: {m3u8_folder}", file=sys.stderr)
        sys.exit(1)

    # --- input xml ---
    if args.xml:
        input_xml = Path(args.xml)
    else:
        input_xml = Path(_prompt("Input Rekordbox XML"))

    if not input_xml.exists():
        print(f"Error: input XML not found: {input_xml}", file=sys.stderr)
        sys.exit(1)

    # --- output mode ---
    if args.inplace and args.output:
        print("Error: --inplace and --output are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    if args.inplace:
        output_xml = input_xml
    elif args.output:
        output_xml = Path(args.output)
    else:
        print("\nOutput mode:")
        print("  [1] In-place (overwrite input XML)")
        print("  [2] Copy to new file")
        choice = input("Choose [1/2]: ").strip()
        if choice == "1":
            output_xml = input_xml
        elif choice == "2":
            default_out = str(input_xml.with_stem(input_xml.stem + "_out"))
            output_xml = Path(_prompt("Output XML path", default_out))
        else:
            print("Invalid choice.", file=sys.stderr)
            sys.exit(1)

    # --- simple mode ---
    if not (args.simple):
        simple = _prompt_yn(
            "Use simple filename-based matching? (recommended if tracks show 0 in Rekordbox)",
            default=True,
        )
    else:
        simple = True

    # --- scan ---
    playlists = scan_folder(m3u8_folder)
    if not playlists:
        print("Warning: no .m3u8 files found - nothing to import.")
        sys.exit(0)

    # --- copy if needed ---
    if output_xml != input_xml:
        output_xml.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_xml, output_xml)
        print(f"Copied {input_xml} -> {output_xml}")
    else:
        print(f"Modifying in-place: {output_xml}")

    upsert_mamuma(output_xml, playlists, simple=simple)
    print(f"Done. Imported {len(playlists)} playlist(s) into mamuma/ -> {output_xml}")


if __name__ == "__main__":
    main()
