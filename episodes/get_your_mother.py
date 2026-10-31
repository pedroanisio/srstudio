#!/usr/bin/env python3
"""Get Your Mother — the sketch as data (see get_your_mother_data.py for the script).

python3 get_your_mother.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 get_your_mother.py PROJECT            # the silent master on the scripted timing
python3 get_your_mother.py PROJECT --voice    # the narrated master from the recording (get_your_mother_audio.py)
"""

import sys

from _common import project_root
from get_your_mother_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, lens, validate
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
