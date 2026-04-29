# tests/test_cli_research.py
from pathlib import Path
import json
import shutil
from unittest.mock import patch
from app.cli import main as cli_main

FIXTURES = Path(__file__).parent / "fixtures"


def _seed(tmp_project: Path):
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text("Greet.\n", encoding="utf-8")
    (tmp_project / "segments" / "02-news.md").write_text("News.\n", encoding="utf-8")


def test_research_writes_status_full_in_manifest(tmp_project, frozen_date):
    _seed(tmp_project)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])

    fake_brief = (
        "## Top stories (prioritized)\n"
        "### 1. h\n- **What happened:** thing\n- **Source:** https://example.com/x\n"
        "### 2. h2\n- **What happened:** other\n- **Source:** https://example.com/y\n"
    )
    with patch("app.research._call_agent_sdk", return_value=fake_brief):
        rc = cli_main(["--root", str(tmp_project), "research", "--date", frozen_date])
    assert rc == 0
    for sid in ("01-intro", "02-news"):
        assert (tmp_project / "episodes" / frozen_date / "research" / f"{sid}.md").exists()
    m = json.loads((tmp_project / "episodes" / frozen_date / "run-manifest.json").read_text())
    assert all(s["status"] == "full" for s in m["segments"])


def test_research_writes_status_empty_for_thin_results(tmp_project, frozen_date):
    _seed(tmp_project)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])
    thin = "## Top stories (prioritized)\n(no stories)\n"
    with patch("app.research._call_agent_sdk", return_value=thin):
        cli_main(["--root", str(tmp_project), "research", "--date", frozen_date])
    m = json.loads((tmp_project / "episodes" / frozen_date / "run-manifest.json").read_text())
    assert all(s["status"] == "empty" for s in m["segments"])


def test_research_writes_status_blurb_for_one_story(tmp_project, frozen_date):
    _seed(tmp_project)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])
    one = "## Top stories (prioritized)\n### 1. only one\n- **What happened:** x\n- **Source:** https://example.com/a\n"
    with patch("app.research._call_agent_sdk", return_value=one):
        cli_main(["--root", str(tmp_project), "research", "--date", frozen_date])
    m = json.loads((tmp_project / "episodes" / frozen_date / "run-manifest.json").read_text())
    assert all(s["status"] == "blurb" for s in m["segments"])


def test_research_single_segment_via_flag(tmp_project, frozen_date):
    _seed(tmp_project)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])
    fake_brief = (
        "## Top stories (prioritized)\n"
        "### 1. h\n- **What happened:** thing\n- **Source:** https://example.com/x\n"
        "### 2. h2\n- **What happened:** other\n- **Source:** https://example.com/y\n"
    )
    with patch("app.research._call_agent_sdk", return_value=fake_brief):
        rc = cli_main(["--root", str(tmp_project), "research", "--date", frozen_date, "--segment", "02-news"])
    assert rc == 0
    assert (tmp_project / "episodes" / frozen_date / "research" / "02-news.md").exists()
    assert not (tmp_project / "episodes" / frozen_date / "research" / "01-intro.md").exists()
