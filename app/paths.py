from pathlib import Path


def episode_dir(root: Path, date: str) -> Path:
    return root / "episodes" / date


def research_dir(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "research"


def research_path(root: Path, date: str, segment_id: str) -> Path:
    return research_dir(root, date) / f"{segment_id}.md"


def transcript_path(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "transcript.md"


def episode_mp3_path(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "episode.mp3"


def show_notes_path(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "show-notes.md"


def summary_path(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "summary.md"


def manifest_path(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "run-manifest.json"


def synthesis_manifest_path(root: Path, date: str) -> Path:
    return episode_dir(root, date) / "synthesis-manifest.json"


def recent_digest_path(root: Path) -> Path:
    return root / "episodes" / "_recent.md"


def segment_history_path(root: Path, segment_id: str) -> Path:
    return root / "segments" / "_history" / f"{segment_id}.md"


def tts_cache_dir(root: Path) -> Path:
    return root / "episodes" / ".cache" / "tts"


def docs_episode_dir(root: Path, date: str) -> Path:
    return root / "docs" / "episodes" / date


def docs_episode_mp3(root: Path, date: str) -> Path:
    return docs_episode_dir(root, date) / "episode.mp3"


def rss_path(root: Path) -> Path:
    return root / "docs" / "podcast.xml"
