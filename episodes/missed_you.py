#!/usr/bin/env python3
"""Missed You — a Toon sketch with a parcel that never comes (see missed_you_data.py for the script).

python3 missed_you.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 missed_you.py PROJECT            # the silent master on the scripted timing
python3 missed_you.py PROJECT --voice    # the narrated master: narration.json (missed_you_audio.py), the beats
                                             # moved to the voices' words, the mouths on their letters
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from missed_you_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, push, validate
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
    camera=push,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
