import pytest
from pathlib import Path
import shutil


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A temporary directory pre-seeded with the canonical project layout."""
    for d in ["app", "segments", "segments/_history", "episodes", "docs"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def frozen_date() -> str:
    return "2026-04-29"
