"""TTS provider registry. Real registry lives in Task 8; this is a placeholder so imports work."""
from app.tts.base import VoiceClip, TTSProvider  # re-export
from app.tts.fake import FakeProvider

__all__ = ["VoiceClip", "TTSProvider", "FakeProvider"]
