from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any
import hashlib
import io
import json
import wave

from pydub import AudioSegment
from pydub.silence import detect_leading_silence  # noqa: F401  (kept available)

from app.transcript import parse_transcript, chunk_for_synthesis, Chunk
from app.tts.base import VoiceClip


@dataclass
class ChunkRecord:
    kind: str            # "speech" | "break"
    role: str | None
    segment_id: str
    text: str | None
    cache_key: str | None
    duration_ms: int


@dataclass
class SynthesisManifest:
    chunks: list[ChunkRecord] = field(default_factory=list)
    sample_rate: int = 24000


def _cache_key(*, provider_name: str, voice_id: str, text: str, options: dict[str, Any]) -> str:
    payload = json.dumps(
        {"p": provider_name, "v": voice_id, "t": text, "o": options},
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _decode(clip: VoiceClip) -> AudioSegment:
    if clip.mime_type == "audio/wav":
        return AudioSegment.from_file(io.BytesIO(clip.audio_bytes), format="wav")
    if clip.mime_type == "audio/mpeg":
        return AudioSegment.from_file(io.BytesIO(clip.audio_bytes), format="mp3")
    # Fallback: let pydub auto-detect
    return AudioSegment.from_file(io.BytesIO(clip.audio_bytes))


def _load_cached(cache_dir: Path, key: str) -> AudioSegment | None:
    blob = cache_dir / f"{key}.bin"
    meta = cache_dir / f"{key}.json"
    if not (blob.exists() and meta.exists()):
        return None
    info = json.loads(meta.read_text(encoding="utf-8"))
    clip = VoiceClip(
        audio_bytes=blob.read_bytes(),
        mime_type=info["mime_type"],
        sample_rate=info.get("sample_rate"),
    )
    return _decode(clip)


def _store_cache(cache_dir: Path, key: str, clip: VoiceClip) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.bin").write_bytes(clip.audio_bytes)
    (cache_dir / f"{key}.json").write_text(
        json.dumps({"mime_type": clip.mime_type, "sample_rate": clip.sample_rate}),
        encoding="utf-8",
    )


def _silence(ms: int, frame_rate: int) -> AudioSegment:
    return AudioSegment.silent(duration=ms, frame_rate=frame_rate)


def synthesize_episode(
    *,
    transcript_path: Path,
    out_mp3: Path,
    manifest_path: Path,
    cache_dir: Path,
    provider: Any,
    voice_for_role: dict[str, str],
    cache_enabled: bool = True,
    provider_options_for_cache: dict[str, Any] | None = None,
) -> None:
    """Synthesize the transcript into an mp3 at out_mp3, writing a manifest at manifest_path."""
    items = parse_transcript(transcript_path.read_text(encoding="utf-8"))
    chunks = chunk_for_synthesis(items, max_chars=1000)

    # Determine sample rate: trust provider declaration, else probe first speech clip.
    sample_rate: int | None = getattr(provider, "sample_rate", None)
    decoded: list[tuple[Chunk, AudioSegment, str | None]] = []  # (chunk, audio, cache_key)

    for c in chunks:
        if c.kind == "break":
            decoded.append((c, _silence(600, sample_rate or 24000), None))
            continue

        voice_id = voice_for_role[c.role]
        key = _cache_key(
            provider_name=getattr(provider, "name", provider.__class__.__name__),
            voice_id=voice_id,
            text=c.text,
            options=provider_options_for_cache or {},
        )
        seg: AudioSegment | None = None
        if cache_enabled:
            seg = _load_cached(cache_dir, key)

        if seg is None:
            clip = provider.synthesize(c.text, voice_id=voice_id)
            if cache_enabled:
                _store_cache(cache_dir, key, clip)
            seg = _decode(clip)
            if sample_rate is None and clip.sample_rate is not None:
                sample_rate = clip.sample_rate

        # If we still don't know rate, take it from the decoded segment
        if sample_rate is None:
            sample_rate = seg.frame_rate
        # Normalize to channel count and bit depth (we always use mono 16-bit)
        seg = seg.set_channels(1).set_sample_width(2).set_frame_rate(sample_rate)

        # Sanity: too short for the text length is suspicious
        if len(seg) < 300 and len(c.text) > 10:
            raise RuntimeError(
                f"Synthesis returned suspiciously short audio ({len(seg)}ms) for chunk: {c.text[:60]!r}"
            )
        decoded.append((c, seg, key))

    # Stitch
    rate = sample_rate or 24000
    final = AudioSegment.silent(duration=0, frame_rate=rate)
    last_role: str | None = None
    for c, seg, _key in decoded:
        if c.kind == "break":
            final += seg
            last_role = None
            continue
        if last_role is None:
            final += seg
        elif last_role == c.role:
            final += AudioSegment.silent(duration=250, frame_rate=rate) + seg
        else:
            # Speaker switch: small crossfade
            final = final.append(seg, crossfade=80)
        last_role = c.role

    # Peak normalize (target -1 dB)
    if final.max_dBFS != float("-inf"):
        final = final.apply_gain(-1.0 - final.max_dBFS)

    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    final.export(out_mp3, format="mp3", bitrate="128k")

    # Manifest
    manifest = SynthesisManifest(sample_rate=rate)
    for c, seg, key in decoded:
        manifest.chunks.append(ChunkRecord(
            kind=c.kind,
            role=c.role,
            segment_id=c.segment_id,
            text=c.text,
            cache_key=key,
            duration_ms=len(seg),
        ))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
