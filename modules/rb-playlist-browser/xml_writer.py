from io import StringIO
from pathlib import Path
import xml.etree.ElementTree as ET

from xml_reader import Library, PlaylistNode


def rename_node(library: Library, node: PlaylistNode, new_name: str) -> None:
    node._element.set("Name", new_name)
    node.name = new_name


def delete_node(library: Library, node: PlaylistNode, parent: PlaylistNode) -> None:
    parent._element.remove(node._element)
    parent.children = [c for c in parent.children if c is not node]
    parent._element.set("Count", str(len(parent._element.findall("NODE"))))


def save(library: Library, xml_path: Path) -> None:
    """Write XML with Rekordbox-compatible declaration (double-quoted UTF-8, CRLF)."""
    ET.indent(library.tree, space="  ")
    buf = StringIO()
    library.tree.write(buf, encoding="unicode", xml_declaration=False)
    body = buf.getvalue()
    output = '<?xml version="1.0" encoding="UTF-8"?>\r\n' + body.replace('\n', '\r\n')
    xml_path.write_text(output, encoding="utf-8")
