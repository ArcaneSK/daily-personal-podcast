from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json


VALID_STATUSES = ("pending", "full", "blurb", "empty")


@dataclass
class SegmentEntry:
    id: str
    path: str
    status: str = "pending"   # "pending" | "full" | "blurb" | "empty"


@dataclass
class RunManifest:
    date: str
    segments: list[SegmentEntry] = field(default_factory=list)

    def set_status(self, segment_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status {status!r}; expected one of {VALID_STATUSES}")
        for s in self.segments:
            if s.id == segment_id:
                s.status = status
                return
        raise KeyError(f"Segment {segment_id!r} not in manifest")


def write_manifest(path: Path, manifest: RunManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")


def read_manifest(path: Path) -> RunManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return RunManifest(
        date=raw["date"],
        segments=[SegmentEntry(**s) for s in raw["segments"]],
    )
