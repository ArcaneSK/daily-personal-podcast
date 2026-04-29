# tests/test_manifest.py
from pathlib import Path
import pytest
from app.manifest import RunManifest, SegmentEntry, write_manifest, read_manifest


def test_roundtrip(tmp_project: Path):
    m = RunManifest(
        date="2026-04-29",
        segments=[
            SegmentEntry(id="01-intro", path="segments/01-intro.md"),
            SegmentEntry(id="02-ai-news", path="segments/02-ai-news.md"),
        ],
    )
    p = tmp_project / "episodes" / "2026-04-29" / "run-manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(p, m)
    loaded = read_manifest(p)
    assert loaded == m
    assert all(s.status == "pending" for s in loaded.segments)


def test_set_status(tmp_project: Path):
    m = RunManifest(
        date="2026-04-29",
        segments=[SegmentEntry(id="02-ai-news", path="segments/02-ai-news.md")],
    )
    p = tmp_project / "episodes" / "2026-04-29" / "run-manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(p, m)

    m2 = read_manifest(p)
    m2.set_status("02-ai-news", "blurb")
    write_manifest(p, m2)

    assert read_manifest(p).segments[0].status == "blurb"


def test_set_status_validates_value(tmp_project: Path):
    m = RunManifest(date="2026-04-29", segments=[SegmentEntry(id="s", path="p")])
    with pytest.raises(ValueError, match="Invalid status"):
        m.set_status("s", "bogus")


def test_set_status_unknown_segment_raises():
    m = RunManifest(date="2026-04-29", segments=[SegmentEntry(id="s", path="p")])
    with pytest.raises(KeyError):
        m.set_status("nope", "full")
