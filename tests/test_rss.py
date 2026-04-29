from pathlib import Path
from app.rss import generate_rss, EpisodeMeta
from app.config import PodcastMeta


def _meta() -> PodcastMeta:
    return PodcastMeta(
        title="T", description="D", author="A", language="en-US",
        base_url="https://example.test/",
    )


def test_rss_contains_basic_metadata(tmp_path: Path):
    eps = [EpisodeMeta(date_iso="2026-04-29", title="Ep 1", description="<p>notes</p>", duration_seconds=600, mp3_url="https://example.test/episodes/2026-04-29/episode.mp3", mp3_size_bytes=12345)]
    out = tmp_path / "podcast.xml"
    generate_rss(_meta(), eps, out)
    text = out.read_text(encoding="utf-8")
    assert "<title>T</title>" in text
    assert "<itunes:author>A</itunes:author>" in text
    assert "https://example.test/episodes/2026-04-29/episode.mp3" in text
    assert "Ep 1" in text


def test_rss_orders_episodes_newest_first(tmp_path: Path):
    eps = [
        EpisodeMeta(date_iso="2026-04-28", title="Old", description="x", duration_seconds=300, mp3_url="https://example.test/episodes/2026-04-28/episode.mp3", mp3_size_bytes=1),
        EpisodeMeta(date_iso="2026-04-29", title="New", description="x", duration_seconds=300, mp3_url="https://example.test/episodes/2026-04-29/episode.mp3", mp3_size_bytes=1),
    ]
    out = tmp_path / "podcast.xml"
    generate_rss(_meta(), eps, out)
    text = out.read_text(encoding="utf-8")
    assert text.index("New") < text.index("Old")
