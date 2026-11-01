"""What is burned into a reel, read as a viewer reads it: rules 7 and 8 of the structural rules (ADR 0146, ADR 0147).

The check named ``caption-grammar``: a burned window does not run across a sentence end. It has two faults, each read
from the scene and the reel's lines. :func:`srstudio.frame_gates.run_together` is a window that drops the stop, and
:func:`srstudio.frame_gates.broken_off` a window that keeps it and stops inside the next sentence. A window that holds
whole sentences with their stops passes.

:func:`refuse_captions` runs both when a reel builds, so a pilot or a reel with no delivery is held too, and
:func:`caption_defects` at a first delivery, where the list excuses nothing. A published reel keeps its frozen windows
as named rows of :data:`EXEMPTIONS`, in the shape of the anatomy rules.

The check named ``text-timing``: a text is on the frame for the reading minimum. The engine times each layer alone, so
a card carried across a cut reads as a short one (``docs/engine-bug-legibility-across-cuts.md``). Here a text is timed
as a viewer sees it, on the frames the engine evaluates: its words, from the first frame they are on to the last,
whichever layers draw them. A page of a burned caption track is read from the engine's own paging. It needs the engine
and no master, so ``srstudio build`` runs it after a build that has an engine, and :func:`timing_defects` at first
delivery.
"""

from __future__ import annotations

import functools
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator, Mapping
from importlib import resources
from pathlib import Path
from typing import NamedTuple

from . import anatomy_ledger, frame_gates, framegraph
from .anatomy_ledger import Exemption, Note
from .errors import SrstudioError
from .frame_gates import FrameGateError
from .framegraph import Drawing, Frame, FrameGraphError
from .releases import Release
from .social import Drift

__all__ = [
    "CAPTION_RUN",
    "EXEMPTIONS",
    "MINIMUM",
    "RULES",
    "TEXT_SHORT",
    "Run",
    "TextRefusedError",
    "after_build",
    "around",
    "caption_defects",
    "caption_notes",
    "exemptions",
    "pages",
    "parse",
    "refuse_captions",
    "runs",
    "short_notes",
    "timing_defects",
    "timing_notes",
]

CAPTION_RUN = "caption-run"  # a burned window that runs across a sentence end (ADR 0146)
TEXT_SHORT = "text-short"  # a text on the composited frames for less than the reading minimum (ADR 0147)
RULES = frozenset({CAPTION_RUN, TEXT_SHORT})
EXEMPTIONS = "text_published.json"
MINIMUM = 0.8333  # seconds: the limit the engine's LEG-SHORT reports
SCAN = 0.25  # seconds between frames of the first pass
LEGIBLE = 0.5  # of a text's opacity, and of its box on the frame and clear of what stands in front
BRIDGE = 2  # frames: a cut or a flip this short does not take a text off the screen
_SCALE = 6.0  # frame pixels to a mask pixel, for what covers a text
_SECONDS = re.compile(r"\d+(?:\.\d+)?")  # a start can be a percentage or a name on what is not a time


class TextRefusedError(SrstudioError, ValueError):
    """A reel whose burned text a rule refuses and no row of the list excuses."""


def parse(text: str) -> tuple[Exemption, ...]:
    """The rows in ``text``, which name these rules alone: the rest of the form is the anatomy list's."""
    return anatomy_ledger.parse_exemptions(text, RULES)


@functools.cache
def exemptions() -> tuple[Exemption, ...]:
    """The closed list of what is published against these rules."""
    return parse((resources.files("srstudio") / "assets" / EXEMPTIONS).read_text(encoding="utf-8"))


def caption_notes(document: bytes, project: Path) -> list[Note]:
    """A note for each window of the scene ``document`` that runs across a sentence of ``project``, a window once."""
    sentences = frame_gates.sentences_of(project)
    found = [*frame_gates.run_together(document, sentences), *frame_gates.broken_off(document, sentences)]
    notes = {r.window: Note(CAPTION_RUN, r.window, f"runs {r.before!r} into {r.after!r}") for r in found}
    return list(notes.values())


def refuse_captions(reel: str, document: bytes, project: Path) -> None:
    """Raise :class:`TextRefusedError` for each window of ``reel`` no row excuses."""
    faults = anatomy_ledger.unexcused(reel, caption_notes(document, project), exemptions())
    if faults:
        said = "; ".join(map(str, faults))
        raise TextRefusedError(f"{reel}: {said}: cut the window at the sentence end (ADR 0146)")


def caption_defects(releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str]) -> list[Drift]:
    """What :func:`srstudio.frame_gates.captions_run_together` does not list of rule 7, on the reels of a ``first``
    delivery: each window that breaks off inside the next sentence. On a first delivery the list excuses nothing, and
    a project with no scene has nothing to read."""
    drift: list[Drift] = []
    for slug, video in first.items():
        project = Path(episodes) / slug
        scene = project / releases[slug].scene_file
        if scene.is_file():
            found = frame_gates.broken_off(scene.read_bytes(), frame_gates.sentences_of(project))
            drift += [Drift(video, f"the caption {r.window!r} breaks off inside the next sentence") for r in found]
    return drift


class Run(NamedTuple):
    """The words ``text`` on the composited frames, from the frame at ``first`` to the frame at ``last``, seconds."""

    text: str
    first: float
    last: float

    def seconds(self, fps: float) -> float:
        return self.last - self.first + 1.0 / fps


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


def _legible(frame: Frame, index: int, drawn: Mapping[str, Drawing]) -> bool:
    """Whether node ``index`` of ``frame`` can be read: visible, on the frame and clear of what stands in front."""
    node = frame.nodes[index]
    if not node.text.strip() or not node.draw or node.opacity < LEGIBLE:
        return False
    box = frame.box(index, drawn)
    if box is None or box.area <= 0:
        return False
    inside = box.within(frame.width, frame.height)
    if inside.area < LEGIBLE * box.area:
        return False
    return float(frame.in_front({index}, drawn, inside, _SCALE).mean()) < LEGIBLE


def runs(frames: Iterable[Frame], drawn: Mapping[str, Drawing], fps: float) -> list[Run]:
    """Each stretch of ``frames`` that shows the same words, whichever layers draw them, so a card carried across a cut
    into another layer is one run. A gap of up to :data:`BRIDGE` frames does not end a run, and the frames need not be
    evenly spaced: a run ends at a frame that does not show it, later than that gap."""
    names: dict[str, str] = {}
    live: dict[str, tuple[float, float]] = {}
    found: list[Run] = []
    bridge = (BRIDGE + 0.5) / fps
    for frame in sorted(frames, key=lambda f: f.time):
        shown = {
            _key(node.text): node.text
            for index, node in enumerate(frame.nodes)
            if node.text and _legible(frame, index, drawn)
        }
        for key, (first, last) in list(live.items()):
            if key not in shown and frame.time - last > bridge:
                found.append(Run(" ".join(names[key].split()), first, last))
                del live[key]
        for key, text in shown.items():
            names.setdefault(key, text)
            live[key] = (live[key][0] if key in live else frame.time, frame.time)
    found += [Run(" ".join(names[key].split()), first, last) for key, (first, last) in live.items()]
    return sorted(found, key=lambda run: (run.first, run.text))


def short_notes(found: Iterable[Run], fps: float) -> list[Note]:
    """A note for each text whose longest run is under :data:`MINIMUM`: a text the viewer has already had long enough
    may come back for a beat."""
    longest: dict[str, Run] = {}
    for run in found:
        key = _key(run.text)
        if key not in longest or run.seconds(fps) > longest[key].seconds(fps):
            longest[key] = run
    return [
        Note(TEXT_SHORT, run.text, f"on screen {run.seconds(fps):.3f} s from {run.first:g} s, minimum {MINIMUM:g} s")
        for run in longest.values()
        if run.seconds(fps) + 1e-6 < MINIMUM
    ]


def around(found: Iterable[Run], fps: float, step: float) -> list[float]:
    """The frames at ``fps`` to read around each run that a pass ``step`` apart cannot call long, so its edges are
    known to the frame."""
    times: set[float] = set()
    for run in found:
        if run.last - run.first < MINIMUM:
            for edge, sign in ((run.first, -1), (run.last, 1)):
                times |= {round(edge + sign * i / fps, 6) for i in range(1, round(step * fps) + 2)}
    return sorted(t for t in times if t >= 0)


def _beats(root: ET.Element) -> set[float]:
    """Each time the scene can change what is on the frame between two frames of the first pass: a start, and a key
    of an opacity. A flash of text starts at one of these, however short it is."""
    found = [element.get("start", "") for element in root.iter()]
    for animate in root.iter("animate"):
        if animate.get("property") == "opacity":
            found += [key.get("time", "") for key in animate.iter("key")]
    return {float(time) for time in found if _SECONDS.fullmatch(time)}


def pages(engine: str | Path, scene: Path) -> Iterator[tuple[str, float, float]]:
    """Each page a burned caption track draws, its text and its seconds, as the engine's burn-in pages it. A caption
    track sits over the whole frame, so its page is on screen from its start to its end."""
    scene = Path(scene)
    command = [str(engine), "captions", scene.name]
    try:
        run = subprocess.run(command, cwd=scene.parent, capture_output=True, text=True, check=False)
    except OSError as e:
        raise FrameGraphError(f"cannot run the engine {engine}: {e}") from None
    if run.returncode != 0:
        raise FrameGraphError(f"{scene.name}: {run.stdout.strip()[:300] or run.stderr.strip()[:300]}")
    try:
        for track in json.loads(run.stdout)["tracks"]:
            if track["burn"]:
                yield from ((page["text"], float(page["start"]), float(page["end"])) for page in track["pages"])
    except (ValueError, KeyError, TypeError) as e:
        raise FrameGraphError(f"{scene.name}: not the engine's captions: {e!r}") from None


def timing_notes(scene: Path, engine: str | Path) -> list[Note]:
    """What the composited frames of ``scene`` show against rule 8: a pass every :data:`SCAN` seconds and at each beat,
    on the reel's frames, then the frames around what it may find short, so a time is to the frame and a long reel does
    not pay for every frame."""
    document = scene.read_bytes()
    root = frame_gates._root(document)
    project = root.find(".//project")
    if project is None:
        raise FrameGraphError(f"{scene.name}: no project to time a text against")
    fps = float(project.get("fps", "24"))
    drawn = framegraph.drawings(document)
    duration = frame_gates._duration(document)
    times = {round(round(t * fps) / fps, 6) for t in frame_gates.sample_times(duration, SCAN)}
    times |= {round((round(t * fps) + 1) / fps, 6) for t in _beats(root) if t + 1.0 / fps < duration}
    frames = list(framegraph.evaluate(engine, scene, sorted(times)))
    closer = [t for t in around(runs(frames, drawn, fps), fps, SCAN) if t not in times and t < duration]
    frames += list(framegraph.evaluate(engine, scene, closer))
    read = runs(frames, drawn, fps)
    read += [Run(" ".join(text.split()), first, last - 1.0 / fps) for text, first, last in pages(engine, scene)]
    return short_notes(read, fps)


def timing_defects(
    releases: Mapping[str, Release], episodes: Path, first: Mapping[str, str], engine: str | Path
) -> list[Drift]:
    """What the frames of each reel on its ``first`` delivery show against rule 8. On a first delivery the list excuses
    nothing, a project with no scene has nothing to read, and a scene the engine cannot read is refused."""
    drift: list[Drift] = []
    for slug, video in first.items():
        scene = Path(episodes) / slug / releases[slug].scene_file
        if not scene.is_file():
            continue
        try:
            drift += [Drift(video, str(note)) for note in timing_notes(scene, engine)]
        except FrameGraphError as e:
            raise FrameGateError(f"{video}: the text was not timed: {e}") from e
    return drift


def after_build(reel: str, scene: Path, engine: str | Path) -> list[Note]:
    """What the frames of the scene just built show against rule 8 and no row excuses: for ``srstudio build``."""
    return anatomy_ledger.unexcused(reel, timing_notes(scene, engine), exemptions())
