#!/usr/bin/env python3
"""Heard Back — a Toon sketch with Dana and Otto over a video interview (see heard_back_data.py for the script).

python3 heard_back.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 heard_back.py PROJECT            # the silent master on the scripted timing
python3 heard_back.py PROJECT --voice    # the narrated master: narration.json (heard_back_audio.py), the beats
                                           # moved to the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from heard_back_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, push, validate
from instagram_posts import PINS, POSTS
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
    camera=push,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
