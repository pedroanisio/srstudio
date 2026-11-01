"""What is burned into a reel, read as a viewer reads it: rule 7 of the structural rules (ADR 0146).

The check named ``caption-grammar``: a burned window does not run across a sentence end. It has two faults, each read
from the scene and the reel's lines. :func:`srstudio.frame_gates.run_together` is a window that drops the stop, and
:func:`srstudio.frame_gates.broken_off` a window that keeps it and stops inside the next sentence. A window that holds
whole sentences with their stops passes.

:func:`refuse_captions` runs both when a reel builds, so a pilot or a reel with no delivery is held too, and
:func:`caption_defects` at a first delivery, where the list excuses nothing. A published reel keeps its frozen windows
as named rows of :data:`EXEMPTIONS`, in the shape of the anatomy rules.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping
from importlib import resources
from pathlib import Path

from . import anatomy_ledger, frame_gates
from .anatomy_ledger import Exemption, Note
from .errors import SrstudioError
from .releases import Release
from .social import Drift

__all__ = [
    "CAPTION_RUN",
    "EXEMPTIONS",
    "RULES",
    "TextRefusedError",
    "caption_defects",
    "caption_notes",
    "exemptions",
    "parse",
    "refuse_captions",
]

CAPTION_RUN = "caption-run"  # a burned window that runs across a sentence end (ADR 0146)
RULES = frozenset({CAPTION_RUN})
EXEMPTIONS = "text_published.json"


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
