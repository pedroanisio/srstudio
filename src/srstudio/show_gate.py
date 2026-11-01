"""What refuses a reel in the show's look that is not in it: the number, the bug and the band (ADR 0074).

The look is opt-in, by a release whose cover is a :class:`~srstudio.thumbnail.ShowCover`, so a published reel never
meets this gate. On the first delivery of a reel that opted in, :func:`show_defects` holds:

- the number: the ledger's claim says what the release says (:mod:`srstudio.show_numbers`), no other release holds it,
  and a series episode says its place on the caption's first line, after the question;
- the bug, read from the scene: drawn for this number, last, so above the camera, and hidden on the cover;
- the bug, measured on the engine's frames from the first to the last: live, unmoved, and clear of the signature's
  marks, of text and of a face;
- the band: no face under it at the cover's frame, at the cover's zoom;
- the video: the corner of its first frame is the corner of its scene, so a render older than the number fails.

A face is an estimate: what a figure draws in the top :data:`FACE_SHARE` of its box, since a scene knows a character's
nodes but not which of them are its head. It reads what the build recorded, so a figure drawn outside a registered
character is not seen. Instagram's own interface is not measured at all: the corner is held by the box it was chosen
for.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path

import numpy as np

from . import figure_record, fonts, framegraph, show, show_numbers
from .figure_gates import figures_on
from .figure_record import Figure
from .frame_gates import FrameGateError, _duration, sample_times
from .framegraph import Box, Drawing, Frame, FrameGraphError
from .releases import Release
from .show_numbers import Ledger
from .social import COVER_VARIANT, Drift
from .thumbnail import ShowCover, ThumbnailError, covered

__all__ = [
    "FACE_SHARE",
    "PIXEL_COUNT",
    "PIXEL_STEP",
    "corner_defect",
    "cover_faces",
    "faces_on",
    "frame_defects",
    "number_defects",
    "scene_defects",
    "show_defects",
]

FACE_SHARE = 0.4  # of a figure's box, from its top: the head and a little of the shoulders on the cast's proportions
PIXEL_STEP = 96.0  # of 255, the channels' mean: a pixel this far from the scene's was drawn differently
PIXEL_COUNT = 16  # pixels past the step: the closest last digits part by 50, an encoder at a rough quality by none
_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_MARK = re.compile(r"sig-(cactus|code)(?:-\d+)?\Z")
_LIVE = 0.02  # opacity under which a text is not seen
_FACE_SCALE = 2.0  # frame pixels to a mask pixel: the bug is small
_BOX = Box(*show.BUG_BOX)


def _meets(a: Box, b: Box) -> bool:
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


def _cover(release: Release) -> ShowCover | None:
    cover = release.post.thumbnail
    return cover if isinstance(cover, ShowCover) else None


def number_defects(release: Release, ledger: Ledger, releases: Mapping[str, Release]) -> list[str]:
    """What is wrong with the number of ``release``, a reel on the show's cover, against ``ledger`` and ``releases``."""
    cover = _cover(release)
    if cover is None:
        return []
    out = [p for p in cover.problems() if "number" in p or "series" in p]
    if not release.cover:
        out.append("the show's cover needs cover=True: the bug hides in the cover variant")
    claim = ledger.reels.get(release.slug)
    if claim is None:
        out.append(f"#{cover.number} is not in the ledger; claim it with srstudio number claim {release.slug}")
    elif (claim.number, claim.series, claim.series_number) != (cover.number, cover.series, cover.series_number):
        said = f"#{claim.number}" + (f", {claim.series} #{claim.series_number}" if claim.series else "")
        out.append(f"the ledger gives it {said}, and its cover says #{cover.number} {cover.tag}".rstrip())
    others = [c for r in releases.values() if r.slug != release.slug and (c := _cover(r)) is not None]
    if any(c.number == cover.number for c in others):
        out.append(f"another release holds #{cover.number}")
    if cover.series and any(c.tag == cover.tag for c in others):
        out.append(f"another release is {cover.tag}")
    if cover.series:
        head = release.post.title.removesuffix(cover.tag).rstrip()
        if not release.post.title.endswith(cover.tag) or not head.endswith("?"):
            out.append(f"the caption's first line must be the question and then {cover.tag}")
    return out


def scene_defects(document: bytes, number: int) -> list[str]:
    """What the scene says against the bug of reel ``number``."""
    root = ET.fromstring(document)
    wanted = show.bug_id(number)
    composition = root.find(".//composition")
    last = [c.get("id", "") for c in composition] if composition is not None else []
    drawn = sorted(g.get("id", "") for g in root.iter("group") if re.fullmatch(rf"{show.BUG_ID}-\d+", g.get("id", "")))
    if not drawn:
        return [f"no bug in the scene: build it with srstudio build, which draws #{number}"]
    if drawn != [wanted]:
        return [f"the scene draws {', '.join(drawn)}, and the reel is #{number}: build it again"]
    out = []
    if not last or last[-1] != wanted:
        out.append("the bug is not the last thing drawn, so it is not above the camera and all else")
    hidden = root.findall(f".//variant[@id='{COVER_VARIANT}']/override[@target='{wanted}']")
    if not hidden:
        out.append("the bug is not hidden on the cover, so the cover says its number twice")
    return out


def _texts(document: bytes, project: Path) -> dict[str, tuple[float, str]]:
    """Each text layer's id: the width its widest line draws at size 1 in its own font, and its alignment. A text
    layer's box is its asset's, often the frame's, so a corner can only be measured against the letters. A font the
    scene names and the project does not hold is a refusal: the letters could land anywhere."""
    root = ET.fromstring(document)
    sources = {f.get("id"): f.get("src") for f in root.iter("font")}
    assets = {a.get("id"): a for a in root.iter("text")}
    out = {}
    for layer in root.iter("layer"):
        asset = assets.get(layer.get("asset"))
        if asset is None:
            continue
        source = Path(project) / str(sources.get(asset.get("fontAsset")))
        try:
            font = source.read_bytes()
        except OSError as e:
            raise FrameGateError(f"{source}: the text's font cannot be read: {e}") from None
        size = float(asset.get("size", 0))
        wide = max(fonts.text_width(font, line, size) for line in (asset.get("text") or "").split("\n"))
        out[layer.get("id", "")] = (wide, asset.get("align", "start"))
    return out


def _text_box(box: Box, world_scale: float, wide: float, align: str) -> Box:
    """Where a text's letters land inside its layer's ``box``."""
    ink = min(box.right - box.left, wide * world_scale)
    left = {"center": (box.left + box.right - ink) / 2, "end": box.right - ink}.get(align, box.left)
    return Box(left, box.top, left + ink, box.bottom)


def faces_on(frame: Frame, drawn: Mapping[str, Drawing], figures: Iterable[Figure]) -> list[tuple[str, Box, list[int]]]:
    """Each character on ``frame``, the box its face is taken to fill on the frame, and its nodes. A figure whose face
    is off the frame is left out."""
    out = []
    for part, members in figures_on(frame, figures):
        boxes = [b for m in members if (b := frame.box(m, drawn)) is not None]
        if boxes:
            top = min(b.top for b in boxes)
            bottom = top + FACE_SHARE * (max(b.bottom for b in boxes) - top)
            face = Box(min(b.left for b in boxes), top, max(b.right for b in boxes), bottom)
            seen = face.within(frame.width, frame.height)
            if seen.area > 0:
                out.append((part, seen, members))
    return out


def _covers_face(frame: Frame, drawn: Mapping[str, Drawing], face: Box, members: Sequence[int]) -> bool:
    """Does the figure draw anything where its face zone meets the bug? A box alone is too wide: an arm held out, or a
    figure mostly off the frame, makes a box over a corner the figure never reaches."""
    zone = Box(
        max(face.left, _BOX.left), max(face.top, _BOX.top), min(face.right, _BOX.right), min(face.bottom, _BOX.bottom)
    )
    if zone.area <= 0:
        return False
    nodes = {n for m in members for n in (m, *frame.descendants(m))}
    outlines = [outline for n in sorted(nodes) for outline in frame.outlines(n, drawn)]
    return bool(framegraph.fill(outlines, zone, _FACE_SCALE).any())


def _on_frame(frame: Frame, number: int, drawn, figures, texts) -> Iterator[str]:
    index = next((i for i, n in enumerate(frame.nodes) if n.id == show.bug_id(number)), None)
    if index is None:
        yield "missing"
        return
    node = frame.nodes[index]
    if not node.draw or node.opacity < 1.0:
        yield "faded"
    if tuple(round(v, 4) for v in node.world) != _IDENTITY:
        yield "moved by what it sits under"
    if any(
        frame.nodes[i].kind == "group" and frame.nodes[i].id != show.bug_id(number) for i in _ancestors(frame, index)
    ):
        yield "under the camera"
    for i, other in enumerate(frame.nodes):
        if _MARK.match(other.id) and other.kind == "group" and other.draw:
            box = frame.box(i, drawn)
            if box is not None and _meets(box, _BOX):
                yield "over a signature mark"
        if other.id in texts and other.draw and other.opacity > _LIVE:
            box = frame.box(i, drawn)
            if box is not None and _meets(_text_box(box, other.world[0], *texts[other.id]), _BOX):
                yield "over text"
    if any(_covers_face(frame, drawn, face, members) for _, face, members in faces_on(frame, drawn, figures)):
        yield "over a face"


def _ancestors(frame: Frame, index: int) -> Iterator[int]:
    parent = frame.nodes[index].parent
    while parent is not None:
        yield parent
        parent = frame.nodes[parent].parent


def frame_defects(
    frames: Iterable[Frame],
    drawn: Mapping[str, Drawing],
    number: int,
    figures: Sequence[Figure],
    texts: Mapping[str, tuple[float, str]],
) -> list[str]:
    """What the bug of reel ``number`` does wrong across ``frames``: each kind once, with its count and first time."""
    counts: Counter[str] = Counter()
    first: dict[str, float] = {}
    total = 0
    for frame in frames:
        total += 1
        for kind in set(_on_frame(frame, number, drawn, figures, texts)):
            counts[kind] += 1
            first.setdefault(kind, frame.time)
    return [
        f"the bug is {kind} in {counts[kind]} of {total} frames, from {first[kind]:.2f} s" for kind in sorted(counts)
    ]


def cover_faces(cover: ShowCover, frame: Frame, drawn, figures, font: bytes) -> list[str]:
    """The characters whose face the band hides at the cover's frame, with the cover's zoom."""
    width, height = round(frame.width), round(frame.height)
    faces = faces_on(frame, drawn, figures)
    boxes = [(b.left, b.top, max(b.right - b.left, 1.0), max(b.bottom - b.top, 1.0)) for _, b, _ in faces]
    hidden = covered(cover, font, width, height, boxes)
    return [part for (part, _, _), box in zip(faces, boxes, strict=True) if box in hidden]


def _corner(path: Path, engine_time: float, width: float, height: float) -> np.ndarray:
    """The bug's box of the frame at ``engine_time`` in the video or still ``path``, as RGB bytes."""
    left, top, right, bottom = (round(v) for v in show.BUG_BOX)
    if (width, height) != (1080.0, 1920.0):
        raise FrameGateError(f"{path.name}: a reel of {width:g} x {height:g} has no bug's corner")
    done = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{engine_time:.3f}", "-i", str(path), "-frames:v", "1",
         "-vf", f"crop={right - left}:{bottom - top}:{left}:{top}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=False,
    )  # fmt: skip
    if done.returncode != 0 or not done.stdout:
        raise FrameGateError(f"{path.name}: cannot read its corner: {done.stderr.decode(errors='replace')[-200:]}")
    return np.frombuffer(done.stdout, dtype=np.uint8).astype(float)


def corner_defect(video: np.ndarray, scene: np.ndarray) -> str:
    """Why the corner of the rendered ``video`` is not the corner its ``scene`` draws, or nothing."""
    if video.shape != scene.shape:
        return "the video's corner is not the size of the scene's"
    apart = int((np.abs(video - scene).reshape(-1, 3).mean(axis=1) > PIXEL_STEP).sum())
    if apart > PIXEL_COUNT:
        return f"{apart} pixels of the video's corner are not the scene's: render it again"
    return ""


def _render_corner(scene: Path, video: Path, engine: str | Path, frame: Frame) -> str:
    with tempfile.TemporaryDirectory(dir=scene.parent) as tmp:
        still = (Path(tmp) / "first.png").resolve()
        made = subprocess.run(
            [str(engine), "render", scene.name, "-f", "0", "-o", str(still)],
            cwd=scene.parent,
            capture_output=True,
            check=False,
        )
        if made.returncode != 0:
            raise FrameGateError(
                f"{scene.name}: the engine cannot draw it: {made.stderr.decode(errors='replace')[-200:]}"
            )
        return corner_defect(
            _corner(video, 0.0, frame.width, frame.height), _corner(still, 0.0, frame.width, frame.height)
        )


def show_defects(
    releases: Mapping[str, Release],
    episodes: Path,
    renders: Path,
    first: Mapping[str, str],
    engine: str | Path,
    ledger: Path,
    font: Path,
) -> list[Drift]:
    """What each reel on its ``first`` delivery does against the look, for those on the show's cover; the ``ledger`` is
    only read if one is. A reel that opted in with no scene or no record of its figures is refused, not skipped."""
    shown = {slug: video for slug, video in first.items() if _cover(releases[slug]) is not None}
    if not shown:
        return []
    numbers = show_numbers.read(ledger)
    drift: list[Drift] = []
    for slug, video in shown.items():
        release = releases[slug]
        cover = _cover(release)
        assert cover is not None
        drift += [Drift(video, why) for why in number_defects(release, numbers, releases)]
        project = Path(episodes) / slug
        scene = project / release.scene_file
        if not scene.is_file():
            drift.append(Drift(video, f"{scene.name} is missing: the bug cannot be read"))
            continue
        figures = figure_record.read(project)
        if figures is None:
            drift.append(Drift(video, f"{figure_record.RECORD} is missing: build it with srstudio build"))
            continue
        document = scene.read_bytes()
        said = scene_defects(document, cover.number)
        drift += [Drift(video, why) for why in said]
        if said:
            continue
        try:
            drawn = framegraph.drawings(document)
            frames = list(framegraph.evaluate(engine, scene, sample_times(_duration(document))))
            drift += [
                Drift(video, w) for w in frame_defects(frames, drawn, cover.number, figures, _texts(document, project))
            ]
            at_cover = next(iter(framegraph.evaluate(engine, scene, [cover.at])))
            hidden = cover_faces(cover, at_cover, drawn, figures, Path(font).read_bytes())
            drift += [Drift(video, f"the band hides the face of {part}: move the cover") for part in hidden]
        except (FrameGraphError, ThumbnailError) as e:
            raise FrameGateError(f"{video}: {e}") from e
        film = Path(renders) / f"{video}.mp4"
        if not film.is_file():
            drift.append(Drift(video, f"{film.name} is missing"))
        elif why := _render_corner(scene, film, engine, frames[0]):
            drift.append(Drift(video, why))
    return drift
