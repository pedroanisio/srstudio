"""An installed consumer can check Timeline calls without exposing the source tree."""

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


def test_installed_package_exposes_timeline_types(tmp_path):
    environment = tmp_path / "consumer-env"
    venv.EnvBuilder().create(environment)
    python = environment / "bin" / "python"
    site = subprocess.check_output(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True
    ).strip()
    package = Path(__file__).resolve().parents[1] / "src" / "srstudio"
    shutil.copytree(package, Path(site) / "srstudio", ignore=shutil.ignore_patterns("__pycache__"))
    env = {key: value for key, value in os.environ.items() if key not in {"MYPYPATH", "PYTHONPATH"}}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--python-executable",
            str(python),
            "--follow-imports=silent",
            "--no-incremental",
            "-c",
            'from srstudio import Timeline\nTimeline.from_dict("invalid")',
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "import-untyped" not in result.stdout, result.stdout + result.stderr
    assert result.returncode == 1, result.stdout + result.stderr
    assert "arg-type" in result.stdout and "dict" in result.stdout, result.stdout + result.stderr
