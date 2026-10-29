#!/usr/bin/env python3
"""Pay to Park — Ink 08: the voices, the effects and the take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 pay_to_park_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The human holds a coin up to a parking meter whose slot is taped over: SCAN TO PAY. Coins? How retro. Download the app,
create an account, a password with a capital, a symbol and a childhood memory. Biscuit. That memory is already in use.
Enable location; he is right in front of it. Minimum session two hours. Almost done: rate your parking experience, five
stars. Session started, and the tow truck lifts his car and drives off with it. He says thank you. Two premade voices:
the human (Chris, as in the earlier Ink episodes) and the meter (Laura), two effects, and a hold-music bed (:data:`BED`,
composed by the ElevenLabs Music API and pinned by its seed; speech-to-text must hear no words in it) that stops dead
when the car goes (:data:`CUT_AT`). The recording is :mod:`srstudio.takes`: one request per take, every line heard back
by speech-to-text, the voices confirmed by name, no retries. ``SCREENS`` gives the app on the phone in each app take,
``DISPLAYS`` the meter's reading in each kerb and meter take (``pay_to_park.py`` draws them with
:mod:`srstudio.ink_meter`); a cue is a word of the take's line, shown as it is said, or seconds into the take.
"""

from __future__ import annotations

import string
import sys
from dataclasses import dataclass

from srstudio import ink_meter, takes
from srstudio.compose import Chunk, Plan
from srstudio.ink_meter import AppRow
from srstudio.voice import Voice, VoiceSettings

SEED = 1108
TITLE = "Pay to Park — Ink 08"
FONT = ("PatrickHand-Regular.ttf", "font-license.txt")
VOICES = {
    "human": Voice(role="human", id="iP95p4xoKVk53GoZ742B", name="Chris"),
    "meter": Voice(role="meter", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
}
SETTINGS = {
    "human": VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.35, speed=1.06),
    "meter": VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.45, speed=1.05),
}
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "On hold",
                31.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "cheerful corporate phone hold music",
                    "steady kick on every beat",
                    "bright electric piano and a soft synth pad",
                    "polite, relentlessly upbeat",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=41108,
    bpm=120,
    gain_db=-20.0,
    fade=0.8,
)
BED_IN = 0.8  # seconds the hold music takes to come up at the start
CUT_AT = "13"  # the hold music stops dead as this take starts: the tow truck and "Thank you." play in silence
# kerb: the wide street; meter: the meter alone; app: the phone; doodle: his close-up; tow-tight: on the car and the
# truck for the lift; tow-wide: pulled back as they leave
SHOTS = ("kerb", "meter", "app", "doodle", "tow-tight", "tow-wide")

TAKES = (
    takes.Take(
        "01",
        "sfx",
        "[CLINK]",
        0.50,  # the taped slot, held before anyone speaks
        shot="kerb",
        prompt="A single coin tapped twice against tape stretched over a parking meter's coin slot, two dull "
        "plastic taps, dry, no voices, no music",
        seconds=0.8,
        longest=0.8,
        peak=0.45,
    ),
    takes.Take("02", "meter", "Coins? How retro.", 0.35, shot="meter", mood="happy"),
    takes.Take("03", "meter", "Download the app!", 0.60, shot="app", mood="happy"),
    takes.Take("04", "meter", "Create an account.", 1.00, shot="app", mood="happy"),
    takes.Take(
        "05",
        "meter",
        "Your password needs a capital, a symbol, and a childhood memory.",
        0.40,
        shot="app",
        mood="happy",
    ),
    # Biskit: operator-approved STT spelling, 2026-10-29, after two takes (1.06, 1.0).
    takes.Take("06", "human", "Biscuit.", 0.45, shot="doodle", mood="calm", speed=1.0, heard=("Biskit",)),
    takes.Take("07", "meter", "That memory is already in use.", 0.90, shot="app", mood="calm"),
    takes.Take("08", "meter", "Enable location.", 0.60, shot="app", mood="happy"),
    takes.Take("09", "human", "I'm right in front of you.", 0.40, shot="kerb", mood="frustrated"),
    takes.Take("10", "meter", "Minimum session: two hours.", 0.40, shot="meter", mood="happy"),
    takes.Take("11", "meter", "Almost done! Rate your parking experience!", 0.80, shot="app", mood="happy"),
    takes.Take("12", "meter", "Session started!", 0.80, shot="tow-tight", mood="happy"),  # the lift, then the cut
    takes.Take(
        "13",
        "sfx",
        "[TOW TRUCK]",
        1.40,  # the empty kerb, held before he speaks
        shot="tow-wide",
        prompt="A tow truck engine revving and pulling away down a street, a rattling chain, dry, no voices, no music",
        seconds=2.0,
        longest=2.0,
        peak=0.45,
    ),
    takes.Take("14", "human", "Thank you.", 1.40, shot="doodle", mood="calm"),
)

Cue = str | float  # a word of the take's line (from when it is said), or seconds into the take


@dataclass(frozen=True)
class Row:
    """A row of the app's form (:class:`srstudio.ink_meter.AppRow`), its times as cues."""

    text: str
    at: Cue = 0.0
    tick: Cue | None = None
    taken: Cue | None = None


APP = "ParkPal"
PASSWORD = "New password"
# What the app shows in each app take: its title, its rows, a bar that fills to the take's end, the stars' cue.
SCREENS: dict[str, dict] = {
    "03": dict(title=APP, rows=(Row("Installing ParkPal..."),), progress=True),
    "04": dict(
        title="Sign up",
        rows=(Row("Full name", tick=0.6), Row("Email", 0.3, tick=1.0), Row("Shoe size", "account", tick=1.5)),
    ),
    "05": dict(
        title=PASSWORD,
        rows=(
            Row("One capital", "capital", tick="symbol"),
            Row("One symbol", "symbol", tick="childhood"),
            Row("A childhood memory", "childhood"),
        ),
    ),
    "07": dict(
        title=PASSWORD,
        rows=(Row("One capital", tick=0.0), Row("One symbol", tick=0.0), Row("A childhood memory", taken="already")),
    ),
    "08": dict(title="Location", rows=(Row("Where are you?"), Row("Searching...", "location")), progress=True),
    "11": dict(title="Rate us!", rows=(Row("How was parking?", "rate"),), stars="experience"),
}
# The meter's display in each kerb, meter and tow take, (cue, reading).
DISPLAYS: dict[str, tuple[tuple[Cue, str], ...]] = {
    "01": ((0.0, "SCAN TO PAY"),),
    "02": ((0.0, "SCAN ME :)"),),
    "09": ((0.0, "LOCATING..."),),
    "10": ((0.0, "MIN 2 HOURS"),),
    "12": ((0.0, "SESSION ON"),),
    "13": ((0.0, "SESSION ON"),),
}
PUSH_IN = 1.15  # the opening kerb closes in on the taped slot while the coin taps, so its sticker reads
TOW_AFTER = 0.10  # seconds after "Session started!" ends: the hook takes the car


def taped_slot() -> tuple[float, float]:
    """Where the meter's taped slot lands in the opening kerb (:data:`srstudio.ink_meter.KERB_VIEW`), frame pixels:
    the push-in's fixed point."""
    scale, x, y = ink_meter.KERB_VIEW
    tape = (ink_meter.METER_X + 58, ink_meter.PAVEMENT - 500 + 180)  # ink_meter.meter's tape, on the meter's head
    return x + tape[0] * scale, y + (tape[1] - ink_meter.PAVEMENT) * scale


def word(text: str) -> str:
    return text.strip(string.punctuation + " ").lower()


def cue(words, at: Cue) -> float:
    """``at`` in seconds into the take: a number as it is, a word as the start of its first saying in ``words``
    (``{text, start, end}`` of the recorded take)."""
    if not isinstance(at, str):
        return float(at)
    for w in words:
        if word(w["text"]) == at:
            return float(w["start"])
    raise ValueError(f"the cue {at!r} is not a word of the take ({' '.join(w['text'] for w in words)!r})")


def screen(take) -> dict:
    """:func:`srstudio.ink_meter.app_screen`'s arguments for the recorded ``take``, its cues resolved."""
    state = SCREENS[take.id]
    rows = tuple(
        AppRow(
            r.text,
            cue(take.words, r.at),
            None if r.tick is None else cue(take.words, r.tick),
            None if r.taken is None else cue(take.words, r.taken),
        )
        for r in state["rows"]
    )
    progress = (0.0, take.duration) if state.get("progress") else None
    stars = cue(take.words, state["stars"]) if "stars" in state else None
    return dict(title=state["title"], rows=rows, progress=progress, stars=stars)


def readings(take) -> tuple[tuple[float, str], ...]:
    """The meter's display in the recorded ``take``, its cues resolved."""
    return tuple((cue(take.words, at), text) for at, text in DISPLAYS[take.id])


def tows(tight_speech: float, tight_duration: float) -> tuple[float, float]:
    """When the hook takes the car, in the tight take and in the wide one after the cut (before it, so negative)."""
    tow = tight_speech + TOW_AFTER
    return tow, tow - tight_duration


def script() -> takes.Script:
    return takes.Script(
        title=TITLE,
        seed=SEED,
        voices=VOICES,
        settings=SETTINGS,
        takes=TAKES,
        voice_note="ElevenLabs premade voices Chris and Laura; no reference-voice cloning. Two effects generated "
        "with ElevenLabs; instrumental hold-music bed composed with the ElevenLabs Music API.",
        shots=SHOTS,
        bed=BED,
        font=FONT,
    )


if __name__ == "__main__":
    sys.exit(takes.main(script()))
