#!/usr/bin/env python3
"""Stick 09 — The Exit: Dev, Noor, the phone and a car-radio bed, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_exit_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names,
and each effect is length-checked. The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its
seed); speech-to-text must hear no words in it, and it is cut to the episode with a fade. The key comes from
``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes, a bed with words and malformed scripts;
``tests/test_the_exit.py`` checks this script and the staging below it.

Dev has missed the exit. A couple who have had this argument forty times run it in shorthand: "Your sister's
wedding." "Your mum's birthday." "The tent." "The tent." Dead air. "Sorry." "Sorry." Then it dawns on them: so
they're not going to her sister's. They are not going to her sister's. The phone in the mount buzzes, "Sis: where
are you??", and Noor puts it face down.

Both say "The tent." in two takes back to back (``hold`` 0.0): takes do not overlap, so "both at once" is one right
after the other. Noor says "my sister's", her own sister.
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_windshield, takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("two", "dev", "noor", "phone", "down")
HOOK = "—you missed the exit."
DEAD_AIR = 2.0  # the silence after "The tent.", the bed hushed under it
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Long drive",
                26.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "mellow soft-rock on a car radio",
                    "steady kick on every beat",
                    "warm electric piano and a clean guitar",
                    "easygoing, a little wistful",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=40909,
    bpm=120,  # at 96 with brushed drums, the beat measured about 226 bpm
    gain_db=-18.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="The Exit — Stick 09",
    seed=1209,
    voices={
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "noor": Voice(role="noor", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    },
    settings={
        "dev": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "noor": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
    },
    takes=(
        takes.Take("01", "noor", "You missed the exit.", 0.30, shot="two", mood="calm"),
        takes.Take("02", "dev", "Your sister's wedding.", 0.25, shot="dev", mood="firm"),
        takes.Take("03", "noor", "Your mum's birthday.", 0.25, shot="noor", mood="firm"),
        takes.Take("04", "dev", "The tent.", 0.0, shot="two", mood="firm", speed=1.1),
        takes.Take("05", "noor", "The tent.", DEAD_AIR, shot="two", mood="firm"),  # dead air; at 1.1 heard "The 10"
        takes.Take("06", "dev", "Sorry.", 0.35, shot="two", mood="calm"),  # long enough to read
        takes.Take("07", "noor", "Sorry.", 0.60, shot="two", mood="calm"),
        takes.Take("08", "dev", "So we're not going to your sister's.", 0.30, shot="two", mood="calm"),
        takes.Take("09", "noor", "We are not going to my sister's.", 0.70, shot="two", mood="happy"),
        takes.Take(
            "10",
            "sfx",
            "[BZZT]",
            0.20,  # the insert holds its text long enough to read (0.833 s)
            shot="phone",
            prompt="A smartphone vibrating twice in a dashboard phone mount, two short buzzes, dry, no voices, no "
            "music",
            seconds=1.0,
            longest=0.7,
            peak=0.45,
        ),
        takes.Take(
            "11",
            "sfx",
            "[THUNK]",
            2.80,
            shot="down",
            prompt="A smartphone placed face down on a car dashboard, one soft plastic tap, dry, no voices, no music",
            seconds=0.5,
            longest=0.4,
            peak=0.45,
        ),
    ),
    voice_note="ElevenLabs premade voices Will and Jessica; no reference-voice cloning. Two effects generated with "
    "ElevenLabs; instrumental music bed composed with the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)

# The staging, on each take's clock. Noor rides on the left (looking right at Dev is +x), Dev drives on the right.
F = stick.Face
AT_DEV, AT_NOOR, AHEAD, AT_PHONE = (1.0, 0.0), (-1.0, 0.0), (0.0, 0.1), (0.6, 0.5)
# take: [(seconds into the take, pose from stick_windshield.FRONT, face)]; a take without a row holds the last pose
PARTS: dict[str, dict[str, list[tuple[float, str, stick.Face]]]] = {
    "noor": {
        "01": [(0, "crossed", F("half", "raised", "flat", AT_DEV))],
        "03": [(0, "crossed", F("open", "angry", "flat", AT_DEV))],
        "04": [(0, "crossed", F("wide", "angry", "flat", AT_DEV))],
        "06": [(0, "slump", F("half", "flat", "flat", AHEAD))],
        "07": [(0, "sit", F("open", "worried", "flat", AT_DEV))],
        "08": [(0, "sit", F("open", "flat", "flat", AHEAD))],
        "09": [(0, "sit", F("open", "raised", "smile", AHEAD))],
        "11": [(0, "reach", F("half", "flat", "smirk", AT_PHONE)), (0.65, "sit", F("happy", "flat", "smile", AHEAD))],
    },
    "dev": {
        "01": [(0, "drive", F("open", "flat", "flat", AHEAD))],
        "02": [(0, "cite", F("open", "angry", "flat", AT_NOOR))],
        "03": [(0, "drive", F("half", "angry", "flat", AT_NOOR))],
        "04": [(0, "cite", F("wide", "angry", "flat", AT_NOOR))],
        "06": [(0, "drive", F("open", "worried", "flat", AT_NOOR))],
        "08": [(0, "drive", F("open", "raised", "flat", AT_NOOR))],
        "09": [(0, "drive", F("open", "raised", "smile", AHEAD))],
        "11": [(0, "drive", F("happy", "flat", "smile", AHEAD))],
    },
}
# take: (seconds after its speech ends, {who: (pose, face)}): the beat after a line lands, in the take's hold
VACANT, BEAMING = F("half", "flat", "flat", AHEAD), F("happy", "flat", "smile", AHEAD)
SETTLE: dict[str, tuple[float, dict[str, tuple[str, stick.Face]]]] = {
    "05": (0.25, {"noor": ("slump", VACANT), "dev": ("drive", VACANT)}),  # the dead air
    "07": (0.2, {"noor": ("sit", VACANT), "dev": ("drive", VACANT)}),
    "09": (0.2, {"noor": ("sit", BEAMING), "dev": ("drive", BEAMING)}),  # both smile at the road
}
DOWN = 0.55  # seconds into the last take: the phone lies face down, heard as the thunk
CUT = 0.95  # then the punch-in cuts back to the two-shot for the held ending
# shot: (focus, zoom, where the focus lands), in frame pixels of the uncut two-shot (stick.camera)
CAMERAS = {
    "two": ((540.0, 1023.0), 1.25, (540.0, 960.0)),  # the windshield centred, the dead hood below cut
    "dev": ((stick_windshield.SEATS[1], 960.0), 1.7, (540.0, 760.0)),  # a single on the seat's centre line
    "noor": ((stick_windshield.SEATS[0], 960.0), 1.7, (540.0, 760.0)),
    "down": ((480.0, 1100.0), 1.5, (540.0, 960.0)),  # Noor's hand, the dashboard and the phone
}
WORDS_Y = 1610  # the word captions sit over the hood, below the dashboard


def part(who: str, ids: list[str], take_id: str) -> list[tuple[float, str, stick.Face]]:
    """``who``'s rows in a take: its own, or the last pose before it, held still."""
    rows = PARTS[who]
    for prior in reversed(ids[: ids.index(take_id) + 1]):
        if prior in rows:
            return rows[prior] if prior == take_id else [(0, *rows[prior][-1][1:])]
    raise ValueError(f"no performance for {who} in take {take_id} or before it")


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))
