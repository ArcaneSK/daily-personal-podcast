from __future__ import annotations
import asyncio
from typing import Any
import edge_tts

from app.tts.base import VoiceClip


class EdgeProvider:
    name: str = "edge"

    def __init__(self, voice_for: dict[str, str] | None = None, **_: Any):
        self._voice_for = voice_for or {}

    def synthesize(self, text: str, voice_id: str) -> VoiceClip:
        return asyncio.run(self._synthesize_async(text, voice_id))

    async def _synthesize_async(self, text: str, voice_id: str) -> VoiceClip:
        communicate = edge_tts.Communicate(text, voice_id)
        chunks: list[bytes] = []
        async for ev in communicate.stream():
            if ev.get("type") == "audio":
                chunks.append(ev["data"])
        return VoiceClip(audio_bytes=b"".join(chunks), mime_type="audio/mpeg", sample_rate=None)

    def voice_for_role(self, role: str) -> str:
        if role not in self._voice_for:
            raise KeyError(f"No Edge voice configured for role {role!r}")
        return self._voice_for[role]
