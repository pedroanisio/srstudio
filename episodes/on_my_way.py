#!/usr/bin/env python3
"""On My Way — a Toon sketch with Pip and Gil over the phone (see on_my_way_data.py for the script).

python3 on_my_way.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 on_my_way.py PROJECT            # the silent master on the scripted timing
python3 on_my_way.py PROJECT --voice    # the narrated master: narration.json (on_my_way_audio.py), the beats
                                           # moved to the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from on_my_way_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, no_desk, push, validate
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
    desk=no_desk,
    camera=push,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
