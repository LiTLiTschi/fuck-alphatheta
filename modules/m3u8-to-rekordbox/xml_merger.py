import re
from io import StringIO
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

from m3u8_reader import PlaylistDef


def _location_to_posix(location: str) -> str:
    """Convert RB URI like file://localhost/D:/music/file.mp3
    to a normalised posix string: D:/music/file.mp3
    Works on both Windows (D:/...) and POSIX (/mnt/...).
    """
    path = unquote(urlparse(location).path)  # e.g. /D:/music/file.mp3
    # Strip leading slash that Windows drive letters produce: /D:/ -> D:/
    if len(path) >= 3 and path[0] == '/' and path[2] == ':':
        path = path[1:]
    return path


def _build_location_index(collection: ET.Element) -> dict[str, str]:
    """Return {posix_path: TrackID} for every TRACK in COLLECTION."""
    index = {}
    for track in collection.findall("TRACK"):
        loc = track.get("Location", "")
        if loc:
            index[_location_to_posix(loc)] = track.get("TrackID")
    return index


def _build_filename_index(collection: ET.Element) -> dict[str, str]:
    """Return {filename: TrackID} keyed by bare filename (no path, no extension).
    Simple mode - matches tracks purely by filename, ignores directory differences.
    Falls back to full filename with extension if stem alone is ambiguous.
    """
    index = {}
    for track in collection.findall("TRACK"):
        loc = track.get("Location", "")
        if not loc:
            continue
        tid = track.get("TrackID")
        fname = Path(unquote(urlparse(loc).path)).name  # e.g. "track.3387842.mp3"
        # Index by full filename
        index[fname] = tid
        # Also index by stem (no extension) for looser matching
        index[Path(fname).stem] = tid
    return index


def _find_folder(parent: ET.Element, name: str) -> ET.Element | None:
    for child in parent:
        if child.tag == "NODE" and child.get("Type") == "0" and child.get("Name") == name:
            return child
    return None


def _get_or_create_folder(parent: ET.Element, name: str) -> ET.Element:
    existing = _find_folder(parent, name)
    if existing is not None:
        return existing
    node = ET.SubElement(parent, "NODE")
    node.set("Name", name)
    node.set("Type", "0")
    node.set("Count", "0")
    return node


def _build_playlist_node(name: str, track_ids: list[str]) -> ET.Element:
    node = ET.Element("NODE")
    node.set("Name", name)
    node.set("Type", "1")
    node.set("KeyType", "0")
    node.set("Entries", str(len(track_ids)))
    for tid in track_ids:
        t = ET.SubElement(node, "TRACK")
        t.set("Key", tid)
    return node


def _update_counts_recursive(node: ET.Element):
    if node.get("Type") == "1":
        node.attrib.pop("Count", None)
        return
    children = node.findall("NODE")
    node.set("Count", str(len(children)))
    for child in children:
        _update_counts_recursive(child)


def _fix_xml(body: str) -> str:
    body = re.sub(r'(<NODE\b[^>]*?\bType="1"[^>]*?)\s+Count="[^"]*"', r'\1', body)
    body = re.sub(r'(<NODE\b[^>]*?)\s+Count="[^"]*"([^>]*?\bType="1"[^>]*?>)', r'\1\2', body)
    body = re.sub(r' />', '/>', body)
    return body


def _write_rb_xml(tree: ET.ElementTree, xml_path: Path) -> None:
    ET.indent(tree, space="  ")
    buf = StringIO()
    tree.write(buf, encoding="unicode", xml_declaration=False)
    body = _fix_xml(buf.getvalue())
    output = '<?xml version="1.0" encoding="UTF-8"?>\r\n' + body.replace('\n', '\r\n')
    xml_path.write_text(output, encoding="utf-8")


def _resolve_track_ids(
    tracks: list[str],
    loc_index: dict[str, str],
    fname_index: dict[str, str],
    simple: bool,
) -> list[str]:
    ids = []
    for t in tracks:
        if simple:
            # Try full filename, then stem
            fname = Path(t).name
            stem = Path(t).stem
            tid = fname_index.get(fname) or fname_index.get(stem)
        else:
            # Normalise to posix and strip leading Windows slash
            p = Path(t).as_posix()
            if len(p) >= 3 and p[0] == '/' and p[2] == ':':
                p = p[1:]
            tid = loc_index.get(p)
        if tid:
            ids.append(tid)
    return ids


def upsert_mamuma(xml_path: Path, playlists: list[PlaylistDef], simple: bool = False) -> None:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    collection = root.find("COLLECTION")
    loc_index = _build_location_index(collection)
    fname_index = _build_filename_index(collection) if simple else {}

    if simple:
        print(f"Simple mode: {len(fname_index)} filename entries indexed.")
    else:
        print(f"Path mode: {len(loc_index)} path entries indexed.")

    root_node = root.find("PLAYLISTS/NODE")

    existing_mamuma = next(
        (c for c in root_node if c.tag == "NODE" and c.get("Name") == "mamuma"), None
    )
    if existing_mamuma is not None:
        root_node.remove(existing_mamuma)

    mamuma_node = ET.SubElement(root_node, "NODE")
    mamuma_node.set("Name", "mamuma")
    mamuma_node.set("Type", "0")
    mamuma_node.set("Count", "0")

    total_matched = 0
    total_tracks = 0

    for pdef in playlists:
        folder_parts = pdef.path[1:-1]
        playlist_name = pdef.path[-1]

        current = mamuma_node
        for part in folder_parts:
            current = _get_or_create_folder(current, part)

        track_ids = _resolve_track_ids(pdef.tracks, loc_index, fname_index, simple)
        total_matched += len(track_ids)
        total_tracks += len(pdef.tracks)
        playlist_node = _build_playlist_node(playlist_name, track_ids)
        current.append(playlist_node)

    print(f"Matched {total_matched}/{total_tracks} tracks across all playlists.")

    _update_counts_recursive(mamuma_node)
    _update_counts_recursive(root_node)

    _write_rb_xml(tree, xml_path)
