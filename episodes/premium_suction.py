#!/usr/bin/env python3
"""Premium Suction — Ink 06, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 premium_suction_audio.py PROJECT --font DIR   # voices, effect, timeline.json
    python3 premium_suction.py PROJECT                                           # → PROJECT/premium-suction.scene.xml

The robot vacuum's free trial has ended: suction is monthly, the kitchen premium, and what is free is the map of
the home, which it sells. The landlord bought it and liked the second bedroom, the closet. Shots: the vacuum on the
floor (:mod:`srstudio.ink_vacuum`), its map, the human close, and the phone (:mod:`srstudio.ink_phone`).
"""

import os

from _common import project_root
from instagram_posts import POSTS
from premium_suction_audio import CONTACT, MAPS, SCREENS, VACUUM
from srstudio import INK, Episode, EpisodeSpec, ink, ink_phone, ink_vacuum, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="premium-suction",
        number="06",
        title="Premium Suction — Ink 06",
        description="Square hand-drawn cartoon: a robot vacuum whose free trial has ended, a map of the home it "
        "sells, and the landlord who bought it. Native vector animation; ElevenLabs dialogue and sound effect.",
        root=ROOT,
        seed=1106,
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
            description="Black and white cartoon: a robot vacuum on a floor, its map of the home, a man in close-up "
            "and a phone with a text from the landlord; on-screen dialogue and external SRT captions."
        ),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")

MAX_PAGE = 40  # one page per line; the band wraps a long one to two lines
MIN_PAGE = 0.85  # the engine's legibility check wants a caption drawn for 20 frames at 24 fps (0.833 s)
MAP_VACUUM = (430, 700, 0.22)  # the vacuum on its map, in the bedroom, where the route ends
srt, burned = [], []
for take in t.takes:
    g = ep.shot(shots, take)
    if take.shot == "phone":
        ink_phone.phone_shot(cv, g, CONTACT, **SCREENS[take.id])
    elif take.shot.startswith("vacuum"):
        ink_vacuum.vacuum_shot(cv, g, take, close=take.shot == "vacuum-close", **VACUUM.get(take.id, {}))
    elif take.shot == "map":
        beat = dict(MAPS[take.id])
        if beat.get("trace") == "take":
            beat["trace"] = (0.2, round(take.duration - 0.3, 3))
        ink_vacuum.floor_map(cv, g, take, **beat)
        ink_vacuum.vacuum(cv, g, take, *MAP_VACUUM)
    else:
        ink.router_scene(cv, g, take)
    cues = (
        [(0, take.duration, take.text)]
        if take.is_effect
        else subtitles.chunk_words(take.words, take.duration, max_chars=MAX_PAGE, min_seconds=MIN_PAGE)
    )
    for start, end, text in cues:
        burned.append(ink.caption(cv, g, text, start=start, end=end, y=84, size=40 if take.is_effect else 48))
        srt.append((take.start + start, take.start + end, text))

ep.audio(take=lambda take: dict(pan={"human": -0.08, "vacuum": 0.08}.get(take.actor, 0.0), fadeIn=".003",
                                fadeOut=".008"))  # fmt: skip
subtitles.write_srt(ROOT / "premium-suction.srt", srt)
ep.hide_on_cover(*burned)  # the cover's own headline replaces them
ep.instagram(POSTS["premium-suction"])
ep.finish(ROOT / "premium-suction.scene.xml", ROOT / "qa" / "sdk-validation.json")
