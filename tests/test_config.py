# tests/test_config.py
from pathlib import Path
import pytest
from app.config import load_config, Config


FIXTURE = Path(__file__).parent / "fixtures" / "config-minimal.yaml"


def test_load_config_returns_typed_object():
    cfg = load_config(FIXTURE)
    assert isinstance(cfg, Config)
    assert cfg.podcast.title == "Test Podcast"
    assert cfg.show.target_total_minutes == 25
    assert cfg.show.host_a.name == "Sam"
    assert cfg.research.max_segments_concurrent == 4
    assert cfg.tts.provider == "fake"
    assert cfg.tts.voices["host_a"] == "voice_a"
    assert cfg.publish.recent_window_days == 7


def test_load_config_missing_required_section_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("podcast: {title: x, description: y, author: z, language: en, base_url: https://a/}\n")
    with pytest.raises(KeyError):
        load_config(bad)


def test_voice_for_role_lookup():
    cfg = load_config(FIXTURE)
    assert cfg.tts.voice_for_role("host_a") == "voice_a"
    assert cfg.tts.voice_for_role("host_b") == "voice_b"


def test_voice_for_role_unknown_raises():
    cfg = load_config(FIXTURE)
    with pytest.raises(KeyError):
        cfg.tts.voice_for_role("nobody")
