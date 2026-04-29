from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Literal
import re

_BREAK_RE = re.compile(r"^##\s+SEGMENT_BREAK\s+(\S+)\s*$")
_LINE_RE = re.compile(r"^\[(NARRATOR|HOST_A|HOST_B)\]\s+(.*)$")
_ROLE_MAP = {"NARRATOR": "narrator", "HOST_A": "host_a", "HOST_B": "host_b"}


@dataclass(frozen=True)
class SegmentBreak:
    segment_id: str


@dataclass(frozen=True)
class Line:
    role: str         # "narrator" | "host_a" | "host_b"
    text: str
    segment_id: str   # which segment this line belongs to


Item = SegmentBreak | Line


def parse_transcript(text: str) -> list[Item]:
    items: list[Item] = []
    current_segment: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _BREAK_RE.match(line)
        if m:
            current_segment = m.group(1)
            items.append(SegmentBreak(segment_id=current_segment))
            continue
        if line.startswith("##"):
            # Other heading lines are ignored (e.g. comment headings)
            continue
        m = _LINE_RE.match(line)
        if m:
            tag, body = m.group(1), m.group(2).strip()
            if current_segment is None:
                raise ValueError("Encountered speaker line before any SEGMENT_BREAK")
            items.append(Line(role=_ROLE_MAP[tag], text=body, segment_id=current_segment))
            continue
        if line.startswith("["):
            # Looks like a tagged line but didn't match
            raise ValueError(f"Unknown speaker tag in line: {line!r}")
        # Anything else: silent prose / comments — ignore
    return items


@dataclass(frozen=True)
class Chunk:
    kind: Literal["speech", "break"]
    role: str | None       # set when kind == "speech"
    text: str | None       # set when kind == "speech"
    segment_id: str        # always present


def chunk_for_synthesis(items: Iterable[Item], max_chars: int = 1000) -> list[Chunk]:
    """Group consecutive same-speaker lines into single chunks; emit silence markers at SEGMENT_BREAK."""
    out: list[Chunk] = []
    pending_role: str | None = None
    pending_segment: str | None = None
    pending_text: list[str] = []

    def flush():
        nonlocal pending_role, pending_segment, pending_text
        if not pending_text:
            return
        joined = " ".join(pending_text).strip()
        # Split on max_chars
        while len(joined) > max_chars:
            # Try to split at a sentence boundary near the cap
            cut = joined.rfind(". ", 0, max_chars)
            if cut == -1 or cut < max_chars // 2:
                cut = joined.rfind(" ", 0, max_chars)
            if cut == -1:
                cut = max_chars
            else:
                cut += 1  # include the space/period
            piece, joined = joined[:cut].strip(), joined[cut:].strip()
            out.append(Chunk(kind="speech", role=pending_role, text=piece, segment_id=pending_segment))
        if joined:
            out.append(Chunk(kind="speech", role=pending_role, text=joined, segment_id=pending_segment))
        pending_role = None
        pending_segment = None
        pending_text = []

    for it in items:
        if isinstance(it, SegmentBreak):
            flush()
            out.append(Chunk(kind="break", role=None, text=None, segment_id=it.segment_id))
            continue
        # Line
        if pending_role == it.role and pending_segment == it.segment_id:
            pending_text.append(it.text)
        else:
            flush()
            pending_role = it.role
            pending_segment = it.segment_id
            pending_text = [it.text]
    flush()
    return out
