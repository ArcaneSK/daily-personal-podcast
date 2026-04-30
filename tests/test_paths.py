from pathlib import Path
from app.paths import episode_dir, research_path, segment_history_path, recent_digest_path, public_episode_dir


def test_episode_dir(tmp_project: Path):
    assert episode_dir(tmp_project, "2026-04-29") == tmp_project / "episodes" / "2026-04-29"


def test_research_path(tmp_project: Path):
    p = research_path(tmp_project, "2026-04-29", "02-ai-news")
    assert p == tmp_project / "episodes" / "2026-04-29" / "research" / "02-ai-news.md"


def test_segment_history_path(tmp_project: Path):
    p = segment_history_path(tmp_project, "02-ai-news")
    assert p == tmp_project / "segments" / "_history" / "02-ai-news.md"


def test_recent_digest_path(tmp_project: Path):
    assert recent_digest_path(tmp_project) == tmp_project / "episodes" / "_recent.md"


def test_public_episode_dir(tmp_project: Path):
    assert public_episode_dir(tmp_project, "2026-04-29") == tmp_project / "public" / "episodes" / "2026-04-29"
