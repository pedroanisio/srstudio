#!/usr/bin/env python3
"""Long Goodbye — the sketch as data (see long_goodbye_data.py for the script).

python3 long_goodbye.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 long_goodbye.py PROJECT            # the silent master on the scripted timing
python3 long_goodbye.py PROJECT --voice    # the narrated master from the recording (long_goodbye_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from long_goodbye_data import ACCESSIBILITY, DESCRIPTION, LIT, NARRATION, SEED, SKETCH, TINTS, dress, lens, validate
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
    lit=LIT,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
