#!/usr/bin/env python3
"""Not a Robot — Ink 03, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 not_a_robot_audio.py PROJECT --font DIR   # voices, effect, timeline.json
    python3 not_a_robot.py PROJECT                                          # → PROJECT/not-a-robot.scene.xml

One form before lunch. The captcha asks for traffic lights, then sad traffic lights, then every moment he felt
truly alive (nine identical laptops). He hesitates like a human and clicks like a robot, so the router welcomes
him home; and the captcha has one more question. Shots: the desk, the human close, the screen (the checkbox card
or the picture grid, :mod:`srstudio.ink_captcha`), and the router on its shelf from *The Router*.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from not_a_robot_audio import SCREENS
from srstudio import INK, Episode, EpisodeSpec, ink, ink_captcha, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="not-a-robot",
        number="03",
        title="Not a Robot — Ink 03",
        description="Square hand-drawn cartoon: one form before lunch, a captcha that gets personal and a router that "
        "welcomes its brother. Native vector animation; ElevenLabs dialogue and sound effect.",
        root=ROOT,
        seed=1029,
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
            description="Black and white cartoon: a man at a laptop, a captcha on his screen and a router on a "
            "shelf; on-screen dialogue and external SRT captions."
        ),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")

MIN_PAGE = 0.85  # the engine's legibility check wants a caption drawn for 20 frames at 24 fps (0.833 s)
srt, burned = [], []
for take in t.takes:
    g = ep.shot(shots, take)
    if take.shot == "screen":
        screen = dict(SCREENS[take.id])
        if "label" in screen:
            tick = screen.pop("tick", None)
            at = None if tick is None else round(take.speech_duration + 0.25, 3)
            ink_captcha.checkbox(cv, g, screen["label"], tick_at=at)
        else:
            ink_captcha.captcha(cv, g, **screen)
    else:
        ink.router_scene(cv, g, take)
    cues = (
        [(0, take.duration, take.text)]
        if take.is_effect
        else subtitles.chunk_words(take.words, take.duration, min_seconds=MIN_PAGE)
    )
    for start, end, text in cues:
        burned.append(ink.caption(cv, g, text, start=start, end=end, y=84, size=40 if take.is_effect else 48))
        srt.append((take.start + start, take.start + end, text))

ep.audio(take=lambda take: dict(pan={"human": -0.08, "router": 0.08}.get(take.actor, 0.0), fadeIn=".003",
                                fadeOut=".008"))  # fmt: skip
subtitles.write_srt(ROOT / "not-a-robot.srt", srt)
ep.hide_on_cover(*burned)  # the cover's own headline replaces them
ep.instagram(POSTS["not-a-robot"])
ep.finish(ROOT / "not-a-robot.scene.xml", ROOT / "qa" / "sdk-validation.json")
