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
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import craft
from .comedy_floor import Scores
from .errors import SrstudioError
from .parts import PartError, pin, read_record
from .social import COVER_VARIANT, Drift, InstagramPost, Item

__all__ = ["Release", "ReleaseError", "Tags", "doubled_captions", "grandfathered", "load", "items", "unpinned"]

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
CHARACTER = re.compile(r"[a-z][a-z0-9-]*")
FINGERPRINT = re.compile(r"[0-9a-f]{64}")

TERRITORIES = (
    "everyday-tech",
    "money-services",
    "job-hunting",
    "relationships",
    "family",
    "own-worst-enemy",
    "epic-world",
    "office",
)
CAUSES = ("institution", "other-person", "protagonist")
EMOTIONS = ("recognition", "embarrassment", "tension", "relief", "affection", "triumph")
TESTS = ("opening", "rhythm", "jargon", "sp-hook_motion")  # sp-: the posting job's own test ids
ARMS = ("a", "b")
RECIPIENTS = ("partner", "family", "best friend", "roommate", "work friend")  # who arm b of the recipient test is for


class ReleaseError(SrstudioError, ValueError):
    """A release, or a folder of them, cannot be published as declared."""


@dataclass(frozen=True)
class Tags:
    """What the account's analytics compare across episodes: the ``territory`` the premise comes from, the
    ``cause`` of the problem (an institution, another person or the protagonist), the ``emotion`` it leaves, the
    ``recurring`` characters it brings back (their registered short names), and, for an episode in a running A/B
    test, the ``test`` and its ``arm``. The recipient test runs beside the first-second test in the same ``ab.json``:
    ``recipient`` is its arm, and arm ``b`` names who the viewer sends it ``to``. Every value comes from a closed set,
    so the tags can be counted."""

    territory: str
    cause: str
    emotion: str
    recurring: tuple[str, ...] = ()
    test: str = ""
    arm: str = ""
    recipient: str = ""
    to: str = ""

    def __post_init__(self) -> None:
        for field, value, allowed in (
            ("territory", self.territory, TERRITORIES),
            ("cause", self.cause, CAUSES),
            ("emotion", self.emotion, EMOTIONS),
        ):
            if value not in allowed:
                raise ReleaseError(f"{field} {value!r} is not one of {', '.join(allowed)}")
        if not isinstance(self.recurring, tuple) or not all(
            isinstance(name, str) and CHARACTER.fullmatch(name) for name in self.recurring
        ):
            raise ReleaseError(f"recurring {self.recurring!r} is not a tuple of lowercase character names")
        if len(set(self.recurring)) != len(self.recurring):
            raise ReleaseError(f"recurring {self.recurring!r} names a character twice")
        if self.test and self.test not in TESTS:
            raise ReleaseError(f"test {self.test!r} is not one of {', '.join(TESTS)}")
        if bool(self.test) != bool(self.arm):
            raise ReleaseError(f"test {self.test!r} and arm {self.arm!r}: an A/B test needs both or neither")
        if self.arm and self.arm not in ARMS:
            raise ReleaseError(f"arm {self.arm!r} is not one of {', '.join(ARMS)}")
        if self.recipient and self.recipient not in ARMS:
            raise ReleaseError(f"recipient {self.recipient!r} is not one of {', '.join(ARMS)}")
        if self.recipient and not self.test:
            raise ReleaseError(
                "the recipient test rides on the first-second test: a reel without test and arm drops both"
            )
        if (self.recipient == "b") != bool(self.to):
            raise ReleaseError(f"recipient {self.recipient!r} and to {self.to!r}: arm b, and only arm b, names who")
        if self.to and self.to not in RECIPIENTS:
            raise ReleaseError(f"to {self.to!r} is not one of {', '.join(RECIPIENTS)}")


@dataclass(frozen=True)
class Release:
    """``slug`` names the episode project (``<episodes>/<slug>/``); ``video`` is the rendered video's file name
    without extension (the slug when empty); ``scene`` is the project's scene file (``<slug>.scene.xml`` when
    empty); ``cover`` says the cover's backdrop is drawn from that scene's ``cover`` variant; ``builder`` is the stem
    of the episode's build script when it is not the slug with underscores. ``frozen`` is the cover fingerprint
    (:func:`~srstudio.social.fingerprint`) the operator accepted for a published video whose post now draws another
    cover than the one delivered: the publish gate takes its delivery as current at that drawing and no other, and
    never delivers it again (ADR 0040). ``style`` is the name of the episode's style
    (:attr:`srstudio.styles.Style.name`): the caption gate holds a new reel to that style's approved looks
    (ADR 0048); a release published before the gate needs none. ``parts`` pins the version of every part it
    draws, by registered name: ``None`` while the reel is being written, when it draws each part's default,
    and refused at delivery (:func:`unpinned`), so a shipped reel never changes when a new version is approved
    (ADR 0047). ``comedy`` holds its two scores on the skill's rubric: a reel's first delivery refuses them under
    the floor, or none at all, and a release already delivered needs none (:mod:`srstudio.comedy_floor`, ADR 0064)."""

    slug: str
    post: InstagramPost
    video: str = ""
    scene: str = ""
    cover: bool = False
    builder: str = ""
    tags: Tags | None = None
    frozen: str = ""
    style: str = ""
    parts: Mapping[str, int] | None = None
    comedy: Scores | None = None

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
        if self.tags is not None and not isinstance(self.tags, Tags):
            raise ReleaseError(f"{self.slug}: tags is a {type(self.tags).__name__}, not Tags")
        if self.frozen and not FINGERPRINT.fullmatch(self.frozen):
            raise ReleaseError(f"{self.slug}: frozen {self.frozen!r} is not a cover fingerprint (64 lowercase hex)")
        if self.parts is not None:
            self._check_pins(self.parts)
        if self.comedy is not None and not isinstance(self.comedy, Scores):
            raise ReleaseError(f"{self.slug}: comedy is a {type(self.comedy).__name__}, not Scores")

    def _check_pins(self, pins: Mapping[str, int]) -> None:
        if not isinstance(pins, Mapping):
            raise ReleaseError(f"{self.slug}: parts maps a part to its version, got {pins!r}")
        for name, number in pins.items():
            if isinstance(number, bool) or not isinstance(number, int):
                raise ReleaseError(f"{self.slug}: {name}'s pin {number!r} is not a version number")
            try:
                pin(name, number)
            except PartError as exc:
                raise ReleaseError(f"{self.slug}: {exc}") from None

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


def _pin_drift(release: Release, drawn: Mapping[str, int] | None) -> list[str]:
    """Why ``release`` may not ship, given what its build drew (``None``: a project built before records)."""
    if release.parts is None:
        if drawn:
            return [f"pins no part versions; add parts={dict(sorted(drawn.items()))!r}"]
        return ["pins no part versions; add parts={...} with what it draws, {} if it draws none"]
    reasons = []
    for name, number in sorted((drawn or {}).items()):
        pinned = release.parts.get(name)
        if pinned is None:
            reasons.append(f"its build drew {name} version {number}, which it does not pin")
        elif pinned != number:
            reasons.append(f"its build drew {name} version {number} but it pins version {pinned}; rebuild it")
    return reasons


def unpinned(releases: Mapping[str, Release], episodes: Path, delivering: Collection[str] = ()) -> list[Drift]:
    """Every way a release would ship without pinning what it draws, against the record its build left in
    ``<episodes>/<slug>/``. A published project holds no record, so a video needs one only while it is ``delivering``.
    It reads files only, so the publish gate stays free of the engine (ADR 0047)."""
    drift: list[Drift] = []
    for release in releases.values():
        try:
            drawn = read_record(Path(episodes) / release.slug)
            reasons = _pin_drift(release, drawn)
            if drawn is None and release.parts is not None and release.video_name in delivering:
                reasons = [f"no record of what its build drew; build it with srstudio build {release.slug} PROJECT"]
        except PartError as exc:
            reasons = [str(exc)]
        drift.extend(Drift(release.video_name, reason) for reason in reasons)
    return drift


def doubled_captions(releases: Mapping[str, Release], episodes: Path, delivering: Collection[str]) -> list[Drift]:
    """Every pair of captions that print over each other in a video being delivered; a published video is frozen and
    a project with no scene has nothing to read."""
    drift: list[Drift] = []
    for release in releases.values():
        scene = Path(episodes) / release.slug / release.scene_file
        if release.video_name in delivering and scene.is_file():
            drift.extend(Drift(release.video_name, why) for why in craft.doubled_captions(scene.read_bytes()))
    return drift


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
        sys.modules[name] = package  # before it runs, as the import system does, so its relative imports resolve
        try:
            spec.loader.exec_module(package)
        except Exception as exc:
            del sys.modules[name]  # a half-imported package would load as one holding no release
            raise ReleaseError(f"{init} cannot be imported: {exc}") from exc
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


def grandfathered(folder: Path) -> frozenset[str]:
    """The closed list of ``folder``'s ``_grandfathered`` module: the slugs published before the caption gate
    (ADR 0048)."""
    folder = Path(folder).resolve()
    try:
        return frozenset(importlib.import_module(f"{_package(folder)}._grandfathered").SLUGS)
    except (ImportError, AttributeError) as exc:
        raise ReleaseError(f"{folder} holds no _grandfathered list of SLUGS: {exc}") from exc


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
