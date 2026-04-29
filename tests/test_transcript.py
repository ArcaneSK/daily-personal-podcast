from pathlib import Path
import pytest
from app.transcript import (
    parse_transcript,
    Line,
    SegmentBreak,
    chunk_for_synthesis,
    Chunk,
)

FIXTURE = Path(__file__).parent / "fixtures" / "transcripts" / "sample.md"


def test_parse_yields_breaks_and_lines():
    items = parse_transcript(FIXTURE.read_text(encoding="utf-8"))
    types = [type(i).__name__ for i in items]
    assert types == [
        "SegmentBreak", "Line", "Line",
        "SegmentBreak", "Line", "Line", "Line",
        "SegmentBreak", "Line",
    ]
    assert items[0] == SegmentBreak(segment_id="01-intro")
    assert items[1] == Line(role="narrator", text="Good morning. It's Wednesday.", segment_id="01-intro")
    assert items[5] == Line(role="host_a", text="The big one is Opus 4.7.", segment_id="02-ai-news")


def test_unknown_speaker_raises():
    bad = "## SEGMENT_BREAK 01-intro\n[GUEST] Hi.\n"
    with pytest.raises(ValueError, match="Unknown speaker"):
        parse_transcript(bad)


def test_line_outside_segment_break_raises():
    bad = "[NARRATOR] Hi without a break.\n"
    with pytest.raises(ValueError, match="before any SEGMENT_BREAK"):
        parse_transcript(bad)


def test_chunk_groups_consecutive_same_speaker():
    items = parse_transcript(FIXTURE.read_text(encoding="utf-8"))
    chunks = chunk_for_synthesis(items, max_chars=1000)
    # 01-intro narrator: 2 lines -> 1 chunk
    # 02-ai-news narrator: 1 line -> 1 chunk
    # 02-ai-news host_a: 1 line -> 1 chunk
    # 02-ai-news host_b: 1 line -> 1 chunk
    # 99-outro narrator: 1 line -> 1 chunk
    # Plus 3 segment breaks (silence markers)
    assert [c.kind for c in chunks] == ["break", "speech", "break", "speech", "speech", "speech", "break", "speech"]
    speech = [c for c in chunks if c.kind == "speech"]
    assert speech[0].role == "narrator"
    assert "Good morning" in speech[0].text and "First up" in speech[0].text
    assert speech[2].role == "host_a"


def test_chunk_splits_on_max_chars():
    items = [SegmentBreak(segment_id="01-intro")] + [
        # 200 lines of 60 chars each, all same speaker -> must split into multiple chunks at 1000 char cap
        type("L", (), {})()  # placeholder to avoid using real Line in this synthetic test
    ]
    # Instead, build 5 lines of 300 chars same-speaker
    from app.transcript import Line as L, SegmentBreak as B
    items = [B(segment_id="01-intro")] + [L(role="narrator", text="x" * 300, segment_id="01-intro") for _ in range(5)]
    chunks = chunk_for_synthesis(items, max_chars=1000)
    speech = [c for c in chunks if c.kind == "speech"]
    # 5 * 300 = 1500 chars total; cap 1000 means 2 chunks (one ~900-ish, one ~600)
    assert len(speech) >= 2
    for c in speech:
        assert len(c.text) <= 1000
