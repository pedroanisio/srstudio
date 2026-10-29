#!/usr/bin/env python3
"""Stick 04 — Unexpected Item: the self-checkout, Dev, the clerk and the store's music, as one take timeline.

    SRSTUDIO_ALLOW_CLOUD=1 python3 unexpected_item_audio.py PROJECT [--font DIR] [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

The recording is :mod:`srstudio.takes`: every take is one ElevenLabs request whose response is parsed and
verified, speech-to-text must hear the scripted words, each voice id must resolve to the premade voice it names,
and the effect is length-checked. The bed is composed by the ElevenLabs Music API (:data:`BED`, pinned by its
seed); speech-to-text must hear no words in it, and it is cut to the episode with a fade. The key comes from
``ELEVENLABS_API_KEY`` and is never written; the script runs only with ``SRSTUDIO_ALLOW_CLOUD=1``.
``tests/test_takes.py`` feeds the pipeline misheard takes, a bed with words and malformed scripts;
``tests/test_unexpected_item.py`` checks this script and the screens.
"""

from __future__ import annotations

import sys

from srstudio import stick, stick_shop, takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

SHOTS = ("wide", "screen", "dev", "clerk", "award", "button")
PLACE = "Please place the item in the bagging area."
UNEXPECTED = "Unexpected item in the bagging area."
UNIFORM = "#2f7d57"  # the store's apron
DEV = stick.Look()
DEV_HIRED = stick.Look(apron=UNIFORM)
CLERK = stick.Look(hair="bun", glasses=True, apron=UNIFORM)
CUSTOMER = stick.Look(hair="side-part", tie="#3d5a80")
NEG = ("vocals", "singing", "choir", "spoken word", "rap", "fade in")
BED = takes.Bed(
    Plan(
        (
            Chunk(
                "Aisle five",
                36.0,
                (
                    "120 BPM",
                    "4/4",
                    "instrumental",
                    "cheerful supermarket muzak",
                    "steady kick on every beat",
                    "bright electric piano and soft vibraphone",
                    "light bossa shaker",
                    "relentlessly pleasant",
                ),  # fmt: skip
                (),
                NEG,
            ),
        )
    ),
    seed=40411,
    bpm=120,
    gain_db=-17.0,
    fade=0.8,
)
SCRIPT = takes.Script(
    title="Unexpected Item — Stick 04",
    seed=1044,
    voices={
        "kiosk": Voice(role="kiosk", id="FGY2WhTYpPnrIDTdsKH5", name="Laura"),
        "dev": Voice(role="dev", id="bIHbv24MWmeRgasZH58o", name="Will"),
        "clerk": Voice(role="clerk", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    },
    settings={
        "kiosk": VoiceSettings(stability=0.85, similarity_boost=0.75, style=0.0, speed=0.95),
        "dev": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0),
        "clerk": VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.35, speed=1.0),
    },
    takes=(
        takes.Take("01", "kiosk", PLACE, 0.15, shot="screen", mood="calm"),
        takes.Take(
            "02",
            "sfx",
            "[BEEP]",
            0.05,
            shot="wide",
            prompt="A supermarket barcode scanner beep, one short bright electronic beep, dry, no voices, no music",
            seconds=0.6,
            longest=0.5,
            peak=0.4,
        ),
        takes.Take("03", "dev", "One avocado. Easy.", 0.20, shot="wide", mood="calm"),
        takes.Take("04", "kiosk", UNEXPECTED, 0.15, shot="screen", mood="calm"),
        takes.Take("05", "dev", "It's the avocado. You asked for it.", 0.15, shot="dev", mood="firm"),
        takes.Take("06", "kiosk", "Please remove the item.", 0.15, shot="wide", mood="calm"),
        takes.Take("07", "kiosk", PLACE, 1.30, shot="wide", mood="calm"),  # he stares at it, holding the avocado
        takes.Take("08", "kiosk", "Unexpected item. Please wait for assistance.", 0.20, shot="screen", mood="calm"),
        takes.Take("10", "dev", "I bought an avocado.", 0.20, shot="wide", mood="firm"),
        takes.Take(
            "11",
            "clerk",
            "You've scanned 200 items this month. Bagged them. Fixed three jams.",
            0.20,
            shot="clerk",
            mood="calm",
        ),  # fmt: skip
        takes.Take("12", "dev", "I shop here.", 1.20, shot="dev", mood="firm"),
        takes.Take("13", "clerk", "Congratulations. You're employee of the month.", 0.20, shot="award", mood="happy"),
        takes.Take("14", "dev", "Do I get paid?", 1.20, shot="dev", mood="calm"),
        takes.Take("15", "kiosk", UNEXPECTED, 0.50, shot="screen", mood="calm"),
        takes.Take("16", "dev", PLACE, 0.60, shot="button", mood="happy"),
    ),
    voice_note="ElevenLabs premade voices Laura, Will and Alice; no reference-voice cloning. Instrumental music "
    "bed composed with the ElevenLabs Music API.",
    shots=SHOTS,
    bed=BED,
)
ALARM = ("04", "08", "15")  # the takes in which the kiosk's lamp flashes, from their start
SCREENS: dict[str, tuple[stick_shop.Screen, ...]] = {  # what the kiosk shows, by take, from the take's start
    "01": (stick_shop.Screen(0.0, PLACE),),
    "02": (stick_shop.Screen(0.0, "Avocado  $2.49"),),
    "03": (stick_shop.Screen(0.0, "Avocado  $2.49"), stick_shop.Screen(1.2, PLACE)),
    "04": (stick_shop.Screen(0.0, UNEXPECTED, "error"),),
    "05": (stick_shop.Screen(0.0, UNEXPECTED, "error"),),
    "06": (stick_shop.Screen(0.0, "Please remove the item.", "help"),),
    "07": (stick_shop.Screen(0.0, PLACE),),
    "08": (stick_shop.Screen(0.0, "Please wait for assistance.", "help"),),
    "10": (stick_shop.Screen(0.0, "Please wait for assistance.", "help"),),
    "11": (stick_shop.Screen(0.0, "This month: 200 scanned · 200 bagged · 3 jams fixed"),),
    "12": (stick_shop.Screen(0.0, "This month: 200 scanned · 200 bagged · 3 jams fixed"),),
    "13": (stick_shop.Screen(0.0, "Employee of the month: DEV", "award", face=DEV_HIRED),),
    "14": (stick_shop.Screen(0.0, "Employee of the month: DEV", "award", face=DEV_HIRED),),
    "15": (stick_shop.Screen(0.0, UNEXPECTED, "error"),),
    "16": (stick_shop.Screen(0.0, PLACE),),
}


if __name__ == "__main__":
    sys.exit(takes.main(SCRIPT))
