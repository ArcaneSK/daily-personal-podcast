from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


@dataclass(frozen=True)
class PodcastMeta:
    title: str
    description: str
    author: str
    language: str
    base_url: str


@dataclass(frozen=True)
class Persona:
    name: str
    persona: str


@dataclass(frozen=True)
class ShowConfig:
    target_total_minutes: int
    narrator: Persona
    host_a: Persona
    host_b: Persona


@dataclass(frozen=True)
class ResearchConfig:
    parallel: bool
    max_segments_concurrent: int
    per_segment_timeout_seconds: int


@dataclass(frozen=True)
class TTSConfig:
    provider: str
    cache: bool
    voices: dict[str, str]
    options: dict[str, dict[str, Any]]

    def voice_for_role(self, role: str) -> str:
        if role not in self.voices:
            raise KeyError(f"No voice configured for role {role!r}")
        return self.voices[role]


@dataclass(frozen=True)
class PublishConfig:
    output_dir: str
    recent_window_days: int
    segment_history_token_cap: int
    recent_digest_word_cap: int


@dataclass(frozen=True)
class SfxCue:
    prompt: str
    duration_seconds: float


@dataclass(frozen=True)
class SfxConfig:
    enabled: bool
    show_open: SfxCue | None
    segment_break: SfxCue | None
    show_close: SfxCue | None


@dataclass(frozen=True)
class Config:
    podcast: PodcastMeta
    show: ShowConfig
    research: ResearchConfig
    tts: TTSConfig
    publish: PublishConfig
    sfx: SfxConfig


def _persona(d: dict[str, Any]) -> Persona:
    return Persona(name=d["name"], persona=d["persona"])


def _sfx_cue(d: dict[str, Any] | None) -> SfxCue | None:
    if not d:
        return None
    return SfxCue(prompt=d["prompt"], duration_seconds=float(d["duration_seconds"]))


def _sfx_config(d: dict[str, Any] | None) -> SfxConfig:
    d = d or {}
    return SfxConfig(
        enabled=bool(d.get("enabled", False)),
        show_open=_sfx_cue(d.get("show_open")),
        segment_break=_sfx_cue(d.get("segment_break")),
        show_close=_sfx_cue(d.get("show_close")),
    )


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(
        podcast=PodcastMeta(**raw["podcast"]),
        show=ShowConfig(
            target_total_minutes=raw["show"]["target_total_minutes"],
            narrator=_persona(raw["show"]["narrator"]),
            host_a=_persona(raw["show"]["host_a"]),
            host_b=_persona(raw["show"]["host_b"]),
        ),
        research=ResearchConfig(**raw["research"]),
        tts=TTSConfig(
            provider=raw["tts"]["provider"],
            cache=raw["tts"]["cache"],
            voices=dict(raw["tts"]["voices"]),
            options=dict(raw["tts"].get("options", {})),
        ),
        publish=PublishConfig(**raw["publish"]),
        sfx=_sfx_config(raw.get("sfx")),
    )
