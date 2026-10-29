"""Releases: what each published episode declares about its delivery, one file per episode.

A release folder is a Python package; every public module in it (``<slug with underscores>.py``) defines
``RELEASE``, a :class:`Release` naming the episode's slug, its Instagram post, the rendered video's name and whether
the cover is drawn from the ``cover`` variant of its scene (:meth:`srstudio.episode.Episode.hide_on_cover`).
Modules whose name starts with ``_`` hold constants the releases share (a series' hashtags) and are not releases.

A new episode adds its own file instead of editing a shared table, so sessions publishing at once do not collide.
:func:`load` refuses a folder it cannot trust (a module without a release, a file named for another slug, two
releases claiming one video), and :func:`items` checks every declared cover against the scene that was built: a
scene that hides its burned-in text on the cover while its release does not say so would put the headline over a
ghost caption, so the two must agree.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import SrstudioError
from .social import COVER_VARIANT, InstagramPost, Item

__all__ = ["Release", "ReleaseError", "load", "items"]

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class ReleaseError(SrstudioError, ValueError):
    """A release, or a folder of them, cannot be published as declared."""


@dataclass(frozen=True)
class Release:
    """``slug`` names the episode project (``<episodes>/<slug>/``); ``video`` is the rendered video's file name
    without extension (the slug when empty); ``scene`` is the project's scene file (``<slug>.scene.xml`` when
    empty); ``cover`` says the cover's backdrop is drawn from that scene's ``cover`` variant; ``builder`` is the stem
    of the episode's build script when it is not the slug with underscores."""

    slug: str
    post: InstagramPost
    video: str = ""
    scene: str = ""
    cover: bool = False
    builder: str = ""

    def __post_init__(self) -> None:
        if not SLUG.fullmatch(self.slug):
            raise ReleaseError(f"slug {self.slug!r} is not lowercase words joined by hyphens")
        if not isinstance(self.post, InstagramPost):
            raise ReleaseError(f"{self.slug}: post is a {type(self.post).__name__}, not an InstagramPost")
        if self.video and not NAME.fullmatch(self.video):
            raise ReleaseError(f"{self.slug}: video {self.video!r} is not a plain file name")
        if self.scene and not (NAME.fullmatch(self.scene) and self.scene.endswith("scene.xml")):
            raise ReleaseError(f"{self.slug}: scene {self.scene!r} is not a plain *scene.xml file name")
        if self.builder and not self.builder.isidentifier():
            raise ReleaseError(f"{self.slug}: builder {self.builder!r} is not a module name")

    @property
    def video_name(self) -> str:
        return self.video or self.slug

    @property
    def scene_file(self) -> str:
        return self.scene or f"{self.slug}.scene.xml"

    @property
    def script(self) -> str:
        """The release file's stem: the slug with underscores."""
        return self.slug.replace("-", "_")

    @property
    def builder_name(self) -> str:
        """The stem of the script that builds the episode (``<builder_name>.py``): :attr:`script` unless told."""
        return self.builder or self.script


def _package(folder: Path) -> str:
    init = folder / "__init__.py"
    if not init.is_file():
        raise ReleaseError(f"{folder} is not a release package: it has no __init__.py")
    name = "_srstudio_releases_" + hashlib.sha256(str(folder).encode()).hexdigest()[:16]
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, init, submodule_search_locations=[str(folder)])
        if spec is None or spec.loader is None:  # pragma: no cover - a file location always yields a spec
            raise ReleaseError(f"cannot import {folder}")
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
    return name


def load(folder: Path) -> dict[str, Release]:
    """Every release in ``folder``, keyed by slug in slug order."""
    folder = Path(folder).resolve()
    package = _package(folder)
    found: dict[str, Release] = {}
    videos: dict[str, str] = {}
    for file in sorted(folder.glob("*.py")):
        if file.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{package}.{file.stem}")
        except Exception as exc:
            raise ReleaseError(f"{file.name} cannot be imported: {exc}") from exc
        if not hasattr(module, "RELEASE"):
            raise ReleaseError(f"{file.name} defines no RELEASE")
        release = module.RELEASE
        if not isinstance(release, Release):
            raise ReleaseError(f"{file.name}: RELEASE is a {type(release).__name__}, not a Release")
        if release.script != file.stem:
            raise ReleaseError(f"{file.name} declares {release.slug!r}: name the file {release.script}.py")
        if release.video_name in videos:
            raise ReleaseError(f"{release.slug} and {videos[release.video_name]} both claim video {release.video_name}")
        videos[release.video_name] = release.slug
        found[release.slug] = release
    return dict(sorted(found.items()))


def _has_cover_variant(scene: Path) -> bool:
    try:
        for _, element in ET.iterparse(scene, events=("start",)):
            if element.tag == "variant" and element.get("id") == COVER_VARIANT:
                return True
    except ET.ParseError as exc:
        raise ReleaseError(f"cannot read {scene}: {exc}") from exc
    return False


def items(releases: Mapping[str, Release], renders: Path, episodes: Path) -> dict[str, Item]:
    """Every release with its rendered video and the scene its cover is drawn from, keyed by the video's name.

    Where the scene is built in ``episodes``, its ``cover`` variant must exist exactly when the release declares
    ``cover``; a project not built here is taken at its word."""
    renders, episodes = Path(renders), Path(episodes)
    out: dict[str, Item] = {}
    for release in releases.values():
        scene = episodes / release.slug / release.scene_file
        if scene.is_file():
            varied = _has_cover_variant(scene)
            if varied and not release.cover:
                raise ReleaseError(f"{release.slug}: {scene.name} hides its text on the cover; declare cover=True")
            if release.cover and not varied:
                raise ReleaseError(f"{release.slug}: {scene.name} has no cover variant, but the release says cover")
        out[release.video_name] = Item(
            release.post, renders / f"{release.video_name}.mp4", scene if release.cover else None
        )
    return out
