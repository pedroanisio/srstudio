"""Short musical stings a reel can buy by name: one table of tested prompts instead of a new prompt in every script.

There is no music bed in a sketch, but a button of music is often the joke's last word. :func:`sting` turns a name from
:data:`STINGS` into an effect :class:`~srstudio.takes.Take`, with the seconds the sting needs and where its peak falls,
so the mix treats it like any other effect and the take is verified the same way.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import SrstudioError
from .takes import Take

__all__ = ["STINGS", "Sting", "StingError", "sting"]


class StingError(SrstudioError, ValueError):
    """A sting that is not in the table."""


@dataclass(frozen=True)
class Sting:
    """``tag`` is the effect take's text, ``prompt`` what is asked for, ``seconds`` how long it runs and ``peak`` the
    level (0 to 1) the take is set to: a button sits under the voices."""

    tag: str
    prompt: str
    seconds: float
    peak: float = 0.45


STINGS: dict[str, Sting] = {
    "cabin-ding": Sting("[DING]", "One soft clean airliner seat belt chime, a single bell tone, no voices", 0.8),
    "cabin-chime": Sting("[CHIME]", "A two-note airliner cabin announcement chime, high then low, no voices", 1.2),
    "rimshot": Sting("[RIMSHOT]", "A snare and cymbal rimshot, badum-tss, dry, no voices", 1.0),
    "sad-trombone": Sting("[WAH]", "A short sad trombone, four falling notes, no voices", 2.0),
    "tada": Sting("[TADA]", "A short bright brass fanfare hit, ta-da, no voices", 1.0),
    "dread": Sting("[DREAD]", "One low dramatic orchestral chord with a hit, no voices", 1.6),
    "wrong": Sting("[WRONG]", "A game show wrong answer buzzer, one low double buzz, no voices", 0.9),
}


def sting(number: int, name: str, hold: float, shot: str) -> Take:
    """The effect take ``number`` playing the sting ``name`` on ``shot``, then ``hold`` seconds."""
    if name not in STINGS:
        raise StingError(f"unknown sting {name!r}; known: {', '.join(STINGS)}")
    known = STINGS[name]
    return Take(f"{number:02d}", "sfx", known.tag, hold, shot=shot, prompt=known.prompt, seconds=known.seconds,
                longest=known.seconds, peak=known.peak)  # fmt: skip
