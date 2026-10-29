#!/usr/bin/env python3
"""Logo Bigger — a Toon sketch with Rex and Fern (see logo_bigger_data.py for the script).

python3 logo_bigger.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 logo_bigger.py PROJECT            # the silent master on the scripted timing
python3 logo_bigger.py PROJECT --voice    # the narrated master: narration.json (logo_bigger_audio.py), the beats
                                      # moved to the voices' words, the keyboard, the phone and the sting heard
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from logo_bigger_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate
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
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()
