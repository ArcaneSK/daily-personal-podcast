from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from app.transcript import parse_transcript, SegmentBreak


WYSTK_ID = "__wystk"


_SYSTEM_PROMPT = """You are scripting a daily personal podcast for one listener.
Output a transcript with explicit speaker tags. Speakers are exactly: [NARRATOR], [HOST_A], [HOST_B].
Use ## SEGMENT_BREAK <segment-id> markers between segments (one before each segment, in rundown order).
Include a SEGMENT_BREAK for every id in the rundown — and ONLY those ids. Do not invent additional segments.
Stay within roughly the target durations per segment (1 spoken minute is about 150 words).
Cite sources by name in spoken text where natural (e.g. "Anthropic announced...", "per The Information").
Do not invent facts. Do not include URLs in spoken text — those go to show notes; spoken text uses
publication names.
If the rundown contains "__wystk" ("What you should know today"), produce a single narrator-only segment
that opens with a brief framing line ("A few quick notes before we close...") and weaves each blurb listed
in the BLURBS section into one or two sentences. The total spoken length of __wystk should be roughly
45 to 90 seconds (about 110-225 words), regardless of the global target.
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


def build_filtered_rundown(segments: list[dict]) -> tuple[list[dict], list, bool]:
    """Apply the §7 spec algorithm:
    - Identify outro = last segment by original order whose id starts with '99-'.
    - For body segments (non-outro): full -> rundown; blurb -> blurbs[]; empty -> drop.
    - Outro: kept as closer if not 'empty', regardless of full/blurb classification.
    - Insert '__wystk' before outro (or at end if no outro) when blurbs is non-empty.
    Raises if everything would be dropped.
    Returns (rundown_items, blurbs_list, has_outro).
    """
    # Find positional outro (last 99- by original order)
    outro_idx = -1
    for i, s in enumerate(segments):
        if _is_outro_id(s["id"]):
            outro_idx = i
    outro_seg = segments[outro_idx] if outro_idx != -1 else None

    body: list[dict] = []
    blurbs: list = []  # list[Story]
    for i, s in enumerate(segments):
        if i == outro_idx:
            continue  # handled separately
        status = s["status"]
        if status == "full":
            body.append(s)
        elif status == "blurb":
            blurbs.extend(s.get("stories", []))
        # empty: drop

    rundown = list(body)

    has_outro = outro_seg is not None and outro_seg["status"] != "empty"
    if blurbs:
        rundown.append({"id": WYSTK_ID, "status": "wystk", "blurbs": blurbs})
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
        f"Narrator: {inp.narrator_name} — {inp.narrator_persona}",
        f"Host A: {inp.host_a_name} — {inp.host_a_persona}",
        f"Host B: {inp.host_b_name} — {inp.host_b_persona}",
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


def _call_anthropic(prompt: str) -> str:
    """Single call to Claude via the Anthropic SDK. Returns the model's text output."""
    from anthropic import Anthropic  # type: ignore
    import os
    client = Anthropic()
    model = os.environ.get("PODCAST_SCRIPT_MODEL", "claude-opus-4-7")
    resp = client.messages.create(
        model=model,
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    out = []
    for block in resp.content:
        text = getattr(block, "text", None)
        if text:
            out.append(text)
    return "".join(out)


def compose_transcript(inp: ScriptInputs) -> Path:
    rundown, _blurbs, _has_outro = build_filtered_rundown(inp.segments)
    expected_ids = [s["id"] for s in rundown]

    prompt = build_prompt(inp)
    text = _call_anthropic(prompt)

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
