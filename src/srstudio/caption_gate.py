"""The caption gate: a new reel's captions wear a look the operator approved, and its frames show the letters open.

Two failures reached the operator's phone on published reels: a look nobody approved as a look, chosen to satisfy a
measurement, and letters a contrast ratio calls fine while the eye cannot read them. ADR 0048 tells the story. So:

- :data:`LOOKS` is the record: per style, each :class:`ApprovedLook` with its :class:`Approval` and its proof. A look
  without an approval is proposed, and a reel wearing it does not pass. No look can be recorded with a stroke in the
  letters' own colour.
- :func:`check_reel` reads the look a reel actually burned from its scene, so a declaration cannot differ from the
  picture, and finds the band of the frame its captions occupy.
- :func:`measure_frames` then measures the rendered frames in that band. Its number is the **counter ratio**: the
  pixels inside the letters' enclosed counters (the holes of a, e, o) that stand clear of the letter's tone, over the
  pixels of the letters. A stroke that fattens a rounded bold face shuts the counters, and the ratio falls with them,
  whatever the contrast of the letter against the floor around it.

Published reels are grandfathered by a closed list (``episodes/instagram_posts.py``): their pictures are frozen, so
the gate does not judge them. :func:`check_releases` is the publish path's entry. The engine's strict contrast check
is a separate control and stays as it is.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Protocol

import numpy as np

from .errors import SrstudioError
from .releases import Release
from .social import Drift, video_size

__all__ = [
    "Approval",
    "ApprovedLook",
    "BAND_PAD",
    "CaptionGateError",
    "LOOKS",
    "Legibility",
    "MIN_COUNTERS",
    "MIN_FRAMES",
    "band_of",
    "check_reel",
    "check_releases",
    "measure_frames",
    "measure_reel",
    "read_frames",
]

MIN_COUNTERS = 0.025  # counter pixels per letter pixel; the masters measured in ADR 0048 set it
MIN_FRAMES = 3  # frames with letters in them: fewer judge nothing, and a gate that judges nothing cannot pass
FPS = 1  # frames measured per second of video
BAND_PAD = 12  # pixels kept around the captions' box, so letters are not lost to the crop's edge
FILL_TOLERANCE = 55.0  # RGB distance from a look's colours that still counts as letter, after the encoder
MIN_BLOB = 25  # pixels: anything smaller is noise, not a letter
MIN_FILL = 300  # letter pixels a frame needs to count as captioned
MIN_COUNTER, MAX_COUNTER = 3, 2000  # pixels of one counter; larger enclosures are panels and pills
MAX_COUNTER_SPAN = 80  # the widest and tallest a counter is, in pixels
COUNTER_CONTRAST = 3.0  # how far a counter must stand from the letter's tone to count as open
HEX = re.compile(r"#[0-9a-fA-F]{6}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class CaptionGateError(SrstudioError, ValueError):
    """A look cannot be recorded, or a scene cannot be read for its look."""


def _colour(value: str) -> str:
    return value.upper()


@dataclass(frozen=True)
class Approval:
    """Who approved a look, when (``YYYY-MM-DD``), and on what evidence."""

    by: str
    on: str
    evidence: str

    def __post_init__(self) -> None:
        if not (self.by.strip() and self.evidence.strip()):
            raise CaptionGateError("an approval names who approved and on what evidence")
        if not DATE.fullmatch(self.on):
            raise CaptionGateError(f"an approval is dated YYYY-MM-DD, not {self.on!r}")


@dataclass(frozen=True)
class ApprovedLook:
    """One caption look of a ``style`` (:attr:`srstudio.styles.Style.name`).

    ``fills`` are the letters' colours (a style's speaker tints among them), ``active`` the sung word's, ``stroke``
    and ``stroke_width`` the outline's (``None`` and 0: no outline). ``zone`` is the part of the frame, in pixels
    from its top, the caption boxes start in: it tells captions from a sign painted alike. ``proof`` is where the
    look was judged: a local proof page, or the published reel it shipped on. Without an ``approval`` the look is
    proposed, and a reel wearing it does not pass. A ``drawn`` look is lettering traced as shapes: its scene holds
    no text to read, so the zone itself is the band."""

    style: str
    name: str
    fills: tuple[str, ...]
    active: str | None
    stroke: str | None
    stroke_width: float
    zone: tuple[int, int]
    proof: str
    approval: Approval | None = None
    drawn: bool = False

    def __post_init__(self) -> None:
        if not (self.style.strip() and self.name.strip() and self.proof.strip()):
            raise CaptionGateError("a look names its style, its name and its proof")
        colours = [*self.fills, *([self.active] if self.active else []), *([self.stroke] if self.stroke else [])]
        if not self.fills or not all(HEX.fullmatch(c) for c in colours):
            raise CaptionGateError(f"look {self.name}: every colour is #rrggbb, and it needs a fill: {colours}")
        if self.stroke_width < 0 or (self.stroke_width > 0) != (self.stroke is not None):
            raise CaptionGateError(f"look {self.name}: a stroke has a colour and a width, or neither")
        if self.stroke and _colour(self.stroke) in {_colour(c) for c in self.fills}:
            raise CaptionGateError(f"look {self.name}: a stroke in the letters' own colour closes their counters")
        if not 0 <= self.zone[0] < self.zone[1]:
            raise CaptionGateError(f"look {self.name}: zone {self.zone} is not a top and a lower bottom")

    @property
    def approved(self) -> bool:
        return self.approval is not None


RECORDED = "2026-10-30"  # the day this record was written: the looks below had shipped by then


def _shipped(reel: str) -> Approval:
    return Approval("operator", RECORDED, f"published on {reel}")


LOOKS: tuple[ApprovedLook, ...] = (
    ApprovedLook("Cel", "lettered-on-a-box", ("#FFFFFF",), None, None, 0, (240, 500),
                 "generated/renders/mushroom-training.mp4", _shipped("mushroom-training"), drawn=True),
    ApprovedLook("Collage", "ink-on-pill", ("#1D1A22",), None, None, 0, (300, 560),
                 "generated/renders/the-lore.mp4", _shipped("the-lore")),
    ApprovedLook("Cutout", "white-outlined", ("#FFFFFF",), "#F4D492", "#121415", 8, (1100, 1500),
                 "generated/renders/the-cactus.mp4", _shipped("the-cactus")),
    ApprovedLook("Gloss", "white-split-outline", ("#FFFFFF",), "#F4D492", "#121415", 8, (1200, 1500),
                 "generated/character-proofs/gloss-captions/index.html"),
    ApprovedLook("Ink", "ink-on-paper", ("#282828",), None, None, 0, (60, 120),
                 "generated/renders/the-router.mp4", _shipped("the-router")),
    ApprovedLook("Saga", "white-outlined", ("#FFFFFF",), "#F4D492", "#121415", 8, (1200, 1500),
                 "generated/renders/saga-the-code.mp4", _shipped("saga-the-code")),
    ApprovedLook("Soft", "ink-outlined-white", ("#1A1714", "#2F5D8C"), None, "#FFFFFF", 7, (200, 500),
                 "generated/renders/the-cake.mp4", _shipped("the-cake")),
    ApprovedLook("Stick", "white-word", ("#FFFFFF",), None, "#070708", 9, (1200, 1800),
                 "generated/renders/cancel-anytime.mp4", _shipped("cancel-anytime")),
    ApprovedLook("Stick", "white-split-outline", ("#FFFFFF",), None, None, 0, (1200, 1800),
                 "generated/renders/screen-share.mp4", _shipped("screen-share")),
    ApprovedLook("Toon", "ink-on-pill", ("#0B0A0D",), None, None, 0, (300, 460),
                 "generated/renders/friday-sync.mp4", _shipped("friday-sync")),
)  # fmt: skip


class _Paint(Protocol):
    @property
    def fills(self) -> tuple[str, ...]: ...

    @property
    def active(self) -> str | None: ...


class _Blob(NamedTuple):
    runs: list[tuple[int, int, int]]  # (row, first column, past the last column)
    area: int
    top: int
    bottom: int  # the last row
    left: int
    right: int  # past the last column

    def touches(self, height: int, width: int) -> bool:
        return self.top == 0 or self.bottom == height - 1 or self.left == 0 or self.right == width


def _blobs(mask: np.ndarray) -> list[_Blob]:
    """The 4-connected components of ``mask``, by joining the runs of neighbouring rows."""
    parent: list[int] = []

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    runs: list[tuple[int, int, int, int]] = []
    above: list[tuple[int, int, int]] = []
    for y, row in enumerate(mask):
        edges = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        here: list[tuple[int, int, int]] = []
        k = 0
        for a, b in zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist(), strict=True):
            label = -1
            while k < len(above) and above[k][1] <= a:
                k += 1
            j = k
            while j < len(above) and above[j][0] < b:
                root = find(above[j][2])
                if label < 0:
                    label = root
                elif root != label:
                    parent[root] = label
                j += 1
            if label < 0:
                label = len(parent)
                parent.append(label)
            here.append((a, b, label))
            runs.append((y, a, b, label))
        above = here
    grouped: dict[int, list[tuple[int, int, int]]] = {}
    for y, a, b, label in runs:
        grouped.setdefault(find(label), []).append((y, a, b))
    blobs = []
    for spans in grouped.values():
        rows = [y for y, _, _ in spans]
        blobs.append(
            _Blob(spans, sum(b - a for _, a, b in spans), rows[0], rows[-1], min(a for _, a, _ in spans),
                  max(b for _, _, b in spans))
        )  # fmt: skip
    return blobs


def _luminance(pixels: np.ndarray) -> np.ndarray:
    c = pixels / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def _rgb(colour: str) -> np.ndarray:
    return np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)


def _distance(pixels: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Each pixel's RGB distance from the segment ``a``-``b``: the sung word fades along it."""
    along = b - a
    length = float(along @ along)
    t = np.clip((pixels - a) @ along / length, 0, 1)[..., None] if length else 0.0
    return np.sqrt(((pixels - (a + t * along)) ** 2).sum(-1))


def _letters(pixels: np.ndarray, paint: _Paint) -> tuple[np.ndarray, int]:
    """The mask of the letters in ``pixels`` and its area: what wears a look's colours, without what reaches the
    band's edges (a floor tile, a shirt) or is too small to be a letter."""
    height, width = pixels.shape[:2]
    active = _rgb(paint.active) if paint.active else None
    near = np.min([_distance(pixels, _rgb(fill), active if active is not None else _rgb(fill))
                   for fill in paint.fills], axis=0)  # fmt: skip
    letters = np.zeros((height, width), dtype=bool)
    area = 0
    for blob in _blobs(near <= FILL_TOLERANCE):
        if blob.area >= MIN_BLOB and not blob.touches(height, width):
            area += blob.area
            for y, a, b in blob.runs:
                letters[y, a:b] = True
    return letters, area


def _counters(luminance: np.ndarray, letters: np.ndarray) -> int:
    """The pixels of the enclosed counters of ``letters`` that stand clear of the letters' tone."""
    height, width = letters.shape
    tone = float(np.median(luminance[letters]))
    total = 0
    for blob in _blobs(~letters):
        if (
            blob.touches(height, width)
            or not MIN_COUNTER <= blob.area <= MAX_COUNTER
            or blob.right - blob.left > MAX_COUNTER_SPAN
            or blob.bottom - blob.top >= MAX_COUNTER_SPAN
        ):
            continue
        inside = float(np.median(np.concatenate([luminance[y, a:b] for y, a, b in blob.runs])))
        if (max(inside, tone) + 0.05) / (min(inside, tone) + 0.05) >= COUNTER_CONTRAST:
            total += blob.area
    return total


@dataclass(frozen=True)
class Legibility:
    """What the frames of a reel showed: ``frames`` with letters of the ``sampled``, the pixels of the letters
    (``fill``) and of their open ``counters``."""

    frames: int
    sampled: int
    fill: int
    counters: int

    @property
    def ratio(self) -> float:
        return self.counters / self.fill if self.fill else 0.0

    @property
    def passes(self) -> bool:
        return self.frames >= MIN_FRAMES and self.ratio >= MIN_COUNTERS


def measure_frames(frames: Iterable[np.ndarray], paint: _Paint) -> Legibility:
    """The counter ratio of ``frames`` (RGB, height x width x 3, cropped to the caption band) in the look ``paint``,
    all frames pooled: one line short of round letters does not decide a reel."""
    used = sampled = fill = counters = 0
    for frame in frames:
        sampled += 1
        pixels = frame.astype(float)
        letters, area = _letters(pixels, paint)
        if area < MIN_FILL:
            continue
        used += 1
        fill += area
        counters += _counters(_luminance(pixels), letters)
    return Legibility(used, sampled, fill, counters)


def read_frames(
    video: Path, band: tuple[int, int], *, width: int | None = None, ffmpeg: str = "ffmpeg"
) -> Iterator[np.ndarray]:
    """One frame per second of ``video``, cropped to ``band``, as RGB arrays. The crop snaps to even rows: the
    decoder's chroma is shared between two."""
    top, bottom = band[0] - band[0] % 2, band[1] + band[1] % 2
    width = width if width is not None else video_size(video)[0]
    cmd = [ffmpeg, "-v", "error", "-i", str(video), "-vf", f"fps={FPS},crop=iw:{bottom - top}:0:{top}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]  # fmt: skip
    try:
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise CaptionGateError(f"cannot read the frames of {video}: {e}") from e
    size = (bottom - top) * width * 3
    for i in range(0, len(raw) - size + 1, size):
        yield np.frombuffer(raw, np.uint8, size, i).reshape(bottom - top, width, 3)


# -- the look a scene burns -----------------------------------------------------------------------------------------
class TrackLook(NamedTuple):
    """The look of a scene's burned caption track and the band it occupies."""

    fills: tuple[str, ...]
    active: str | None
    stroke: str | None
    stroke_width: float
    top: float
    bottom: float


def _parse(scene: Path) -> ET.Element:
    try:
        return ET.parse(scene).getroot()
    except (OSError, ET.ParseError) as e:
        raise CaptionGateError(f"cannot read {scene}: {e}") from e


def _number(value: str | None, default: float = 0.0) -> float:
    return float(value) if value else default


def _burned_track(root: ET.Element) -> ET.Element | None:
    named = {o.get("burnCaptions") for o in root.iter("output")} - {None}
    for track in root.iter("captionTrack"):
        if track.get("id") in named or (not named and track.get("mode", "burn") != "sidecar"):
            return track
    return None


def track_look(root: ET.Element, track: ET.Element) -> TrackLook:
    """The look ``track`` burns, as the scene writes it."""
    styles = {style.get("id"): style for style in root.iter("textStyle")}
    style, active = styles.get(track.get("style")), styles.get(track.get("activeStyle"))
    project = root.find("project")
    if style is None or project is None:
        raise CaptionGateError(f"caption track {track.get('id')} has no style or the scene no project")
    stroke, width = style.get("strokeColor"), _number(style.get("strokeWidth"))
    if not (stroke and width):  # a split outline (ADR 0048): ink text under the burned letters, the track's own stroke
        prefix = f"{track.get('id')}-outline-"
        split = next((t for t in root.iter("text") if t.get("id", "").startswith(prefix)), None)
        if split is not None:
            stroke, width = split.get("strokeColor"), _number(split.get("strokeWidth"))
    size, leading = _number(style.get("size"), 1), _number(style.get("lineHeight"), 1)
    y = track.get("y", "75%")
    height = _number(project.get("height"))
    top = float(y[:-1]) / 100 * height if y.endswith("%") else float(y)
    block = int(track.get("maxLines", "2")) * size * leading + 2 * width
    return TrackLook((_colour(style.get("color", "#FFFFFF")),), _colour(active.get("color", "")) if active is not None
                     else None, _colour(stroke) if stroke and width else None, width, top, top + block)  # fmt: skip


def _same_track(look: ApprovedLook, burned: TrackLook) -> bool:
    return (
        {_colour(c) for c in look.fills} == set(burned.fills)
        and (_colour(look.active) if look.active else None) == burned.active
        and (_colour(look.stroke) if look.stroke else None) == burned.stroke
        and look.stroke_width == burned.stroke_width
        and look.zone[0] <= burned.top < look.zone[1]
    )


def _layer_boxes(root: ET.Element, look: ApprovedLook) -> list[tuple[float, float]]:
    """The boxes of the text layers painted as ``look``, inside its zone."""
    painted = {}
    fills = {_colour(c) for c in look.fills}
    for text in root.iter("text"):
        stroke, width = text.get("strokeColor"), _number(text.get("strokeWidth"))
        if (
            _colour(text.get("color", "")) in fills
            and (_colour(stroke) if stroke and width else None) == (_colour(look.stroke) if look.stroke else None)
            and width == look.stroke_width
        ):
            painted[text.get("id")] = _number(text.get("height"))
    boxes = []
    for layer in root.iter("layer"):
        y = _number(layer.get("y"))
        if layer.get("asset") in painted and look.zone[0] <= y < look.zone[1]:
            boxes.append((y, y + painted[layer.get("asset")]))
    return boxes


def _pad(top: float, bottom: float) -> tuple[int, int]:
    return max(0, round(top) - BAND_PAD), round(bottom) + BAND_PAD


def band_of(scene: Path, look: ApprovedLook) -> tuple[int, int] | None:
    """The rows of ``scene``'s frame its captions occupy when they wear ``look``, else None."""
    root = _parse(scene)
    track = _burned_track(root)
    if look.drawn:
        return look.zone if track is None and root.find(".//text") is None else None
    if track is not None:
        burned = track_look(root, track)
        return _pad(burned.top, burned.bottom) if _same_track(look, burned) else None
    boxes = _layer_boxes(root, look)
    return _pad(min(b[0] for b in boxes), max(b[1] for b in boxes)) if boxes else None


def measure_reel(
    scene: Path,
    video: Path,
    look: ApprovedLook | None = None,
    *,
    read: Callable[..., Iterable[np.ndarray]] = read_frames,
) -> Legibility:
    """The counter ratio of a rendered reel, in ``look``, or without one in what its burned track wears. A look the
    scene does not wear is a :class:`CaptionGateError`."""
    if look is not None:
        band = band_of(scene, look)
        if band is None:
            raise CaptionGateError(f"{scene.name} does not wear the look {look.style}/{look.name}")
        return measure_frames(read(video, band), look)
    root = _parse(scene)
    track = _burned_track(root)
    if track is None:
        raise CaptionGateError(f"{scene.name} burns no caption track: name the look its layers wear")
    burned = track_look(root, track)
    return measure_frames(read(video, _pad(burned.top, burned.bottom)), burned)


# -- the gate -------------------------------------------------------------------------------------------------------
def check_reel(
    style: str,
    scene: Path,
    video: Path,
    *,
    looks: Iterable[ApprovedLook] = LOOKS,
    read: Callable[..., Iterable[np.ndarray]] = read_frames,
) -> list[str]:
    """Why the reel with this ``scene`` and rendered ``video`` may not be published, if any reason: its ``style``
    undeclared or without a recorded look, a burned stroke in the letters' own colour, a look that is not an
    approved one of its style, or letters whose counters the frames show shut."""
    if not style:
        return ["the release declares no style, so its caption look cannot be checked"]
    if not Path(scene).is_file():
        return [f"no scene at {scene}"]
    if not Path(video).is_file():
        return [f"no render at {video}"]
    own = [look for look in looks if look.style == style]
    if not own:
        return [f"no caption look is approved for the style {style!r}"]
    problems = []
    root = _parse(scene)
    track = _burned_track(root)
    if track is not None:
        burned = track_look(root, track)
        if burned.stroke in burned.fills:
            problems.append(f"the captions are stroked in the letters' own colour {burned.stroke}: counters close")
    worn = next((look for look in own if band_of(scene, look) is not None), None)
    if worn is None:
        names = ", ".join(look.name for look in own)
        return [*problems, f"the captions are not an approved look of {style} ({names})"]
    if not worn.approved:
        return [*problems, f"the look {style}/{worn.name} has not been approved: see its proof at {worn.proof}"]
    measured = measure_reel(scene, video, worn, read=read)
    if measured.frames < MIN_FRAMES:
        problems.append(
            f"letters found in only {measured.frames} of {measured.sampled} frames: the gate needs {MIN_FRAMES}"
        )
    elif not measured.passes:
        problems.append(f"the letters' counters are closed: ratio {measured.ratio:.4f}, minimum {MIN_COUNTERS}")
    return problems


def check_releases(
    releases: Mapping[str, Release],
    renders: Path,
    episodes: Path,
    *,
    grandfathered: Collection[str],
    looks: Iterable[ApprovedLook] = LOOKS,
    only: Collection[str] | None = None,
    read: Callable[..., Iterable[np.ndarray]] = read_frames,
) -> list[Drift]:
    """Every problem of the releases being published, as :class:`~srstudio.social.Drift`, in slug order: all of them,
    or the ones whose video is in ``only``. A slug in ``grandfathered`` was published before this gate and is not
    judged. A reel's frames are decoded only when its look is approved."""
    drift = []
    for slug, release in sorted(releases.items()):
        if slug in grandfathered or (only is not None and release.video_name not in only):
            continue
        scene = Path(episodes) / slug / release.scene_file
        video = Path(renders) / f"{release.video_name}.mp4"
        problems = check_reel(release.style, scene, video, looks=looks, read=read)
        drift += [Drift(release.video_name, problem) for problem in problems]
    return drift
