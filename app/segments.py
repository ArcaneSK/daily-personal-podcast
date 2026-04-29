from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

_NAME_RE = re.compile(r"^\d{2}-[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Segment:
    id: str          # "01-intro" (filename without extension)
    path: Path       # absolute path to the segment file
    prose: str       # the file's full content


def discover_segments(root: Path) -> list[Segment]:
    """Return segments sorted by filename. Skips files starting with '_' and non-.md files."""
    segments_dir = root / "segments"
    out: list[Segment] = []
    for p in sorted(segments_dir.iterdir(), key=lambda x: x.name):
        if not p.is_file():
            continue
        if p.suffix != ".md":
            continue
        if p.name.startswith("_"):
            continue
        stem = p.stem
        if not _NAME_RE.match(stem):
            raise ValueError(
                f"Segment filename {p.name!r} must start with NN- (two digits + dash) "
                "and contain only letters, digits, hyphens, underscores."
            )
        out.append(Segment(id=stem, path=p, prose=p.read_text(encoding="utf-8")))
    return out
