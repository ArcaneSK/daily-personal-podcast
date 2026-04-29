from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from feedgen.feed import FeedGenerator

from app.config import PodcastMeta


@dataclass(frozen=True)
class EpisodeMeta:
    date_iso: str           # YYYY-MM-DD
    title: str
    description: str        # HTML or plain text
    duration_seconds: int
    mp3_url: str
    mp3_size_bytes: int


def generate_rss(podcast: PodcastMeta, episodes: list[EpisodeMeta], out_path: Path) -> None:
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(podcast.title)
    fg.description(podcast.description)
    fg.author({"name": podcast.author})
    fg.language(podcast.language)
    fg.link(href=podcast.base_url, rel="alternate")
    fg.link(href=f"{podcast.base_url.rstrip('/')}/podcast.xml", rel="self")
    fg.podcast.itunes_author(podcast.author)
    fg.podcast.itunes_category("News")
    fg.podcast.itunes_explicit("no")

    # Newest first by date.
    for ep in sorted(episodes, key=lambda e: e.date_iso, reverse=True):
        fe = fg.add_entry()
        fe.id(f"{podcast.base_url.rstrip('/')}/episodes/{ep.date_iso}/")
        fe.title(ep.title)
        fe.description(ep.description)
        fe.enclosure(ep.mp3_url, str(ep.mp3_size_bytes), "audio/mpeg")
        fe.pubDate(datetime.combine(datetime.fromisoformat(ep.date_iso).date(), time(7, 0), tzinfo=timezone.utc))
        fe.podcast.itunes_duration(ep.duration_seconds)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(out_path))
