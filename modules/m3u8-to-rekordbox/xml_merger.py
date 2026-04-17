import re
from io import StringIO
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

from m3u8_reader import PlaylistDef


def _location_to_path(location: str) -> str:
    """Convert RB URI like file://localhost/path/to/file.mp3 to /path/to/file.mp3"""
    parsed = urlparse(location)
    return unquote(parsed.path)


def _build_location_index(collection: ET.Element) -> dict[str, str]:
    """Return {/abs/path: TrackID} for every TRACK in COLLECTION."""
    index = {}
    for track in collection.findall("TRACK"):
        loc = track.get("Location", "")
        if loc:
            index[_location_to_path(loc)] = track.get("TrackID")
    return index


def _find_folder(parent: ET.Element, name: str) -> ET.Element | None:
    """Find a Type=0 NODE child by name — no XPath interpolation, safe for all characters."""
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
    """Update Count on folder nodes (Type=0) only. Playlist nodes (Type=1) must not have Count."""
    if node.get("Type") == "1":
        # Playlist node: remove Count if present (ET may have added it), never set it
        node.attrib.pop("Count", None)
        return
    children = node.findall("NODE")
    node.set("Count", str(len(children)))
    for child in children:
        _update_counts_recursive(child)


def _fix_xml(body: str) -> str:
    """Fix Rekordbox XML serialization issues from ElementTree:

    1. ET.indent() adds Count="0" to every NODE. Strip it from Type="1" playlist nodes.
    2. Python 3.8+ ET emits ' />' (space before slash). Rekordbox rejects this.
    """
    body = re.sub(r'(<NODE\b[^>]*?\bType="1"[^>]*?)\s+Count="[^"]*"', r'\1', body)
    body = re.sub(r'(<NODE\b[^>]*?)\s+Count="[^"]*"([^>]*?\bType="1"[^>]*?>)', r'\1\2', body)
    body = re.sub(r' />', '/>', body)
    return body


def _write_rb_xml(tree: ET.ElementTree, xml_path: Path) -> None:
    """Write XML with Rekordbox-compatible declaration (double-quoted UTF-8, CRLF)."""
    ET.indent(tree, space="  ")
    buf = StringIO()
    tree.write(buf, encoding="unicode", xml_declaration=False)
    body = _fix_xml(buf.getvalue())
    output = '<?xml version="1.0" encoding="UTF-8"?>\r\n' + body.replace('\n', '\r\n')
    xml_path.write_text(output, encoding="utf-8")


def upsert_mamuma(xml_path: Path, playlists: list[PlaylistDef]) -> None:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    collection = root.find("COLLECTION")
    loc_index = _build_location_index(collection)

    root_node = root.find("PLAYLISTS/NODE")

    # Remove existing mamuma node using plain Python comparison (safe for all chars)
    existing_mamuma = next(
        (c for c in root_node if c.tag == "NODE" and c.get("Name") == "mamuma"), None
    )
    if existing_mamuma is not None:
        root_node.remove(existing_mamuma)

    # Create fresh mamuma folder
    mamuma_node = ET.SubElement(root_node, "NODE")
    mamuma_node.set("Name", "mamuma")
    mamuma_node.set("Type", "0")
    mamuma_node.set("Count", "0")

    for pdef in playlists:
        folder_parts = pdef.path[1:-1]
        playlist_name = pdef.path[-1]

        current = mamuma_node
        for part in folder_parts:
            current = _get_or_create_folder(current, part)

        track_ids = [loc_index[t] for t in pdef.tracks if t in loc_index]
        playlist_node = _build_playlist_node(playlist_name, track_ids)
        current.append(playlist_node)

    _update_counts_recursive(mamuma_node)
    _update_counts_recursive(root_node)

    _write_rb_xml(tree, xml_path)
