from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re
import shutil
import sys
from datetime import date as date_cls
from typing import Callable

from pydub.utils import mediainfo

from app.config import Config
from app.history import (
    SegmentHistoryEntry, RecentEntry,
    append_segment_history, update_recent_digest,
)
from app.manifest import read_manifest
from app.paths import (
    episode_dir, manifest_path, transcript_path, episode_mp3_path,
    show_notes_path, summary_path, research_path,
    recent_digest_path, segment_history_path,
    rss_path, public_episode_dir, public_episode_mp3,
    public_index_path, public_static_dir,
    synthesis_manifest_path,
)
from app.rss import EpisodeMeta, generate_rss
from app.site import EpisodeView, render_index


@dataclass
class PublishInputs:
    root: Path
    date_iso: str
    config: Config
    summarizer: Callable[[str, str], str]   # (transcript_md, briefs_blob) -> summary.md body
    compressor: Callable[[str], str]        # used for digest + segment history compression


_STORY_RE = re.compile(r"###\s+\d+\.\s+(.+)\n((?:.|\n)*?)(?=\n###\s+\d+\.|\n##\s|\Z)", re.MULTILINE)
_SOURCE_RE = re.compile(r"\*\*Source:\*\*\s*(\S+)")


_OPEN_THREADS_RE = re.compile(
    r"##\s+Open threads to revisit\s*\n((?:[ \t]*-[ \t]+.+\n?)*)",
    re.IGNORECASE,
)


def _extract_open_threads(brief_md: str) -> list[str]:
    """Parse '## Open threads to revisit' section and return each bullet as a string.

    Leading '- ' is stripped; the rest of the bullet body is kept as-is.
    Returns an empty list if the section is absent or has no bullet items.
    """
    m = _OPEN_THREADS_RE.search(brief_md)
    if not m:
        return []
    threads: list[str] = []
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            threads.append(stripped[2:].strip())
        elif stripped.startswith("-"):
            threads.append(stripped[1:].strip())
    return [t for t in threads if t]


def _extract_stories(brief_md: str) -> list[tuple[str, str]]:
    """Return [(headline, source_url)] from a research brief's 'Top stories' section."""
    out: list[tuple[str, str]] = []
    for m in _STORY_RE.finditer(brief_md):
        headline = m.group(1).strip()
        body = m.group(2)
        src = _SOURCE_RE.search(body)
        if src:
            out.append((headline, src.group(1).strip()))
    return out


def _render_show_notes(
    date_iso: str,
    full_segments: list[tuple[str, list[tuple[str, str]]]],     # [(sid, [(headline, url)])]
    blurb_items: list[tuple[str, str, str]],                    # [(sid, headline, url)] in rundown order
    duration_label: str,
) -> str:
    """Status-aware show notes.

    - `full` segments get their own ## <sid> section.
    - `blurb` items aggregate under a single ## What you should know today section,
      with *from <sid>* italics for traceability.
    - `empty` segments are not rendered (caller should not pass them).
    """
    parts = [
        f"# Daily Personal Podcast — {date_iso}",
        f"Duration: {duration_label} · [Listen (mp3)](./episode.mp3)",
        "",
    ]
    for sid, stories in full_segments:
        parts.append(f"## {sid}")
        for headline, url in stories:
            parts.append(f"- **{headline}** ([source]({url}))")
        parts.append("")
    if blurb_items:
        parts.append("## What you should know today")
        for sid, headline, url in blurb_items:
            parts.append(f"- **{headline}** *from {sid}* ([source]({url}))")
        parts.append("")
    return "\n".join(parts)


def _md_to_html(md: str) -> str:
    """Minimal markdown -> HTML for show-notes rendering. Handles headings, lists, links, paragraphs."""
    html_lines: list[str] = []
    in_list = False
    for line in md.splitlines():
        if line.startswith("# "):
            if in_list:
                html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>"); in_list = True
            item = line[2:].strip()
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            item = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', item)
            html_lines.append(f"<li>{item}</li>")
        elif not line.strip():
            if in_list:
                html_lines.append("</ul>"); in_list = False
        else:
            if in_list:
                html_lines.append("</ul>"); in_list = False
            text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)
            html_lines.append(f"<p>{text}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _ms_label(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def _episode_duration_ms(synthesis_manifest: Path, mp3: Path) -> int:
    if synthesis_manifest.exists():
        info = json.loads(synthesis_manifest.read_text(encoding="utf-8"))
        if "total_ms" in info:
            return int(info["total_ms"])
        chunks = info.get("chunks", [])
        if chunks:
            return sum(int(c.get("duration_ms", 0)) for c in chunks)
    # Fallback: probe with ffmpeg
    try:
        meta = mediainfo(str(mp3))
        return int(float(meta["duration"]) * 1000)
    except Exception:
        return 0


def _all_episode_dates(root: Path) -> list[str]:
    edir = root / "episodes"
    return sorted(p.name for p in edir.iterdir() if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", p.name))


def _spoken_text_for_segment(transcript_md: str, segment_id: str) -> str:
    in_seg = False
    parts: list[str] = []
    for line in transcript_md.splitlines():
        if line.startswith("## SEGMENT_BREAK"):
            in_seg = (segment_id in line)
            continue
        if in_seg and line.startswith("["):
            close = line.find("]")
            if close != -1:
                parts.append(line[close + 1:].strip())
    return " ".join(parts)


def publish_episode(inp: PublishInputs) -> None:
    root = inp.root
    date = inp.date_iso
    cfg = inp.config

    manifest = read_manifest(manifest_path(root, date))
    transcript_md = transcript_path(root, date).read_text(encoding="utf-8")

    # 1. Build per-segment story lists and classify them by manifest status
    full_segments: list[tuple[str, list[tuple[str, str]]]] = []   # [(sid, [(headline, url)])]
    blurb_items: list[tuple[str, str, str]] = []                  # [(sid, headline, url)] in rundown order
    per_segment_stories: dict[str, list[tuple[str, str]]] = {}    # for history rendering
    briefs_blob_parts: list[str] = []
    for s in manifest.segments:
        rpath = research_path(root, date, s.id)
        brief = rpath.read_text(encoding="utf-8") if rpath.exists() else ""
        briefs_blob_parts.append(f"--- {s.id} ---\n{brief}")
        stories = _extract_stories(brief)
        per_segment_stories[s.id] = stories
        if s.status == "full":
            full_segments.append((s.id, stories))
        elif s.status == "blurb":
            for h, u in stories:
                blurb_items.append((s.id, h, u))
        # empty: not added to either list

    duration_ms = _episode_duration_ms(synthesis_manifest_path(root, date), episode_mp3_path(root, date))
    duration_label = _ms_label(duration_ms)
    show_notes_md = _render_show_notes(date, full_segments, blurb_items, duration_label)
    show_notes_path(root, date).write_text(show_notes_md, encoding="utf-8")

    # Soft warning: spoken claims with no sourced stories at all
    if (not full_segments and not blurb_items
            and any(_spoken_text_for_segment(transcript_md, s.id) for s in manifest.segments)):
        print("WARN: episode has spoken text but no sourced stories were extracted from briefs.", file=sys.stderr)

    # 2. Summary
    briefs_blob = "\n\n".join(briefs_blob_parts)
    summary_body = inp.summarizer(transcript_md, briefs_blob)
    summary_path(root, date).write_text(f"# Episode summary — {date}\n\n{summary_body}", encoding="utf-8")

    # 3. Update rolling recent digest
    update_recent_digest(
        recent_digest_path(root),
        RecentEntry(date_iso=date, body=summary_body),
        today_iso=date,
        window_days=cfg.publish.recent_window_days,
        word_cap=cfg.publish.recent_digest_word_cap,
        compressor=inp.compressor,
    )

    # 4. Per-segment history — every segment gets an entry, regardless of status.
    #    Covered: included for full/blurb (with the headlines), omitted for empty.
    for s in manifest.segments:
        rpath = research_path(root, date, s.id)
        brief = rpath.read_text(encoding="utf-8") if rpath.exists() else ""
        stories = per_segment_stories.get(s.id, [])
        covered = [h for h, _ in stories] if s.status != "empty" else []
        open_threads = _extract_open_threads(brief) if s.status != "empty" else []
        entry = SegmentHistoryEntry(
            date_iso=date,
            status=s.status,
            covered=covered,
            open_threads=open_threads,
        )
        append_segment_history(
            segment_history_path(root, s.id),
            entry,
            token_cap=cfg.publish.segment_history_token_cap,
            compressor=inp.compressor,
        )

    # 5. Copy mp3 into public/ (audio files only — no per-episode HTML pages
    # in the new accordion-style index).
    public_episode_dir(root, date).mkdir(parents=True, exist_ok=True)
    shutil.copy2(episode_mp3_path(root, date), public_episode_mp3(root, date))

    # Walk every episode and build views for the index + RSS
    rss_episodes: list[EpisodeMeta] = []
    index_views: list[EpisodeView] = []
    for ds in _all_episode_dates(root):
        ep_show_notes = show_notes_path(root, ds)
        if not ep_show_notes.exists():
            continue
        ep_md = ep_show_notes.read_text(encoding="utf-8")
        title = ep_md.splitlines()[0].lstrip("# ").strip() if ep_md else ds
        ep_dur_ms = _episode_duration_ms(synthesis_manifest_path(root, ds), episode_mp3_path(root, ds))
        notes_html = _md_to_html(ep_md)

        # Make sure every published episode has an mp3 at the public path.
        # (Older publish runs may have left mp3s only under episodes/ on disk.)
        src_mp3 = episode_mp3_path(root, ds)
        dst_mp3 = public_episode_mp3(root, ds)
        if src_mp3.exists() and not dst_mp3.exists():
            dst_mp3.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_mp3, dst_mp3)

        index_views.append(EpisodeView(
            date_iso=ds, title=title, show_notes_html=notes_html,
            mp3_relpath=f"episodes/{ds}/episode.mp3",
            duration_label=_ms_label(ep_dur_ms),
        ))

        mp3_size = episode_mp3_path(root, ds).stat().st_size
        rss_episodes.append(EpisodeMeta(
            date_iso=ds, title=title, description=notes_html,
            duration_seconds=ep_dur_ms // 1000,
            mp3_url=f"{cfg.podcast.base_url.rstrip('/')}/episodes/{ds}/episode.mp3",
            mp3_size_bytes=mp3_size,
        ))

    # Single-page accordion index — every episode lives here.
    public_index_path(root).parent.mkdir(parents=True, exist_ok=True)
    public_index_path(root).write_text(
        render_index(cfg.podcast, index_views), encoding="utf-8"
    )

    # Static assets: copy site/static -> public/static (CSS + JS)
    src_static = Path(__file__).parent / "site" / "static"
    dst_static = public_static_dir(root)
    dst_static.mkdir(parents=True, exist_ok=True)
    for p in src_static.glob("*"):
        shutil.copy2(p, dst_static / p.name)

    # RSS
    generate_rss(cfg.podcast, rss_episodes, rss_path(root))
