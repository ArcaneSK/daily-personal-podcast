"""ElevenLabs sound-effects helper.

Generates short stinger / segue audio via ElevenLabs' sound-generation API
and caches the results on disk. Stingers are reused across episodes — they
should not be regenerated every day.

Public surface is small:

    ensure_stingers(cfg.sfx, cache_dir, api_key) -> dict[str, Path]

returning a mapping of cue id ("show_open" / "segment_break" / "show_close")
to a cached mp3 file. Cues that are disabled or missing return an empty
mapping so callers can no-op.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import httpx

from app.config import SfxConfig, SfxCue


_API_URL = "https://api.elevenlabs.io/v1/sound-generation"


def _cue_key(cue: SfxCue) -> str:
    payload = json.dumps(
        {"prompt": cue.prompt, "duration": cue.duration_seconds}, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _generate_one(api_key: str, cue: SfxCue, out_path: Path) -> None:
    """Synchronously call the ElevenLabs sound-generation API and write the
    returned mp3 bytes to ``out_path``."""
    payload = {
        "text": cue.prompt,
        "duration_seconds": cue.duration_seconds,
        # 0.3 = leans more toward the prompt; ~the documented default.
        "prompt_influence": 0.3,
    }
    headers = {"xi-api-key": api_key, "accept": "audio/mpeg"}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(_API_URL, headers=headers, json=payload)
        r.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(r.content)


def ensure_stingers(
    sfx: SfxConfig,
    cache_dir: Path,
    api_key: str | None = None,
) -> dict[str, Path]:
    """Return a dict of {cue_id: mp3_path} for whatever stingers are enabled
    and cached (or freshly generated). Disabled cues are absent from the dict.
    """
    if not sfx.enabled:
        return {}

    cues: list[tuple[str, SfxCue | None]] = [
        ("show_open", sfx.show_open),
        ("segment_break", sfx.segment_break),
        ("show_close", sfx.show_close),
    ]

    out: dict[str, Path] = {}
    pending: list[tuple[str, SfxCue, Path]] = []
    for cue_id, cue in cues:
        if cue is None:
            continue
        target = cache_dir / f"{cue_id}-{_cue_key(cue)}.mp3"
        if target.exists() and target.stat().st_size > 0:
            out[cue_id] = target
        else:
            pending.append((cue_id, cue, target))

    if not pending:
        return out

    key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        # Surface upstream — caller should treat as "SFX skipped" not crash.
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set; cannot generate SFX stingers"
        )

    for cue_id, cue, target in pending:
        _generate_one(key, cue, target)
        out[cue_id] = target

    return out


def cleanup_stale(cache_dir: Path, keep_paths: Iterable[Path]) -> None:
    """Optional: remove cached stingers that aren't referenced by current
    config (e.g., after the prompt was edited)."""
    keep = {p.resolve() for p in keep_paths}
    if not cache_dir.exists():
        return
    for p in cache_dir.glob("*.mp3"):
        if p.resolve() not in keep:
            p.unlink(missing_ok=True)
