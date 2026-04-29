# tests/test_research.py
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from app.research import research_segment, ResearchInputs, ResearchResult, extract_stories, _publication_from_url


def _inputs(tmp_project: Path) -> ResearchInputs:
    seg = tmp_project / "segments" / "02-ai-news.md"
    seg.write_text("Cover AI news with focus on agent frameworks.\n", encoding="utf-8")
    return ResearchInputs(
        segment_id="02-ai-news",
        segment_prose=seg.read_text(encoding="utf-8"),
        segment_history="",
        recent_digest="Yesterday: launches.",
        date_iso="2026-04-29",
        out_path=tmp_project / "episodes" / "2026-04-29" / "research" / "02-ai-news.md",
        timeout_seconds=60,
    )


def test_research_segment_classifies_full_when_two_plus_sources(tmp_project):
    fake_brief = (
        "# Research brief\n## Top stories (prioritized)\n"
        "### 1. Headline A\n- **What happened:** A thing.\n- **Source:** https://anthropic.com/news/x\n"
        "### 2. Headline B\n- **What happened:** Another.\n- **Source:** https://www.theverge.com/y\n"
    )
    with patch("app.research._call_agent_sdk", return_value=fake_brief):
        result = research_segment(_inputs(tmp_project))
    assert isinstance(result, ResearchResult)
    assert result.status == "full"
    assert len(result.stories) == 2
    assert result.stories[0].source_publication == "Anthropic"
    assert result.stories[1].source_publication == "Theverge"
    assert result.brief_path.exists()


def test_research_segment_classifies_blurb_for_single_source(tmp_project):
    fake_brief = (
        "## Top stories (prioritized)\n"
        "### 1. One headline\n- **What happened:** singular.\n- **Source:** https://example.com/a\n"
    )
    with patch("app.research._call_agent_sdk", return_value=fake_brief):
        result = research_segment(_inputs(tmp_project))
    assert result.status == "blurb"
    assert len(result.stories) == 1


def test_research_segment_classifies_empty_for_zero_sources(tmp_project):
    thin = "## Top stories (prioritized)\n\n(no stories found today)\n"
    with patch("app.research._call_agent_sdk", return_value=thin):
        result = research_segment(_inputs(tmp_project))
    assert result.status == "empty"
    assert result.stories == []
    assert result.brief_path.exists()  # the thin brief is still written


def test_research_segment_classifies_empty_on_exception(tmp_project):
    with patch("app.research._call_agent_sdk", side_effect=RuntimeError("boom")):
        result = research_segment(_inputs(tmp_project))
    assert result.status == "empty"
    assert result.brief_path.exists()
    assert "no fresh research available" in result.brief_path.read_text().lower()


def test_research_prompt_includes_required_sections(tmp_project):
    captured = {}
    def fake_call(prompt: str, *, timeout_seconds: int) -> str:
        captured["prompt"] = prompt
        return "## Top stories (prioritized)\n### 1. real\n- **Source:** https://x.com/y\n### 2. r2\n- **Source:** https://z.com/q\n"
    with patch("app.research._call_agent_sdk", side_effect=fake_call):
        research_segment(_inputs(tmp_project))
    p = captured["prompt"]
    assert "TODAY: 2026-04-29" in p
    assert "Cover AI news with focus on agent frameworks" in p
    assert "Yesterday: launches" in p


def test_extract_stories_parses_what_happened_and_source():
    brief = (
        "## Top stories (prioritized)\n"
        "### 1. First\n- **What happened:** Sentence one. Sentence two.\n- **Source:** https://anthropic.com/x\n- **Date:** today\n"
        "### 2. Second\n- **What happened:** Other.\n- **Source:** https://www.openai.com/y\n"
    )
    stories = extract_stories("02-ai-news", brief)
    assert len(stories) == 2
    assert stories[0].headline == "First"
    assert "Sentence one" in stories[0].what_happened
    assert stories[0].source_url == "https://anthropic.com/x"
    assert stories[0].source_publication == "Anthropic"
    assert stories[1].source_publication == "Openai"


def test_publication_from_url_strips_www_and_tld():
    assert _publication_from_url("https://www.theverge.com/path") == "Theverge"
    assert _publication_from_url("https://anthropic.com/news") == "Anthropic"
    assert _publication_from_url("not a url") == ""
