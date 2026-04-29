from pathlib import Path
from app.site import render_index, render_episode, EpisodeView
from app.config import PodcastMeta


def _pmeta() -> PodcastMeta:
    return PodcastMeta(title="T", description="D", author="A", language="en-US", base_url="https://example.test/")


def test_render_index_lists_episodes_newest_first():
    eps = [
        EpisodeView(date_iso="2026-04-28", title="Old", show_notes_html="<p>x</p>", mp3_relpath="episodes/2026-04-28/episode.mp3", duration_label="5:00"),
        EpisodeView(date_iso="2026-04-29", title="New", show_notes_html="<p>x</p>", mp3_relpath="episodes/2026-04-29/episode.mp3", duration_label="5:00"),
    ]
    html = render_index(_pmeta(), eps)
    assert html.index("New") < html.index("Old")
    assert "<title>T</title>" in html
    assert "https://example.test/" in html  # base url somewhere


def test_render_episode_includes_audio_and_notes():
    ev = EpisodeView(
        date_iso="2026-04-29",
        title="Ep",
        show_notes_html="<h2>Section</h2><p>body</p>",
        mp3_relpath="episode.mp3",
        duration_label="10:00",
    )
    html = render_episode(_pmeta(), ev)
    assert "<audio" in html and "episode.mp3" in html
    assert "Section" in html
    assert "10:00" in html
