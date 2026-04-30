# tests/test_cli_publish.py
from pathlib import Path
import shutil
import json
from unittest.mock import patch
from app.cli import main as cli_main
from app.manifest import RunManifest, SegmentEntry, write_manifest

FIXTURES = Path(__file__).parent / "fixtures"


def _seed(tmp_project, date):
    shutil.copy(FIXTURES / "config-minimal.yaml", tmp_project / "config.yaml")
    (tmp_project / "segments" / "01-intro.md").write_text("Greet.\n", encoding="utf-8")
    edir = tmp_project / "episodes" / date
    (edir / "research").mkdir(parents=True, exist_ok=True)
    (edir / "research" / "01-intro.md").write_text(
        "## Top stories (prioritized)\n"
        "### 1. h\n- **What happened:** thing\n- **Source:** https://example.com/a\n"
        "### 2. h2\n- **What happened:** other\n- **Source:** https://example.com/b\n",
        encoding="utf-8",
    )
    (edir / "transcript.md").write_text(
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n", encoding="utf-8"
    )
    (edir / "episode.mp3").write_bytes(b"\x00" * 50)
    (edir / "synthesis-manifest.json").write_text(json.dumps({"chunks": [], "total_ms": 60000}), encoding="utf-8")
    write_manifest(edir / "run-manifest.json", RunManifest(
        date=date,
        segments=[SegmentEntry(id="01-intro", path="segments/01-intro.md", status="full")],
    ))


def test_publish_command_uses_real_anthropic_via_stub(tmp_project, frozen_date):
    _seed(tmp_project, frozen_date)
    with patch("app.cli._make_summarizer", return_value=lambda t, b: "summary body"), \
         patch("app.cli._make_compressor", return_value=lambda t: "(c)"):
        rc = cli_main(["--root", str(tmp_project), "publish", "--date", frozen_date])
    assert rc == 0
    assert (tmp_project / "episodes" / frozen_date / "show-notes.md").exists()
    assert (tmp_project / "public" / "index.html").exists()
