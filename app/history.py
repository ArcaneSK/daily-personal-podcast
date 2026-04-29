from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable
import re


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def count_words(text: str) -> int:
    return len(text.split())


@dataclass
class SegmentHistoryEntry:
    date_iso: str
    status: str             # "full" | "blurb" | "empty"
    covered: list[str]      # one-liner per headline; omitted (empty list) when status == "empty"
    open_threads: list[str] # one-liner per thread


@dataclass
class RecentEntry:
    date_iso: str
    body: str               # the summary.md body for that date


def _segment_entry_md(e: SegmentHistoryEntry) -> str:
    parts = [f"## {e.date_iso}", f"Status: {e.status}"]
    if e.status != "empty" and e.covered:
        parts.append("Covered: " + "; ".join(e.covered) + ".")
    if e.open_threads:
        parts.append("Open threads: " + "; ".join(e.open_threads) + ".")
    return "\n".join(parts) + "\n"


def append_segment_history(
    path: Path,
    entry: SegmentHistoryEntry,
    *,
    token_cap: int,
    compressor: Callable[[str], str],
) -> None:
    """Append a dated section. If the file then exceeds token_cap, replace dated history with a
    compressed 'Background context' section followed by today's entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    new_section = _segment_entry_md(entry)
    candidate = (existing.rstrip() + "\n\n" + new_section).lstrip()
    if estimate_tokens(candidate) <= token_cap:
        path.write_text(candidate, encoding="utf-8")
        return
    compressed = compressor(existing).strip()
    if not compressed.startswith("## Background context"):
        compressed = "## Background context\n" + compressed
    path.write_text(compressed.rstrip() + "\n\n" + new_section, encoding="utf-8")


_DATE_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


def _split_dated_sections(text: str) -> list[tuple[str, str]]:
    """Return a list of (date_iso, body) for top-level '## YYYY-MM-DD' sections, in order."""
    matches = list(_DATE_HEADING_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((m.group(1), body))
    return sections


def update_recent_digest(
    path: Path,
    new_entry: RecentEntry,
    *,
    today_iso: str,
    window_days: int,
    word_cap: int,
    compressor: Callable[[str], str],
) -> None:
    """Append today's summary, drop entries older than window_days, compress if over word_cap."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_text = path.read_text(encoding="utf-8") if path.exists() else ""

    today = date.fromisoformat(today_iso)
    cutoff = today - timedelta(days=window_days)

    sections = _split_dated_sections(existing_text)
    kept: list[tuple[str, str]] = []
    for ds, body in sections:
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if d >= cutoff and ds != new_entry.date_iso:
            kept.append((ds, body))

    kept.append((new_entry.date_iso, new_entry.body.strip()))
    kept.sort(key=lambda x: x[0])

    rendered = "\n\n".join(f"## {ds}\n{body}".rstrip() for ds, body in kept) + "\n"

    if count_words(rendered) > word_cap and len(kept) > 1:
        # Compress everything except today; keep today's entry verbatim.
        old_blob = "\n\n".join(f"## {ds}\n{body}" for ds, body in kept[:-1])
        compressed = compressor(old_blob).strip()
        latest_ds, latest_body = kept[-1]
        rendered = (
            "## Compressed digest\n" + compressed + "\n\n"
            f"## {latest_ds}\n{latest_body.strip()}\n"
        )

    path.write_text(rendered, encoding="utf-8")
