from __future__ import annotations
import io
import math
import struct
import wave
from dataclasses import dataclass

from app.tts.base import VoiceClip


_ROLE_MAP = {"narrator": "fake_narrator", "host_a": "fake_host_a", "host_b": "fake_host_b"}


@dataclass
class FakeProvider:
    sample_rate: int = 24000
    name: str = "fake"

    def synthesize(self, text: str, voice_id: str) -> VoiceClip:
        # Duration scales with text length so concatenation remains audible-distinguishable in tests.
        seconds = max(0.4, min(8.0, len(text) * 0.06))
        # Voice id seeds frequency (deterministic) so voice changes produce different bytes.
        freq = 220.0 + (sum(ord(c) for c in voice_id) % 600)
        n_frames = int(seconds * self.sample_rate)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            for i in range(n_frames):
                value = int(0.4 * 32767 * math.sin(2 * math.pi * freq * i / self.sample_rate))
                wf.writeframes(struct.pack("<h", value))
        return VoiceClip(audio_bytes=buf.getvalue(), mime_type="audio/wav", sample_rate=self.sample_rate)

    def voice_for_role(self, role: str) -> str:
        if role not in _ROLE_MAP:
            raise KeyError(f"Unknown role {role!r}")
        return _ROLE_MAP[role]
