import os
import shutil
import sys
from pathlib import Path

import pytest

from fakes import make_mp3
from srstudio.sample import Line, write_sample_project

LINES = [
    Line("manager", "What's your greatest strength?", 1.3, caption="What's your greatest\nstrength?"),
    Line("candidate", "I'm fast at math.", 1.1),
    Line("manager", "Seventeen times nineteen?", 1.2),
    Line("candidate", "Forty-two.", 0.8),
]


@pytest.fixture(scope="session")
def project(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("project")
    write_sample_project(root, LINES, angles=["wide", "close", "wide", "close"])
    return root


@pytest.fixture(scope="session")
def packages() -> Path:
    """Folder holding the extracted packages (``<name>-<version>/project``), or skip."""
    env = os.environ.get("SRSTUDIO_PACKAGES")
    if not env or not Path(env).is_dir():
        pytest.skip("set SRSTUDIO_PACKAGES to the folder of extracted .vpkg projects")
    return Path(env)


@pytest.fixture(scope="session")
def scene_render() -> Path:
    """The scene-render binary (``$SRSTUDIO_ENGINE``, else ``scene-render`` on the PATH), or skip: a test that runs
    the engine cannot pass without one."""
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).is_file():
        pytest.skip("runs the scene-render engine: set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


@pytest.fixture
def fake_env(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    assert make_mp3(tmp_path / "tone.mp3")
    return {
        "SR_PROVIDER_SRSTUDIO_ELEVENLABS": f"{sys.executable} {Path(__file__).parent / 'fake_provider.py'}",
        "FAKE_MP3": str(tmp_path / "tone.mp3"),
        "FAKE_LOG": str(tmp_path / "calls.log"),
    }
