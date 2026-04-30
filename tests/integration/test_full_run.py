# tests/integration/test_full_run.py
from pathlib import Path
import shutil
from unittest.mock import patch
from app.cli import main as cli_main

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_full_pipeline_produces_complete_episode(tmp_project, frozen_date):
    # Use the fake TTS provider via config-minimal.yaml so no network calls happen.
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text(
        "Greet the listener. ~30 seconds, narrator-only.\n", encoding="utf-8"
    )
    (tmp_project / "segments" / "02-ai-news.md").write_text(
        "Cover AI news. ~3 minutes, two-host conversational.\n", encoding="utf-8"
    )
    (tmp_project / "segments" / "99-outro.md").write_text(
        "Close the show. ~20 seconds, narrator-only.\n", encoding="utf-8"
    )

    fake_brief = (
        "# Research brief\nDate: 2026-04-29\n\n"
        "## Top stories (prioritized)\n"
        "### 1. Story one\n- **What happened:** thing\n- **Source:** https://example.com/a\n"
        "### 2. Story two\n- **What happened:** thing\n- **Source:** https://example.com/b\n"
    )
    fake_transcript = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] Good morning.\n"
        "## SEGMENT_BREAK 02-ai-news\n[NARRATOR] News.\n[HOST_A] First.\n[HOST_B] Counter.\n"
        "## SEGMENT_BREAK 99-outro\n[NARRATOR] Goodbye.\n"
    )
    with patch("app.research._call_agent_sdk", return_value=fake_brief), \
         patch("app.script._call_claude", return_value=fake_transcript), \
         patch("app.cli._make_summarizer", return_value=lambda t, b: "## Headlines\n- ok\n"), \
         patch("app.cli._make_compressor", return_value=lambda t: "(compressed)"):
        rc = cli_main(["--root", str(tmp_project), "generate", "--date", frozen_date])
    assert rc == 0

    # All canonical artifacts exist
    e = tmp_project / "episodes" / frozen_date
    for name in ("episode.mp3", "transcript.md", "show-notes.md", "summary.md", "run-manifest.json", "synthesis-manifest.json"):
        assert (e / name).exists(), f"missing {name}"
    for sid in ("01-intro", "02-ai-news", "99-outro"):
        assert (e / "research" / f"{sid}.md").exists()
        assert (tmp_project / "segments" / "_history" / f"{sid}.md").exists()
    assert (tmp_project / "episodes" / "_recent.md").exists()
    assert (tmp_project / "public" / "podcast.xml").exists()
    assert (tmp_project / "public" / "index.html").exists()
    assert (tmp_project / "public" / "episodes" / frozen_date / "episode.mp3").exists()

    # mp3 has nonzero duration (the FakeProvider yielded sine waves)
    assert (e / "episode.mp3").stat().st_size > 1000


def test_full_pipeline_with_mixed_status(tmp_project, frozen_date):
    """End-to-end with full / blurb / empty / full mix to exercise __wystk and segment skipping."""
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text("Greet listener.\n", encoding="utf-8")
    (tmp_project / "segments" / "02-ai-news.md").write_text("Cover AI news.\n", encoding="utf-8")
    (tmp_project / "segments" / "03-markets.md").write_text("Cover markets.\n", encoding="utf-8")
    (tmp_project / "segments" / "04-weather.md").write_text("Cover weather.\n", encoding="utf-8")
    (tmp_project / "segments" / "99-outro.md").write_text("Close the show.\n", encoding="utf-8")

    full_brief = (
        "## Top stories (prioritized)\n"
        "### 1. A\n- **What happened:** a thing\n- **Source:** https://example.com/a\n"
        "### 2. B\n- **What happened:** b thing\n- **Source:** https://example.com/b\n"
    )
    blurb_brief = (
        "## Top stories (prioritized)\n"
        "### 1. S&P closed flat\n- **What happened:** flat day\n- **Source:** https://wsj.com/x\n"
    )
    empty_brief = "## Top stories (prioritized)\n(no stories)\n"

    def fake_sdk(prompt, *, timeout_seconds):
        if "Cover markets" in prompt:
            return blurb_brief
        if "Cover weather" in prompt:
            return empty_brief
        return full_brief

    fake_transcript = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] Good morning.\n"
        "## SEGMENT_BREAK 02-ai-news\n[NARRATOR] News today.\n"
        "## SEGMENT_BREAK __wystk\n[NARRATOR] Quick note: per Wsj, the S&P closed flat.\n"
        "## SEGMENT_BREAK 99-outro\n[NARRATOR] Goodbye.\n"
    )
    with patch("app.research._call_agent_sdk", side_effect=fake_sdk), \
         patch("app.script._call_claude", return_value=fake_transcript), \
         patch("app.cli._make_summarizer", return_value=lambda t, b: "## Headlines\n- ok\n"), \
         patch("app.cli._make_compressor", return_value=lambda t: "(compressed)"):
        rc = cli_main(["--root", str(tmp_project), "generate", "--date", frozen_date])
    assert rc == 0

    # Show notes: 04-weather absent (empty), 03-markets aggregated under WYSTK
    notes = (tmp_project / "episodes" / frozen_date / "show-notes.md").read_text()
    assert "## What you should know today" in notes
    assert "*from 03-markets*" in notes
    assert "04-weather" not in notes
    assert "## 03-markets" not in notes
    assert "## 01-intro" in notes and "## 02-ai-news" in notes and "## 99-outro" in notes

    # All segments (including empty) get a history entry; statuses recorded
    assert "Status: empty" in (tmp_project / "segments" / "_history" / "04-weather.md").read_text()
    assert "Status: blurb" in (tmp_project / "segments" / "_history" / "03-markets.md").read_text()
    assert "Status: full" in (tmp_project / "segments" / "_history" / "02-ai-news.md").read_text()

    # Manifest reflects per-segment statuses
    import json
    m = json.loads((tmp_project / "episodes" / frozen_date / "run-manifest.json").read_text())
    by_id = {s["id"]: s["status"] for s in m["segments"]}
    assert by_id == {"01-intro": "full", "02-ai-news": "full", "03-markets": "blurb", "04-weather": "empty", "99-outro": "full"}
