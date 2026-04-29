from pathlib import Path
import pytest
from app.segments import Segment, discover_segments


def _seg(root: Path, name: str, content: str = "# segment\n") -> Path:
    p = root / "segments" / name
    p.write_text(content, encoding="utf-8")
    return p


def test_discover_returns_sorted_active(tmp_project: Path):
    _seg(tmp_project, "03-markets.md", "markets")
    _seg(tmp_project, "01-intro.md", "intro")
    _seg(tmp_project, "02-ai-news.md", "ai")
    segs = discover_segments(tmp_project)
    assert [s.id for s in segs] == ["01-intro", "02-ai-news", "03-markets"]


def test_underscore_prefix_is_skipped(tmp_project: Path):
    _seg(tmp_project, "01-intro.md")
    _seg(tmp_project, "_disabled.md")
    _seg(tmp_project, "_TEMPLATE.md")
    segs = discover_segments(tmp_project)
    assert [s.id for s in segs] == ["01-intro"]


def test_non_markdown_files_ignored(tmp_project: Path):
    _seg(tmp_project, "01-intro.md")
    (tmp_project / "segments" / "notes.txt").write_text("ignore me")
    (tmp_project / "segments" / "README").write_text("readme")
    segs = discover_segments(tmp_project)
    assert [s.id for s in segs] == ["01-intro"]


def test_segment_carries_prose(tmp_project: Path):
    _seg(tmp_project, "01-intro.md", "Intro prose body")
    [seg] = discover_segments(tmp_project)
    assert seg.id == "01-intro"
    assert seg.prose == "Intro prose body"
    assert seg.path.name == "01-intro.md"


def test_invalid_filename_raises(tmp_project: Path):
    _seg(tmp_project, "no-prefix.md")
    with pytest.raises(ValueError, match="must start with NN-"):
        discover_segments(tmp_project)
