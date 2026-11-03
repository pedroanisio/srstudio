"""A reel's first delivery is refused when its scene declares no safe area (ADR 0218).

arc4d3, Slack 1793678456.387679: "Every scene declares its safe area, not only multi-character dances, and the overlay
check refuses a scene without one." A library episode declares its style's area when it is built
(:class:`~srstudio.episode.EpisodeSpec`), but a scene can be written outside :class:`~srstudio.episode.Episode`, or
built before the rule. This gate reads the scene that is about to go out, so it holds whatever wrote it. It runs on a
first delivery only: a video in the manifest is published and frozen, and nothing here asks it to change. It reads the
scene, so it needs no engine.
"""

from __future__ import annotations

import zipfile
from collections.abc import Mapping
from pathlib import Path

from .layout import LayoutError, UndeclaredSafeAreaError, declared_safe_area
from .releases import Release
from .social import Drift

__all__ = ["MISSING", "UNDECLARED", "defect", "package_defect", "undeclared"]

UNDECLARED = "its scene declares no safe area (ADR 0218): declare the style's or its own"
MISSING = "no scene to read its safe area from: a gate that reads nothing passes nothing"


def defect(document: bytes) -> str:
    """Why ``document`` cannot go out for its safe area, or ``""``."""
    try:
        declared_safe_area(document)
    except UndeclaredSafeAreaError:
        return UNDECLARED
    except LayoutError as e:
        return str(e)
    return ""


def undeclared(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> list[Drift]:
    """The reels on their ``first`` delivery (slug to video name) whose scene in ``episodes`` declares no safe area,
    or has no scene to read."""
    drift: list[Drift] = []
    for slug, video in sorted(first.items()):
        scene = Path(episodes) / slug / releases[slug].scene_file
        if not scene.is_file():
            drift.append(Drift(video, MISSING))
        elif why := defect(scene.read_bytes()):
            drift.append(Drift(video, why))
    return drift


def package_defect(package: Path, slug: str) -> str:
    """Why the pilot ``slug`` packed in ``package`` (a ``vpkg.zip`` with ``project/<slug>.scene.xml``) cannot go out
    for its safe area, or ``""``."""
    name = f"project/{slug}.scene.xml"
    try:
        with zipfile.ZipFile(package) as z:
            if name not in z.namelist():
                return f"no {name} in {Path(package).name}: {MISSING}"
            return defect(z.read(name))
    except zipfile.BadZipFile:
        return f"{Path(package).name} is not a zip, so its scene cannot be read"
