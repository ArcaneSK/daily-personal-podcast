from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import PodcastMeta


@dataclass(frozen=True)
class EpisodeView:
    date_iso: str
    title: str
    show_notes_html: str
    mp3_relpath: str    # relative to the page being rendered
    duration_label: str # "MM:SS"


_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_index(podcast: PodcastMeta, episodes: list[EpisodeView]) -> str:
    env = _env()
    tpl = env.get_template("index.html")
    eps = sorted(episodes, key=lambda e: e.date_iso, reverse=True)
    return tpl.render(podcast=podcast, episodes=eps)


def render_episode(podcast: PodcastMeta, episode: EpisodeView) -> str:
    env = _env()
    tpl = env.get_template("episode.html")
    return tpl.render(podcast=podcast, episode=episode)
