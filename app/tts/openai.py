from __future__ import annotations
import os
from typing import Any
from openai import OpenAI

from app.tts.base import VoiceClip


class OpenAIProvider:
    name: str = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "tts-1",
        voice_for: dict[str, str] | None = None,
        **_: Any,
    ):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set; cannot use OpenAI provider")
        self._client = OpenAI(api_key=key)
        self._model = model
        self._voice_for = voice_for or {}

    def synthesize(self, text: str, voice_id: str) -> VoiceClip:
        resp = self._client.audio.speech.create(
            model=self._model,
            voice=voice_id,
            input=text,
            response_format="mp3",
        )
        return VoiceClip(audio_bytes=resp.read(), mime_type="audio/mpeg", sample_rate=None)

    def voice_for_role(self, role: str) -> str:
        if role not in self._voice_for:
            raise KeyError(f"No OpenAI voice configured for role {role!r}")
        return self._voice_for[role]
