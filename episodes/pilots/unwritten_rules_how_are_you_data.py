"""The Unwritten Rules, how are you: the talking-head pilot with Rafa as host, main trigger recognition.

The script as data.

Rafa, a clay man at his own worktop, explains the rules of "how are you" with a smile he is holding up by hand. Every
rule tells you it is fine, and every time the thing under his hand says otherwise: the mug says "(I think)", the phone
says 99+, the folder says PENDING. Rule three is that nobody asked. He says so, and then answers anyway, which breaks
rule one: he went out for bread, it was a hundred and eighty-seven dollars, and he does not know where the bread is. The
smile comes back on a cut. "Good."

Nothing is recorded: no voice is chosen, so this is a script and not a :class:`srstudio.sketch.Sketch`, which needs a
speaker with a voice. :data:`VOICE` stays ``None`` until the operator picks one of :data:`VOICE_CANDIDATES`.
:func:`validate` checks every word, mood, prop and framing, and the length the script comes to at :data:`PACE`.
"""

from __future__ import annotations

from dataclasses import dataclass

from srstudio import host_kit, rafa, rafa_host
from srstudio.errors import SrstudioError

SLUG = "unwritten-rules-how-are-you"
HOST = "rafa"
VOICE: str | None = None  # the operator's choice, with his look
PACE = 2.7  # spoken words a second, the estimate a length is checked at until a take measures it
SHORTEST, LONGEST = 20.0, 30.0
SIGN_OFF = "You know what you did."
HOOK_LABEL = "HOW ARE YOU HAS RULES"
FRAMINGS = ("medium", "close", "tight")


class ScriptError(SrstudioError, ValueError):
    """A beat this show cannot stage."""


@dataclass(frozen=True)
class Beat:
    """One line of the script: its ``id``, the words (a silent beat has none), his ``mood``, what his hand is on, the
    ``framing``, the seconds he holds after it, an ``insert`` that takes the frame for a moment, and the ``label``."""

    id: str
    line: str
    mood: str
    prop: str
    framing: str = "medium"
    hold: float = 0.0
    insert: str = ""
    label: str = ""


BEATS: tuple[Beat, ...] = (
    Beat("hook", "Nobody tells you how are you has rules.", "public-smile", "rafa-mug", label=HOOK_LABEL),
    Beat("one", "Rule one. You say good. Whatever happened.", "public-smile", "rafa-mug", label="RULE 1", hold=0.3),
    Beat("two", "Rule two. You can add busy.", "public-smile", "rafa-phone", label="RULE 2"),
    Beat("choice", "Busy sounds like a choice.", "public-smile", "rafa-phone", "close", hold=0.3),
    Beat("three", "Rule three. The one nobody admits.", "social-battery", "rafa-bills", label="RULE 3"),
    Beat(
        "walking", "They didn't ask. They're already walking away.", "social-battery", "rafa-bills", "close", hold=1.4
    ),
    Beat("break", "You didn't ask.", "social-battery", "rafa-bills", "tight", hold=0.5),
    Beat("bread", "I went out for bread.", "internal-meltdown", "rafa-tote"),
    Beat("price", "It was a hundred and eighty-seven dollars.", "internal-meltdown", "rafa-tote", insert="rafa-tote"),
    Beat("where", "I don't know where the bread is.", "internal-meltdown", "rafa-tote", "tight", hold=1.3),
    Beat("good", "Good.", "public-smile", "rafa-mug", hold=0.7),
    Beat("off", SIGN_OFF, "public-smile", "rafa-mug", "close"),
)
VOICE_CANDIDATES = (  # premade voices already used in this library; none has been auditioned for this part
    ("Chris", "iP95p4xoKVk53GoZ742B", "casual and down to earth, the man at the worktop; carries the deadpan rules"),
    (
        "Eric",
        "cjVigY5qzO86Huf0OWal",
        "smooth and friendly, a customer-service smile that has further to fall at the bread",
    ),
    (
        "Will",
        "bIHbv24MWmeRgasZH58o",
        "young and relaxed, cheerful denial; the closest to a man of 34 keeping it together",
    ),
)


def spoken_words() -> int:
    return sum(len(beat.line.split()) for beat in BEATS)


def estimated_seconds() -> float:
    """The script's length at :data:`PACE`, with its holds: an estimate until a take measures it."""
    return spoken_words() / PACE + sum(beat.hold for beat in BEATS)


def moods() -> tuple[tuple[float, str], ...]:
    """His mood from the second it starts, at :data:`PACE`, as :func:`srstudio.rafa_host.faces` takes it."""
    rows: list[tuple[float, str]] = []
    at = 0.0
    for beat in BEATS:
        if not rows or rows[-1][1] != beat.mood:
            rows.append((round(at, 3), beat.mood))
        at += len(beat.line.split()) / PACE + beat.hold
    return tuple(rows)


def validate(beats: tuple[Beat, ...] = BEATS) -> None:
    """Every beat is one the show can stage, and the script keeps the show's rules; a :class:`ScriptError` if not."""
    for beat in beats:
        host_kit.check_copy(beat.line)
        if beat.mood not in rafa.MOODS:
            raise ScriptError(f"{beat.id}: Rafa's moods are {tuple(rafa.MOODS)}, got {beat.mood!r}")
        for prop in (beat.prop, beat.insert):
            if prop and prop not in rafa.PROPS:
                raise ScriptError(f"{beat.id}: his props are {tuple(rafa.PROPS)}, got {prop!r}")
        if beat.framing not in FRAMINGS:
            raise ScriptError(f"{beat.id}: a framing is one of {FRAMINGS}, got {beat.framing!r}")
        if beat.hold < 0.0:
            raise ScriptError(f"{beat.id}: a hold is not negative, got {beat.hold!r}")
        if len(beat.label.split()) > 7:
            raise ScriptError(f"{beat.id}: a label holds seven words at most, got {beat.label!r}")
    if not beats[0].line.startswith("Nobody tells you"):
        raise ScriptError(f"the show opens on a Nobody Tells You claim, got {beats[0].line!r}")
    if [beat.label for beat in beats if beat.label.startswith("RULE")] != ["RULE 1", "RULE 2", "RULE 3"]:
        raise ScriptError("the show has three rules, in order")
    if beats[-1].line != SIGN_OFF:
        raise ScriptError(f"the show ends on its sign-off, got {beats[-1].line!r}")
    if not any(beat.hold >= 1.2 for beat in beats):
        raise ScriptError("a punchline needs a hold of at least 1.2 s before it")
    if not {beat.prop for beat in beats} <= set(rafa_host.PLACES):
        raise ScriptError("every prop needs a place on the worktop")
    length = sum(len(beat.line.split()) for beat in beats) / PACE + sum(beat.hold for beat in beats)
    if not SHORTEST <= length <= LONGEST:
        raise ScriptError(
            f"the show runs {SHORTEST} to {LONGEST} s, this comes to {length:.1f} s at {PACE} words a second"
        )
