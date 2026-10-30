"""What test_takes.py shares with other test modules."""

from srstudio import takes
from srstudio.compose import Chunk, Plan
from srstudio.voice import Voice, VoiceSettings

DEV = Voice(role="dev", id="dev123", name="Will")


SETTINGS = {"dev": VoiceSettings(0.45, 0.75, 0.3)}


BED_PLAN = Plan((Chunk("Bed", 6.0, ("instrumental", "light ukulele")),))


def script(**changes) -> takes.Script:
    base = dict(
        title="Test — Stick 99",
        seed=7,
        voices={"dev": DEV},
        settings=SETTINGS,
        takes=(
            takes.Take("01", "dev", "Repeat after me.", 0.2, shot="drive", mood="calm", extra={"beat": "vow"}),
            takes.Take("02", "dev", "Repeat after me.", 0.1, shot="push", speed=1.1),
            takes.Take("03", "sfx", "[BUZZ]", 0.1, shot="seat", prompt="a phone buzzing", seconds=1.0, longest=0.5),
        ),
        voice_note="premade voice Will",
        shots=("drive", "push", "seat"),
    )
    return takes.Script(**{**base, **changes})
