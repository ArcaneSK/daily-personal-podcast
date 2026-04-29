from __future__ import annotations
import argparse
from pathlib import Path
from typing import Sequence

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
)
from app.synthesize import synthesize_episode
from app.tts import get_provider


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
    p_research.set_defaults(func=_todo("research"))

    p_script = sub.add_parser("script")
    p_script.add_argument("--date", required=True)
    p_script.set_defaults(func=_todo("script"))

    p_synth = sub.add_parser("synthesize")
    p_synth.add_argument("--date", required=True)
    p_synth.set_defaults(func=cmd_synthesize)

    p_publish = sub.add_parser("publish")
    p_publish.add_argument("--date", required=True)
    p_publish.set_defaults(func=_todo("publish"))

    p_generate = sub.add_parser("generate")
    p_generate.add_argument("--date", required=False, default=None)
    p_generate.add_argument("--force", action="store_true")
    p_generate.set_defaults(func=_todo("generate"))

    args = parser.parse_args(argv)
    return args.func(args)
