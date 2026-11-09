"""A scene from the folder sreditor exports, with a default staging: ``srstudio build-export EXPORT SCENE``.

sreditor exports an episode as data: ``episode.json`` (slug, title, seed, frame, language), ``timeline.json`` (a
shot sequence of takes with word timings), a WAV per take under ``audio/``, the bible, the beats and ``style.json``.
It never sends code, so its render worker cannot run an episode script; this module is the one builder it calls.

The staging is deliberately plain and the same for every exported style: the exported frame and rate, the stage in
the exported palette's background, each take's own audio in the mix, every spoken word burned as the engine's own
caption track in the bundled DejaVu Sans Bold inside the safe area, and the signature cactus at the top corner. It
draws no cast or location, because the export names drawings (``toon-host``) that are parts of an episode's own
build, and the styles' fonts are not bundled; an episode that needs them is built by its own script with
``srstudio build``.

The engine resolves a scene's files against the scene's folder, so the takes' audio and the font are copied beside
the scene, at the paths the scene names; nothing else is written there but the scene and its validation report.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from typing import Any

from . import native
from .episode import Episode, EpisodeSpec
from .errors import SrstudioError
from .onboarding import FONT
from .sample import copy_dejavu
from .signature import cactus
from .styles import CUTOUT

__all__ = ["ExportError", "build_export"]

SCHEMA = "srstudio.build-export/1.0.0"
TIMELINE = "timeline.json"
FONT_FOLDER = "assets"
HEX = re.compile(r"#[0-9A-Fa-f]{6}")
FRAME_KEYS = ("width", "height", "fps")
# The signature cactus (ADR 0001) at a corner clear of the captions; no pot code, as ADR 0250 asks of new deliveries.
CACTUS_SCALE = 0.55
CACTUS_INSET = 110


class ExportError(SrstudioError, ValueError):
    """The exported folder is missing a file or holds one the builder cannot use."""

    @property
    def path(self) -> str | None:
        path = self._diagnostic_details["path"]
        return path if isinstance(path, str) else None


def _read(export: Path, name: str, *, required: bool = True) -> dict[str, Any] | None:
    """One exported JSON document, or None when an optional one is absent."""
    file = export / name
    if not file.is_file():
        if not required:
            return None
        raise ExportError(
            f"{export}: {name} is missing",
            code="export.missing",
            path=name,
            actual=str(file),
            remedy="Pass the folder sreditor's export was unzipped into; export the episode again if it is incomplete.",
        )
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"{file}: cannot read: {exc}", code="export.unreadable", path=name) from exc
    if not isinstance(data, dict):
        raise ExportError(f"{file}: expected an object", code="export.shape", path=name, actual=type(data).__name__)
    return data


def _episode(export: Path) -> dict[str, Any]:
    """episode.json, checked for the fields the staging reads."""
    episode = _read(export, "episode.json")
    assert episode is not None
    for key in ("slug", "title"):
        if not isinstance(episode.get(key), str) or not episode[key].strip():
            raise ExportError(f"episode.json: {key} must be a nonempty string", code="export.field", path=key)
    for key in (*FRAME_KEYS, "seed"):
        value = episode.get(key, 0 if key == "seed" else None)
        if isinstance(value, bool) or not isinstance(value, int) or value < (0 if key == "seed" else 1):
            raise ExportError(
                f"episode.json: {key} must be a positive integer", code="export.field", path=key, actual=value
            )
    return episode


def _background(export: Path) -> str | None:
    """The exported palette's background, or None for the style's own stage colour."""
    style = _read(export, "style.json", required=False) or {}
    palette = style.get("palette")
    colour = palette.get("background") if isinstance(palette, dict) else None
    return colour.upper() if isinstance(colour, str) and HEX.fullmatch(colour) else None


def _audio(export: Path) -> list[str]:
    """Each take's audio path, refused when it would leave the export or is not there."""
    timeline = _read(export, TIMELINE)
    assert timeline is not None
    items = timeline.get("items")
    if not isinstance(items, list) or not items:
        raise ExportError(f"{TIMELINE}: items must be a nonempty list", code="export.field", path="items")
    paths = []
    for i, item in enumerate(items):
        audio = item.get("audio") if isinstance(item, dict) else None
        if audio is None:
            continue
        where = f"items[{i}].audio"
        relative = PurePosixPath(audio) if isinstance(audio, str) else None
        if relative is None or relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ExportError(
                f"{TIMELINE}: {where} must be a path inside the export",
                code="export.path",
                path=where,
                actual=audio,
                remedy="Export the episode again; sreditor writes each take as audio/take-NN.wav.",
            )
        if not (export / relative).is_file():
            raise ExportError(f"{TIMELINE}: {where}: {audio} is missing", code="export.missing", path=where)
        paths.append(str(relative))
    return paths


def _stage(export: Path, root: Path, audio: list[str], font: Path) -> None:
    """Put the timeline, the takes' audio and the font where the scene names them, relative to its folder."""
    for name in (TIMELINE, *audio):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not (target.exists() and target.samefile(export / name)):
            shutil.copyfile(export / name, target)
    (root / FONT_FOLDER).mkdir(parents=True, exist_ok=True)
    copy_dejavu(font, root / FONT_FOLDER)


def _spec(episode: dict[str, Any], root: Path, background: str | None) -> EpisodeSpec:
    """A clock-timed caption episode in the exported frame, whatever style the export names."""
    width, height, fps = (episode[key] for key in FRAME_KEYS)
    return EpisodeSpec(
        slug=episode["slug"],
        title=episode["title"],
        description=f"{episode['title']}, built from sreditor's export",
        root=root,
        seed=episode.get("seed", 0),
        style=CUTOUT,
        width=width,
        height=height,
        fps=fps,
        language=str(episode.get("language") or "en"),
        dialogue=TIMELINE,
        audio=None,
        background=background,
        signature_code=None,
        extra={"exported_style": str(episode.get("style", ""))},
    )


def build_export(export: Path, scene: Path) -> Path:
    """Write the scene of an unzipped sreditor export at ``scene`` (output id ``main``); return its path.

    The takes' audio and the caption font are copied beside the scene, and its validation report is written as
    ``sdk-validation.json`` there. Nothing is written when the export is missing a file or names one outside it."""
    export, scene = Path(export).resolve(), Path(scene).resolve()
    if not export.is_dir():
        raise ExportError(
            f"{export}: not a folder",
            code="export.folder",
            path="export",
            actual=str(export),
            remedy="Unzip sreditor's export and pass its folder.",
        )
    episode = _episode(export)
    background = _background(export)
    audio = _audio(export)
    root = scene.parent
    with as_file(files("srstudio").joinpath(FONT)) as font, tempfile.TemporaryDirectory(prefix="srstudio-") as work:
        stage = Path(work)
        _stage(export, stage, audio, font)
        ep = Episode(_spec(episode, stage, background))
        signed = ep.comp.add_group(id="signature")
        cactus(ep.cv, signed, episode["width"] - CACTUS_INSET, CACTUS_INSET * 2, CACTUS_SCALE)
        # the engine's own track, kept inside the safe area; a long take is split at its words into cues that fit
        ep.native_captions(native.cues_from_takes(ep.takes, native.CAPTION_LOOK))
        ep.audio()
        written = ep.finish(stage / scene.name, stage / "sdk-validation.json")
        root.mkdir(parents=True, exist_ok=True)
        for file in sorted(p for p in stage.rglob("*") if p.is_file() and p.name != TIMELINE):
            target = root / file.relative_to(stage)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
    return root / written.name


def result(scene: Path) -> dict[str, Any]:
    """What ``build-export --json`` prints."""
    return {"schema": SCHEMA, "scene": str(scene), "render": ["scene-render", "encode", str(scene)]}
