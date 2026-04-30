from __future__ import annotations
import argparse
import asyncio
from datetime import date as _date_cls
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

# Load .env from the project root if present, so ELEVENLABS_API_KEY (and any
# other local secrets) are picked up automatically. Does nothing if the file
# is absent. We do this at import time so every CLI subcommand sees the vars.
load_dotenv()

from app import __version__
from app.config import load_config
from app.segments import discover_segments
from app.manifest import RunManifest, SegmentEntry, write_manifest, read_manifest
from app.paths import (
    episode_dir,
    research_dir,
    transcript_path,
    episode_mp3_path,
    manifest_path,
    synthesis_manifest_path,
    tts_cache_dir,
    research_path,
    recent_digest_path,
    segment_history_path,
)
from app.research import research_segment, ResearchInputs, extract_stories
from app.script import compose_transcript, ScriptInputs
from app.synthesize import synthesize_episode
from app.tts import get_provider
from app.publish import publish_episode, PublishInputs


def cmd_prepare(args: argparse.Namespace) -> int:
    root: Path = args.root
    date: str = args.date
    cfg = load_config(root / "config.yaml")
    segments = discover_segments(root)
    if not segments:
        print("No active segments found.", flush=True)
        return 2

    edir = episode_dir(root, date)
    edir.mkdir(parents=True, exist_ok=True)
    research_dir(root, date).mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        date=date,
        segments=[SegmentEntry(id=s.id, path=str(s.path.relative_to(root)).replace("\\", "/")) for s in segments],
    )
    write_manifest(manifest_path(root, date), manifest)
    print(f"Prepared episode {date} with {len(segments)} segments.", flush=True)
    _ = cfg  # validated; not used directly in prepare
    return 0


def cmd_synthesize(args: argparse.Namespace) -> int:
    root: Path = args.root
    date: str = args.date
    cfg = load_config(root / "config.yaml")
    options = cfg.tts.options.get(cfg.tts.provider, {})
    options = {**options, "voice_for": dict(cfg.tts.voices)}
    provider = get_provider(cfg.tts.provider, options)
    synthesize_episode(
        transcript_path=transcript_path(root, date),
        out_mp3=episode_mp3_path(root, date),
        manifest_path=synthesis_manifest_path(root, date),
        cache_dir=tts_cache_dir(root),
        provider=provider,
        voice_for_role=dict(cfg.tts.voices),
        cache_enabled=cfg.tts.cache,
        provider_options_for_cache={k: v for k, v in (cfg.tts.options.get(cfg.tts.provider) or {}).items()},
    )
    print(f"Wrote {episode_mp3_path(root, date)}", flush=True)
    return 0


def cmd_research(args: argparse.Namespace) -> int:
    root: Path = args.root
    date: str = args.date
    cfg = load_config(root / "config.yaml")
    manifest = read_manifest(manifest_path(root, date))

    targets = manifest.segments
    if args.segment:
        targets = [s for s in manifest.segments if s.id == args.segment]
        if not targets:
            print(f"Segment {args.segment!r} not in manifest.", flush=True)
            return 2

    recent = ""
    rd = recent_digest_path(root)
    if rd.exists():
        recent = rd.read_text(encoding="utf-8")

    async def _run_all():
        sem = asyncio.Semaphore(cfg.research.max_segments_concurrent)

        async def _one(entry):
            async with sem:
                seg_path = root / entry.path
                history_path = segment_history_path(root, entry.id)
                history = history_path.read_text(encoding="utf-8") if history_path.exists() else ""
                inputs = ResearchInputs(
                    segment_id=entry.id,
                    segment_prose=seg_path.read_text(encoding="utf-8"),
                    segment_history=history,
                    recent_digest=recent,
                    date_iso=date,
                    out_path=research_path(root, date, entry.id),
                    timeout_seconds=cfg.research.per_segment_timeout_seconds,
                )
                return await asyncio.to_thread(research_segment, inputs)

        return await asyncio.gather(*(_one(s) for s in targets))

    results = asyncio.run(_run_all())
    for entry, result in zip(targets, results):
        manifest.set_status(entry.id, result.status)

    write_manifest(manifest_path(root, date), manifest)
    counts = {"full": 0, "blurb": 0, "empty": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    print(
        f"Researched {len(results)} segments — "
        f"{counts['full']} full, {counts['blurb']} blurb, {counts['empty']} empty.",
        flush=True,
    )
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    root: Path = args.root
    date: str = args.date
    cfg = load_config(root / "config.yaml")
    manifest = read_manifest(manifest_path(root, date))

    recent = ""
    rd = recent_digest_path(root)
    if rd.exists():
        recent = rd.read_text(encoding="utf-8")

    segments_input = []
    for s in manifest.segments:
        prose = (root / s.path).read_text(encoding="utf-8")
        history_path_ = segment_history_path(root, s.id)
        history = history_path_.read_text(encoding="utf-8") if history_path_.exists() else ""
        rpath = research_path(root, date, s.id)
        research_text = rpath.read_text(encoding="utf-8") if rpath.exists() else ""
        # Re-extract stories from the on-disk brief (single source of truth)
        stories = extract_stories(s.id, research_text) if research_text else []
        segments_input.append({
            "id": s.id,
            "status": s.status,
            "prose": prose,
            "history": history,
            "research": research_text,
            "stories": stories,
        })

    inputs = ScriptInputs(
        date_iso=date,
        target_total_minutes=cfg.show.target_total_minutes,
        narrator_name=cfg.show.narrator.name, narrator_persona=cfg.show.narrator.persona,
        host_a_name=cfg.show.host_a.name, host_a_persona=cfg.show.host_a.persona,
        host_b_name=cfg.show.host_b.name, host_b_persona=cfg.show.host_b.persona,
        recent_digest=recent,
        segments=segments_input,
        out_path=transcript_path(root, date),
    )
    out = compose_transcript(inputs)
    print(f"Wrote {out}", flush=True)
    return 0


def _make_summarizer():
    """Returns a callable (transcript_md, briefs_blob) -> summary body string. Uses claude-agent-sdk."""
    import asyncio
    import os
    from claude_agent_sdk import query, ClaudeAgentOptions  # type: ignore

    model = os.environ.get("PODCAST_SUMMARY_MODEL") or None

    def _call(transcript_md: str, briefs_blob: str) -> str:
        prompt = (
            "Summarize this podcast episode in <=250 words. Use this exact structure:\n\n"
            "## Headlines covered\n- [segment_id] One-line headline. (source-domain)\n\n"
            "## Named entities\n<comma list>\n\n"
            "## Open threads\n- [segment_id] One-liner.\n\n"
            "## Tone notes\n- One-line guidance for tomorrow.\n\n"
            f"TRANSCRIPT:\n{transcript_md}\n\nRESEARCH BRIEFS:\n{briefs_blob}\n"
        )

        async def _run() -> str:
            options = ClaudeAgentOptions(allowed_tools=[], model=model)
            chunks: list[str] = []
            async for message in query(prompt=prompt, options=options):
                text = getattr(message, "text", None) or getattr(message, "content", None)
                if isinstance(text, str):
                    chunks.append(text)
            return "".join(chunks)

        return asyncio.run(_run())

    return _call


def _make_compressor():
    """Returns a callable text -> compressed text. Uses claude-agent-sdk."""
    import asyncio
    import os
    from claude_agent_sdk import query, ClaudeAgentOptions  # type: ignore

    model = os.environ.get("PODCAST_COMPRESS_MODEL") or None

    def _call(text: str) -> str:
        prompt = (
            "Compress this history into a tight 'Background context' paragraph (<=120 words). "
            "Preserve named entities, open threads, and rough chronology. Drop repeated daily detail.\n\n"
            f"{text}\n"
        )

        async def _run() -> str:
            options = ClaudeAgentOptions(allowed_tools=[], model=model)
            chunks: list[str] = []
            async for message in query(prompt=prompt, options=options):
                text2 = getattr(message, "text", None) or getattr(message, "content", None)
                if isinstance(text2, str):
                    chunks.append(text2)
            return "".join(chunks)

        return asyncio.run(_run())

    return _call


def cmd_publish(args: argparse.Namespace) -> int:
    root: Path = args.root
    date: str = args.date
    cfg = load_config(root / "config.yaml")
    publish_episode(PublishInputs(
        root=root,
        date_iso=date,
        config=cfg,
        summarizer=_make_summarizer(),
        compressor=_make_compressor(),
    ))
    print(f"Published episode {date}", flush=True)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    root: Path = args.root
    date_iso = args.date or _date_cls.today().isoformat()

    if not args.force and episode_mp3_path(root, date_iso).exists():
        print(f"Episode {date_iso} already exists. Pass --force to overwrite.", flush=True)
        return 3

    sub_args = argparse.Namespace(root=root, date=date_iso, segment=None)
    for step in (cmd_prepare, cmd_research, cmd_script, cmd_synthesize, cmd_publish):
        rc = step(sub_args)
        if rc != 0:
            return rc
    return 0


def _todo(name: str):
    def _impl(_args: argparse.Namespace) -> int:
        raise NotImplementedError(f"CLI subcommand {name!r} not yet wired")
    return _impl


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily-personal-podcast")
    parser.add_argument("--version", action="version", version=f"daily-personal-podcast {__version__}")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root")

    sub = parser.add_subparsers(dest="cmd", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--date", required=True)
    p_prepare.set_defaults(func=cmd_prepare)

    p_research = sub.add_parser("research")
    p_research.add_argument("--date", required=True)
    p_research.add_argument("--segment", default=None)
    p_research.set_defaults(func=cmd_research)

    p_script = sub.add_parser("script")
    p_script.add_argument("--date", required=True)
    p_script.set_defaults(func=cmd_script)

    p_synth = sub.add_parser("synthesize")
    p_synth.add_argument("--date", required=True)
    p_synth.set_defaults(func=cmd_synthesize)

    p_publish = sub.add_parser("publish")
    p_publish.add_argument("--date", required=True)
    p_publish.set_defaults(func=cmd_publish)

    p_generate = sub.add_parser("generate")
    p_generate.add_argument("--date", required=False, default=None)
    p_generate.add_argument("--force", action="store_true")
    p_generate.set_defaults(func=cmd_generate)

    args = parser.parse_args(argv)
    return args.func(args)
