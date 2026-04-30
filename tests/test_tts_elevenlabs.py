from unittest.mock import patch, MagicMock
from app.tts.elevenlabs import ElevenLabsProvider
from app.tts.base import VoiceClip


def test_synthesize_calls_sdk_and_wraps_clip():
    fake_client = MagicMock()
    # ElevenLabs SDK returns an iterator of bytes chunks for streaming convert calls.
    fake_client.text_to_speech.convert.return_value = iter([b"\x00\x01", b"\x02\x03"])
    with patch("app.tts.elevenlabs.ElevenLabs", return_value=fake_client):
        p = ElevenLabsProvider(api_key="fake", model="eleven_turbo_v2_5", voice_for={
            "host_a": "vA", "host_b": "vB"
        })
        clip = p.synthesize("hi", voice_id="vN")
    assert isinstance(clip, VoiceClip)
    assert clip.audio_bytes == b"\x00\x01\x02\x03"
    assert clip.mime_type == "audio/mpeg"
    assert clip.sample_rate is None  # unknown without decoding; downstream probes
    fake_client.text_to_speech.convert.assert_called_once()
    kwargs = fake_client.text_to_speech.convert.call_args.kwargs
    assert kwargs["voice_id"] == "vN"
    assert kwargs["text"] == "hi"
    assert kwargs["model_id"] == "eleven_turbo_v2_5"


def test_voice_for_role_uses_constructor_map():
    p = ElevenLabsProvider(api_key="x", voice_for={"host_a": "vA", "host_b": "vB"})
    assert p.voice_for_role("host_b") == "vB"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    import pytest
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        ElevenLabsProvider(voice_for={"host_a": "vA", "host_b": "vB"})
