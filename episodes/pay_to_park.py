#!/usr/bin/env python3
"""Pay to Park — Ink 08, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 pay_to_park_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    python3 pay_to_park.py PROJECT                                           # → PROJECT/pay-to-park.scene.xml

The doodle wants to pay a parking meter with a coin; the meter sends him through its app, a step at a time, until
the session starts and the tow truck takes his car. Shots (:mod:`srstudio.ink_meter`): the kerb, wide; the meter
alone; the app on the phone; the doodle's close-up (:func:`srstudio.ink.closeup`); the tow, tight on the car and
the truck for the lift, then wide as they leave, the tow carried on across the cut.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from pay_to_park_audio import BED_IN, CUT_AT, PUSH_IN, readings, screen, taped_slot, tows
from srstudio import INK, Episode, EpisodeSpec, ink, ink_meter, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="pay-to-park",
        number="08",
        title="Pay to Park — Ink 08",
        description="Square hand-drawn cartoon: a parking meter that will not take coins sends a man through its "
        "app, step by step, until his session starts and his car is towed. Native vector animation; ElevenLabs "
        "dialogue and sound effects.",
        root=ROOT,
        seed=1108,
        style=INK,
        language="en-US",
        output_options=dict(
            codec="h264",
            container="mp4",
            fps="24",
            crf="18",
            preset="medium",
            pixelFormat="yuv420p",
            audioBitrate="192000",
            faststart=True,
            report="qa/render-report.json",
        ),
        accessibility=dict(
            description="Black and white cartoon: a man beside a parking meter whose coin slot is taped over, the "
            "meter's parking app on a phone asking for an account, a password and a rating, and a tow truck taking "
            "his car; on-screen dialogue and external SRT captions."
        ),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")


DUCK = -6.0
MAX_PAGE = 40  # one page per line; the band wraps a long one to two lines
MIN_PAGE = 0.85  # the engine's legibility check wants a caption drawn for 20 frames at 24 fps (0.833 s)
carried = None  # the tow, as the wide shot after the lift picks it up
srt, burned = [], []
for take in t.takes:
    g = ep.shot(shots, take)
    if take.shot == "kerb" and take.is_effect:  # the opening: closing in on the taped slot as the coin taps
        sx, sy = taped_slot()
        push = ink.group(cv, g, anchorX=sx, anchorY=sy, x=sx, y=sy)
        for axis in ("scaleX", "scaleY"):
            cv.keys(push, axis, [(0.0, 1.0), (take.duration, PUSH_IN)], kind="sine-in-out")
        ink_meter.kerb(cv, push, take, display=readings(take))
    elif take.shot == "kerb":
        ink_meter.kerb(cv, g, take, display=readings(take))
    elif take.shot == "meter":
        ink_meter.kerb(cv, g, take, close=True, display=readings(take))
    elif take.shot == "app":
        ink_meter.app_screen(cv, g, take, **screen(take))
    elif take.shot == "doodle":
        ink.closeup(cv, g, take)
    elif take.shot == "tow-tight":
        tow, carried = tows(take.speech_duration, take.duration)
        ink_meter.kerb(cv, g, take, tow=tow, view=ink_meter.TOW_TIGHT, display=readings(take))
    elif take.shot == "tow-wide":
        if carried is None:
            raise ValueError(f"take {take.id}: the wide tow follows the tight one")
        ink_meter.kerb(cv, g, take, tow=carried, view=ink_meter.TOW_WIDE, display=readings(take))
    else:
        raise ValueError(f"take {take.id}: unknown shot {take.shot!r}")
    cues = (
        [(0, take.duration, take.text)]
        if take.is_effect
        else subtitles.chunk_words(take.words, take.duration, max_chars=MAX_PAGE, min_seconds=MIN_PAGE)
    )
    for start, end, text in cues:
        burned.append(ink.caption(cv, g, text, start=start, end=end, y=84, size=40 if take.is_effect else 48))
        srt.append((take.start + start, take.start + end, text))

music = t.meta["music"]
(cut,) = [take.start for take in t.takes if take.id == CUT_AT]
ep.audio(
    take=lambda take: dict(pan={"human": -0.08, "meter": 0.08}.get(take.actor, 0.0), fadeIn=".003", fadeOut=".008"),
    # the hold music stops dead when the car goes: clipped at the cut, one frame's ramp so it does not click
    extra=[
        (
            "music",
            music["file"],
            dict(
                role="music",
                gain=str(music["gain_db"]),
                clipIn="0",
                clipOut=f"{cut:.6f}",
                fadeIn=str(BED_IN),
                fadeOut=f"{1 / 24:.6f}",
            ),
        )
    ],  # fmt: skip
    duck=DUCK,
)
subtitles.write_srt(ROOT / "pay-to-park.srt", srt)
ep.hide_on_cover(*burned)  # the cover's own headline replaces them
ep.instagram(POSTS["pay-to-park"])
ep.finish(ROOT / "pay-to-park.scene.xml", ROOT / "qa" / "sdk-validation.json")
