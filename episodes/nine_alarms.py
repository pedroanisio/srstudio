#!/usr/bin/env python3
"""Nine Alarms — the sketch as data (see nine_alarms_data.py for the script).

python3 nine_alarms.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 nine_alarms.py PROJECT            # the silent master on the scripted timing
python3 nine_alarms.py PROJECT --voice    # the narrated master from the recording (nine_alarms_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from nine_alarms_data import (
    ACCESSIBILITY,
    BARE,
    DESCRIPTION,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    count,
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
    camera=lens,
    bare=BARE,
    overlay=count,
    loudness="-14",
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
