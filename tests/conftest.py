import os
from pathlib import Path

import pytest

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
