"""TTS provider registry."""
from __future__ import annotations
from importlib import import_module
from typing import Any

from app.tts.base import VoiceClip, TTSProvider
from app.tts.fake import FakeProvider

# Built-in provider names → factory callable. Real provider classes self-register lazily
# so we don't pay import cost for unused providers.
_BUILTINS: dict[str, str] = {
    "fake": "app.tts.fake.FakeProvider",
    "elevenlabs": "app.tts.elevenlabs.ElevenLabsProvider",
    "openai": "app.tts.openai.OpenAIProvider",
    "edge": "app.tts.edge.EdgeProvider",
}


def _resolve(dotted: str):
    module_name, _, attr = dotted.rpartition(".")
    if not module_name:
        raise KeyError(f"Provider spec {dotted!r} is not a module path")
    module = import_module(module_name)
    return getattr(module, attr)


def get_provider(name: str, options: dict[str, Any]) -> TTSProvider:
    """Resolve a provider by builtin name or fully-qualified module path, instantiating with options."""
    if name in _BUILTINS:
        cls = _resolve(_BUILTINS[name])
    elif "." in name:
        cls = _resolve(name)
    else:
        raise KeyError(f"Unknown TTS provider {name!r} (not in registry, not a module path)")
    return cls(**options)


__all__ = ["VoiceClip", "TTSProvider", "FakeProvider", "get_provider"]
