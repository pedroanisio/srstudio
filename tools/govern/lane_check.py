#!/usr/bin/env python3
"""The exit checks of srstudio's govern lanes: a lane leaves a stage on what the repository and Drive say (ADR 0058).

    python3 tools/govern/lane_check.py merged LANE_DIR     # the lane's branch is in develop
    python3 tools/govern/lane_check.py published LANE_DIR  # the publish check is clean
    python3 tools/govern/lane_check.py on-drive LANE_DIR   # Drive holds every staged file of the lane's pilot series

``LANE_DIR/lane.json`` names the ``branch`` and, for pilots, the ``series``, and refuses any other field. A check that
passes prints one line and exits 0. A failed or unreadable one prints why and exits 2. Every check only reads.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO.parent
LANE_FILE = "lane.json"
FIELDS = frozenset({"branch", "series"})
BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
SERIES = re.compile(r"[a-z][a-z0-9-]*")
ENGINE_PATHS = {
    "SRSTUDIO_ENGINE": "generated/bin/scene-render",
    "SRSTUDIO_RENDERS": "generated/renders",
    "SRSTUDIO_FONTS": "generated/fonts",
}

Run = Callable[..., "subprocess.CompletedProcess[str]"]


class LaneError(ValueError):
    """A lane's check failed, or its lane file cannot be trusted."""


def read_lane(directory: Path) -> Mapping[str, str]:
    """The lane's file, or :class:`LaneError` for one that is missing, malformed or holds an unknown field."""
    path = directory / LANE_FILE
    try:
        lane: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise LaneError(f"no {LANE_FILE} in {directory}") from error
    except (OSError, ValueError) as error:
        raise LaneError(f"{path} is unreadable: {error}") from error
    if not isinstance(lane, dict):
        raise LaneError(f"{path} must hold an object")
    unknown = sorted(set(lane) - FIELDS)
    if unknown:
        raise LaneError(f"{path} has unknown fields: {', '.join(unknown)}")
    branch = lane.get("branch")
    if not isinstance(branch, str) or BRANCH.fullmatch(branch) is None:
        raise LaneError(f"{path} needs a branch name, got {branch!r}")
    return lane


def _merged(lane: Mapping[str, str], run: Run) -> None:
    branch = lane["branch"]
    argv = ["git", "-C", str(REPO), "merge-base", "--is-ancestor", branch, "develop"]
    if run(argv, capture_output=True, text=True).returncode != 0:
        raise LaneError(f"{branch} is not in develop")


def _published(lane: Mapping[str, str], run: Run) -> None:
    script = str(REPO / "episodes" / "instagram_posts.py")
    argv = [sys.executable, script, "check", "generated/renders/ig", "generated/renders", "--fonts", "generated/fonts"]
    done = run(argv, capture_output=True, text=True, cwd=WORKSPACE, env={**os.environ, **ENGINE_PATHS})
    if done.returncode != 0:
        raise LaneError(f"the publish check failed:\n{done.stdout}{done.stderr}")


def _on_drive(lane: Mapping[str, str], run: Run) -> None:
    series = lane.get("series")
    if not isinstance(series, str) or SERIES.fullmatch(series) is None:
        raise LaneError(f"a pilot lane needs a series, got {series!r}")
    remote = f"gdrive:srstudio/pilots/{series}"
    argv = ["rclone", "check", f"generated/pilots/{series}", remote, "--checksum", "--one-way"]
    done = run(argv, capture_output=True, text=True, cwd=WORKSPACE)
    if done.returncode != 0:
        raise LaneError(f"{remote} differs from the stage:\n{done.stderr}")


CHECKS = {"merged": _merged, "published": _published, "on-drive": _on_drive}


def check(name: str, directory: Path, run: Run = subprocess.run) -> None:
    """Run one exit check; :class:`LaneError` says why the lane may not leave its stage."""
    if name not in CHECKS:
        raise LaneError(f"unknown check {name!r}")
    CHECKS[name](read_lane(directory), run)


def main(argv: Sequence[str] | None = None, run: Run = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("check")
    parser.add_argument("lane", type=Path)
    options = parser.parse_args(argv)
    try:
        check(options.check, options.lane, run)
    except LaneError as error:
        print(f"{options.check}: {error}", file=sys.stderr)
        return 2
    print(f"{options.check}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
