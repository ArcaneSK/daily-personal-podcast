from pathlib import Path
from app.site import render_index, EpisodeView
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


def test_render_index_embeds_audio_and_show_notes_inline():
    """Each episode is an accordion with the audio element + show notes
    rendered inline (no per-episode page anymore)."""
    ev = EpisodeView(
        date_iso="2026-04-29",
        title="Ep",
        show_notes_html="<h2>Section</h2><p>body</p>",
        mp3_relpath="episodes/2026-04-29/episode.mp3",
        duration_label="10:00",
    )
    html = render_index(_pmeta(), [ev])
    assert "<audio" in html and "episodes/2026-04-29/episode.mp3" in html
    assert "Section" in html
    assert "10:00" in html
    # Accordion structure
    assert "<details" in html and "<summary" in html
    # Search input + pagination scaffolding present
    assert 'id="search"' in html
    assert 'id="pagination"' in html
    # JS attached
    assert "static/app.js" in html


def test_render_index_handles_empty_episode_list():
    html = render_index(_pmeta(), [])
    assert "No episodes published yet" in html
