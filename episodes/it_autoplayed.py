#!/usr/bin/env python3
"""It Autoplayed (see it_autoplayed_data.py for the script).

python3 it_autoplayed.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 it_autoplayed.py PROJECT            # the silent master on the scripted timing
python3 it_autoplayed.py PROJECT --voice    # the narrated master from the recording (it_autoplayed_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from it_autoplayed_data import (
    ACCESSIBILITY,
    BARE,
    DESCRIPTION,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    overlay,
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
    bare=BARE,
    overlay=overlay,
    loudness="-14",
    bleed=True,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
