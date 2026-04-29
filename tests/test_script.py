# tests/test_script.py
from pathlib import Path
from unittest.mock import patch
import pytest
from app.script import compose_transcript, ScriptInputs, build_prompt, build_filtered_rundown


def _seg(sid, status, prose="prose", history="", research="", stories=None):
    return {
        "id": sid, "status": status, "prose": prose, "history": history,
        "research": research, "stories": stories or [],
    }


def _stories(*tuples):
    """Helper: each tuple is (segment_id, headline, what_happened, url, publication)."""
    from app.research import Story
    return [Story(*t) for t in tuples]


def _inputs(tmp_project: Path, segments) -> ScriptInputs:
    return ScriptInputs(
        date_iso="2026-04-29",
        target_total_minutes=20,
        narrator_name="Alex", narrator_persona="Calm.",
        host_a_name="Sam", host_a_persona="Curious.",
        host_b_name="Jordan", host_b_persona="Skeptical.",
        recent_digest="Yesterday: launches.",
        segments=segments,
        out_path=tmp_project / "transcript.md",
    )


def test_filter_keeps_full_drops_empty_collects_blurbs():
    segments = [
        _seg("01-intro", "full"),
        _seg("02-news", "full"),
        _seg("03-markets", "blurb", stories=_stories(("03-markets", "S&P flat", "details", "https://wsj.com/x", "Wsj"))),
        _seg("04-weather", "empty"),
        _seg("99-outro", "full"),
    ]
    rundown, blurbs, has_outro = build_filtered_rundown(segments)
    ids = [r["id"] for r in rundown]
    # full body segments preserved in order, then __wystk before outro, then outro
    assert ids == ["01-intro", "02-news", "__wystk", "99-outro"]
    assert len(blurbs) == 1
    assert blurbs[0].segment_id == "03-markets"
    assert has_outro is True


def test_filter_no_blurbs_no_wystk():
    segments = [
        _seg("01-intro", "full"),
        _seg("02-news", "full"),
        _seg("03-empty", "empty"),
        _seg("99-outro", "full"),
    ]
    rundown, blurbs, has_outro = build_filtered_rundown(segments)
    assert [r["id"] for r in rundown] == ["01-intro", "02-news", "99-outro"]
    assert blurbs == []


def test_filter_empty_outro_is_dropped_wystk_becomes_closer():
    segments = [
        _seg("01-intro", "full"),
        _seg("02-news", "full"),
        _seg("03-markets", "blurb", stories=_stories(("03-markets", "S&P flat", "x", "https://wsj.com/x", "Wsj"))),
        _seg("99-outro", "empty"),
    ]
    rundown, blurbs, has_outro = build_filtered_rundown(segments)
    assert [r["id"] for r in rundown] == ["01-intro", "02-news", "__wystk"]
    assert has_outro is False


def test_filter_blurb_outro_stays_as_closer_not_in_wystk():
    segments = [
        _seg("01-intro", "full"),
        _seg("02-news", "full"),
        _seg("99-outro", "blurb", stories=_stories(("99-outro", "preview", "x", "https://e.com/y", "E"))),
    ]
    rundown, blurbs, has_outro = build_filtered_rundown(segments)
    # outro is closer regardless of blurb classification; not pulled into __wystk
    assert [r["id"] for r in rundown] == ["01-intro", "02-news", "99-outro"]
    assert blurbs == []
    assert has_outro is True


def test_filter_no_outro_segment_appends_wystk_at_end():
    segments = [
        _seg("01-intro", "full"),
        _seg("02-news", "blurb", stories=_stories(("02-news", "h", "x", "https://e.com/a", "E"))),
    ]
    rundown, blurbs, has_outro = build_filtered_rundown(segments)
    assert [r["id"] for r in rundown] == ["01-intro", "__wystk"]
    assert has_outro is False


def test_filter_all_empty_raises():
    segments = [
        _seg("01-intro", "empty"),
        _seg("02-news", "empty"),
    ]
    with pytest.raises(ValueError, match="every segment is empty"):
        build_filtered_rundown(segments)


def test_build_prompt_contains_filtered_rundown_and_blurbs(tmp_project):
    segments = [
        _seg("01-intro", "full", prose="Greet listener.", research="## Top stories\n### 1. ...\n"),
        _seg("02-news", "full", prose="Cover news.", history="Last week: y",
             research="## Top stories\n### 1. ...\n"),
        _seg("03-markets", "blurb", prose="Markets.",
             stories=_stories(("03-markets", "S&P flat", "what happened body", "https://wsj.com/x", "Wsj"))),
        _seg("04-weather", "empty", prose="Weather."),
        _seg("99-outro", "full", prose="Sign off."),
    ]
    p = build_prompt(_inputs(tmp_project, segments))
    assert "TODAY: 2026-04-29" in p
    assert "Total target length: ~20 minutes" in p
    # filtered rundown
    rundown_block = p.split("RUNDOWN")[1]
    rundown_block = rundown_block.split("BLURBS")[0]
    assert "01-intro" in rundown_block
    assert "02-news" in rundown_block
    assert "__wystk" in rundown_block
    assert "99-outro" in rundown_block
    assert "04-weather" not in rundown_block       # empty dropped
    # body sections only for FULL segments + outro
    assert "--- SEGMENT 01-intro ---" in p
    assert "--- SEGMENT 02-news ---" in p
    assert "--- SEGMENT 99-outro ---" in p
    assert "--- SEGMENT 03-markets ---" not in p   # blurb pulled to BLURBS
    assert "--- SEGMENT 04-weather ---" not in p   # empty dropped
    # BLURBS section present with structured fields
    assert "BLURBS" in p
    assert "segment_id: 03-markets" in p
    assert "S&P flat" in p
    assert "what happened body" in p
    assert "Wsj" in p
    # __wystk instructions present
    assert "__wystk" in p
    # outro instructions
    assert "Sign off" in p
    # Recent digest threaded through
    assert "Yesterday: launches" in p


def test_compose_transcript_writes_filtered_transcript(tmp_project):
    segments = [
        _seg("01-intro", "full"),
        _seg("02-news", "full"),
        _seg("03-markets", "blurb", stories=_stories(("03-markets", "h", "w", "https://e.com/a", "E"))),
        _seg("99-outro", "full"),
    ]
    transcript_text = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n"
        "## SEGMENT_BREAK 02-news\n[NARRATOR] news\n"
        "## SEGMENT_BREAK __wystk\n[NARRATOR] quick notes\n"
        "## SEGMENT_BREAK 99-outro\n[NARRATOR] bye\n"
    )
    with patch("app.script._call_anthropic", return_value=transcript_text):
        result = compose_transcript(_inputs(tmp_project, segments))
    assert result.read_text() == transcript_text


def test_compose_transcript_validates_speaker_tags(tmp_project):
    bad = "## SEGMENT_BREAK 01-intro\n[GUEST] hi\n"
    segments = [_seg("01-intro", "full")]
    with patch("app.script._call_anthropic", return_value=bad):
        with pytest.raises(ValueError, match="Unknown speaker"):
            compose_transcript(_inputs(tmp_project, segments))


def test_compose_transcript_requires_all_filtered_segment_breaks(tmp_project):
    segments = [_seg("01-intro", "full"), _seg("02-news", "full"), _seg("99-outro", "full")]
    missing = "## SEGMENT_BREAK 01-intro\n[NARRATOR] only one\n"
    with patch("app.script._call_anthropic", return_value=missing):
        with pytest.raises(ValueError, match="missing SEGMENT_BREAK"):
            compose_transcript(_inputs(tmp_project, segments))


def test_compose_transcript_rejects_unexpected_segment_break(tmp_project):
    """Empty-classified segments must NOT appear in the transcript."""
    segments = [_seg("01-intro", "full"), _seg("02-news", "empty"), _seg("99-outro", "full")]
    transcript_with_empty = (
        "## SEGMENT_BREAK 01-intro\n[NARRATOR] hi\n"
        "## SEGMENT_BREAK 02-news\n[NARRATOR] should not be here\n"
        "## SEGMENT_BREAK 99-outro\n[NARRATOR] bye\n"
    )
    with patch("app.script._call_anthropic", return_value=transcript_with_empty):
        with pytest.raises(ValueError, match="unexpected SEGMENT_BREAK"):
            compose_transcript(_inputs(tmp_project, segments))
