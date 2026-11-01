#!/usr/bin/env python3
"""Firm Handshake — the sketch as data (see firm_handshake_data.py for the script).

python3 firm_handshake.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 firm_handshake.py PROJECT            # the silent master on the scripted timing
python3 firm_handshake.py PROJECT --voice    # the narrated master from the recording (firm_handshake_audio.py)
"""

import sys

from _common import project_root
from firm_handshake_data import (
    ACCESSIBILITY,
    BARE,
    DESCRIPTION,
    FIGURES,
    HEADS,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    lens,
    validate,
)
from instagram_posts import PINS, POSTS
from srstudio import toon_world
from srstudio.toon_sketch import Staging, build

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
    loudness="-14",
    desk=toon_world.no_desk,
    figures=FIGURES,
    camera=lens,
    heads=HEADS,
    bare=BARE,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
