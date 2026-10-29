#!/usr/bin/env python3
"""Message Failed — Ink 04, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 message_failed_audio.py PROJECT --font DIR   # voices, effects, timeline.json
    python3 message_failed.py PROJECT                                          # → PROJECT/message-failed.scene.xml

A text about the boss goes to the boss. The router drops the Wi-Fi so it fails, then retries it, because it hates
failing; the boss types, agrees, and the router offers a reply. Shots: the phone (the chat, :mod:`srstudio.ink_phone`),
the human close, and the router on its shelf from *The Router*.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from message_failed_audio import CONTACT, ROUTER_BEATS, SCREENS
from srstudio import INK, Episode, EpisodeSpec, ink, ink_phone, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="message-failed",
        number="04",
        title="Message Failed — Ink 04",
        description="Square hand-drawn cartoon: a text about the boss goes to the boss, and the router that drops "
        "the Wi-Fi to stop it also hates failing. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=ROOT,
        seed=1104,
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
            description="Black and white cartoon: a phone chat with the boss, a man in close-up and a router on a "
            "shelf; on-screen dialogue and external SRT captions."
        ),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")

MAX_PAGE = 40  # "Wait. Did I just send that to my boss?" stays one page; the band wraps it to two lines
MIN_PAGE = 0.85  # the engine's legibility check wants a caption drawn for 20 frames at 24 fps (0.833 s)
srt, burned = [], []
for take in t.takes:
    g = ep.shot(shots, take)
    if take.shot == "phone":
        screen = dict(SCREENS[take.id])
        if screen.get("typing") == "take":
            screen["typing"] = (0.0, round(take.duration, 3))
        ink_phone.phone_shot(cv, g, CONTACT, **screen)
    else:
        ink.router_scene(cv, g, take, **ROUTER_BEATS.get(take.id, {}))
    cues = (
        [(0, take.duration, take.text)]
        if take.is_effect
        else subtitles.chunk_words(take.words, take.duration, max_chars=MAX_PAGE, min_seconds=MIN_PAGE)
    )
    for start, end, text in cues:
        burned.append(ink.caption(cv, g, text, start=start, end=end, y=84, size=40 if take.is_effect else 48))
        srt.append((take.start + start, take.start + end, text))

ep.audio(take=lambda take: dict(pan={"human": -0.08, "router": 0.08}.get(take.actor, 0.0), fadeIn=".003",
                                fadeOut=".008"))  # fmt: skip
subtitles.write_srt(ROOT / "message-failed.srt", srt)
ep.hide_on_cover(*burned)  # the cover's own headline replaces them
ep.instagram(POSTS["message-failed"])
ep.finish(ROOT / "message-failed.scene.xml", ROOT / "qa" / "sdk-validation.json")
