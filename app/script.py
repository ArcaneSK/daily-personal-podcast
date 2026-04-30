from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from app.transcript import parse_transcript, SegmentBreak


WYSTK_ID = "__wystk"


_SYSTEM_PROMPT = """You are scripting a daily personal podcast for one listener.

The show is a two-host conversation. Host names and personas are provided
below in the user prompt — use those names verbatim in your reasoning, but
always tag spoken lines with [HOST_A] and [HOST_B], not the names.

- HOST_A is THE DRIVER: opens, transitions between segments, asks the obvious
  questions, keeps the pace moving, closes the show. Talks first and last;
  lines are usually shorter.
- HOST_B is THE INFO-BRINGER: delivers the facts, names the sources, adds
  analysis and depth. Most substantive content is in HOST_B's lines.
  Can show genuine excitement when something matters.
- They have a real back-and-forth — HOST_A sets up, HOST_B delivers, HOST_A
  reacts or pulls a thread, HOST_B expands. Keep turns short — usually 1-2
  sentences, rarely 3.

DON'T BURY THE LEDE. EQUALLY IMPORTANT.
For each segment, ask: "what was THE story today?" — the biggest, most
consequential item in that segment's research brief. That goes FIRST. Lead with
the dominant story; only after it's covered do you move to second-tier items
and niche details.

If the brief has a clearly dominant story (a frontier model release, an Apple
earnings beat, a Supreme Court ruling, a major fusion milestone), it leads the
segment. Niche items follow. Don't open a segment with the third-most-important
story because it's more interesting to you stylistically — the listener gets
the day's biggest story first, every time.

Within each segment, prioritize roughly: 60% of segment time on the top story,
30% on second-tier, 10% on the rest. If the day is quiet and there's no
dominant story, lead with the most consequential of what you have and say so
plainly ("quiet day in markets, but here's what moved").

WRITE TIGHT. EQUALLY IMPORTANT.
The listener wants signal, not chatter. Every line earns its place by carrying
information or moving the show forward.

Concrete rules:
- LEAD WITH THE POINT. Not "so it turns out that what's really interesting here
  is…" — instead, "Anthropic shipped MCP connectors for Adobe today." Start
  with the verb and the fact.
- NO PREAMBLE. Cut: "Well…", "So…", "I think the interesting thing is…",
  "What's wild about this is…", "Let me tell you about…", "Here's the thing…",
  "Speaking of which…", "Now…", "Alright, so…", "Yeah, exactly." If a line
  starts with throat-clearing, delete the preamble and keep the substance.
- NO RESTATEMENT. Don't have one host repeat what the other just said in
  different words ("So basically what you're saying is…"). The other host's
  reaction should add a thread, not summarize.
- NO HEDGE PADDING. Cut "kind of", "sort of", "I mean", "you know", "right?",
  "to be clear", "obviously" unless they're load-bearing.
- ONE THOUGHT PER LINE. If a line has two ideas connected by "and also" or
  "but more importantly", split them or pick one.
- DENSE FACTS. When HOST_B delivers a story, name the company, the thing, and
  the number that matters in the first sentence. Save context for the
  second sentence only if the listener needs it.
- AVOID META-COMMENTARY. Don't describe what the show is doing
  ("In this segment we'll cover…" / "Moving on now to…"). Just do it.
- CUT QUESTIONS THAT DON'T PULL A THREAD. HOST_A's questions should be
  ones a listener actually has — "what does that mean for NVIDIA?" — not
  filler ones — "huh, interesting?".

Word budget per line is ~15-25 words for HOST_A, ~25-50 words for HOST_B, with
the longer end reserved for substantive single-thought delivery.

Output a transcript with explicit speaker tags. Speakers are exactly: [HOST_A]
and [HOST_B]. Do NOT use [NARRATOR]. Every spoken line must be tagged.

Use ## SEGMENT_BREAK <segment-id> markers between segments (one before each
segment, in rundown order). Include a SEGMENT_BREAK for every id in the rundown
— and ONLY those ids. Do not invent additional segments.

Show structure (keep this shape strictly):
1. The first segment in the rundown is the show open. Begin it with a "cold
   open" — HOST_B delivers the day's sharpest fact in one sentence ("Apple
   missed by ten cents tonight."), HOST_A reacts in 3-5 words ("wait, what?"),
   then HOST_A does a tight show open: greet, name the show, the date, and
   the rundown in one breath. ~25-35 seconds total. No throat-clearing.
2. The body segments follow in rundown order. HOST_A transitions in tight —
   "First up, AI news." — and immediately hands to HOST_B. No preamble before
   the transition.
3. If the rundown contains "__wystk" ("What you should know today"), it's the
   penultimate segment. HOST_A's setup is one short line ("Quick hits before
   we close."); HOST_B then delivers each blurb from the BLURBS section as
   one tight sentence. Aim for ~40-70 seconds total, not 90.
4. The final segment (the outro) is HOST_A closing the show — one line
   thank-you, one line forward look (HOST_B can have it), one line sign-off.
   ~10-15 seconds total.

Stay within roughly the target durations per segment (1 spoken minute ≈ 150
words). If you find yourself padding to hit a target, the target was wrong —
end short and crisp instead. Cite sources by name in spoken text where
natural ("Anthropic announced…", "per The Information"). Do not invent
facts. Do not include URLs in spoken text — those go to show notes.

Output only the transcript. No prologue, no commentary outside the speaker tags."""


@dataclass
class ScriptInputs:
    date_iso: str
    target_total_minutes: int
    narrator_name: str
    narrator_persona: str
    host_a_name: str
    host_a_persona: str
    host_b_name: str
    host_b_persona: str
    recent_digest: str
    # Each segment dict: {id, status, prose, history, research, stories: list[Story]}
    segments: list[dict]
    out_path: Path


def _is_outro_id(seg_id: str) -> bool:
    return seg_id.startswith("99-")


def _is_intro_id(seg_id: str) -> bool:
    return seg_id.startswith("01-")


def build_filtered_rundown(segments: list[dict]) -> tuple[list[dict], list, bool]:
    """Apply the §7 spec algorithm with intro/outro slots ALWAYS preserved:
    - Identify intro = first segment whose id starts with '01-' (positional).
    - Identify outro = last segment whose id starts with '99-' (positional).
    - Intro and outro are narrator-driven shells; they are kept in the rundown
      regardless of research status (their prose typically opts out of research
      and they will classify as 'empty', but structurally they must remain so
      the cold open and outro show up where the spec promises).
    - For body segments (non-intro, non-outro): full -> rundown; blurb -> blurbs[];
      empty -> drop.
    - Insert '__wystk' before outro (or at end if no outro) when blurbs is non-empty.
    Raises if everything would be dropped.
    Returns (rundown_items, blurbs_list, has_outro).
    """
    intro_idx = -1
    for i, s in enumerate(segments):
        if _is_intro_id(s["id"]):
            intro_idx = i
            break
    outro_idx = -1
    for i, s in enumerate(segments):
        if _is_outro_id(s["id"]):
            outro_idx = i
    intro_seg = segments[intro_idx] if intro_idx != -1 else None
    outro_seg = segments[outro_idx] if outro_idx != -1 else None

    body: list[dict] = []
    blurbs: list = []  # list[Story]
    for i, s in enumerate(segments):
        if i == intro_idx or i == outro_idx:
            continue  # handled separately
        status = s["status"]
        if status == "full":
            body.append(s)
        elif status == "blurb":
            blurbs.extend(s.get("stories", []))
        # empty: drop

    rundown: list[dict] = []
    if intro_seg is not None:
        rundown.append(intro_seg)
    rundown.extend(body)
    if blurbs:
        rundown.append({"id": WYSTK_ID, "status": "wystk", "blurbs": blurbs})
    has_outro = outro_seg is not None
    if has_outro:
        rundown.append(outro_seg)

    if not rundown:
        raise ValueError("No segments to script: every segment is empty.")
    return rundown, blurbs, has_outro


def build_prompt(inp: ScriptInputs) -> str:
    rundown, blurbs, _ = build_filtered_rundown(inp.segments)

    parts: list[str] = [
        _SYSTEM_PROMPT,
        "",
        f"TODAY: {inp.date_iso}",
        "",
        f"Total target length: ~{inp.target_total_minutes} minutes",
        f"Host A (driver): {inp.host_a_name} — {inp.host_a_persona}",
        f"Host B (info-bringer): {inp.host_b_name} — {inp.host_b_persona}",
        "",
        "GLOBAL RECENT DIGEST (cross-segment continuity):",
        inp.recent_digest or "(empty)",
        "",
        "RUNDOWN (after status-aware filtering — produce SEGMENT_BREAK exactly for these ids, in this order):",
    ]
    for i, s in enumerate(rundown, start=1):
        parts.append(f"  {i}. {s['id']}")
    parts.append("")
    parts.append("BLURBS (one block per blurb segment; weave these into the __wystk segment if present):")
    if blurbs:
        for st in blurbs:
            parts.extend([
                f"  - segment_id: {st.segment_id}",
                f"    headline: {st.headline}",
                f"    what_happened: {st.what_happened}",
                f"    source_publication: {st.source_publication}",
            ])
    else:
        parts.append("  (none)")
    parts.append("")

    # Body sections: only for entries that came from segments[] (not __wystk synthetic)
    for s in rundown:
        if s["id"] == WYSTK_ID:
            continue
        parts.append(f"--- SEGMENT {s['id']} ---")
        parts.append("PROSE INSTRUCTIONS:")
        parts.append(s["prose"])
        parts.append("")
        if s.get("history"):
            parts.append("SEGMENT HISTORY (recent themes):")
            parts.append(s["history"])
            parts.append("")
        parts.append("RESEARCH BRIEF:")
        parts.append(s.get("research", "(none)"))
        parts.append("")
    parts.append("Produce the full transcript now.")
    return "\n".join(parts)


def _call_claude(prompt: str) -> str:
    """Single call to Claude via claude-agent-sdk. Returns the model's text output."""
    import asyncio
    import os
    from claude_agent_sdk import query, ClaudeAgentOptions  # type: ignore

    model = os.environ.get("PODCAST_SCRIPT_MODEL") or None

    async def _run() -> str:
        options = ClaudeAgentOptions(allowed_tools=[], model=model)
        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            # See research.py: ResultMessage.result is the final consolidated text.
            result = getattr(message, "result", None)
            if isinstance(result, str):
                chunks.append(result)
        return "".join(chunks)

    return asyncio.run(_run())


def compose_transcript(inp: ScriptInputs) -> Path:
    rundown, _blurbs, _has_outro = build_filtered_rundown(inp.segments)
    expected_ids = [s["id"] for s in rundown]

    prompt = build_prompt(inp)
    text = _call_claude(prompt)

    items = parse_transcript(text)  # raises on unknown speaker tags

    # Verify the transcript covers EXACTLY the filtered rundown
    seen_breaks = [it.segment_id for it in items if isinstance(it, SegmentBreak)]
    missing = set(expected_ids) - set(seen_breaks)
    if missing:
        raise ValueError(f"Transcript is missing SEGMENT_BREAK for segments: {sorted(missing)}")
    unexpected = set(seen_breaks) - set(expected_ids)
    if unexpected:
        raise ValueError(f"Transcript contains unexpected SEGMENT_BREAK: {sorted(unexpected)}")

    inp.out_path.parent.mkdir(parents=True, exist_ok=True)
    inp.out_path.write_text(text, encoding="utf-8")

    # Soft word-count warnings (CLI stderr only). __wystk is exempt.
    import sys
    countable = [sid for sid in expected_ids if sid != WYSTK_ID]
    if countable:
        target_per_segment = (inp.target_total_minutes * 150) / len(countable)
        for seg_id in countable:
            words = sum(len(it.text.split()) for it in items
                        if not isinstance(it, SegmentBreak) and it.segment_id == seg_id)
            if words and abs(words - target_per_segment) / target_per_segment > 0.25:
                print(
                    f"WARN: segment {seg_id} word count {words} is more than ±25% off "
                    f"target ({target_per_segment:.0f}).",
                    file=sys.stderr,
                )
    return inp.out_path
