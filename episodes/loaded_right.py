#!/usr/bin/env python3
"""Loaded Right — the sketch as data (see loaded_right_data.py for the script).

python3 loaded_right.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 loaded_right.py PROJECT            # the silent master on the scripted timing
python3 loaded_right.py PROJECT --voice    # the narrated master from the recording (loaded_right_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from loaded_right_data import (
    ACCESSIBILITY,
    BARE,
    DESCRIPTION,
    FIGURES,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    lens,
    validate,
)
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
    desk=toon_world.no_desk,
    figures=FIGURES,
    camera=lens,
    bare=BARE,
    loudness="-14",
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
