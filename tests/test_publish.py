# tests/test_publish.py
from pathlib import Path
import json
import shutil
from app.publish import publish_episode, PublishInputs
from app.config import load_config
from app.manifest import RunManifest, SegmentEntry, write_manifest

FIXTURES = Path(__file__).parent / "fixtures"


def _seed(tmp_project: Path):
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text("Greet.\n", encoding="utf-8")
    (tmp_project / "segments" / "02-news.md").write_text("News.\n", encoding="utf-8")
    (tmp_project / "segments" / "03-markets.md").write_text("Markets.\n", encoding="utf-8")
    (tmp_project / "segments" / "04-weather.md").write_text("Weather.\n", encoding="utf-8")


def _seed_episode_mixed(tmp_project: Path, date: str):
    """Seed an episode with full / blurb / empty / full status mix."""
    edir = tmp_project / "episodes" / date
    (edir / "research").mkdir(parents=True, exist_ok=True)
    # 01-intro: full (2 stories)
    (edir / "research" / "01-intro.md").write_text(
        "## Top stories (prioritized)\n"
        "### 1. Hello\n- **What happened:** intro thing\n- **Source:** https://example.com/1\n"
        "### 2. World\n- **What happened:** another\n- **Source:** https://example.com/1b\n"
    )
    # 02-news: full (2 stories) with open threads
    (edir / "research" / "02-news.md").write_text(
        "## Top stories (prioritized)\n"
        "### 1. News\n- **What happened:** news thing\n- **Source:** https://example.com/2\n"
        "### 2. More news\n- **What happened:** more\n- **Source:** https://example.com/2b\n"
        "\n## Open threads to revisit\n"
        "- AI regulation bill still in committee, no vote scheduled\n"
        "- Open-source LLM benchmark controversy ongoing\n"
    )
    # 03-markets: blurb (1 story)
    (edir / "research" / "03-markets.md").write_text(
        "## Top stories (prioritized)\n"
        "### 1. S&P closed flat\n- **What happened:** Index closed flat today.\n- **Source:** https://wsj.com/markets\n"
    )
    # 04-weather: empty
    (edir / "research" / "04-weather.md").write_text(
        "## Top stories (prioritized)\n(no stories today)\n"
    )
    (edir / "transcript.md").write_text(
        "## SEGMENT_BREAK 01-intro\n[HOST_A] hi\n"
        "## SEGMENT_BREAK 02-news\n[HOST_A] News from example.\n"
        "## SEGMENT_BREAK __wystk\n[HOST_A] One quick note: S&P closed flat per Wsj.\n",
        encoding="utf-8",
    )
    (edir / "episode.mp3").write_bytes(b"ID3" + b"\x00" * 100)
    (edir / "synthesis-manifest.json").write_text(
        json.dumps({"chunks": [], "sample_rate": 24000, "total_ms": 305000}), encoding="utf-8"
    )
    write_manifest(edir / "run-manifest.json", RunManifest(
        date=date,
        segments=[
            SegmentEntry(id="01-intro", path="segments/01-intro.md", status="full"),
            SegmentEntry(id="02-news", path="segments/02-news.md", status="full"),
            SegmentEntry(id="03-markets", path="segments/03-markets.md", status="blurb"),
            SegmentEntry(id="04-weather", path="segments/04-weather.md", status="empty"),
        ],
    ))


def test_publish_writes_status_aware_show_notes(tmp_project, frozen_date):
    _seed(tmp_project)
    _seed_episode_mixed(tmp_project, frozen_date)
    cfg = load_config(tmp_project / "config.yaml")

    publish_episode(PublishInputs(
        root=tmp_project, date_iso=frozen_date, config=cfg,
        summarizer=lambda t, b: "## Headlines covered\n- (test)\n",
        compressor=lambda t: "(compressed)",
    ))

    notes = (tmp_project / "episodes" / frozen_date / "show-notes.md").read_text()
    # Full segments get their own section
    assert "## 01-intro" in notes
    assert "## 02-news" in notes
    # Blurb rolled into "What you should know today" with traceability italics
    assert "## What you should know today" in notes
    assert "*from 03-markets*" in notes
    assert "https://wsj.com/markets" in notes
    # Empty segment is entirely omitted
    assert "04-weather" not in notes
    assert "## 03-markets" not in notes


def test_publish_writes_status_aware_history(tmp_project, frozen_date):
    _seed(tmp_project)
    _seed_episode_mixed(tmp_project, frozen_date)
    cfg = load_config(tmp_project / "config.yaml")
    publish_episode(PublishInputs(
        root=tmp_project, date_iso=frozen_date, config=cfg,
        summarizer=lambda t, b: "## Headlines covered\n- (test)\n",
        compressor=lambda t: "(compressed)",
    ))

    intro = (tmp_project / "segments" / "_history" / "01-intro.md").read_text()
    assert f"## {frozen_date}" in intro
    assert "Status: full" in intro
    assert "Covered:" in intro

    blurb = (tmp_project / "segments" / "_history" / "03-markets.md").read_text()
    assert "Status: blurb" in blurb
    assert "Covered:" in blurb     # blurb has 1 headline, included
    assert "S&P closed flat" in blurb

    empty = (tmp_project / "segments" / "_history" / "04-weather.md").read_text()
    assert "Status: empty" in empty
    assert "Covered:" not in empty  # omitted for empty


def test_publish_writes_summary_recent_rss_and_site(tmp_project, frozen_date):
    _seed(tmp_project)
    _seed_episode_mixed(tmp_project, frozen_date)
    cfg = load_config(tmp_project / "config.yaml")
    publish_episode(PublishInputs(
        root=tmp_project, date_iso=frozen_date, config=cfg,
        summarizer=lambda t, b: "## Headlines covered\n- ok\n",
        compressor=lambda t: "(c)",
    ))
    e = tmp_project / "episodes" / frozen_date
    assert (e / "summary.md").exists()
    assert (tmp_project / "episodes" / "_recent.md").exists()
    assert (tmp_project / "public" / "podcast.xml").exists()
    assert (tmp_project / "public" / "index.html").exists()
    assert (tmp_project / "public" / "episodes" / frozen_date / "episode.mp3").exists()


def test_publish_extracts_open_threads_into_segment_history(tmp_project, frozen_date):
    """Open threads from the research brief should appear in the segment history entry."""
    _seed(tmp_project)
    _seed_episode_mixed(tmp_project, frozen_date)
    cfg = load_config(tmp_project / "config.yaml")
    publish_episode(PublishInputs(
        root=tmp_project, date_iso=frozen_date, config=cfg,
        summarizer=lambda t, b: "## Headlines covered\n- (test)\n",
        compressor=lambda t: "(compressed)",
    ))

    news_history = (tmp_project / "segments" / "_history" / "02-news.md").read_text()
    assert "Open threads:" in news_history
    assert "AI regulation bill still in committee, no vote scheduled" in news_history
    assert "Open-source LLM benchmark controversy ongoing" in news_history
