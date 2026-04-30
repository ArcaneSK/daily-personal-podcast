from pathlib import Path
import shutil
from unittest.mock import patch
from app.cli import main as cli_main

FIXTURES = Path(__file__).parent / "fixtures"


def _seed(tmp_project):
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text("Greet.\n", encoding="utf-8")
    (tmp_project / "segments" / "02-news.md").write_text("Cover news.\n", encoding="utf-8")


def test_generate_runs_full_pipeline(tmp_project, frozen_date):
    _seed(tmp_project)
    fake_brief = "## Top stories (prioritized)\n### 1. h\n- **Source:** https://x\n### 2. h2\n- **Source:** https://y\n"
    transcript_text = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n"
        "## SEGMENT_BREAK 02-news\n[NARRATOR] news\n"
    )
    with patch("app.research._call_agent_sdk", return_value=fake_brief), \
         patch("app.script._call_claude", return_value=transcript_text), \
         patch("app.cli._make_summarizer", return_value=lambda t, b: "summary body"), \
         patch("app.cli._make_compressor", return_value=lambda t: "(c)"):
        rc = cli_main(["--root", str(tmp_project), "generate", "--date", frozen_date])
    assert rc == 0
    assert (tmp_project / "episodes" / frozen_date / "episode.mp3").exists()
    assert (tmp_project / "public" / "podcast.xml").exists()


def test_generate_refuses_when_episode_already_exists(tmp_project, frozen_date):
    _seed(tmp_project)
    edir = tmp_project / "episodes" / frozen_date
    edir.mkdir(parents=True, exist_ok=True)
    (edir / "episode.mp3").write_bytes(b"\x00")
    rc = cli_main(["--root", str(tmp_project), "generate", "--date", frozen_date])
    assert rc != 0


def test_generate_force_overrides(tmp_project, frozen_date):
    _seed(tmp_project)
    edir = tmp_project / "episodes" / frozen_date
    edir.mkdir(parents=True, exist_ok=True)
    (edir / "episode.mp3").write_bytes(b"\x00")
    fake_brief = "## Top stories (prioritized)\n### 1. h\n- **Source:** https://x\n### 2. h2\n- **Source:** https://y\n"
    transcript_text = "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n## SEGMENT_BREAK 02-news\n[NARRATOR] news\n"
    with patch("app.research._call_agent_sdk", return_value=fake_brief), \
         patch("app.script._call_claude", return_value=transcript_text), \
         patch("app.cli._make_summarizer", return_value=lambda t, b: "summary body"), \
         patch("app.cli._make_compressor", return_value=lambda t: "(c)"):
        rc = cli_main(["--root", str(tmp_project), "generate", "--date", frozen_date, "--force"])
    assert rc == 0
