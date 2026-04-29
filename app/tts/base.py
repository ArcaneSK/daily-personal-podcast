from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VoiceClip:
    audio_bytes: bytes
    mime_type: str           # e.g. "audio/mpeg" or "audio/wav"
    sample_rate: int | None  # None if unknown — caller probes


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, voice_id: str) -> VoiceClip: ...
    def voice_for_role(self, role: str) -> str: ...
