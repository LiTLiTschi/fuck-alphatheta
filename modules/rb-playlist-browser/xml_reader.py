from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET


@dataclass
class Track:
    track_id: str
    name: str
    artist: str
    path: str


@dataclass
class PlaylistNode:
    name: str
    is_folder: bool
    children: list["PlaylistNode"] = field(default_factory=list)
    track_ids: list[str] = field(default_factory=list)
    _element: object = field(default=None, repr=False)


@dataclass
class Library:
    root: PlaylistNode
    tracks: dict[str, Track]
    tree: object  # ET.ElementTree


def _parse_node(el) -> PlaylistNode:
    is_folder = el.get("Type") == "0"
    node = PlaylistNode(
        name=el.get("Name", ""),
        is_folder=is_folder,
        _element=el,
    )
    if is_folder:
        for child in el:
            if child.tag == "NODE":
                node.children.append(_parse_node(child))
    else:
        for track_el in el:
            if track_el.tag == "TRACK":
                node.track_ids.append(track_el.get("Key", ""))
    return node


def load(xml_path: Path) -> Library:
    tree = ET.parse(xml_path)
    root_el = tree.getroot()

    tracks: dict[str, Track] = {}
    for t in root_el.findall("COLLECTION/TRACK"):
        tid = t.get("TrackID", "")
        loc = t.get("Location", "")
        parsed = urlparse(loc)
        path = unquote(parsed.path)
        tracks[tid] = Track(
            track_id=tid,
            name=t.get("Name", ""),
            artist=t.get("Artist", ""),
            path=path,
        )

    root_node_el = root_el.find("PLAYLISTS/NODE")
    playlist_root = _parse_node(root_node_el)

    return Library(root=playlist_root, tracks=tracks, tree=tree)
