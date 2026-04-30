from __future__ import annotations
from dataclasses import dataclass
from datetime import date as date_cls
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


def _format_date(date_iso: str) -> str:
    """'2026-04-30' -> 'Wed, Apr 30, 2026'."""
    try:
        d = date_cls.fromisoformat(date_iso)
    except ValueError:
        return date_iso
    return d.strftime("%a, %b %d, %Y")


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["format_date"] = _format_date
    return env


def render_index(podcast: PodcastMeta, episodes: list[EpisodeView]) -> str:
    env = _env()
    tpl = env.get_template("index.html")
    eps = sorted(episodes, key=lambda e: e.date_iso, reverse=True)
    return tpl.render(podcast=podcast, episodes=eps)
