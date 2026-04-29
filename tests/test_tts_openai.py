from unittest.mock import patch, MagicMock
import pytest
from app.tts.openai import OpenAIProvider
from app.tts.base import VoiceClip


def test_synthesize_calls_openai_and_returns_clip():
    response = MagicMock()
    response.read.return_value = b"\xff\xfb\x90"
    fake_client = MagicMock()
    fake_client.audio.speech.create.return_value = response
    with patch("app.tts.openai.OpenAI", return_value=fake_client):
        p = OpenAIProvider(api_key="x", voice_for={"narrator": "alloy", "host_a": "echo", "host_b": "onyx"})
        clip = p.synthesize("hi", voice_id="alloy")
    assert isinstance(clip, VoiceClip)
    assert clip.audio_bytes == b"\xff\xfb\x90"
    assert clip.mime_type == "audio/mpeg"
    fake_client.audio.speech.create.assert_called_once()
    kwargs = fake_client.audio.speech.create.call_args.kwargs
    assert kwargs["voice"] == "alloy"
    assert kwargs["input"] == "hi"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIProvider(voice_for={"narrator": "alloy", "host_a": "echo", "host_b": "onyx"})
