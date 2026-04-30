import math
import struct
import wave
import io
from app.tts.fake import FakeProvider
from app.tts.base import VoiceClip


def test_fake_provider_returns_wav_bytes_at_known_rate():
    p = FakeProvider(sample_rate=24000)
    clip = p.synthesize("hello world", voice_id="voice_a")
    assert isinstance(clip, VoiceClip)
    assert clip.mime_type == "audio/wav"
    assert clip.sample_rate == 24000
    # Validate it's a real wav we can read back
    with wave.open(io.BytesIO(clip.audio_bytes)) as wf:
        assert wf.getframerate() == 24000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        # ~ 11 chars * 0.06s/char = ~0.66s of audio. Allow generous slack.
        frames = wf.getnframes()
        seconds = frames / 24000
        assert 0.3 <= seconds <= 5.0


def test_fake_provider_voice_for_role_returns_distinct_ids():
    p = FakeProvider(sample_rate=24000)
    assert p.voice_for_role("host_a") == "fake_host_a"
    assert p.voice_for_role("host_b") == "fake_host_b"


def test_fake_provider_is_deterministic():
    p1 = FakeProvider(sample_rate=24000)
    p2 = FakeProvider(sample_rate=24000)
    a = p1.synthesize("test", voice_id="v1").audio_bytes
    b = p2.synthesize("test", voice_id="v1").audio_bytes
    assert a == b


def test_fake_provider_voice_id_changes_pitch():
    p = FakeProvider(sample_rate=24000)
    a = p.synthesize("test", voice_id="v1").audio_bytes
    b = p.synthesize("test", voice_id="v2").audio_bytes
    assert a != b
