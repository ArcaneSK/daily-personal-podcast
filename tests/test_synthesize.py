# tests/test_synthesize.py
from pathlib import Path
import json
import wave
from app.synthesize import synthesize_episode, SynthesisManifest, _cache_key
from app.tts.fake import FakeProvider


TRANSCRIPT = """## SEGMENT_BREAK 01-intro

[HOST_A] Hello there.
[HOST_A] Today's show.

## SEGMENT_BREAK 02-ai-news

[HOST_A] First story.
[HOST_B] Counterpoint.
"""


def _voice_map():
    return {"host_a": "vA", "host_b": "vB"}


def test_synthesize_writes_mp3_and_manifest(tmp_project: Path):
    transcript_path = tmp_project / "episodes" / "2026-04-29" / "transcript.md"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(TRANSCRIPT, encoding="utf-8")

    provider = FakeProvider(sample_rate=24000)
    out_mp3 = tmp_project / "episodes" / "2026-04-29" / "episode.mp3"
    manifest_path = tmp_project / "episodes" / "2026-04-29" / "synthesis-manifest.json"
    cache_dir = tmp_project / "episodes" / ".cache" / "tts"

    synthesize_episode(
        transcript_path=transcript_path,
        out_mp3=out_mp3,
        manifest_path=manifest_path,
        cache_dir=cache_dir,
        provider=provider,
        voice_for_role=_voice_map(),
        cache_enabled=True,
    )

    assert out_mp3.exists() and out_mp3.stat().st_size > 0
    assert manifest_path.exists()
    m = json.loads(manifest_path.read_text())
    assert m["chunks"]
    # 3 speech chunks (HOST_A lines merge) + 2 segment breaks = 5 entries
    assert sum(1 for c in m["chunks"] if c["kind"] == "speech") == 3
    assert sum(1 for c in m["chunks"] if c["kind"] == "break") == 2


def test_cache_hit_skips_provider_call(tmp_project: Path, monkeypatch):
    # Pre-populate cache for a known chunk; verify provider is not called for it.
    transcript = "## SEGMENT_BREAK 01-intro\n[HOST_A] one chunk only.\n"
    tp = tmp_project / "episodes" / "2026-04-29" / "transcript.md"
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text(transcript, encoding="utf-8")

    provider = FakeProvider(sample_rate=24000)
    cache_dir = tmp_project / "episodes" / ".cache" / "tts"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Synthesize once to populate cache.
    synthesize_episode(
        transcript_path=tp,
        out_mp3=tmp_project / "episodes" / "2026-04-29" / "episode.mp3",
        manifest_path=tmp_project / "episodes" / "2026-04-29" / "synthesis-manifest.json",
        cache_dir=cache_dir,
        provider=provider,
        voice_for_role={"host_a": "vA", "host_b": "vB"},
        cache_enabled=True,
    )

    # Now wrap the provider so a second call would raise.
    class Boom:
        sample_rate = 24000
        name = "fake"
        def synthesize(self, *a, **k): raise AssertionError("Provider should not be called on cache hit")
        def voice_for_role(self, role): return "vN"

    synthesize_episode(
        transcript_path=tp,
        out_mp3=tmp_project / "episodes" / "2026-04-29" / "episode.mp3",
        manifest_path=tmp_project / "episodes" / "2026-04-29" / "synthesis-manifest.json",
        cache_dir=cache_dir,
        provider=Boom(),
        voice_for_role={"host_a": "vA", "host_b": "vB"},
        cache_enabled=True,
    )


def test_cache_key_is_stable_and_includes_voice():
    k1 = _cache_key(provider_name="fake", voice_id="v1", text="hello", options={"x": 1})
    k2 = _cache_key(provider_name="fake", voice_id="v1", text="hello", options={"x": 1})
    k3 = _cache_key(provider_name="fake", voice_id="v2", text="hello", options={"x": 1})
    assert k1 == k2
    assert k1 != k3
