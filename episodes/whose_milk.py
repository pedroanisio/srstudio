#!/usr/bin/env python3
"""Whose Milk? — a Toon sketch with Fern and Rex in the office kitchen (see whose_milk_data.py for the script).

python3 whose_milk.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 whose_milk.py PROJECT            # the silent master on the scripted timing
python3 whose_milk.py PROJECT --voice    # the narrated master: narration.json (whose_milk_audio.py), the beats
                                         # moved to the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.toon_sketch import Staging, build
from whose_milk_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
