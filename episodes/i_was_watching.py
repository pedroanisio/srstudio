#!/usr/bin/env python3
"""I Was Watching — a Toon sketch with Bruno and Mae (see i_was_watching_data.py for the script).

python3 i_was_watching.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 i_was_watching.py PROJECT            # the silent master on the scripted timing
python3 i_was_watching.py PROJECT --voice    # the narrated master: narration.json (i_was_watching_audio.py), the beats
                                             # moved to the voices' words, the mouths on their letters
"""

import sys

from _common import project_root
from i_was_watching_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, push, validate
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
    desk=toon_world.no_desk,
    camera=push,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
