from pathlib import Path
import subprocess
import sys
import json
import shutil
import pytest

from app.cli import main as cli_main


def _seed(tmp_project: Path, fixture_dir: Path) -> Path:
    # config
    shutil.copy(fixture_dir / "config-minimal.yaml", tmp_project / "config.yaml")
    # one segment
    (tmp_project / "segments" / "01-intro.md").write_text("Greet the listener.\n", encoding="utf-8")
    (tmp_project / "segments" / "02-news.md").write_text("Cover news.\n", encoding="utf-8")
    return tmp_project


FIXTURES = Path(__file__).parent / "fixtures"


def test_prepare_creates_episode_dir_and_manifest(tmp_project, frozen_date):
    _seed(tmp_project, FIXTURES)
    rc = cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])
    assert rc == 0
    manifest = tmp_project / "episodes" / frozen_date / "run-manifest.json"
    assert manifest.exists()
    m = json.loads(manifest.read_text())
    assert m["date"] == frozen_date
    assert [s["id"] for s in m["segments"]] == ["01-intro", "02-news"]
    # research dir scaffolded
    assert (tmp_project / "episodes" / frozen_date / "research").is_dir()


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli_main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "daily-personal-podcast" in out


def test_synthesize_uses_existing_transcript(tmp_project, frozen_date):
    _seed(tmp_project, FIXTURES)
    cli_main(["--root", str(tmp_project), "prepare", "--date", frozen_date])
    transcript = tmp_project / "episodes" / frozen_date / "transcript.md"
    transcript.write_text(
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] Hello.\n## SEGMENT_BREAK 02-news\n[NARRATOR] News.\n",
        encoding="utf-8",
    )
    rc = cli_main(["--root", str(tmp_project), "synthesize", "--date", frozen_date])
    assert rc == 0
    assert (tmp_project / "episodes" / frozen_date / "episode.mp3").exists()
