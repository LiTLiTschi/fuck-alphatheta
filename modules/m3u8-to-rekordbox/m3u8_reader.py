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
            if line and not line.startswith("#"):
                tracks.append(line)
        results.append(PlaylistDef(path=path, tracks=tracks))
    return results
