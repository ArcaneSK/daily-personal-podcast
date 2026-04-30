from pathlib import Path
import shutil
from unittest.mock import patch
from app.cli import main as cli_main

FIXTURES = Path(__file__).parent / "fixtures"


def _seed(tmp_project):
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text("Greet.\n", encoding="utf-8")
    (tmp_project / "segments" / "02-news.md").write_text("News.\n", encoding="utf-8")


def test_script_command_writes_transcript_for_full_rundown(tmp_project, frozen_date):
    _seed(tmp_project)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])
    full_brief = (
        "## Top stories (prioritized)\n"
        "### 1. h\n- **What happened:** thing\n- **Source:** https://example.com/a\n"
        "### 2. h2\n- **What happened:** other\n- **Source:** https://example.com/b\n"
    )
    transcript_text = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n"
        "## SEGMENT_BREAK 02-news\n[NARRATOR] news\n"
    )
    with patch("app.research._call_agent_sdk", return_value=full_brief), \
         patch("app.script._call_claude", return_value=transcript_text):
        cli_main(["--root", str(tmp_project), "research", "--date", frozen_date])
        rc = cli_main(["--root", str(tmp_project), "script", "--date", frozen_date])
    assert rc == 0
    transcript = (tmp_project / "episodes" / frozen_date / "transcript.md").read_text()
    assert "[NARRATOR] hi" in transcript


def test_script_command_includes_wystk_when_blurb_present(tmp_project, frozen_date):
    """Mixed-status run: 01-intro is full, 02-news is blurb -> transcript must include __wystk."""
    _seed(tmp_project)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])

    full_brief = (
        "## Top stories (prioritized)\n"
        "### 1. h\n- **What happened:** thing\n- **Source:** https://example.com/a\n"
        "### 2. h2\n- **What happened:** other\n- **Source:** https://example.com/b\n"
    )
    blurb_brief = (
        "## Top stories (prioritized)\n"
        "### 1. one only\n- **What happened:** singular thing\n- **Source:** https://example.com/c\n"
    )

    def fake_sdk(prompt, *, timeout_seconds):
        # 01-intro gets full; 02-news gets blurb (distinguish by segment id in prompt)
        return full_brief if "01-intro" in prompt or "Greet" in prompt else blurb_brief

    transcript_text = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n"
        "## SEGMENT_BREAK __wystk\n[NARRATOR] one quick note before we close.\n"
    )
    with patch("app.research._call_agent_sdk", side_effect=fake_sdk), \
         patch("app.script._call_claude", return_value=transcript_text):
        cli_main(["--root", str(tmp_project), "research", "--date", frozen_date])
        rc = cli_main(["--root", str(tmp_project), "script", "--date", frozen_date])
    assert rc == 0
    t = (tmp_project / "episodes" / frozen_date / "transcript.md").read_text()
    assert "__wystk" in t
