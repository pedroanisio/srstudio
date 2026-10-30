"""What test_interview.py shares with other test modules."""

from __future__ import annotations

from srstudio import interview as I
from srstudio.song import Singer
from test_song import engine, fake_env, tone  # noqa: F401  (fake_env is a fixture)

WILL = Singer("bIHbv24MWmeRgasZH58o", "Will", {"stability": 0.4, "similarity_boost": 0.75, "style": 0.2})


ERIC = Singer("cjVigY5qzO86Huf0OWal", "Eric", {"stability": 0.55, "similarity_boost": 0.75, "style": 0.1})


def make(**changes) -> I.Interview:
    kw: dict = dict(
        slug="test-interview",
        title="Test Interview",
        seed=11,
        voices={"manager": ERIC, "candidate": WILL},
        lines=[I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", "The chair.", "The chair.", 0.95)],
        effects=[I.Sound("squeak", "a chair squeak", seconds=0.8, longest=0.5, peak=0.5)],
        voice_note="test voices",
        room_tone_seed=12,
        reaction_after=0.3,
        reaction_hold=1.0,
        end_card=2.0,
    )
    kw.update(changes)
    return I.Interview(**kw)
