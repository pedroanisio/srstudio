#!/usr/bin/env python3
"""Ink 02 — The Router, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_router_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    python3 the_router.py PROJECT                                          # → PROJECT/the-router.scene.xml

The internet is down. The router knows exactly how to fix it; it would just rather the human did it.
Twenty takes cut as a shot sequence: the desk, the human close, the router on its shelf (normal and
close, with the hand that reboots it), and the wide room. Captions are burned per take and written to
an external SRT as well.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import INK, Episode, EpisodeSpec, Timeline, ink, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
SCREAM = Timeline.load(ROOT / "timeline.json").take("16")  # "YOU'RE A ROUTER!": the cover frame
ep = Episode(
    EpisodeSpec(
        slug="the-router",
        number="02",
        title="The Router — Ink 02",
        description="Square hand-drawn cartoon: the internet is down and the router would rather be rebooted by hand. "
        "Native vector animation; ElevenLabs dialogue and sound effects.",
        root=ROOT,
        seed=1028,
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
        poster=dict(time=round(SCREAM.start + 0.45, 3), path="the-router-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Black and white cartoon with on-screen dialogue and external SRT captions."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")

# What each router take does with its power and the hand (take ids from the script in the_router_audio.py).
ROUTER_BEATS = {
    "10": dict(hand_action="reach", hand_at=0.45),  # "Fine. Off." — the hand comes in for the button
    "11": dict(power="down", hand_action="press", hand_at=0.08),  # click; the LEDs step down, the fan winds down
    "12": dict(power="up", hand_action="leave", hand_at=0.5),  # "...and on." — the LEDs sweep back up
}

MIN_PAGE = 0.85  # the engine's legibility check wants a caption drawn for 20 frames at 24 fps (0.833 s)
srt = []
for take in t.takes:
    g = ep.shot(shots, take)
    beats = dict(ROUTER_BEATS.get(take.id, {}))
    if take.id == "19":  # "Connected. ... Oh, wait. No." — every LED goes dark on "Oh"
        oh = next(w for w in take.words if w["text"].lower().startswith("oh"))
        beats["drop_at"] = round(oh["start"], 3)
    ink.router_scene(cv, g, take, **beats)
    cues = (
        [(0, take.duration, take.text)]
        if take.is_effect
        else subtitles.chunk_words(take.words, take.duration, min_seconds=MIN_PAGE)
    )
    for start, end, text in cues:
        size = 66 if take.id == "16" else 40 if take.is_effect else 48
        ink.caption(cv, g, text, start=start, end=end, y=84, size=size)
        srt.append((take.start + start, take.start + end, text))

ep.audio(take=lambda take: dict(pan=-0.08 if take.actor == "human" else 0.08, fadeIn=".003", fadeOut=".008"))
subtitles.write_srt(ROOT / "the-router.srt", srt)
ep.instagram(POSTS["the-router"])
ep.finish(ROOT / "the-router.scene.xml", ROOT / "qa" / "sdk-validation.json")
