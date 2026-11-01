"""One specimen per family of characters, and the digest of what it draws (ADR 0047, after ADR 0037).

An approved drawing must never change, so each one is redrawn and compared. A specimen puts a character through its
public contract once, every kind of expression shown once: no product of kinds and characters. The kinds are fixed
here, not read from the style, so a new kind for new characters moves nobody's digest.

The digest (:func:`fingerprint`) holds the drawing and nothing around it, so a change to the engine, to sr-core's
output or to how ids are handed out cannot say "add a version" when no drawing changed:

- only ``<composition>`` counts, with each definition it uses (an effect, a gradient) in place of its name;
- ids are dropped, attributes are sorted, numbers are compared by value;
- a text asset's letters count and a font does not: a font is not drawing, and what it shapes is placed already;
- a group that draws nothing and moves nothing is dissolved into its parent.

Order stays: what is drawn over what is the drawing. An attribute or element not classified in :data:`DRAWN` or
:data:`IGNORED` raises :class:`SpecimenError`, so a new one is decided once, not guessed at.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import pkgutil
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from sr_core.scene import Scene

from . import (
    blob,
    cel,
    collage,
    gloss,
    host_kit,
    news_inked,
    news_kit,
    parts,
    registry,
    rig,
    stick,
    toon,
    toon_head,
    toon_rigs,
)
from .canvas import Canvas, flat_counter
from .errors import SrstudioError
from .timeline import Take

__all__ = [
    "ARMS",
    "DRAWN",
    "EYES",
    "GESTURES",
    "IGNORED",
    "MOUTHS",
    "OWN_ARMS",
    "SPECIMENS",
    "WEAR",
    "DrawingChangedError",
    "SpecimenError",
    "check",
    "check_rig",
    "digest",
    "fingerprint",
    "load_parts",
    "rig_digest",
]

PLACE = frozenset({"x", "y", "scaleX", "scaleY", "rotation", "opacity", "anchorX", "anchorY", "start", "end"})
PAINT = frozenset({"fill", "fillRule", "stroke", "strokeWidth", "strokeCap", "strokeJoin", "opacity"})
GRADIENT = frozenset({"interpolationSpace", "x1", "y1", "x2", "y2", "cx", "cy", "r"})
LETTERS = frozenset(
    {"text", "size", "color", "align", "verticalAlign", "lineHeight", "wrap", "width", "height", "weight", "maxLines"}
    | {"overflow", "strokeColor", "strokePosition", "strokeWidth"}
)
DRAWN: dict[str, frozenset[str]] = {  # element -> the attributes that are the drawing
    "group": PLACE | {"effects", "width", "height", "blend", "isolate", "motionBlur", "shutterAngle"},
    "shape": PLACE | PAINT | {"shape", "path", "width", "height", "radius", "dash", "effects"},
    "layer": frozenset({"asset", "x", "y"}),
    "animate": frozenset({"property", "defaultInterpolation", "timeBase"}),
    "key": frozenset({"time", "value", "stiffness", "damping", "mass", "carry"}),
    "effect": frozenset(
        {"type", "intensity", "radius", "color", "offsetX", "offsetY"}
        | {"threshold", "amount", "seed", "size", "softness"}
    ),
    "expression": frozenset({"property"}),
    "mask": frozenset({"type", "x", "y", "width", "height", "path", "invert"}),
    "textAnimator": frozenset({"preset", "presetStart", "presetDuration"}),
    "linearGradient": GRADIENT | {"units"},
    "radialGradient": GRADIENT,
    "stop": frozenset({"color", "offset"}),
    "text": LETTERS | {"fontAsset"},
    "image": frozenset({"src", "width", "height"}),  # a plate: its file is named by the digest of what it draws
    "geo": frozenset({"src", "sha256", "license", "credit"}),
    "map": frozenset({"width", "height", "projection", "centerLon", "centerLat", "zoom", "background"})
    | {"fitPadding", "outline", "outlineWidth"},
    "geoLayer": frozenset({"geo", "filter", "fill", "stroke", "strokeWidth", "opacity", "pointRadius"}),
    "graticule": frozenset({"step", "stroke", "strokeWidth"}),
    "route": frozenset({"points", "stroke", "strokeWidth", "progress", "opacity"}),
    "flyTo": frozenset({"begin", "duration", "lon", "lat", "zoom", "rho"}),
}
IGNORED = frozenset({"id"})  # an id says nothing about what is drawn
UNDRAWN_ASSETS = frozenset({"font"})  # an asset that is not drawing: what it shapes is in the document already


class SpecimenError(SrstudioError, ValueError):
    """A specimen document holds something :data:`DRAWN` has not classified, or a character has no specimen."""


class DrawingChangedError(SrstudioError, ValueError):
    """An approved version no longer draws what was approved."""


# The fixed kinds of a specimen: the vocabulary as it stood when versions began, kept here so growing it moves nothing.
EYES = ("wide", "half", "left", "up", "down", "side", "closed", "narrow", "shock", "roll", "teary", "wince", "hearts")
MOUTHS = ("flat", "open", "round", "o", "drop", "grin", "wave", "smirk", "none", "grimace", "frown", "tongue", "kiss")
TRACED_EYES = EYES[:9]
NEWER_EYES = (*EYES, "sleepy")  # what the characters drawn since draw besides, shown only on those
NEWER_MOUTHS = (*MOUTHS, "yawn", "scream", "puff")
TRACED_MOUTHS = MOUTHS[:9]
ARMS = ("desk", "type", "crossed", "sigh", "lean", "face", "face2")
GESTURES = ("ready", "present", "empathy", "shrug", "folded", "firm", "panic", "facepalm", "tablet")  # Bento's own
OWN_ARMS = {"toon-bento@2": GESTURES}  # a drawing whose hands are in its own poses, drawn after the shared arms
WEAR = ("glasses", "sweat", "flush")
PAPER_EYES = ("open", "side", "up", "half", "closed", "wide", "angry", "sad")
PAPER_MOUTHS = ("flat", "smile", "frown", "o", "grin", "smug")
PAPER_ARMS = ("down", "point", "shrug", "hold", "face", "fist")
VISEMES = ("closed", "open", "round", "teeth")
STEP = 0.5
HOLD = 4.0  # seconds a specimen without a timeline of kinds runs for
FEET = (540.0, 1700.0)


def _stage(style: str, seconds: float) -> Canvas:
    from .styles import STYLES

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background="#ffffff")
    return Canvas(scene, STYLES[style].palettes[0], font_asset="caption", namer=flat_counter("n"))


def _track(kinds: Iterable[str], step: float = STEP) -> list[tuple[float, str]]:
    return [(i * step, kind) for i, kind in enumerate(kinds)]


def _poses(eyes: tuple[str, ...], mouths: tuple[str, ...], arms: tuple[str, ...], wear: tuple[str, ...] = ()):
    worn: tuple[tuple[str, ...], ...] = ((), *((w,) for w in wear))
    return [
        toon.Pose(i * STEP, eyes[i % len(eyes)], mouths[i % len(mouths)], arms[i % len(arms)], worn[i % len(worn)])
        for i in range(max(len(eyes), len(mouths), len(arms)))
    ]


def _taps(poses) -> tuple[float, ...]:
    return tuple(p.start + STEP / 2 for p in poses if p.arms == "type")


def _traced_toon(entry: registry.Entry) -> Canvas:
    poses = _poses(TRACED_EYES, TRACED_MOUTHS, ("desk", "type"), WEAR)
    seconds = len(poses) * STEP
    cv = _stage("toon", seconds)
    entry(cv, cv.comp, poses, seconds, _taps(poses))
    return cv


def _brush_toon(entry: registry.Entry) -> Canvas:
    poses = _poses(EYES, MOUTHS, ARMS, WEAR)
    seconds = len(poses) * STEP
    cv = _stage("toon", seconds)
    entry(cv, cv.comp, poses, seconds, _taps(poses), mouths=_track(VISEMES))
    return cv


def _newer_toon(entry: registry.Entry) -> Canvas:
    poses = _poses(NEWER_EYES, NEWER_MOUTHS, (*ARMS, *OWN_ARMS.get(entry.name, ())), WEAR)
    seconds = len(poses) * STEP
    cv = _stage("toon", seconds)
    entry(cv, cv.comp, poses, seconds, _taps(poses), mouths=_track(VISEMES))
    return cv


def _rigged(rig: toon_head.HeadRig) -> Canvas:
    """A rig through every kind a drawn face has, its head at rest and at the corners of what it can reach."""
    poses = _poses(NEWER_EYES, NEWER_MOUTHS, ARMS, WEAR)
    seconds = len(poses) * STEP
    cv = _stage("toon", seconds)
    toon_head._draw_reach(cv, cv.comp, rig, poses, seconds, _taps(poses), mouths=_track(VISEMES))
    return cv


def _paper(entry: registry.Entry) -> Canvas:
    poses = _poses(PAPER_EYES, PAPER_MOUTHS, PAPER_ARMS)
    seconds = len(poses) * STEP
    cv = _stage("collage", seconds)
    entry(cv, cv.comp, poses, seconds, (), mouths=_track(VISEMES))
    return cv


def _guest(entry: registry.Entry) -> Canvas:
    cv = _stage("gloss", HOLD)
    if entry.name == "gloss-sunny":
        entry(cv, cv.comp, at=FEET, talk=_track(VISEMES), face=_track(gloss.HOST_FACES), end=HOLD)
    else:
        entry(cv, cv.comp, at=FEET, talk=_track(VISEMES), face=_track(gloss.FACES), pose=_track(gloss.POSES), end=HOLD)
    return cv


def _space(entry: registry.Entry) -> Canvas:
    cv = _stage("saga", HOLD)
    entry(cv, cv.comp, at=FEET, talk=_track(VISEMES), end=HOLD)
    return cv


def _blob(entry: registry.Entry) -> Canvas:
    poses = tuple(pose for pose in blob.POSES if pose not in blob.POSES_SINCE_APPROVAL)
    eyes, mouths = tuple(blob.EYES), tuple(blob.MOUTHS)
    count = max(len(poses), len(eyes), len(mouths))
    cues = [
        blob.Cue(i * STEP, poses[i % len(poses)], eyes[i % len(eyes)], mouths[i % len(mouths)]) for i in range(count)
    ]
    seconds = count * STEP
    cv = _stage("soft", seconds)
    entry(cv, cv.comp, cues, end=seconds, x=FEET[0], y=FEET[1], mouth_states=_track(("rest", "open")))
    return cv


def _actor(entry: registry.Entry) -> Canvas:
    cv = _stage("cutout", HOLD)
    perf = rig.Performance(mouth=_track(("closed", "open")), blinks=[(1.0, 1.1)], nods=[(0.0, 0.0), (1.0, 3.0)])
    actor = entry(cv)
    # Approved specimens used an undrawn "closed" pose. Keep that historical vocabulary on this instance only;
    # ordinary actors still reject it, and changing it to "rest" would change the approved drawing.
    actor.mouth_poses = (*actor.mouth_poses, 'closed')
    actor.build(cv.comp, FEET[0], FEET[1], 1.0, perf)
    return cv


def _anchor(entry: registry.Entry) -> Canvas:
    cv = _stage("toon", HOLD)
    who = entry.name.removeprefix("news-").split("@")[0]
    acts = tuple(
        (HOLD * n / len(news_kit.ARMS), news_kit.Pose(eyes, "talk", arms))
        for n, (eyes, arms) in enumerate(zip(news_kit.EYES, news_kit.ARMS, strict=False))
    )
    if "@" not in entry.name:
        news_kit.perform(cv, cv.comp, who, 540.0, acts, 0.0, HOLD)
        return cv
    number = int(entry.name.split("@")[1])
    mouths = news_inked.mouths_shown(HOLD, number) if number >= 4 else ()
    news_inked.perform(cv, cv.comp, who, 540.0, acts, 0.0, HOLD, mouths, number=number)
    return cv


def _moth(entry: registry.Entry) -> Canvas:
    cv = _stage("toon", HOLD)
    acts = tuple(
        (HOLD * n / len(host_kit.EYES), host_kit.Pose(eyes, mouth, arm))
        for n, (eyes, mouth, arm) in enumerate(
            zip(
                host_kit.EYES, ("flat", "open", "round", "wide", "smirk", "chew"), (*host_kit.ARMS, "rest"), strict=True
            )
        )
    )
    host_kit.perform(cv, cv.comp, cv.comp, acts, 0.0, HOLD)
    return cv


def _clay(entry: registry.Entry) -> Canvas:
    """Every face of a character shot on plates, one plate at a time (ADR 0068)."""
    from . import pedro_host, rafa_host

    host = pedro_host if entry.name == "pedro" else rafa_host
    cv = _stage("toon", HOLD)
    faces = host.part_plates(entry.name)
    for n, plate in enumerate(faces):
        shown = cv.group(cv.comp, cv.uid("g"), opacity=0.0)
        cv.gate(shown, [(HOLD * n / len(faces), HOLD * (n + 1) / len(faces))])
        host.place(cv, shown, plate)
    return cv


def _pigeon(entry: registry.Entry) -> Canvas:
    cv = _stage("cutout", HOLD)
    entry(cv, cv.comp, nods=[(0.0, 0.0), (1.0, 8.0)])
    return cv


def _inked(entry: registry.Entry) -> Canvas:
    cv = _stage("ink", HOLD)
    phones = tuple({"c": c, "start": i * 0.25, "end": (i + 1) * 0.25} for i, c in enumerate("hello"))
    take = Take("01", entry.name, "shot", "Hello.", 0.0, HOLD, phones=phones, speech_duration=1.25)
    entry(cv, cv.comp, take, FEET[0], FEET[1])
    return cv


def _traced_stick(entry: registry.Entry) -> Canvas:
    plate = stick.Plate("#111111", "M 0 0 L 10 0 L 10 10 Z")
    cv = _stage("stick", 1.0)
    room, yard = stick.parse_poses(
        [
            {"start": 0.0, "end": 0.5, "shot": "room", "legs": [[520.0, 470.0], [540.0, 500.0]],
             "head": [{"fill": plate.fill, "path": plate.path}], "ink": []},
            {"start": 0.5, "end": 1.0, "shot": "yard", "cx": 200.0, "cy": 820.0, "angle": -4.5,
             "centers": [[460.0, 830.0]], "head": [{"fill": plate.fill, "path": plate.path}],
             "body": [{"fill": plate.fill, "path": plate.path}]},
        ]
    )  # fmt: skip
    entry(cv, cv.comp, [room, yard], [stick.Badge(stick.Icon((430.0, 834.0), (plate,)), "#70a599", 47, -5.0)], 1.0)
    return cv


def _stick_rig(entry: registry.Entry) -> Canvas:
    poses = tuple(stick.SEATED)
    seconds = len(poses) * STEP
    cv = _stage("stick", seconds)
    keys = [stick.RigKey(i * STEP, pose) for i, pose in enumerate(poses)]
    phones = tuple({"c": c, "start": i * 0.1, "end": (i + 1) * 0.1} for i, c in enumerate("hello"))
    entry(cv, cv.comp, keys, seconds, phones=phones, blinks=(0.25,))
    return cv


def _traced_cel(entry: registry.Entry) -> Canvas:
    cv = _stage("cel", 1.0)
    drawings = {"a": (cel.Fill("#111111", "M 0 0 L 10 0 L 10 10 Z"),), "b": (cel.Fill("#222222", "M 0 0 L 20 0 Z"),)}
    entry(cv, cv.comp, [cel.Run("a", 0.0, 0.5), cel.Run("b", 0.5, 1.0)], drawings)
    return cv


TOON_BRUSH = ("dog", "frog", "bear", "rabbit", "fox", "raccoon", "hedgehog")
TOON_REDRAWN = ("dog", "frog", "bear", "rabbit", "raccoon", "hedgehog")
SPECIMENS: dict[str, Callable[[registry.Entry], Canvas]] = {
    "toon-cat": _traced_toon,
    **{f"toon-{name}": _brush_toon for name in TOON_BRUSH},
    "toon-fox@2": _newer_toon,
    **dict.fromkeys(("toon-sloth", "toon-goat", "toon-hamster", "toon-bento"), _newer_toon),
    **{f"toon-{name}@2": _newer_toon for name in TOON_REDRAWN},
    "toon-bento@2": _newer_toon,
    **{f"collage-{name}": _paper for name in collage.LOOKS},
    **{f"gloss-{name}": _guest for name in ("nadia", "gus", "tamsin", "sunny")},
    **{f"saga-{name}": _space for name in ("gloom", "enforcer", "droid", "juno", "rook", "mabel")},
    **dict.fromkeys(("pip", "bo", "juno", "remy"), _blob),
    **dict.fromkeys(("manager", "candidate", "rosa", "barista", "customer"), _actor),
    "pigeon": _pigeon,
    **dict.fromkeys(
        (
            "news-vera",
            "news-gus",
            "news-vera@2",
            "news-gus@2",
            "news-vera@3",
            "news-gus@3",
            "news-vera@4",
            "news-gus@4",
            "news-vera@5",
            "news-gus@5",
            "news-vera@6",
            "news-gus@6",
        ),
        _anchor,
    ),
    "host-lint": _moth,
    "rafa": _clay,
    "pedro": _clay,
    "doodle": _inked,
    **{f"talking-{name}": _inked for name in ("printer", "router", "doorbell", "meter", "vacuum")},
    "stick-figure": _traced_stick,
    "stick-rig": _stick_rig,
    "cel-traced": _traced_cel,
}


def load_parts() -> None:
    """Import every module of the library, so the registry holds every drawing."""
    import srstudio

    for module in pkgutil.iter_modules(srstudio.__path__):
        if module.name != "__main__":
            importlib.import_module(f"srstudio.{module.name}")


_REFERENCE = re.compile(r"url\(#(.+)\)")
_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _number(text: str) -> str:
    value = f"{float(text):.6f}".rstrip("0").rstrip(".")
    return "0" if value in ("", "-0") else value


def _value(attribute: str, value: str) -> str:
    if attribute == "path":
        return _NUMBER.sub(lambda m: _number(m.group()), value)
    return _number(value) if _NUMBER.fullmatch(value) else value


def _node(element: ET.Element, defined: dict[str, ET.Element]) -> list[Any]:
    if element.tag not in DRAWN:
        raise SpecimenError(f"<{element.tag}> is not classified; add it to specimens.DRAWN")
    attributes: dict[str, object] = {}
    for key, value in element.attrib.items():
        if key in IGNORED:
            continue
        if key not in DRAWN[element.tag]:
            raise SpecimenError(f"{element.tag}@{key} is not classified; add it to specimens.DRAWN or IGNORED")
        reference = _REFERENCE.fullmatch(value)
        tokens = [reference.group(1)] if reference else value.split()
        if tokens and all(token in defined for token in tokens):
            attributes[key] = [_node(defined[token], defined) for token in tokens]
        else:
            attributes[key] = _value(key, value)
    if element.tag == "expression":
        attributes["body"] = (element.text or "").strip()
    children: list[object] = []
    for child in element:
        node = _node(child, defined)
        children.extend(node[2] if node[0] == "group" and not node[1] else [node])
    return [element.tag, dict(sorted(attributes.items())), children]


def fingerprint(document: bytes) -> str:
    """The digest of the drawing in a scene document: see the module's notes for what it holds."""
    root = ET.fromstring(document)
    composition = root.find("composition")
    if composition is None:
        raise SpecimenError("a scene document with no composition draws nothing")
    inside = {id(e) for e in composition.iter()}
    defined = {
        e.attrib["id"]: e
        for e in root.iter()
        if "id" in e.attrib and id(e) not in inside and e.tag not in UNDRAWN_ASSETS
    }
    drawing = [_node(child, defined) for child in composition]
    while len(drawing) == 1 and drawing[0][0] == "group" and not drawing[0][1]:
        drawing = drawing[0][2]
    flat: list[object] = []
    for node in drawing:
        flat.extend(node[2] if node[0] == "group" and not node[1] else [node])
    return hashlib.sha256(json.dumps(flat, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def digest(name: str, number: int = 1, *, episodes: Path | None = None) -> str:
    """The drawing's digest; non-character specimens use project assets from ``episodes``."""
    recorded = parts.get(name)
    if recorded.refused is not None:
        raise SpecimenError(f"{name} has no standalone specimen ({recorded.refused.reason.value})")
    if recorded.kind != "character":
        from . import catalog_specimens

        projects = (
            Path(episodes)
            if episodes is not None
            else Path(os.environ.get("SRSTUDIO_EPISODES") or "generated/episodes")
        )
        try:
            return catalog_specimens.digest(name, number, projects)
        except catalog_specimens.SpecimenRenderError as exc:
            raise SpecimenError(
                f"{name}: {exc}; pass episodes=Path('/path/to/projects') or set SRSTUDIO_EPISODES"
            ) from exc
    part = parts.part_name(name, number)
    if part not in SPECIMENS:
        raise SpecimenError(f"{part} has no specimen; add it to specimens.SPECIMENS")
    return fingerprint(SPECIMENS[part](registry.get("character", part)).scene.to_bytes(layout="pretty"))


def check(name: str, number: int = 1, *, episodes: Path | None = None) -> None:
    """Verify an approved builder; non-character specimens use project assets from ``episodes``."""
    part = parts.get(name)
    version = part.version(number)
    if version.status != "approved":
        raise parts.NotApprovedError(
            f"{name} version {number} is {version.status}; only approved drawings can be verified"
        )
    entry = registry.get(part.kind, parts.part_name(name, number))
    if part.refused is not None:
        if entry._original is None:
            raise SpecimenError(f"{name} has no standalone specimen and no original builder was recorded")
        raise SpecimenError(f"{name} has no standalone specimen; use parts.restore({name!r}, {number})")
    builder = entry.builder
    entry._verified_builder = None
    entry._verified_drawing = None
    if episodes is None:
        actual = digest(name, number)
    else:
        actual = digest(name, number, episodes=episodes)
    if actual != version.drawing:
        raise DrawingChangedError(
            f"{name} version {number} is approved and immutable, and it no longer draws what was approved. "
            f"Restore its drawing and add a version: an approved look is never revised in place"
        )
    if registry.get(part.kind, parts.part_name(name, number)) is not entry or entry.builder is not builder:
        raise SpecimenError(f"{name} version {number}: registered builder changed during specimen check; retry")
    entry._verified_builder = builder
    entry._verified_drawing = version.drawing


def rig_digest(name: str, number: int = 1) -> str:
    """The digest of the head rig of version ``number`` of ``name``, a drawing outside that version's own digest."""
    part = parts.part_name(name, number)
    if part in news_inked.RIGS:
        cv = _stage("toon", HOLD)
        news_inked.rig_specimen(cv, news_inked.RIGS[part].who, HOLD, number)
        return fingerprint(cv.scene.to_bytes(layout="pretty"))
    if part not in toon_rigs.RIGS:
        raise SpecimenError(f"{name} version {number} has no head rig")
    return fingerprint(_rigged(toon_rigs.RIGS[part]).scene.to_bytes(layout="pretty"))


def check_rig(name: str, number: int = 1) -> None:
    """Raises :class:`DrawingChangedError` when an approved rig no longer draws what was approved."""
    held = parts.get(name).version(number).rig
    if held is not None and held.status == "approved" and rig_digest(name, number) != held.drawing:
        raise DrawingChangedError(
            f"{name} version {number}'s head rig is approved and immutable, and it no longer draws what was approved. "
            f"Restore its drawing and add a version: an approved rig is never revised in place"
        )
