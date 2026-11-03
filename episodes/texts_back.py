#!/usr/bin/env python3
"""Texts Back — the sketch as data (see texts_back_data.py for the script).

python3 texts_back.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 texts_back.py PROJECT            # the silent master on the scripted timing
python3 texts_back.py PROJECT --voice    # the narrated master from the recording (texts_back_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from srstudio import toon_world
from srstudio.toon_sketch import Staging, build
from texts_back_data import ACCESSIBILITY, BARE, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, key, lens, validate

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    versions=PINS[SKETCH.slug],
    desk=toon_world.no_desk,
    camera=lens,
    bare=BARE,
    overlay=key,
    loudness="-14",
    bleed=True,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
