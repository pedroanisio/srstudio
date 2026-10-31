#!/usr/bin/env python3
"""Baby Monitor — the sketch as data (see baby_monitor_data.py for the script).

python3 baby_monitor.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 baby_monitor.py PROJECT            # the silent master on the scripted timing
python3 baby_monitor.py PROJECT --voice    # the narrated master from the recording (baby_monitor_audio.py)
"""

import sys

from _common import project_root
from baby_monitor_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, lens, validate
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
    camera=lens,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
