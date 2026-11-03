#!/usr/bin/env python3
"""The exit checks of srstudio's govern lanes: a lane leaves a stage on what the repository and Drive say (ADR 0058).

    python3 tools/govern/lane_check.py merged LANE_DIR     # the lane's branch is in develop
    python3 tools/govern/lane_check.py published LANE_DIR  # the publish check is clean
    python3 tools/govern/lane_check.py on-drive LANE_DIR   # Drive holds every staged file of the lane's pilot series
    python3 tools/govern/lane_check.py reviewed LANE_DIR   # every reel's frames and comedy read by a non-author

``LANE_DIR/lane.json`` names the ``branch``, for pilots the ``series`` and for reel batches the ``reels``, and refuses
any other field. ``LANE_DIR/reviews.json`` maps each reel to its ``author``, its ``reviewer``, the ``comedy`` pair
(author's score, reviewer's) and the ``frames`` the reviewer read at full size, and refuses any other field. A check
that passes prints one line and exits 0. A failed or unreadable one prints why and exits 2. Every check only reads.
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

from srstudio.comedy_floor import FLOOR

REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO.parent
LANE_FILE = "lane.json"
REVIEWS_FILE = "reviews.json"
FIELDS = frozenset({"branch", "series", "reels"})
REVIEW_FIELDS = frozenset({"author", "reviewer", "comedy", "frames"})
MIN_FRAMES = 4  # the first, 2 s, 75 % and the last, before any shot change adds to them
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


def read_lane(directory: Path) -> Mapping[str, Any]:
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


def _merged(lane: Mapping[str, Any], _directory: Path, run: Run) -> None:
    branch = lane["branch"]
    argv = ["git", "-C", str(REPO), "merge-base", "--is-ancestor", branch, "develop"]
    if run(argv, capture_output=True, text=True).returncode != 0:
        raise LaneError(f"{branch} is not in develop")


def _published(lane: Mapping[str, Any], _directory: Path, run: Run) -> None:
    script = str(REPO / "episodes" / "instagram_posts.py")
    argv = [sys.executable, script, "check", "generated/renders/ig", "generated/renders", "--fonts", "generated/fonts"]
    done = run(argv, capture_output=True, text=True, cwd=WORKSPACE, env={**os.environ, **ENGINE_PATHS})
    if done.returncode != 0:
        raise LaneError(f"the publish check failed:\n{done.stdout}{done.stderr}")


def _on_drive(lane: Mapping[str, Any], _directory: Path, run: Run) -> None:
    series = lane.get("series")
    if not isinstance(series, str) or SERIES.fullmatch(series) is None:
        raise LaneError(f"a pilot lane needs a series, got {series!r}")
    remote = f"gdrive:srstudio/pilots/{series}"
    argv = ["rclone", "check", f"generated/pilots/{series}", remote, "--checksum", "--one-way"]
    done = run(argv, capture_output=True, text=True, cwd=WORKSPACE)
    if done.returncode != 0:
        raise LaneError(f"{remote} differs from the stage:\n{done.stderr}")


def _review_problems(slug: str, review: Any) -> list[str]:
    """What keeps one reel's review from counting."""
    if not isinstance(review, dict):
        return [f"{slug}: a review must be an object"]
    unknown = sorted(set(review) - REVIEW_FIELDS)
    if unknown:
        return [f"{slug}: unknown fields: {', '.join(unknown)}"]
    author, reviewer, comedy, frames = (review.get(field) for field in ("author", "reviewer", "comedy", "frames"))
    problems = []
    if not (isinstance(author, str) and author and isinstance(reviewer, str) and reviewer):
        problems.append(f"{slug}: needs an author and a reviewer")
    elif author == reviewer:
        problems.append(f"{slug}: {reviewer} reviewed their own reel")
    scored = isinstance(comedy, list) and len(comedy) == 2 and all(type(score) is int for score in comedy)
    if not scored:
        problems.append(f"{slug}: comedy must be the pair of scores, got {comedy!r}")
    elif min(comedy) < FLOOR:
        problems.append(f"{slug}: comedy {min(comedy)} is under the floor of {FLOOR}")
    if type(frames) is not int or frames < MIN_FRAMES:
        problems.append(f"{slug}: needs at least {MIN_FRAMES} frames read at full size, got {frames!r}")
    return problems


def _reviewed(lane: Mapping[str, Any], directory: Path, _run: Run) -> None:
    reels = lane.get("reels")
    if not isinstance(reels, list) or not reels or not all(isinstance(reel, str) for reel in reels):
        raise LaneError(f"a reel lane needs its reels, got {reels!r}")
    path = directory / REVIEWS_FILE
    try:
        reviews: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise LaneError(f"no {REVIEWS_FILE} in {directory}") from error
    except (OSError, ValueError) as error:
        raise LaneError(f"{path} is unreadable: {error}") from error
    if not isinstance(reviews, dict):
        raise LaneError(f"{path} must hold an object")
    problems = [f"{slug}: not reviewed" for slug in reels if slug not in reviews]
    problems += [f"{slug}: not one of the lane's reels" for slug in sorted(set(reviews) - set(reels))]
    for slug in reels:
        if slug in reviews:
            problems += _review_problems(slug, reviews[slug])
    if problems:
        raise LaneError("; ".join(problems))


CHECKS = {"merged": _merged, "published": _published, "on-drive": _on_drive, "reviewed": _reviewed}


def check(name: str, directory: Path, run: Run = subprocess.run) -> None:
    """Run one exit check; :class:`LaneError` says why the lane may not leave its stage."""
    if name not in CHECKS:
        raise LaneError(f"unknown check {name!r}")
    CHECKS[name](read_lane(directory), directory, run)


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
