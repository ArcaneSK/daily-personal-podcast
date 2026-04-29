from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
import re


_SYSTEM_PROMPT = """You are a research agent producing a brief for a daily podcast segment.
Find current, sourced information using the provided web tools. Output the structured
brief format below, exactly. Do not write a podcast script — just facts with sources.
Stay focused on the listener's interests as described in the segment instructions.
"""


@dataclass(frozen=True)
class Story:
    segment_id: str
    headline: str
    what_happened: str
    source_url: str
    source_publication: str   # derived from URL host (e.g., "anthropic.com" -> "Anthropic")


@dataclass(frozen=True)
class ResearchInputs:
    segment_id: str
    segment_prose: str
    segment_history: str
    recent_digest: str
    date_iso: str
    out_path: Path
    timeout_seconds: int = 180


@dataclass(frozen=True)
class ResearchResult:
    brief_path: Path
    status: str           # "full" | "blurb" | "empty"
    stories: list[Story] = field(default_factory=list)


def _build_prompt(inp: ResearchInputs) -> str:
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"TODAY: {inp.date_iso}\n\n"
        f"GLOBAL RECENT DIGEST (cross-segment continuity):\n{inp.recent_digest}\n\n"
        f"SEGMENT HISTORY (recent themes for this segment):\n{inp.segment_history or '(none)'}\n\n"
        f"SEGMENT INSTRUCTIONS:\n{inp.segment_prose}\n\n"
        "Produce the brief now in this exact format. If you find no current, sourced "
        "stories worth a listener's attention, return the brief with zero numbered stories — "
        "do not invent filler. If you find exactly one strong story, return only that one.\n\n"
        "# Research brief: <segment name>\n"
        f"Date: {inp.date_iso}\n\n"
        "## Top stories (prioritized)\n\n"
        "### 1. <One-line headline>\n"
        "- **What happened:** [2-3 sentences, factual]\n"
        "- **Why it matters:** [1-2 sentences, framed for the listener's interests]\n"
        "- **Source:** [URL]\n"
        "- **Date:** [Source publication date]\n"
        "- **Continuity:** [Optional]\n\n"
        "## Honorable mentions\n- [One-liner + URL]\n\n"
        "## Open threads to revisit\n- [Thread + URL + why it's not ready yet]\n"
    )


def _call_agent_sdk(prompt: str, *, timeout_seconds: int) -> str:
    """Invoke claude-agent-sdk with web tools enabled. Returns the agent's final text output."""
    import asyncio
    from claude_agent_sdk import query, ClaudeAgentOptions  # type: ignore

    async def _run() -> str:
        options = ClaudeAgentOptions(allowed_tools=["WebSearch", "WebFetch"])
        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            text = getattr(message, "text", None) or getattr(message, "content", None)
            if isinstance(text, str):
                chunks.append(text)
        return "".join(chunks)

    return asyncio.run(asyncio.wait_for(_run(), timeout=timeout_seconds))


# Story extraction
_STORY_RE = re.compile(
    r"^###\s+\d+\.\s+(.+?)\n((?:.|\n)*?)(?=\n###\s+\d+\.|\n##\s|\Z)",
    re.MULTILINE,
)
_WHAT_HAPPENED_RE = re.compile(
    r"\*\*What happened:\*\*\s*(.+?)(?=\n\s*[-*]\s|\n###|\n##|\Z)",
    re.DOTALL,
)
_SOURCE_RE = re.compile(r"\*\*Source:\*\*\s*(\S+)")


def _publication_from_url(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "")
    except Exception:
        return ""
    if not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[-2].replace("-", " ").title()
    return host.title()


def extract_stories(segment_id: str, brief_md: str) -> list[Story]:
    """Parse the brief's 'Top stories' section into structured Story records.
    Only stories with a parseable Source URL are returned."""
    out: list[Story] = []
    for m in _STORY_RE.finditer(brief_md):
        headline = m.group(1).strip()
        body = m.group(2)
        wm = _WHAT_HAPPENED_RE.search(body)
        what = (wm.group(1).strip() if wm else "")
        sm = _SOURCE_RE.search(body)
        if not sm:
            continue
        url = sm.group(1).strip()
        out.append(Story(
            segment_id=segment_id,
            headline=headline,
            what_happened=what,
            source_url=url,
            source_publication=_publication_from_url(url),
        ))
    return out


def _classify(stories: list[Story]) -> str:
    if not stories:
        return "empty"
    if len(stories) == 1:
        return "blurb"
    return "full"


def _empty_placeholder(date_iso: str, segment_id: str) -> str:
    return (
        f"# Research brief: {segment_id}\n"
        f"Date: {date_iso}\n\n"
        "## Top stories (prioritized)\n\n"
        "(no fresh research available — empty run; segment will be skipped or rolled into WYSTK)\n"
    )


def research_segment(inp: ResearchInputs) -> ResearchResult:
    inp.out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = _call_agent_sdk(_build_prompt(inp), timeout_seconds=inp.timeout_seconds)
    except Exception:
        inp.out_path.write_text(_empty_placeholder(inp.date_iso, inp.segment_id), encoding="utf-8")
        return ResearchResult(brief_path=inp.out_path, status="empty", stories=[])

    inp.out_path.write_text(text, encoding="utf-8")
    stories = extract_stories(inp.segment_id, text)
    return ResearchResult(brief_path=inp.out_path, status=_classify(stories), stories=stories)
