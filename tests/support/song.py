"""What test_song.py shares with other test modules."""

from __future__ import annotations

from srstudio import song as S
from srstudio.music import Groove, Section

GROOVE = Groove(bpm=120)  # one bar = 2 s


def make_song(**changes) -> S.Song:
    kw: dict = dict(
        slug="test-song",
        title="Test Song",
        seed=7,
        groove=GROOVE,
        voices={
            "pip": S.Singer("bIHbv24MWmeRgasZH58o", "Will", {"stability": 0.3, "similarity_boost": 0.75, "style": 0.4})
        },
        lines=[S.Line("pip", "Sit down.", "SIT DOWN.", (0, 0)), S.Line("pip", "Work.", "WORK.", (1, 0), 1.08)],
        sections=[Section(0, 2)],
        effects=[S.Effect("scratch", "a record scratch", seconds=1.0, longest=0.5, peak=0.5, at=(1, 2))],
        lines_end=GROOVE.at(2),
        voice_note="test voices",
    )
    kw.update(changes)
    return S.Song(**kw)
