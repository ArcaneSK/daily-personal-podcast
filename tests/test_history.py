from pathlib import Path
from datetime import date
from app.history import (
    append_segment_history,
    update_recent_digest,
    estimate_tokens,
    SegmentHistoryEntry,
    RecentEntry,
)


def test_estimate_tokens_is_chars_div_4():
    assert estimate_tokens("a" * 4000) == 1000


def test_append_segment_history_full_status_writes_status_and_covered(tmp_project: Path):
    path = tmp_project / "segments" / "_history" / "02-ai-news.md"
    e = SegmentHistoryEntry(
        date_iso="2026-04-29",
        status="full",
        covered=["Opus 4.7 launch", "Agent SDK adoption"],
        open_threads=["Adoption signal next week"],
    )
    def no_compress(_text: str) -> str:
        raise AssertionError("Should not compress under cap")

    append_segment_history(path, e, token_cap=1500, compressor=no_compress)
    content = path.read_text(encoding="utf-8")
    assert "## 2026-04-29" in content
    assert "Status: full" in content
    assert "Covered:" in content
    assert "Opus 4.7 launch" in content
    assert "Adoption signal next week" in content


def test_append_segment_history_empty_status_omits_covered(tmp_project: Path):
    path = tmp_project / "segments" / "_history" / "02-ai-news.md"
    e = SegmentHistoryEntry(date_iso="2026-04-29", status="empty", covered=[], open_threads=[])
    append_segment_history(path, e, token_cap=1500, compressor=lambda _t: "")
    content = path.read_text(encoding="utf-8")
    assert "Status: empty" in content
    assert "Covered:" not in content


def test_append_segment_history_blurb_status_writes_single_headline(tmp_project: Path):
    path = tmp_project / "segments" / "_history" / "03-markets.md"
    e = SegmentHistoryEntry(date_iso="2026-04-29", status="blurb",
                            covered=["S&P closed flat"], open_threads=[])
    append_segment_history(path, e, token_cap=1500, compressor=lambda _t: "")
    content = path.read_text(encoding="utf-8")
    assert "Status: blurb" in content
    assert "Covered:" in content
    assert "S&P closed flat" in content


def test_append_segment_history_compresses_when_over_cap(tmp_project: Path):
    path = tmp_project / "segments" / "_history" / "02-ai-news.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("## 2026-04-01\nStatus: full\n" + ("filler " * 1000) + "\n", encoding="utf-8")

    def fake_compress(text: str) -> str:
        return "## Background context\n[compressed]"

    e = SegmentHistoryEntry(date_iso="2026-04-29", status="full", covered=["new"], open_threads=[])
    append_segment_history(path, e, token_cap=1500, compressor=fake_compress)
    content = path.read_text(encoding="utf-8")
    assert content.startswith("## Background context\n[compressed]")
    assert "## 2026-04-29" in content


def test_update_recent_digest_drops_old_entries(tmp_project: Path):
    path = tmp_project / "episodes" / "_recent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "## 2026-04-15\nold\n\n## 2026-04-25\nrecent\n",
        encoding="utf-8",
    )
    new_entry = RecentEntry(date_iso="2026-04-29", body="today's summary")
    update_recent_digest(
        path,
        new_entry,
        today_iso="2026-04-29",
        window_days=7,
        word_cap=500,
        compressor=lambda _text: "compressed",
    )
    content = path.read_text(encoding="utf-8")
    assert "2026-04-15" not in content     # >7 days old, dropped
    assert "2026-04-25" in content         # within window
    assert "2026-04-29" in content
    assert "today's summary" in content


def test_update_recent_digest_compresses_over_word_cap(tmp_project: Path):
    path = tmp_project / "episodes" / "_recent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    big = ("word " * 200).strip()
    path.write_text(f"## 2026-04-28\n{big}\n", encoding="utf-8")
    update_recent_digest(
        path,
        RecentEntry(date_iso="2026-04-29", body=("alpha " * 200).strip()),
        today_iso="2026-04-29",
        window_days=7,
        word_cap=300,
        compressor=lambda _text: "[compressed digest]",
    )
    content = path.read_text(encoding="utf-8")
    assert "[compressed digest]" in content
    assert "2026-04-29" in content
