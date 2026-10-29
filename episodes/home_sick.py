#!/usr/bin/env python3
"""Home Sick — Ink 07, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 home_sick_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    python3 home_sick.py PROJECT                                           # → PROJECT/home-sick.scene.xml

The human's video doorbell will not let him in: the resident is home sick today. It asks the street's group chat
who he is, and his boss answers. Shots: the doorbell's camera on the human, the doorbell by the front door, normal
and close (:mod:`srstudio.ink_doorbell`), and the phone (:mod:`srstudio.ink_phone`).
"""

import os

from _common import project_root
from home_sick_audio import CLOCK, DOORBELL, LENS, NUMBER, SCREENS
from instagram_posts import POSTS
from srstudio import INK, Episode, EpisodeSpec, ink, ink_doorbell, ink_phone, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="home-sick",
        number="07",
        title="Home Sick — Ink 07",
        description="Square hand-drawn cartoon: a video doorbell that will not let a man in because the resident is "
        "home sick, the street's group chat and his boss. Native vector animation; ElevenLabs dialogue and sound "
        "effects.",
        root=ROOT,
        seed=1107,
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
            description="Black and white cartoon: a man with sunglasses on his forehead seen through a doorbell "
            "camera with a face box, the doorbell beside a front door, and a phone with a neighbourhood group chat "
            "and a text from his boss; on-screen dialogue and external SRT captions."
        ),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")

MAX_PAGE = 40  # one page per line; the band wraps a long one to two lines
MIN_PAGE = 0.85  # the engine's legibility check wants a caption drawn for 20 frames at 24 fps (0.833 s)
srt, burned = [], []
for take in t.takes:
    g = ep.shot(shots, take)
    if take.shot == "phone":
        ink_phone.phone_shot(cv, g, **SCREENS[take.id])
    elif take.shot.startswith("doorbell"):
        close = take.shot == "doorbell-close"
        ink_doorbell.doorstep(cv, g, take, close=close, number=NUMBER, **DOORBELL.get(take.id, {}))
    elif take.shot == "lens":
        ink_doorbell.doorbell_view(cv, g, take, tags=LENS[take.id], clock=CLOCK, shades=True)
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

ep.audio(take=lambda take: dict(pan={"human": -0.08, "doorbell": 0.08}.get(take.actor, 0.0), fadeIn=".003",
                                fadeOut=".008"))  # fmt: skip
subtitles.write_srt(ROOT / "home-sick.srt", srt)
ep.hide_on_cover(*burned)  # the cover's own headline replaces them
ep.instagram(POSTS["home-sick"])
ep.finish(ROOT / "home-sick.scene.xml", ROOT / "qa" / "sdk-validation.json")
