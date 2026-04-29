from __future__ import annotations
import os
from typing import Any
from elevenlabs.client import ElevenLabs

from app.tts.base import VoiceClip


class ElevenLabsProvider:
    name: str = "elevenlabs"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "eleven_turbo_v2_5",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        voice_for: dict[str, str] | None = None,
        **_: Any,
    ):
        key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set; cannot use ElevenLabs provider")
        self._client = ElevenLabs(api_key=key)
        self._model = model
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._voice_for = voice_for or {}

    def synthesize(self, text: str, voice_id: str) -> VoiceClip:
        stream = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=self._model,
            voice_settings={"stability": self._stability, "similarity_boost": self._similarity_boost},
        )
        audio = b"".join(stream)
        return VoiceClip(audio_bytes=audio, mime_type="audio/mpeg", sample_rate=None)

    def voice_for_role(self, role: str) -> str:
        if role not in self._voice_for:
            raise KeyError(f"No ElevenLabs voice configured for role {role!r}")
        return self._voice_for[role]
