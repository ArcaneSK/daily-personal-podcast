# tests/test_tts_edge.py
from unittest.mock import patch, AsyncMock
from app.tts.edge import EdgeProvider
from app.tts.base import VoiceClip


def test_synthesize_runs_async_and_collects_bytes():
    async def fake_stream():
        yield {"type": "audio", "data": b"\xab\xcd"}
        yield {"type": "audio", "data": b"\xef"}

    fake_communicate = AsyncMock()
    fake_communicate.stream = fake_stream  # plain attribute access, returns async iterator
    with patch("app.tts.edge.edge_tts.Communicate", return_value=fake_communicate):
        p = EdgeProvider(voice_for={"host_a": "en-US-GuyNeural", "host_b": "en-GB-RyanNeural"})
        clip = p.synthesize("hi", voice_id="en-US-AriaNeural")
    assert isinstance(clip, VoiceClip)
    assert clip.mime_type == "audio/mpeg"
    assert clip.audio_bytes == b"\xab\xcd\xef"
