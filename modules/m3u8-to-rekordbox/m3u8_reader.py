from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PlaylistDef:
    path: list[str]   # e.g. ["mamuma", "techno", "hard"] — always starts with "mamuma"
    tracks: list[str] = field(default_factory=list)


def scan_folder(root: Path) -> list[PlaylistDef]:
    results = []
    for m3u8_file in sorted(root.rglob("*.m3u8")):
        rel = m3u8_file.relative_to(root)
        path = ["mamuma"] + [p for p in list(rel.parent.parts) if p != "."] + [rel.stem]
        tracks = []
        for line in m3u8_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Resolve relative paths (e.g. ../../library/track.mp3) to absolute
            # using the m3u8 file's directory as the base.
            # Normalise to forward slashes so it matches loc_index keys built
            # from URL-decoded file://localhost/D:/... Location attributes.
            p = Path(line)
            if not p.is_absolute():
                p = (m3u8_file.parent / p).resolve()
            tracks.append(p.as_posix())
        results.append(PlaylistDef(path=path, tracks=tracks))
    return results
