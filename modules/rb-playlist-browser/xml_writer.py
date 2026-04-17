import re
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


def _fix_xml(body: str) -> str:
    """Fix two Rekordbox XML serialization issues introduced by ElementTree:

    1. ET.indent() adds Count="0" to every NODE element, including playlist
       nodes (Type="1"). Rekordbox only accepts Count on folder nodes (Type="0").
       Strip Count="0" (or any Count="...") from Type="1" nodes.

    2. Python 3.8+ ET serialises self-closing tags as ' />' (space before slash).
       Rekordbox's strict parser rejects this — remove the space.
    """
    # Issue 1: remove Count="..." from playlist NODEs (Type="1")
    body = re.sub(
        r'(<NODE\b[^>]*?\bType="1"[^>]*?)\s+Count="[^"]*"',
        r'\1',
        body,
    )
    # Also handle attribute order where Count appears before Type
    body = re.sub(
        r'(<NODE\b[^>]*?)\s+Count="[^"]*"([^>]*?\bType="1"[^>]*?>)',
        r'\1\2',
        body,
    )

    # Issue 2: remove space before self-closing />
    body = re.sub(r' />', '/>', body)

    return body


def save(library: Library, xml_path: Path) -> None:
    """Write XML with Rekordbox-compatible declaration (double-quoted UTF-8, CRLF)."""
    ET.indent(library.tree, space="  ")
    buf = StringIO()
    library.tree.write(buf, encoding="unicode", xml_declaration=False)
    body = _fix_xml(buf.getvalue())
    output = '<?xml version="1.0" encoding="UTF-8"?>\r\n' + body.replace('\n', '\r\n')
    xml_path.write_text(output, encoding="utf-8")
